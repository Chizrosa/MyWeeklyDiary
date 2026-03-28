import streamlit as st

# --- 0. アプリ全体のスタイル設定 ---
def apply_global_style():
    """
    ダークパープルの近未来的なテーマを適用します。
    """
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        /* 全体の背景とテキスト */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            font-family: 'Inter', sans-serif;
            background-color: #191121 !important;
            color: #f1f5f9;
        }

        /* サイドバー */
        [data-testid="stSidebar"] {
            background-color: #120b18 !important;
            border-right: 1px solid rgba(153, 71, 235, 0.15);
        }
        
        /* サイドバー内のラベル */
        [data-testid="stSidebar"] label {
            color: #9947eb !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em;
        }

        /* 共通ボタンデザイン */
        .stButton > button {
            background: linear-gradient(135deg, #9947eb 0%, #7e22ce 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 0.8rem !important;
            padding: 0.6rem 1.5rem !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 15px rgba(153, 71, 235, 0.3);
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(153, 71, 235, 0.5);
        }

        /* 入力エリア */
        .stDateInput div[data-baseweb="input"], .stTextArea textarea {
            background-color: #0f172a !important;
            color: #e2e8f0 !important;
            border: 1px solid rgba(153, 71, 235, 0.2) !important;
            border-radius: 0.8rem !important;
        }

        /* カスタムスクロールバー */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: rgba(153, 71, 235, 0.05); }
        ::-webkit-scrollbar-thumb { background: rgba(153, 71, 235, 0.3); border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

# --- 1. サイドバー・ステータス ---
def render_sidebar_status(logical_date):
    st.sidebar.markdown(f"""
        <div style="margin-bottom: 25px; padding: 10px; border-bottom: 1px solid rgba(153, 71, 235, 0.15);">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <div style="font-size: 20px;">🌙</div>
                <div style="font-weight: 700; font-size: 16px; letter-spacing: 0.05em;">SYSTEM CORE</div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px;">
                    <span style="color: #94a3b8;">STATUS</span>
                    <span style="color: #4ade80; font-weight: 700;">● ONLINE</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px;">
                    <span style="color: #94a3b8;">LOGICAL DATE</span>
                    <span style="color: #b794f4;">{logical_date}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 2. メインヘッダー ---
def render_header(logical_date):
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 30px;">
            <div style="font-size: 28px;">🐾</div>
            <h2 style="margin: 0; font-size: 24px; font-weight: 700; color: #f1f5f9;">My Auto Diary</h2>
        </div>
    """, unsafe_allow_html=True)

# --- 3. 取得データ表示 ---
def display_status_info(target_date, weather, aw_show, dc):
    col1, col2 = st.columns([1, 2])
    card_style = "background: rgba(42, 31, 61, 0.4); border: 1px solid rgba(153, 71, 235, 0.2); padding: 20px; border-radius: 1.5rem; height: 200px; box-sizing: border-box;"
    
    with col1:
        st.markdown(f"""
            <div style="{card_style}">
                <div style="margin-bottom: 15px;">
                    <label style="color: #9947eb; font-size: 0.7rem; font-weight: 700;">📅 DATE</label>
                    <div style="font-weight: 600; font-size: 1.1rem; color: #f1f5f9;">{target_date}</div>
                </div>
                <div>
                    <label style="color: #9947eb; font-size: 0.7rem; font-weight: 700;">☀️ WEATHER</label>
                    <div style="font-weight: 600; font-size: 1.1rem; color: #f1f5f9;">{weather}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # 改行をHTMLタグに変換
        dc_html = dc.replace('\n', '<br>')
        st.markdown(f"""
            <div style="{card_style}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <label style="color: #9947eb; font-size: 0.7rem; font-weight: 700;">💬 Discord Log</label>
                </div>
                <div style="font-size: 0.8rem; color: #e2e8f0; line-height: 1.5; height: 110px; overflow-y: auto;">
                    {dc_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Activity Watchログ（下段）
    aw_html = aw_show.replace('\n', '<br>')
    st.markdown(f"""
        <div style="background: rgba(42, 31, 61, 0.4); border: 1px solid rgba(153, 71, 235, 0.2); padding: 20px; border-radius: 1.5rem; margin-top: 20px;">
            <label style="color: #9947eb; font-size: 0.7rem; font-weight: 700; display: block; margin-bottom: 10px;">📊 Activity Watch (Detailed Log)</label>
            <div style="font-size: 0.8rem; color: #e2e8f0; line-height: 1.6; max-height: 200px; overflow-y: auto;">
                {aw_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 4. 日記のプレビュー ---
def render_diary(content, target_date):
    # 本文の改行処理
    body_html = content.replace('\n', '<br>')
    st.markdown(f"""
        <div style="
            background-color: #ffffff; 
            padding: 35px; 
            border-radius: 1.5rem; 
            margin: 30px 0;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            color: #1e293b;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 2px solid #f1f5f9; padding-bottom: 15px;">
                <h1 style="font-size: 1.4rem; font-weight: 700; color: #0f172a; margin: 0;">{target_date} の記録</h1>
                <div style="font-size: 24px;">📝</div>
            </div>
            <div style="line-height: 1.9; font-size: 1.05rem; color: #334155; font-family: 'Inter', sans-serif;">
                {body_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 5. エフェクト ---
def cat_run():
    st.markdown("""
        <style>
        @keyframes cat-dash {
            0% { left: -100px; transform: scaleX(-1); }
            100% { left: 110%; transform: scaleX(-1); }
        }
        .running-cat {
            position: fixed; bottom: 50px; font-size: 60px; z-index: 10000;
            animation: cat-dash 2s ease-in-out forwards; pointer-events: none;
        }
        </style>
        <div class="running-cat">🐈💨</div>
    """, unsafe_allow_html=True)

# ユーティリティ（送信前チェックエリアはStreamlit標準パーツを使うため整理）
def render_review_area(target_date, weather, aw_ai, dc):
    st.markdown("<br><label style='color: #9947eb; font-weight:700;'>📂 AI Submission Preview</label>", unsafe_allow_html=True)
    review_text = f"【日付】: {target_date}\n【天気】: {weather}\n\n【活動ログ】:\n{aw_ai}\n\n【Discord】:\n{dc}"
    return st.text_area("内容の最終確認（編集可）", value=review_text, height=300, label_visibility="collapsed")