# --- 標準ライブラリ ---
import re
import os
import pathlib
import json
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# --- 外部ライブラリ ---
import streamlit as st
import ui_parts
import requests
from google import genai
from dotenv import load_dotenv

# --- 0. 設定と定数 ---
load_dotenv()

# 門番（セットアップチェック）
def check_env():
    # 1. ActivityWatchの起動確認
    try:
        requests.get("http://localhost:5600/api/0/ping", timeout=1)
    except:
        st.error("## ⚠️ ActivityWatch が起動していません")
        st.info("日記を生成するには、ActivityWatchを立ち上げておく必要があります。[公式サイトはこちら](https://activitywatch.net/)")
        st.stop()

    # 2. .envの設定（APIキー）確認
    if not os.getenv("GEMINI_API_KEY"):
        st.warning("## ⚠️ APIキーが設定されていません")
        st.info("`.env` ファイルを作成し、`GEMINI_API_KEY` を記入してください。詳細はREADMEを確認してください。")
        st.stop()

# 起動時に真っ先に実行
check_env()

# デフォルトの保存先
DEFAULT_SAVE_PATH = os.getenv("SAVE_DIR", "./diaries")
SAVE_DIR = pathlib.Path(DEFAULT_SAVE_PATH)
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# --- 使用するAIモデルの選択 ---
# GEMINI_MODEL = "gemini-3.1-flash-lite-preview" 
# GEMINI_MODEL = "gemma-4-31b-it"       # 最も賢い高機能モデル
GEMINI_MODEL = "gemma-4-26b-a4b-it"  # 高速で効率的なモデル

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

# --- 1. ユーティリティ関数 ---

def get_logical_date():
    """夜型人間用：午前3時までは前日として扱う"""
    now = datetime.now()
    if now.hour < 3:
        return now.date() - timedelta(days=1)
    return now.date()

def get_aw_summary(target_date):
    """ActivityWatchから活動ログを取得"""
    tz_name = os.getenv("TIMEZONE", "UTC")
    local_tz = ZoneInfo(tz_name)
    try:
        url = "http://localhost:5600/api/0/query/"
        naive_start = datetime.combine(target_date, time(3, 0, 0))
        local_start = naive_start.replace(tzinfo=local_tz)
        utc_start = local_start.astimezone(ZoneInfo("UTC"))
        utc_end = utc_start + timedelta(days=1)
        
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
            ai_summary, local_summary = [], []

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
                ai_summary.append(f"・{app}: {safe_title} ({duration}分)")

            return {
                "ai": "\n".join(ai_summary) if ai_summary else "活動ログなし",
                "local": "\n".join(local_summary) if local_summary else "活動ログなし"
            }
        return {"ai": "取得エラー", "local": "取得エラー"}
    except Exception as e:
        return {"ai": f"接続不可 ({type(e).__name__})", "local": f"接続不可 ({e})"}

def get_discord_messages(target_date):
    """Discordからメッセージを取得"""
    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if not token or not channel_id:
        return "Discord設定（TOKEN/ID）が未設定です。"

    tz_name = os.getenv("TIMEZONE", "UTC")
    local_tz = ZoneInfo(tz_name)
    try:
        headers = {"Authorization": f"Bot {token}"}
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            messages = res.json()
            start_threshold = datetime.combine(target_date, time(3, 0, 0))
            end_threshold = start_threshold + timedelta(days=1)
            
            texts = []
            for m in messages:
                utc_time = datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00'))
                msg_time = utc_time.astimezone(local_tz).replace(tzinfo=None)
                if start_threshold <= msg_time < end_threshold:
                    time_str = msg_time.strftime('%m/%d %H:%M')
                    texts.append(f"[{time_str}] {m['content']}") 
            
            return "\n".join(texts[::-1]) if texts else "指定した日のつぶやきはありません。"
        return f"Discordエラー: {res.status_code}"
    except Exception as e:
        return f"Discord取得失敗: {type(e).__name__}"

