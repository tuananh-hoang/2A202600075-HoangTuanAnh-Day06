import streamlit as st
import requests
import time

# --- CONFIGURATION & BRANDING ---
st.set_page_config(
    page_title="Hỗ Trợ Tài Xế Xanh SM",
    page_icon="🚖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ultra-Premium CSS V2
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    :root {
        --primary: #008D96;
        --primary-light: #00B4BF;
        --secondary: #7FFFD4;
        --bg-main: #F1F5F9;
        --glass: rgba(255, 255, 255, 0.7);
        --text-main: #1E293B;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism Background */
    .stApp {
        background-image: radial-gradient(at 0% 0%, hsla(184,100%,95%,1) 0, transparent 50%), 
                          radial-gradient(at 50% 0%, hsla(184,100%,98%,1) 0, transparent 50%), 
                          radial-gradient(at 100% 0%, hsla(184,100%,95%,1) 0, transparent 50%);
        background-attachment: fixed;
    }

    /* Header with Blur */
    .main-header {
        position: sticky;
        top: 0;
        z-index: 999;
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 1rem 2rem;
        border-radius: 0 0 24px 24px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
    }
    
    .header-title {
        background: linear-gradient(90deg, #008D96, #00B4BF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 1.5rem;
        margin: 0;
    }

    /* Chat Bubbles Upgraded */
    .stChatMessage {
        animation: fadeIn 0.5s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .user-bubble {
        background-color: var(--primary) !important;
        color: white !important;
        border-radius: 20px 20px 4px 20px !important;
        padding: 1.2rem !important;
        margin-left: auto;
        box-shadow: 0 10px 15px -3px rgba(0, 141, 150, 0.2);
    }

    .bot-bubble {
        background: white !important;
        color: var(--text-main) !important;
        border-radius: 20px 20px 20px 4px !important;
        padding: 1.2rem !important;
        margin-right: auto;
        border: 1px solid rgba(226, 232, 240, 0.8) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Reasoning/Thinking Section */
    .thought-process {
        background-color: #F8FAFC;
        border-left: 3px solid #CBD5E1;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #64748B;
        font-style: italic;
    }
    
    .thought-title {
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Floating Input Card */
    .input-container {
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        width: 60%;
        max-width: 800px;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        padding: 1rem;
        border-radius: 40px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        z-index: 1000;
    }

    /* Sidebar Glassmorphism */
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(10px);
    }

    /* Pulsating Indicator */
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #22C55E;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
        box-shadow: 0 0 0 rgba(34, 197, 94, 0.4);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); }
        100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }

    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color: #008D96;">🚖 Driver Assistant</h2>', unsafe_allow_html=True)
    st.markdown("""
        <div style="background: rgba(0, 141, 150, 0.05); padding: 1rem; border-radius: 12px; border: 1px solid rgba(0, 141, 150, 0.1);">
            <p style="font-size: 0.9rem; margin: 0;">Chào tài xế! Hệ thống đang ở trạng thái <b>Sẵn sàng</b>.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📚 Thư viện chính sách")
    st.button("📜 Bộ quy tắc ứng xử", use_container_width=True)
    st.button("💵 Cơ cấu phí & chiết khấu", use_container_width=True)
    st.button("🗺️ Bản đồ khu vực hoạt động", use_container_width=True)
    
    st.spacer = st.empty()
    st.divider()
    st.caption("NHM Team © 2026 | Phiên bản 2.0 (Premium)")

# --- HEADER ---
st.markdown("""
    <div class="main-header">
        <p class="header-title">Chatbot Tài Xế Xanh SM</p>
        <div style="display: flex; align-items: center; background: white; padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.8rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <span class="status-dot"></span> Online - Qdrant Vector DB
        </div>
    </div>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Welcome Screen (Upgraded)
if not st.session_state.messages:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="text-align: center; padding: 3rem 0;">
                <h1 style="font-size: 3rem;">👋</h1>
                <h2 style="font-weight: 800; color: #1E293B;">Làm thế nào tôi có thể giúp bạn?</h2>
                <p style="color: #64748B; font-size: 1.1rem;">Tôi là trợ lý AI chuyên biệt cho cộng đồng tài xế Xanh SM.</p>
            </div>
        """, unsafe_allow_html=True)
        
        suggestions = [
            "Quy định về việc sạc xe điện?",
            "Làm sao để khiếu nại cuốc xe?",
            "Chương trình Xanh SM Reward là gì?",
            "Thủ tục đăng ký cho người mới?"
        ]
        
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            if cols[i % 2].button(s, key=f"s_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": s})
                st.rerun()

# Display logic
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    thought = msg.get("thought", "")
    sources = msg.get("sources", [])
    
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="user-bubble">{content}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            # Reasoning section
            if thought:
                with st.expander("💭 Xem luồng suy luận của AI", expanded=False):
                    st.markdown(f'<div class="thought-process"><p class="thought-title">🔍 PHÂN TÍCH</p>{thought}</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="bot-bubble">{content}</div>', unsafe_allow_html=True)
            
            if sources:
                source_html = " ".join([f'<span style="display: inline-block; background: #F1F5F9; color: #64748B; padding: 2px 8px; border-radius: 8px; font-size: 0.7rem; margin-top: 8px; border: 1px solid #E2E8F0; margin-right: 5px;">📄 {src}</span>' for src in sources])
                st.markdown(source_html, unsafe_allow_html=True)

# Chat Input (The input uses the standard st.chat_input which stays bottom)
if prompt := st.chat_input("Hỏi tôi bất cứ điều gì về Xanh SM..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Processing logic (when the last message is from user)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_query = st.session_state.messages[-1]["content"]
    
    with st.chat_message("assistant", avatar="🤖"):
        # Initial status
        status_placeholder = st.empty()
        status_placeholder.markdown("🔍 *Đang truy vấn kiến thức Xanh SM...*")
        
        try:
            # Simulate a real API call delay
            time.sleep(1)
            
            # Call Backend (Placeholder URL)
            response = requests.post(
                "http://localhost:8000/chat",
                json={"message": user_query},
                timeout=20
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data["reply"]
                sources = data.get("sources", [])
                
                # Mock a "thought" process for demo purposes 
                # In a real RAG app, this would come from the backend's internal logs
                thought_process = f"1. Nhận truy vấn: '{user_query}'\n2. Tìm kiếm Vector DB (Qdrant) cho các từ khóa cốt lõi.\n3. Tìm thấy 3 đoạn văn bản liên quan trong sổ tay tài xế.\n4. Đang tổng hợp câu trả lời ngắn gọn và chính xác nhất..."
                
                # Update UI
                status_placeholder.empty()
                
                with st.expander("💭 Xem luồng suy luận của AI", expanded=True):
                     st.markdown(f'<div class="thought-process"><p class="thought-title">🔍 PHÂN TÍCH</p>{thought_process}</div>', unsafe_allow_html=True)
                
                # Streaming effect
                message_placeholder = st.empty()
                full_response = ""
                for chunk in reply.split():
                    full_response += chunk + " "
                    time.sleep(0.04)
                    message_placeholder.markdown(f'<div class="bot-bubble">{full_response}▌</div>', unsafe_allow_html=True)
                
                message_placeholder.markdown(f'<div class="bot-bubble">{reply}</div>', unsafe_allow_html=True)
                
                if sources:
                    source_html = " ".join([f'<span style="display: inline-block; background: #F1F5F9; color: #64748B; padding: 2px 8px; border-radius: 8px; font-size: 0.7rem; margin-top: 8px; border: 1px solid #E2E8F0; margin-right: 5px;">📄 {src}</span>' for src in sources])
                    st.markdown(source_html, unsafe_allow_html=True)
                
                # Save to history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": reply, 
                    "thought": thought_process,
                    "sources": sources
                })
            else:
                status_placeholder.markdown("❌ Lỗi kỹ thuật hệ thống. Đang kết nối lại...")
                
        except Exception as e:
            status_placeholder.markdown(f"⚠️ Không thể kết nối Backend. Error: {str(e)}")
