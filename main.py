# --- 標準ライブラリ ---
import re
import os
import pathlib
import json
from datetime import datetime, timedelta, time, date
from zoneinfo import ZoneInfo
from time import perf_counter

# --- 外部ライブラリ ---
import streamlit as st
import ui_parts
import requests
from google import genai
from dotenv import load_dotenv

# --- 0. 設定と定数 ---
load_dotenv()

# モデルの選択肢（サイドバーに表示される順番）
#   - "local-" で始まるもの: Ollama のローカルモデル（"local-" を外した名前で呼び出す）
#   - それ以外: Gemini API（Google AI Studio）のモデル名
MODEL_OPTIONS = [
    "local-gemma4:26b",        # ローカル (Ollama) 26B版：高性能だが重い
    "local-gemma4:12b",        # ローカル (Ollama) 12B版：26Bより軽い中間サイズ
    "local-gemma4:latest",     # ローカル (Ollama) いちばん軽い
    "gemini-3.8-flash",        # API (Google AI Studio)
    "gemini-3.5-flash-lite",   # API (Google AI Studio)
]

GEMINI_MODEL = st.sidebar.selectbox("🤖 AIモデルを選択", MODEL_OPTIONS)
IS_LOCAL = GEMINI_MODEL.startswith("local-")
LOCAL_MODEL_NAME = GEMINI_MODEL.removeprefix("local-")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# モデルに応じて読み込むプロンプトを自動切り替え
if IS_LOCAL and os.path.exists("prompt_local.txt"):
    prompt_file = "prompt_local.txt"
else:
    prompt_file = "prompt.txt"

# 門番（セットアップチェック）
def check_env():
    # 1. ActivityWatchの起動確認
    try:
        requests.get("http://localhost:5600/api/0/ping", timeout=1)
    except requests.exceptions.RequestException:
        st.error("## ⚠️ ActivityWatch が起動していません")
        st.info("日記を生成するには、ActivityWatchを立ち上げておく必要があります。[公式サイトはこちら](https://activitywatch.net/)")
        st.stop()

    # 2. APIキーの確認（Gemini API のモデルを選んだときだけ必要）
    if not IS_LOCAL and not os.getenv("GEMINI_API_KEY"):
        st.warning("## ⚠️ APIキーが設定されていません")
        st.info("Gemini のモデルを使うには、`.env` ファイルに `GEMINI_API_KEY` を記入してください。"
                "ローカルLLM（local-...）を選べば、APIキーなしでも使えます。詳細はREADMEを確認してください。")
        st.stop()

# 起動時に真っ先に実行
check_env()

# デフォルトの保存先
DEFAULT_SAVE_PATH = os.getenv("SAVE_DIR", "./diaries")
SAVE_DIR = pathlib.Path(DEFAULT_SAVE_PATH)
SAVE_DIR.mkdir(parents=True, exist_ok=True)
ONELINE_FILENAME = "1行日記まとめ.md"

# 詳細を秘匿したいアプリの設定
SENSITIVE_APPS = {
    "WINWORD.EXE": "執筆作業（原稿）",
    "EXCEL.EXE": "事務作業（資料）",
    "WindowsTerminal.exe": "システム開発・設定",
    "iAWriter.exe": "創作活動",
    "chrome.exe": "ブラウジング（調査・執筆）",
    "msedge.exe": "ブラウジング（仕事関連）",
    "ms-teams.exe": "オンライン会議",
}

# AIに渡すときのアプリの表示名（ここにないものは ".exe" を外した名前になる）
APP_DISPLAY_NAMES = {
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "Code.exe": "VS Code",
    "WINWORD.EXE": "Word",
    "EXCEL.EXE": "Excel",
    "POWERPNT.EXE": "PowerPoint",
    "ms-teams.exe": "Teams",
    "WindowsTerminal.exe": "ターミナル",
    "claude.exe": "Claude",
    "Obsidian.exe": "Obsidian",
    "ollama app.exe": "Ollama",
    "Letsview.exe": "LetsView",
    "BeWidgets.TimeWidget.exe": "時計ウィジェット",
}

