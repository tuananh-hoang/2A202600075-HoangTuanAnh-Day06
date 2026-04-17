"""
auth.py — API Key Authentication

Simple API key auth cho Chatbot Xanh SM.
Client gửi key qua header: X-API-Key: <key>
"""
import hashlib
import hmac
import logging
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Header name cho API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_key(key: str) -> str:
    """Hash key để so sánh an toàn hoặc dùng làm định danh."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(x_api_key: str = Security(api_key_header)) -> str:
    """
    FastAPI Dependency: verify API key từ X-API-Key header.

    Returns:
        user_id (str): derived từ API key

    Raises:
        HTTPException 401: nếu không có key hoặc key sai
    """
    # Fallback cho development mode
    if not settings.agent_api_key:
        logger.warning("⚠️ AGENT_API_KEY not set — auth disabled (dev mode)")
        return "dev-user"

    # Block nếu không truyền key
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include header: X-API-Key: <your-key>",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Sử dụng hmac.compare_digest để chống timing attack chuẩn xác
    expected_key = settings.agent_api_key
    if not hmac.compare_digest(x_api_key, expected_key):
        # Chỉ log một phần hash để debug, tuyệt đối không log raw key sai của user
        logger.warning(f"Invalid API key attempt. Key hash start: {_hash_key(x_api_key)[:8]}")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Derive user_id từ key để sử dụng cho Rate Limiter / Cost Guard
    user_id = f"user_{_hash_key(x_api_key)[:8]}"
    logger.debug(f"Authenticated user: {user_id}")
    return user_id