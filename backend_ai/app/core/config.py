import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Lấy thư mục gốc của toàn bộ dự án
# Giả sử cấu trúc là: project_root/backend_ai/app/core/config.py
# Và thư mục data nằm ở: project_root/data_pipeline/db_setup/
BASE_DIR = Path(__file__).resolve().parents[3] 
DB_DIR = BASE_DIR / "data_pipeline" / "db_setup"

# ==========================================
# CẤU HÌNH TỪ TEAM DATA
# ==========================================
SQLITE_PATH = str(DB_DIR / "knowledge_base.sqlite")
FAISS_PATH = str(DB_DIR / "knowledge_base.faiss")
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# ==========================================
# CẤU HÌNH AI & API
# ==========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_TEMPERATURE = 0.0 
LLM_MODEL = "gpt-4o-mini"
USER_IDENTIFIER_KEY = "thread_id"