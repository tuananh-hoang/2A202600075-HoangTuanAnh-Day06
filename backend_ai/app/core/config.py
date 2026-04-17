"""
✅ PRODUCTION-READY Config Management

Centralized configuration với validation và 12-Factor App principles:
- Tất cả config từ environment variables
- Không hardcode secrets
- Validation fail-fast
- Type-safe với Pydantic
"""
import os
import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file nếu có
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parents[3]

# For Docker/Railway deployment, check if running in container
if os.path.exists("/app/data_pipeline"):
    DB_DIR = Path("/app/data_pipeline/db_setup")
else:
    DB_DIR = BASE_DIR / "data_pipeline" / "db_setup"

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Production-ready settings với validation.
    Tất cả config đọc từ environment variables.
    """
    
    # ==========================================
    # SERVER CONFIG
    # ==========================================
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"  # development | staging | production
    debug: bool = False
    
    # ==========================================
    # APP INFO
    # ==========================================
    app_name: str = "Chatbot Tài Xế Xanh SM"
    app_version: str = "1.0.0"
    
    # ==========================================
    # AI & LLM CONFIG
    # ==========================================
    openai_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    ai_temperature: float = 0.0
    max_tokens: int = 500
    
    # ==========================================
    # RAG & RETRIEVAL CONFIG
    # ==========================================
    sqlite_path: str = str(DB_DIR / "knowledge_base.sqlite")
    faiss_path: str = str(DB_DIR / "knowledge_base.faiss")
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    retrieval_top_k: int = 5
    rerank_top_k: int = 5
    
    # ==========================================
    # SECURITY CONFIG
    # ==========================================
    agent_api_key: Optional[str] = None  # API key cho authentication
    allowed_origins: str = "*"  # CORS origins (comma-separated)
    
    # ==========================================
    # REDIS CONFIG (for rate limiting & stateless)
    # ==========================================
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False  # Enable khi có Redis
    
    # ==========================================
    # RATE LIMITING CONFIG
    # ==========================================
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 10
    
    # ==========================================
    # COST GUARD CONFIG
    # ==========================================
    cost_guard_enabled: bool = False
    monthly_budget_usd: float = 10.0
    
    # ==========================================
    # LOGGING CONFIG
    # ==========================================
    log_level: str = "INFO"
    log_format: str = "json"  # json | text
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Allow AGENT_API_KEY to map to agent_api_key
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def validate_production(self) -> None:
        """
        Validation cho production environment.
        Fail fast nếu thiếu config quan trọng.
        """
        warnings = []
        errors = []
        
        # Check OpenAI API key
        if not self.openai_api_key:
            warnings.append("⚠️  OPENAI_API_KEY not set — using mock LLM")
        
        # Check production-specific requirements
        if self.environment == "production":
        # Check cả Pydantic field lẫn os.environ trực tiếp
            api_key = self.agent_api_key or os.environ.get("AGENT_API_KEY")
        if not api_key:
            errors.append("❌ AGENT_API_KEY must be set in production!")
        else:
            self.agent_api_key = api_key  # Đảm bảo field được set

        # Check file paths
        if not Path(self.sqlite_path).exists():
            warnings.append(f"⚠️  SQLite DB not found: {self.sqlite_path}")
        if not Path(self.faiss_path).exists():
            warnings.append(f"⚠️  FAISS index not found: {self.faiss_path}")
        
        # Log warnings
        for warning in warnings:
            logger.warning(warning)
        
        # Raise errors
        if errors:
            error_msg = "\n".join(errors)
            raise ValueError(f"Configuration validation failed:\n{error_msg}")
        
        logger.info(f"✅ Configuration validated for environment: {self.environment}")
    
    def get_allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS string to list."""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]


# ==========================================
# SINGLETON INSTANCE
# ==========================================
settings = Settings()

# Validate on import (fail fast)
try:
    settings.validate_production()
except ValueError as e:
    if settings.environment == "production":
        raise  # Fail hard in production
    else:
        logger.warning(f"Config validation warning: {e}")


# ==========================================
# BACKWARD COMPATIBILITY (for existing code)
# ==========================================
SQLITE_PATH = settings.sqlite_path
FAISS_PATH = settings.faiss_path
EMBEDDING_MODEL = settings.embedding_model
OPENAI_API_KEY = settings.openai_api_key
AI_TEMPERATURE = settings.ai_temperature
LLM_MODEL = settings.llm_model
USER_IDENTIFIER_KEY = "thread_id"