def get_weather(target_date):
    """Open-Meteoから天気を取得"""
    try:
        city = os.getenv("CITY_NAME", "Tokyo") 
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ja&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if "results" not in geo_res:
            return f"天気エラー: {city} が見つかりません"
        lat, lon = geo_res["results"][0]["latitude"], geo_res["results"][0]["longitude"]
        date_str = target_date.isoformat()
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&start_date={date_str}&end_date={date_str}&hourly=temperature_2m,weathercode&timezone=auto"
        w_res = requests.get(weather_url, timeout=5).json()
        temp_10am = w_res["hourly"]["temperature_2m"][10]
        code_10am = w_res["hourly"]["weathercode"][10]
        weather_map = {0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り", 45: "霧", 61: "雨", 71: "雪", 95: "雷雨"}
        desc = weather_map.get(code_10am, "不明/その他")
        return f"{desc} (気温: {temp_10am}℃)"
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

def update_oneline_md(memory_data):
    """Obsidian用「1行日記まとめ.md」の更新"""
    content = "# 📅 1行日記まとめ\n\n"
    for d in sorted(memory_data.keys()):
        content += f"- **{d}**: {memory_data[d]}\n"
    oneline_path = SAVE_DIR / "1行日記まとめ.md"
    with open(oneline_path, "w", encoding="utf-8") as f:
        f.write(content)

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
    if st.sidebar.button("✨ データを集計"):
        with st.spinner("集計中..."):
            aw_result = get_aw_summary(target_date)
            st.session_state.aw_ai = aw_result["ai"]
            st.session_state.aw_local = aw_result["local"]
            st.session_state.dc = get_discord_messages(target_date)
            st.session_state.weather = get_weather(target_date)
            st.session_state.is_collected = True

    weather_data = st.session_state.get("weather", "（未取得）")
    aw_show = st.session_state.get("aw_local", "（未取得）")
    dc_data = st.session_state.get("dc", "（未取得）")
    
    ui_parts.display_status_info(target_date, weather_data, aw_show, dc_data)
    memo = st.text_area("✍️ 付け加えたいこと", placeholder="今日あったことや、AIに伝えたいことを書いてください。", height=150)

    if st.session_state.get("is_collected"):
        edited_logs = ui_parts.render_review_area(
            target_date, weather_data, st.session_state.get("aw_ai", "（未取得）"), dc_data
        )

        if st.button("🌟 AIに日記を書いてもらう"):
            with st.spinner("AIが執筆中..."):
                prompt_path = pathlib.Path(__file__).parent / "prompt.txt"
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        instruction = f.read()
                    
                    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                    weekday_str = weekdays[target_date.weekday()]
                    perfect_date = f"{target_date.year}年{target_date.month}月{target_date.day}日（{weekday_str}曜日）"
                    
                    # 記憶の読み込み（直近7日分）
                    memory_db = load_memory()
                    sorted_dates = sorted(memory_db.keys())
                    last_7_dates = sorted_dates[-7:]
                    memory_lines = [f"{d}: {memory_db[d]}" for d in last_7_dates]
                    memory_text = "\n".join(memory_lines) if memory_lines else "過去の記録はまだありません。"
                    
                    full_prompt = instruction.format(
                        target_date=perfect_date,
                        weather_data=weather_data,
                        aw_data=edited_logs,
                        dc_data=dc_data,
                        memo=memo,
                        weekly_memory=memory_text
                    )

                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    
                    # 1. メイン日記の生成
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=full_prompt
                    )
                    st.session_state.result = response.text

                    # 2. 今日のハイライトを1行で抽出（事実ベースに改善）
                    summary_prompt = f"""
以下は今日の日記です。この日の「主要な活動」と「体調や気分の変化」を、
事実ベースで簡潔に1行（50文字以内）で記録してください。
※「明日は〜する」という予定よりも、「今日は〜だった」という事実を優先してください。
※「おなかいたい」等の日常的なつぶやきは、深刻な体調不良ではなく等身大で表現してください。

{response.text}
"""
                    summary_response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=summary_prompt
                    )
                    
                    date_key = target_date.isoformat()
                    memory_db[date_key] = summary_response.text.strip()
                    save_memory(memory_db)
                    update_oneline_md(memory_db)

                except Exception as e:
                    st.error(f"エラー: {e}")

    if "result" in st.session_state:
        ui_parts.render_diary(st.session_state.result, target_date)
        
        if st.button("💾 ファイルに保存する"):
            file_name = f"{target_date.isoformat()}.md"
            file_path = SAVE_DIR / file_name
            
            # content構成：日記本文、モデル署名、詳細ログ
            content = f"""# {target_date}

{st.session_state.result}

---
### 🤖 使用モデル
`{GEMINI_MODEL}`

### 📊 ログ（詳細）
{st.session_state.aw_local}

### 💬 Discord
```text
{dc_data}
```
"""
            # ファイル書き込み
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            st.success(f"『{file_name}』を保存しました！")
            ui_parts.cat_run()

            # 日曜日の週次まとめ
            if target_date.weekday() == 6:
                with st.spinner("日曜日のため、1週間の総括を生成中..."):
                    memory_db = load_memory()
                    sorted_dates = sorted(memory_db.keys())
                    last_7_dates = sorted_dates[-7:]
                    memory_lines = [f"{d}: {memory_db[d]}" for d in last_7_dates]
                    memory_text = "\n".join(memory_lines)
                    
                    archive_prompt = f"以下の1週間の記録を元に、今週の総括を3行でまとめてください。\n\n{memory_text}"
                    archive_response = client.models.generate_content(model=GEMINI_MODEL, contents=archive_prompt)
                    
                    year, week_num, _ = target_date.isocalendar()
                    archive_filename = f"{year}-W{week_num:02d}_Summary.md"
                    archive_content = f"# {year}年 第{week_num}週のまとめ\n\n## AI総括\n{archive_response.text}\n\n## ハイライト\n{memory_text}"
                    
                    with open(SAVE_DIR / archive_filename, "w", encoding="utf-8") as f:
                        f.write(archive_content)
                    st.success(f"🎊 週次アーカイブを保存しました！")

with tab2:
    st.subheader("これまでの記録")
    if SAVE_DIR.exists():
        files = sorted(list(SAVE_DIR.glob("*.md")), reverse=True)
        if files:
            selected_file = st.selectbox("読む日記を選んでください", files, format_func=lambda x: x.stem)
            with open(selected_file, "r", encoding="utf-8") as f:
                st.markdown("---")
                st.markdown(f.read())
        else:
            st.write("まだ日記がありません。")