# 天気コード（WMO）の日本語表記
WEATHER_CODES = {
    0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り",
    45: "霧", 48: "霧（霧氷）",
    51: "弱い霧雨", 53: "霧雨", 55: "強い霧雨",
    56: "着氷性の霧雨", 57: "強い着氷性の霧雨",
    61: "弱い雨", 63: "雨", 65: "強い雨",
    66: "着氷性の雨", 67: "強い着氷性の雨",
    71: "弱い雪", 73: "雪", 75: "強い雪", 77: "霧雪",
    80: "にわか雨", 81: "強いにわか雨", 82: "激しいにわか雨",
    85: "にわか雪", 86: "強いにわか雪",
    95: "雷雨", 96: "雷雨（ひょう）", 99: "激しい雷雨（ひょう）",
}

# 予報APIで取れる過去の日数（公式の上限は92日。境目の取りこぼしを避けて少し手前で切り替える）
FORECAST_PAST_DAYS = 90

# Discord のメッセージIDの基準時刻（2015-01-01 00:00 UTC）
DISCORD_EPOCH_MS = 1420070400000
DISCORD_MAX_PAGES = 10  # 1回100件 × 最大10回 = 1日あたり最大1000件まで


# --- 1. ユーティリティ関数 ---

def get_logical_date():
    """夜型人間用：午前3時までは前日として扱う"""
    now = datetime.now()
    if now.hour < 3:
        return now.date() - timedelta(days=1)
    return now.date()

def get_local_tz():
    return ZoneInfo(os.getenv("TIMEZONE", "UTC"))

def get_day_range(target_date, local_tz):
    """日記の1日（午前3時〜翌午前3時）を、タイムゾーン付きで返す"""
    start = datetime.combine(target_date, time(3, 0, 0), tzinfo=local_tz)
    return start, start + timedelta(days=1)

def app_display_name(app):
    """プログラム名（chrome.exe など）を、人間向けの名前（Chrome など）にする"""
    if app in APP_DISPLAY_NAMES:
        return APP_DISPLAY_NAMES[app]
    return re.sub(r"\.exe$", "", app, flags=re.IGNORECASE)

def get_aw_summary(target_date):
    """ActivityWatchから活動ログを取得"""
    try:
        url = "http://localhost:5600/api/0/query/"
        local_start, local_end = get_day_range(target_date, get_local_tz())
        utc_start = local_start.astimezone(ZoneInfo("UTC"))
        utc_end = local_end.astimezone(ZoneInfo("UTC"))

        query = [
            'window_bucket = find_bucket("aw-watcher-window");',
            'window_events = query_bucket(window_bucket);',
            'events = merge_events_by_keys(window_events, ["app", "title"]);',
            'RETURN = sort_by_duration(events);'
        ]

        data = {
            "query": query,
            "timeperiods": [f"{utc_start.isoformat()}/{utc_end.isoformat()}"]
        }
        res = requests.post(url, json=data, timeout=5)

        if res.status_code == 200:
            events = res.json()[0]
            local_summary = []
            ai_totals = {}  # (表示名, タイトル) -> 合計秒数。匿名化で同じ名前になった行をまとめる
            apps_seen = set()

            for e in events[:20]:
                app = e['data']['app']
                if app == "unknown" or app in ["explorer.exe", "OptionalFeatures.exe", "steamwebhelper.exe"]:
                    continue
                if e['duration'] < 60:
                    continue

                raw_title = e['data']['title']
                duration = int(e['duration'] / 60)
                clean_title = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[email hidden]', raw_title)
                local_summary.append(f"・{app}: {clean_title} ({duration}分)")
                safe_title = f"（{SENSITIVE_APPS[app]}）" if app in SENSITIVE_APPS else clean_title
                key = (app_display_name(app), safe_title)
                ai_totals[key] = ai_totals.get(key, 0) + e['duration']
                apps_seen.add(app)

            ai_summary = [
                f"・{name}: {title} ({int(total / 60)}分)"
                for (name, title), total in sorted(ai_totals.items(), key=lambda x: -x[1])
            ]
            return {
                "ai": "\n".join(ai_summary) if ai_summary else "活動ログなし",
                "local": "\n".join(local_summary) if local_summary else "活動ログなし",
                "apps": sorted(apps_seen),
            }
        return {"ai": "取得エラー", "local": "取得エラー", "apps": []}
    except Exception as e:
        return {"ai": f"接続不可 ({type(e).__name__})", "local": f"接続不可 ({e})", "apps": []}

