import html
import streamlit as st


def _to_html(text):
    """ログやAIの文章をHTMLとして安全に表示できる形にする（タグを無効化して改行を<br>に）"""
    return html.escape(str(text)).replace('\n', '<br>')

# --- 0. アプリ全体のスタイル設定（ダークパープル・Stitch完全再現版） ---
def apply_global_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        /* 1. 全体の背景とテキスト */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            font-family: 'Inter', sans-serif;
            background-color: #191121 !important;
            color: #f1f5f9;
        }

        /* 2. サイドバー（左フレーム）の徹底強化 */
        [data-testid="stSidebar"] {
            background-color: #120b18 !important;
            border-right: 1px solid rgba(153, 71, 235, 0.15);
            padding-top: 2rem;
        }
        
        /* サイドバー内のウィジェットのラベル */
        [data-testid="stSidebar"] label {
            color: #9947eb !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
        }

        /* 3. ボタン（集計ボタンなど）のデザイン */
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

        /* 4. 日付入力やテキストエリアの装飾 */
        .stDateInput div[data-baseweb="input"], .stTextArea textarea {
            background-color: #0f172a !important;
            color: #e2e8f0 !important;
            border: 1px solid rgba(153, 71, 235, 0.2) !important;
            border-radius: 0.8rem !important;
        }

        /* 5. 通知系ボックス */
        div[data-testid="stNotification"] {
            background-color: rgba(42, 31, 61, 0.6) !important;
            border: 1px solid rgba(153, 71, 235, 0.3) !important;
            color: #f1f5f9 !important;
            border-radius: 1rem !important;
        }
        
        /* スクロールバー */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: rgba(153, 71, 235, 0.05); }
        ::-webkit-scrollbar-thumb { background: rgba(153, 71, 235, 0.3); border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

# --- 1. サイドバー（左フレーム）の装飾 ---
def render_sidebar_status(logical_date):
    """
    サイドバーの最上部に表示するステータス
    """
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
                    <span style="color: #94a3b8;">RESET</span>
                    <span style="color: #b794f4;">03:00 AM</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 2. メインヘッダー表示 ---
def render_header(logical_date):
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 30px;">
            <div style="font-size: 28px;">🐾</div>
            <h2 style="margin: 0; font-size: 24px; font-weight: 700; color: #f1f5f9;">My Auto Diary</h2>
        </div>
    """, unsafe_allow_html=True)

# --- 3. ステータス情報の表示（2段レイアウト） ---
def display_status_info(target_date, weather, aw_show, dc):
    row1_col1, row1_col2 = st.columns([1, 2])
    row1_height = "180px"
    
    with row1_col1:
        st.markdown(f"""
            <div style="background: rgba(42, 31, 61, 0.4); border: 1px solid rgba(153, 71, 235, 0.2); padding: 20px; border-radius: 1.5rem; height: {row1_height}; box-sizing: border-box;">
                <div style="margin-bottom: 15px;">
                    <label>📅 DATE</label>
                    <div style="font-weight: 600; font-size: 1.1rem; margin-top: 4px; color: #f1f5f9;">{_to_html(target_date)}</div>
                </div>
                <div>
                    <label>☀️ WEATHER</label>
                    <div style="font-weight: 600; font-size: 1.1rem; margin-top: 4px; color: #f1f5f9;">{_to_html(weather)}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with row1_col2:
        st.markdown(f"""
            <div style="background: rgba(42, 31, 61, 0.4); border: 1px solid rgba(153, 71, 235, 0.2); padding: 20px; border-radius: 1.5rem; height: {row1_height}; box-sizing: border-box;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <label>💬 Discord Activity Log</label>
                    <span style="background: #9947eb; color: white; padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: bold;">本日</span>
                </div>
                <div style="font-size: 0.85rem; color: #e2e8f0; line-height: 1.6; height: 100px; overflow-y: auto;">
                    {_to_html(dc)}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="background: rgba(42, 31, 61, 0.4); border: 1px solid rgba(153, 71, 235, 0.2); padding: 20px; border-radius: 1.5rem; margin-top: 20px; min-height: 150px; box-sizing: border-box;">
            <div style="margin-bottom: 10px;">
                <label>📊 Activity Watch (Detailed Log)</label>
            </div>
            <div style="font-size: 0.85rem; color: #e2e8f0; line-height: 1.8; max-height: 250px; overflow-y: auto;">
                {_to_html(aw_show)}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 4. 送信前チェックエリア ---
# ui_parts.py の render_review_area
def render_review_area(aw_ai, dc):
    # PC活動ログ
    st.markdown("ActivityWatchログ (編集可)")
    # value=aw_ai をあえて書かず、session_state経由で表示させる
    edited_aw = st.text_area(
        label="aw_editor",
        # value は書かない（keyがある場合、session_stateの値が優先される）
        height=200,
        label_visibility="collapsed",
        key="edit_aw_logs"
    )

    # Discordログ
    st.markdown("Discordログ (編集可)")
    edited_dc = st.text_area(
        label="dc_editor",
        height=200,
        label_visibility="collapsed",
        key="edit_dc_logs"
    )
    
    return edited_aw, edited_dc

# --- 5. 日記の表示スタイル ---
def render_diary(content, target_date):
    st.markdown(f"""
        <div style="
            background-color: #ffffff; 
            padding: 30px; 
            border-radius: 1.5rem; 
            margin: 30px 0;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
            color: #1e293b;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px;">
                <div>
                    <!-- ここを target_date を使った固定タイトルに変更 -->
                    <h1 style="font-size: 1.3rem; font-weight: 700; color: #0f172a; margin: 0;">{target_date} の日記</h1>
                </div>
                <div style="font-size: 24px;">🐾</div>
            </div>
            <div style="line-height: 1.8; font-size: 1rem; color: #334155;">
                <!-- 本文はそのまま全て表示 -->
                {_to_html(content)}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 6. ネコちゃん ---
def cat_run():
    st.markdown("""
        <style>
        @keyframes cat-dash {
            0% { left: -100px; transform: scaleX(-1); }
            100% { left: 110%; transform: scaleX(-1); }
        }
        .running-cat {
            position: fixed; bottom: 80px; font-size: 50px; z-index: 9999;
            animation: cat-dash 2.5s ease-in-out forwards; pointer-events: none;
        }
        </style>
        <div class="running-cat">🐈✨</div>
    """, unsafe_allow_html=True)