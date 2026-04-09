import streamlit as st
import requests
import time
import os
import uuid
import datetime
from dotenv import load_dotenv

# Load environment variables if .env exists
load_dotenv()

# --- CONFIGURATION ---
# BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")

BRAND_COLOR = "#00CCBB"
LOGO_URL = "https://www.xanhsm.com/wp-content/uploads/2023/04/Logo-Xanh-SM.png"

# --- BRANDING & ULTRA-PREMIUM CSS ---
st.set_page_config(
    page_title="Xanh SM - Trợ Lý Đối Tác",
    page_icon="🚖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Signature CSS (Combined Cyan Brand + Glassmorphism)
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    :root {{
        --xanh-primary: {BRAND_COLOR};
        --xanh-secondary: #00B4BF;
        --xanh-accent: #7FFFD4;
        --xanh-bg: #F8FAFC;
        --text-dark: #0F172A;
        --text-muted: #64748B;
        --glass-bg: rgba(255, 255, 255, 0.7);
        --glass-border: rgba(255, 255, 255, 0.4);
    }}

    * {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* Background Gradient */
    .stApp {{
        background: radial-gradient(circle at 0% 0%, rgba(0, 204, 187, 0.05) 0%, transparent 50%),
                    radial-gradient(circle at 100% 100%, rgba(0, 180, 191, 0.05) 0%, transparent 50%),
                    #FFFFFF;
    }}

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--glass-border) !important;
    }}

    /* Header Styling */
    .premium-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.5rem 2rem;
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--glass-border);
        border-radius: 0 0 24px 24px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.02);
    }}

    .brand-title {{
        font-weight: 800;
        font-size: 1.5rem;
        background: linear-gradient(135deg, var(--xanh-primary), var(--xanh-secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }}

    /* Enhanced Chat Bubbles */
    .chat-bubble {{
        padding: 1.25rem;
        border-radius: 20px;
        margin-bottom: 1rem;
        max-width: 85%;
        line-height: 1.6;
        font-size: 0.95rem;
        position: relative;
        animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .user-bubble {{
        background: var(--xanh-primary);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
        box-shadow: 0 10px 15px -3px rgba(0, 204, 187, 0.2);
    }}

    .bot-bubble {{
        background: white;
        color: var(--text-dark);
        margin-right: auto;
        border-bottom-left-radius: 4px;
        border: 1px solid rgba(0, 204, 187, 0.1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
    }}

    /* Confidence Badge */
    .confidence-badge {{
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 8px;
    }}
    
    .conf-low {{
        background: #FEF9C3;
        color: #854D0E;
        border: 1px solid #FDE047;
    }}
    
    .conf-high {{
        background: #DCFCE7;
        color: #166534;
        border: 1px solid #BBF7D0;
    }}

    /* Hotline Button Style */
    .hotline-btn {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        background: #EF4444;
        color: white !important;
        padding: 12px 20px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: 700;
        margin-top: 10px;
        transition: transform 0.2s;
    }}
    
    .hotline-btn:hover {{
        transform: scale(1.02);
        background: #DC2626;
    }}

    /* Micro-buttons for feedback */
    .stButton > button[kind="secondary"] {{
        padding: 0.2rem 0.5rem !important;
        font-size: 0.8rem !important;
        min-height: 24px !important;
        line-height: 1 !important;
        border-radius: 8px !important;
    }}

    /* Source tags */
    .source-tag {{
        display: inline-block;
        padding: 2px 10px;
        margin: 5px 5px 0 0;
        background-color: rgba(0, 204, 187, 0.1);
        border: 1px solid var(--xanh-primary);
        border-radius: 20px;
        font-size: 0.8rem;
        color: var(--xanh-primary);
        font-weight: 500;
    }}

    /* Hide Streamlit components */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "failure_count" not in st.session_state:
    st.session_state.failure_count = 0
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.markdown("### 🚖 Trợ Lý Đối Tác")
    st.info("Hỗ trợ Đối tác tra cứu quy định, chính sách và hướng dẫn vận hành nhanh chóng.")
    
    st.markdown("### 💡 Câu hỏi gợi ý")
    suggestions = ["Quy định về hành lý?", "Chính sách giá cước?", "Làm sao để đăng ký đối tác?", "Quy định về thú cưng?"]
    for suggestion in suggestions:
        if st.button(suggestion, use_container_width=True):
            st.session_state.pending_prompt = suggestion

    st.divider()
    if st.button("🗑️ Xoa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    if st.session_state.failure_count >= 2:
        st.error("🆘 Cần hỗ trợ gấp?")
        st.markdown('<a href="tel:19002088" class="hotline-btn">📞 GỌI HOTLINE NGAY</a>', unsafe_allow_html=True)

    st.spacer = st.empty()
    st.caption("Phiên bản 4.0 | Xanh SM NHM Team")

# --- MAIN HEADER ---
st.markdown(f"""
    <div class="premium-header">
        <div class="brand-title">Dịch Vụ Từ Trái Tim ❤️</div>
        <div style="font-size: 0.8rem; color: var(--text-muted);">Trợ lý ảo chính thức của Xanh SM</div>
    </div>
""", unsafe_allow_html=True)

# --- CHAT DISPLAY ---
for idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    content = msg["content"]
    sources = msg.get("sources", [])
    
    if role == "user":
        st.markdown(f'<div class="chat-bubble user-bubble">{content}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)
            if sources:
                st.markdown('<div style="margin-top: 10px; font-weight: 600; font-size: 0.85rem;">📚 Nguồn tham khảo:</div>', unsafe_allow_html=True)
                for source in sources:
                    title = source.get("title", "") if isinstance(source, dict) else source
                    st.markdown(f'<span class="source-tag">{title}</span>', unsafe_allow_html=True)

# --- CHAT INPUT ---
if prompt := st.chat_input("Hỏi về quy định, chính sách..."):
    pass # logic below handles both input methods

if hasattr(st.session_state, "pending_prompt"):
    prompt = st.session_state.pending_prompt
    del st.session_state.pending_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Logic xử lý tin nhắn mới nhất
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    with st.chat_message("assistant"):
        with st.spinner("Xanh SM đang tra cứu..."):
            try:
                response = requests.post(
                    BACKEND_URL,
                    json={
                        "message": last_prompt,
                        "thread_id": st.session_state.thread_id
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("reply", "Dạ, tôi chưa có thông tin cụ thể về vấn đề này.")
                    sources = data.get("sources", [])
                    
                    st.markdown(answer)
                    if sources:
                        st.markdown('<div style="margin-top: 10px; font-weight: 600; font-size: 0.85rem;">📚 Nguồn tham khảo:</div>', unsafe_allow_html=True)
                        for source in sources:
                            st.markdown(f'<span class="source-tag">{source}</span>', unsafe_allow_html=True)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error(f"❌ Lỗi kết nối Backend ({response.status_code})")
                    st.session_state.failure_count += 1
            except Exception as e:
                st.error(f"❌ Lỗi: {str(e)}")
                st.session_state.failure_count += 1
    st.rerun()