def time_of_day_label(hour):
    """時刻（0〜23時）を、AIが読みやすい時間帯の言葉にする
    ※ 日記の1日は午前3時で区切るので、0〜3時は「その日の最後」にあたる"""
    if hour < 3:
        return "深夜・日付が変わった直後"
    if hour < 5:
        return "明け方"
    if hour < 10:
        return "朝"
    if hour < 14:
        return "昼"
    if hour < 18:
        return "夕方"
    return "夜"

def datetime_to_snowflake(dt):
    """時刻を Discord のメッセージID（snowflake）の形に変換する"""
    ms = int(dt.timestamp() * 1000)
    return max(ms - DISCORD_EPOCH_MS, 0) << 22

def get_discord_messages(target_date):
    """Discordから、指定した日（午前3時〜翌午前3時）のメッセージを取得"""
    token = os.getenv("DISCORD_TOKEN")
    # 古い .env の書き方（CHANNEL_ID）でも読めるようにしておく
    channel_id = os.getenv("DISCORD_CHANNEL_ID") or os.getenv("CHANNEL_ID")
    if not token or not channel_id:
        return "Discord設定（TOKEN/ID）が未設定です。"

    local_tz = get_local_tz()
    start, end = get_day_range(target_date, local_tz)
    try:
        headers = {"Authorization": f"Bot {token}"}
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        # その日の午前3時ちょうどのIDを計算し、そこから後ろを取得する
        # （最新から順にさかのぼらないので、数日前の日記でも取りこぼさない）
        after_id = max(datetime_to_snowflake(start) - 1, 0)

        collected = []
        for _ in range(DISCORD_MAX_PAGES):
            res = requests.get(url, headers=headers,
                               params={"after": str(after_id), "limit": 100}, timeout=10)
            if res.status_code != 200:
                return f"Discordエラー: {res.status_code}"
            batch = res.json()
            if not batch:
                break

            reached_end = False
            for m in batch:
                msg_time = datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00'))
                if msg_time >= end:
                    reached_end = True
                elif msg_time >= start and m.get('content'):
                    collected.append((msg_time, m['content']))

            after_id = max(int(m['id']) for m in batch)
            if reached_end or len(batch) < 100:
                break

        collected.sort(key=lambda x: x[0])
        texts = []
        for t, c in collected:
            local_t = t.astimezone(local_tz)
            texts.append(f"[{local_t.strftime('%m/%d %H:%M')} {time_of_day_label(local_t.hour)}] {c}")
        return "\n".join(texts) if texts else "指定した日のつぶやきはありません。"
    except Exception as e:
        return f"Discord取得失敗: {type(e).__name__}"

def format_weather(daily):
    """Open-Meteo の daily データを1行の文字列にする"""
    code = daily["weather_code"][0]
    if code is None:
        return "天気データなし"
    desc = WEATHER_CODES.get(code, "不明/その他")
    t_max = daily["temperature_2m_max"][0]
    t_min = daily["temperature_2m_min"][0]
    return f"{desc}（最高 {t_max}℃ / 最低 {t_min}℃）"

def get_weather(target_date):
    """Open-Meteoから天気を取得（3か月より前の日付は過去天気APIを使う）"""
    try:
        city = os.getenv("CITY_NAME", "Tokyo")
        geo_res = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ja", "format": "json"},
            timeout=5,
        ).json()
        if not geo_res.get("results"):
            return f"天気エラー: {city} が見つかりません"
        lat, lon = geo_res["results"][0]["latitude"], geo_res["results"][0]["longitude"]

        days_ago = (date.today() - target_date).days
        if days_ago > FORECAST_PAST_DAYS:
            base_url = "https://archive-api.open-meteo.com/v1/archive"
        else:
            base_url = "https://api.open-meteo.com/v1/forecast"

        date_str = target_date.isoformat()
        w_res = requests.get(
            base_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": date_str,
                "end_date": date_str,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
            },
            timeout=10,
        ).json()
        if "daily" not in w_res:
            return f"天気データ取得失敗 ({w_res.get('reason', '不明なエラー')})"
        return format_weather(w_res["daily"])
    except Exception as e:
        return f"天気データ取得失敗 ({e})"

