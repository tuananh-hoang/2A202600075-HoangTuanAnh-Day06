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
        /* Using Streamlit theme variables */
        --st-bg: var(--background-color);
        --st-secondary-bg: var(--secondary-background-color);
        --st-text: var(--text-color);
    }}

    * {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* Background Gradient - Subtle in Dark Mode */
    .stApp {{
        background: radial-gradient(circle at 0% 0%, rgba(0, 204, 187, 0.03) 0%, transparent 50%),
                    radial-gradient(circle at 100% 100%, rgba(0, 180, 191, 0.03) 0%, transparent 50%),
                    var(--st-bg);
    }}

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {{
        background: var(--st-secondary-bg) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(128, 128, 128, 0.1) !important;
    }}

    /* Header Styling - Adaptive */
    .premium-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1.5rem;
        background: rgba(128, 128, 128, 0.05);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
    }}

    .brand-title {{
        font-weight: 800;
        font-size: 1.2rem;
        background: linear-gradient(135deg, var(--xanh-primary), var(--xanh-secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }}

    /* Adaptive Chat Bubbles */
    .chat-bubble {{
        padding: 1rem 1.25rem;
        border-radius: 18px;
        margin-bottom: 0.75rem;
        max-width: 85%;
        line-height: 1.5;
        font-size: 0.95rem;
        position: relative;
        animation: slideUp 0.3s ease-out;
    }}

    @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .user-bubble {{
        background: var(--xanh-primary);
        color: white !important;
        margin-left: auto;
        border-bottom-right-radius: 4px;
        box-shadow: 0 4px 15px rgba(0, 204, 187, 0.15);
    }}

    .bot-bubble {{
        background: var(--st-secondary-bg);
        color: var(--st-text);
        margin-right: auto;
        border-bottom-left-radius: 4px;
        border: 1px solid rgba(128, 128, 128, 0.1);
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
    
    .conf-low {{ background: rgba(254, 249, 195, 0.2); color: #EAB308; border: 1px solid rgba(234, 179, 8, 0.3); }}
    .conf-high {{ background: rgba(220, 252, 231, 0.2); color: #22C55E; border: 1px solid rgba(34, 197, 94, 0.3); }}

    /* Hotline Button */
    .hotline-btn {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        background: #EF4444;
        color: white !important;
        padding: 10px 15px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 700;
        font-size: 0.9rem;
        margin-top: 10px;
    }}

    /* Mini-feedback buttons */
    .stButton > button[kind="secondary"] {{
        padding: 0.2rem 0.4rem !important;
        font-size: 0.8rem !important;
        border-radius: 20px !important;
        background: transparent !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        transition: all 0.2s ease !important;
        min-width: 35px !important;
        height: 35px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    .stButton > button[kind="secondary"]:hover {{
        border-color: var(--xanh-primary) !important;
        background: rgba(0, 204, 187, 0.05) !important;
        transform: scale(1.1);
    }}

    /* Container to push buttons to the right */
    .feedback-container {{
        display: flex;
        justify-content: flex-end;
        width: 100%;
        margin-top: -35px;
        padding-right: 10px;
    }}

    /* Adaptive Source Tags */
    .source-tag {{
        display: inline-block;
        padding: 4px 12px;
        margin: 5px 8px 5px 0;
        background: rgba(0, 204, 187, 0.08);
        border: 1px solid rgba(0, 204, 187, 0.3);
        border-radius: 12px;
        font-size: 0.8rem;
        color: var(--xanh-primary);
        text-decoration: none;
        transition: all 0.2s ease;
        font-weight: 500;
    }}

    .source-tag:hover {{
        background: var(--xanh-primary);
        color: white !important;
        border-color: var(--xanh-primary);
        box-shadow: 0 4px 12px rgba(0, 204, 187, 0.2);
        transform: translateY(-1px);
    }}

    /* Clean UI */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "failure_count" not in st.session_state:
    st.session_state.failure_count = 0
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "use_ai" not in st.session_state:
    st.session_state.use_ai = True

# --- FEEDBACK FUNCTION ---
def send_feedback(msg_idx, reason):
    try:
        requests.post(
            f"{BACKEND_URL.replace('/chat', '/feedback')}",
            json={
                "thread_id": st.session_state.thread_id,
                "message_index": msg_idx,
                "reason": reason
            },
            timeout=5
        )
        st.toast("Cảm ơn phản hồi của bạn! ❤️")
    except:
        st.toast("⚠️ Gửi phản hồi thất bại.")

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.markdown("### 🚖 Trợ Lý Đối Tác")
    st.info("Hỗ trợ Đối tác tra cứu quy định, chính sách và hướng dẫn vận hành nhanh chóng.")
    
    # Opt-out Setting (Path 4)
    st.session_state.use_ai = st.toggle("🤖 Sử dụng Trợ lý AI", value=True, help="Tắt để chỉ tìm kiếm tài liệu gốc")

    if st.button("🗑️ Xoá lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.failure_count = 0
        st.rerun()

    if st.session_state.failure_count >= 2:
        st.error("🆘 Cần hỗ trợ gấp?")
        st.markdown('<a href="tel:19002088" class="hotline-btn">📞 GỌI HOTLINE NGAY</a>', unsafe_allow_html=True)

    st.divider()
    st.caption("Phiên bản 5.0 | Xanh SM NHM Team")

# --- MAIN HEADER ---
st.markdown(f"""
    <div class="premium-header">
        <div class="brand-title">Dịch Vụ Từ Trái Tim ❤️</div>
    </div>
""", unsafe_allow_html=True)

# --- CHAT DISPLAY ---
for idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    content = msg["content"]
    sources = msg.get("sources", [])
    confidence = msg.get("confidence", "high")
    escalate = msg.get("escalate", False)
    
    if role == "user":
        st.markdown(f'<div class="chat-bubble user-bubble">{content}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            # Path 2: Confidence Badge
            if confidence == "low":
                st.markdown('<div class="confidence-badge conf-low">⚠️ Cần xác nhận</div>', unsafe_allow_html=True)
            
            st.markdown(content)
            
            # Path 4: Escalation Hotline inside message
            if escalate:
                st.warning("Thông tin này có thể chưa đầy đủ cho trường hợp của bạn.")
                st.markdown('<a href="tel:19002088" class="hotline-btn">📞 GỌI HOTLINE KIỂM TRA NGAY</a>', unsafe_allow_html=True)

            if sources:
                st.markdown('<div style="margin-top: 10px; font-weight: 600; font-size: 0.85rem;">📚 Nguồn tham khảo:</div>', unsafe_allow_html=True)
                for source in sources:
                    if isinstance(source, dict):
                        title = source.get("title", "")
                        url = source.get("url", "")
                    else:
                        title = source
                        url = ""
                    
                    if url:
                        st.markdown(f'<a href="{url}" target="_blank" class="source-tag">🔗 {title}</a>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="source-tag">{title}</span>', unsafe_allow_html=True)
            
            # Path 3: Feedback Buttons (Right Aligned)
            st.markdown('<div class="feedback-container">', unsafe_allow_html=True)
            col_space, col1, col2 = st.columns([0.85, 0.07, 0.08])
            with col1:
                if st.button("👍", key=f"up_{idx}", help="Hữu ích"):
                    st.toast("Cảm ơn bạn! ❤️")
            with col2:
                if st.button("👎", key=f"down_{idx}", help="Thông tin chưa đúng"):
                    send_feedback(idx, "wrong_info")
            st.markdown('</div>', unsafe_allow_html=True)

# --- CHAT INPUT ---
if prompt := st.chat_input("Hỏi về quy định, chính sách..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Logic xử lý tin nhắn mới nhất
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    with st.chat_message("assistant"):
        with st.spinner("Xanh SM đang tra cứu..."):
            try:
                # Prepare payload
                payload = {
                    "message": last_prompt,
                    "thread_id": st.session_state.thread_id
                }
                
                response = requests.post(BACKEND_URL, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("reply", "Dạ, tôi chưa có thông tin cụ thể về vấn đề này.")
                    sources = data.get("sources", [])
                    confidence = data.get("confidence", "high")
                    escalate = data.get("escalate", False)
                    
                    # Update session state
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "confidence": confidence,
                        "escalate": escalate
                    })
                    st.session_state.failure_count = 0 # reset on success
                    st.rerun()
                else:
                    st.error(f"❌ Lỗi kết nối Backend ({response.status_code})")
                    # Append a system message to stop the loop
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "⚠️ Đã có lỗi xảy ra khi kết nối tới hệ thống. Bạn vui lòng thử lại sau hoặc gọi Hotline.",
                        "confidence": "low"
                    })
                    st.session_state.failure_count += 1
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Lỗi: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ Lỗi: {str(e)}",
                    "confidence": "low"
                })
                st.session_state.failure_count += 1
                st.rerun()