# --- 記憶管理の関数 ---
MEMORY_FILE = pathlib.Path("./memory_db.json")

def load_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(memory_data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=2)

def get_memory_lines(memory_data, start, end):
    """記憶のうち、start〜end（両端を含む）の日付のものだけを古い順に返す"""
    lines = []
    for d in sorted(memory_data.keys()):
        try:
            day = date.fromisoformat(d)
        except ValueError:
            continue
        if start <= day <= end:
            lines.append(f"{d}: {memory_data[d]}")
    return lines

def update_oneline_md(memory_data):
    """Obsidian用「1行日記まとめ.md」の更新"""
    content = "# 📅 1行日記まとめ\n\n"
    for d in sorted(memory_data.keys()):
        content += f"- **{d}**: {memory_data[d]}\n"
    oneline_path = SAVE_DIR / ONELINE_FILENAME
    with open(oneline_path, "w", encoding="utf-8") as f:
        f.write(content)

# --- AI呼び出しの関数 ---

def generate_text(prompt, temperature=0.1, max_tokens=1500):
    """選択中のモデル（ローカル or Gemini API）で文章を生成する"""
    if IS_LOCAL:
        import ollama  # ローカルモデル用にインポート
        client = ollama.Client(host=OLLAMA_BASE_URL)
        response = client.chat(
            model=LOCAL_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            think=False,  # 思考モードをオフにして、日記以外の独り言が混ざらないようにする
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": 8192,  # 一度に扱える量。小さいと指示を忘れて脱線する
                "num_gpu": 20,
            },
        )
        return response["message"]["content"]

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text or ""

def format_duration(seconds):
    """秒数を「1分52秒」のような表記にする"""
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}分{secs:02d}秒" if minutes else f"{secs}秒"

def build_banned_link_words(apps):
    """リンクにしても意味のない、機械的なラベルの一覧を作る
    （プログラム名そのもの・匿名化で伏せた分類名とその部分）
    ※ Chrome や Obsidian のような人間向けの名前は対象外（リンクするかどうかはAIに任せる）"""
    words = set()
    for app in apps:
        words.add(app)
        stem = re.sub(r"\.exe$", "", app, flags=re.IGNORECASE)
        if stem != app_display_name(app):  # 例: ms-teams（表示名は Teams）
            words.add(stem)
    for label in SENSITIVE_APPS.values():
        words.add(label)
        m = re.match(r"(.+?)（(.+)）$", label)  # 例: ブラウジング（調査・執筆）
        if m:
            words.update([m.group(1), m.group(2)])
    return words

def remove_junk_links(text, banned_words):
    """[[ ]] のうち、プログラム名や伏せた分類名のものだけ括弧を外す（数の上限はつけない）"""
    def fix(m):
        target, alias = m.group(1), m.group(2)
        shown = alias[1:] if alias else target
        t = target.strip()
        if t in banned_words or re.search(r"\.exe$", t, flags=re.IGNORECASE):
            return shown
        return m.group(0)
    return re.sub(r"\[\[([^\]|]+)(\|[^\]]*)?\]\]", fix, text)

def split_diary_and_summary(text):
    """[DIARY] と [SUMMARY] の形式で返ってきた文章を、本文と要約に分ける"""
    m = re.search(r"\[DIARY\](.*?)\[SUMMARY\](.*)", text, re.S)
    if not m:
        return text.strip(), ""
    diary = m.group(1).strip()
    summary_lines = [line.strip() for line in m.group(2).strip().splitlines() if line.strip()]
    return diary, (summary_lines[0] if summary_lines else "")

# --- 2. 画面構成 ---
st.set_page_config(page_title="My Auto Diary", page_icon="🌙", layout="centered")
ui_parts.apply_global_style()

logical_now = get_logical_date()
ui_parts.render_header(logical_now)
ui_parts.render_sidebar_status(logical_now)

st.sidebar.header("⚙️ 設定")
target_date = st.sidebar.date_input("📅 日記の日付", value=logical_now)

tab1, tab2 = st.tabs(["📝 今日を書く", "📚 過去を振り返る"])

with tab1:
    if st.sidebar.button("✨ データを集計", key="collect_data_btn"):
        with st.spinner("最新データを取得中..."):
            # 各種データの取得
            aw_result = get_aw_summary(target_date)
            new_dc = get_discord_messages(target_date)
            new_weather = get_weather(target_date)

            # 1. 表示用のステート保存
            st.session_state.aw_ai = aw_result["ai"]
            st.session_state.aw_local = aw_result["local"]
            st.session_state.aw_apps = aw_result["apps"]
            st.session_state.dc = new_dc
            st.session_state.weather = new_weather
            st.session_state.is_collected = True

            # 2. 編集用テキストエリアのStateに直接流し込む
            # これで、再集計した時にテキストエリアの中身も即座に最新になる
            st.session_state["edit_aw_logs"] = aw_result["ai"]
            st.session_state["edit_dc_logs"] = new_dc

    weather_data = st.session_state.get("weather", "（未取得）")
    aw_show = st.session_state.get("aw_local", "（未取得）")
    dc_data = st.session_state.get("dc", "（未取得）")

    ui_parts.display_status_info(target_date, weather_data, aw_show, dc_data)
    memo = st.text_area("✍️ 付け加えたいこと", placeholder="今日あったことや、AIに伝えたいことを書いてください。",
                        height=150, key="memo_input")

    if st.session_state.get("is_collected"):
        edited_aw, edited_dc = ui_parts.render_review_area(
            st.session_state.get("aw_ai", "（未取得）"), dc_data
        )

        if st.button("🌟 AIに日記を書いてもらう"):
            # --- ローカルモデル選択時のOllama起動チェック ---
            if IS_LOCAL:
                try:
                    requests.get(OLLAMA_BASE_URL, timeout=1)
                except requests.exceptions.RequestException:
                    st.warning("⚠️ Ollamaが起きていないみたい。ローカルLLMを使う場合は、Ollamaアプリを立ち上げるか、ターミナルで `ollama serve` を実行してからもう一度試してみてね。")
                    st.stop()  # エラーを出さずにここで安全に処理を止める
            # ---------------------------------------------
            with st.spinner("AIが執筆中..."):
                try:
                    with open(prompt_file, "r", encoding="utf-8") as f:
                        instruction = f.read()

                    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                    weekday_str = weekdays[target_date.weekday()]
                    perfect_date = f"{target_date.year}年{target_date.month}月{target_date.day}日（{weekday_str}曜日）"

                    # 記憶の読み込み（日記の日付の前日までの7日分）
                    memory_db = load_memory()
                    memory_lines = get_memory_lines(
                        memory_db, target_date - timedelta(days=7), target_date - timedelta(days=1)
                    )
                    memory_text = "\n".join(memory_lines) if memory_lines else "過去の記録はまだありません。"

                    # 編集後のログを format に渡す
                    full_prompt = instruction.format(
                        target_date=perfect_date,
                        weather_data=weather_data,
                        aw_data=edited_aw,  # 手動編集したAWログ
                        dc_data=edited_dc,  # 手動編集したDiscordログ
                        memo=memo,
                        weekly_memory=memory_text
                    )

                    # 1. メイン日記の生成（ここから時間を計る）
                    started = perf_counter()
                    raw_text = generate_text(full_prompt, temperature=0.1, max_tokens=1500)
                    diary_text, summary_text = split_diary_and_summary(raw_text)
                    diary_text = remove_junk_links(
                        diary_text, build_banned_link_words(st.session_state.get("aw_apps", []))
                    )
                    st.session_state.result = diary_text

                    # 2. 今日のハイライトを1行で抽出（日記と一緒に返ってこなかった場合だけ）
                    if not summary_text:
                        summary_prompt = f"""以下は今日の日記です。この日の「主要な活動」と「体調や気分の変化」を、
事実ベースで簡潔に1行（50文字以内）で記録してください。
※「明日は〜する」という予定よりも、「今日は〜だった」という事実を優先してください。
※「おなかいたい」等の日常的なつぶやきは、深刻な体調不良ではなく等身大で表現してください。
※要約の1行だけを出力してください。

{diary_text}
"""
                        summary_text = generate_text(summary_prompt, temperature=0.1, max_tokens=100).strip()
                        summary_text = summary_text.splitlines()[0].strip() if summary_text else ""

                    st.session_state.gen_seconds = perf_counter() - started
                    st.session_state.gen_model = GEMINI_MODEL

                    # --- 記憶の保存処理 ---
                    if summary_text:
                        memory_db[target_date.isoformat()] = summary_text
                        save_memory(memory_db)
                        update_oneline_md(memory_db)

                except Exception as e:
                    st.error(f"エラー: {e}")

    if "result" in st.session_state:
        ui_parts.render_diary(st.session_state.result, target_date)
        if "gen_seconds" in st.session_state:
            st.caption(f"⏱️ {st.session_state.gen_model} で {format_duration(st.session_state.gen_seconds)} かかりました")

        if st.button("💾 ファイルに保存する"):
            file_name = f"{target_date.isoformat()}.md"
            file_path = SAVE_DIR / file_name

            # 「付け加えたいこと」欄の原文（空のときは出力しない）
            final_memo = st.session_state.get("memo_input", "").strip()
            memo_block = f"\n### ✍️ 当日のメモ\n```text\n{final_memo}\n```\n" if final_memo else ""

            gen_time_note = (f"（生成時間: {format_duration(st.session_state.gen_seconds)}）"
                             if "gen_seconds" in st.session_state else "")

            # content構成：日記本文、モデル署名、詳細ログ、メモ
            content = f"""# {target_date}

{st.session_state.result}

---
### 🤖 使用モデル
`{st.session_state.get("gen_model", GEMINI_MODEL)}`{gen_time_note}

### 📊 ログ（詳細）
{st.session_state.get("aw_local", "ログなし")}

### 💬 Discord
```text
{dc_data}
```
{memo_block}"""
            # ファイル書き込み
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            st.success(f"『{file_name}』を保存しました！")
            ui_parts.cat_run()

            # 日曜日の週次まとめ
            if target_date.weekday() == 6:
                with st.spinner("日曜日のため、1週間の総括を生成中..."):
                    memory_db = load_memory()
                    # その週の月曜日〜日曜日（今日）の記録
                    memory_lines = get_memory_lines(memory_db, target_date - timedelta(days=6), target_date)
                    memory_text = "\n".join(memory_lines) if memory_lines else "（記録なし）"

                    archive_prompt = f"以下の1週間の記録を元に、今週の総括を3行でまとめてください。\n\n{memory_text}"
                    archive_text = generate_text(archive_prompt, temperature=0.2, max_tokens=300)

                    year, week_num, _ = target_date.isocalendar()
                    archive_filename = f"{year}-W{week_num:02d}_Summary.md"
                    archive_content = f"# {year}年 第{week_num}週のまとめ\n\n## AI総括\n{archive_text}\n\n## ハイライト\n{memory_text}"

                    with open(SAVE_DIR / archive_filename, "w", encoding="utf-8") as f:
                        f.write(archive_content)
                    st.success("🎊 週次アーカイブを保存しました！")

with tab2:
    st.subheader("これまでの記録")
    if SAVE_DIR.exists():
        files = sorted(SAVE_DIR.glob("*.md"), reverse=True)
        # 1行日記まとめファイルは選択肢から除外
        files = [f for f in files if f.name != ONELINE_FILENAME]
        if files:
            selected_file = st.selectbox("読む日記を選んでください", files, format_func=lambda x: x.stem)
            with open(selected_file, "r", encoding="utf-8") as f:
                st.markdown("---")
                st.markdown(f.read())
        else:
            st.write("まだ日記がありません。")
