"""
main_v3.py
FastAPI app — Production-ready với config management + security
Response schema: confidence, sources, escalate, feedback endpoint
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

# Import settings
from app.core.config import settings

# Import security
from app.auth import verify_api_key

# Import Redis-based security (with fallback to in-memory)
from app.rate_limiter_redis import check_rate_limit_redis, get_rate_limit_stats_redis
from app.cost_guard_redis import check_budget_redis, record_usage_redis, get_usage_redis
from app.redis_client import RedisClient

# Setup logging theo config
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
if settings.log_format == "json":
    logging.basicConfig(
        level=log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )
else:
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s | %(message)s",
    )

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# LIFESPAN
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "port": settings.port,
    }))
    
    # Initialize Redis connection
    if settings.redis_enabled:
        redis_client = RedisClient.get_client()
        if redis_client:
            logger.info("✅ Redis initialized successfully")
        else:
            logger.warning("⚠️ Redis initialization failed, using in-memory fallback")
    
    logger.info("Loading RAG agent...")
    from app.core.agent_graph_v4 import app_graph, get_retriever  # noqa
    get_retriever()   # trigger FAISS + reranker load ngay khi startup
    logger.info("RAG agent ready.")
    
    yield
    
    # Graceful shutdown
    logger.info("Shutting down gracefully...")
    RedisClient.close()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    # Ẩn /docs trong production
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Thêm security headers vào mọi response."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ──────────────────────────────────────────────
# SCHEMA
# ──────────────────────────────────────────────

class ChatQuery(BaseModel):
    message: str
    thread_id: str = ""      # giữ lịch sử hội thoại qua MemorySaver


class SourceItem(BaseModel):
    title: str
    url: Optional[str] = None
    chunk_id: int = -1
    rerank_score: float = 0.0


class ChatResponse(BaseModel):
    reply: str
    confidence: str          # "high" | "low"
    query_type: str          # "policy" | "incident" | "general"
    escalate: bool           # True → frontend hiện badge "Cần xác nhận" + nút hotline
    sources: List[SourceItem] = []
    thread_id: str = ""


class FeedbackPayload(BaseModel):
    thread_id: str
    message_index: int = -1
    reason: str              # "old_info" | "wrong_case" | "other"
    detail: str = ""


# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
    }


@app.get("/health")
async def health():
    """
    Liveness probe - container còn sống không?
    Kubernetes/Railway sẽ restart container nếu endpoint này fail.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/ready")
async def ready():
    """
    Readiness probe - container sẵn sàng nhận traffic chưa?
    Kubernetes/Railway sẽ không route traffic nếu endpoint này fail.
    
    Checks:
    - Redis connection (nếu enabled)
    - RAG agent loaded
    """
    checks = {
        "status": "ready",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": {}
    }
    
    # Check Redis
    if settings.redis_enabled:
        redis_healthy = RedisClient.is_healthy()
        checks["checks"]["redis"] = "ok" if redis_healthy else "degraded"
        if not redis_healthy:
            checks["status"] = "degraded"
            logger.warning("Readiness check: Redis is down, using fallback")
    else:
        checks["checks"]["redis"] = "disabled"
    
    # Check RAG agent (simple check - nếu import được là ok)
    try:
        from app.core.agent_graph_v4 import app_graph  # noqa
        checks["checks"]["rag_agent"] = "ok"
    except Exception as e:
        checks["checks"]["rag_agent"] = f"error: {str(e)}"
        checks["status"] = "not_ready"
        logger.error(f"Readiness check: RAG agent not loaded: {e}")
    
    # Return 503 nếu not ready, 200 nếu ready hoặc degraded
    status_code = 503 if checks["status"] == "not_ready" else 200
    
    from fastapi.responses import JSONResponse
    return JSONResponse(content=checks, status_code=status_code)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    query: ChatQuery,
    request: Request,
    user_id: str = Depends(verify_api_key),           # ✅ Auth required
    _rate: dict = Depends(check_rate_limit_redis),     # ✅ Rate limiting (Redis)
    _budget: None = Depends(check_budget_redis),       # ✅ Cost guard (Redis)
):
    if not query.message.strip():
        raise HTTPException(status_code=400, detail="message không được để trống.")

    thread_id = query.thread_id or str(uuid.uuid4())

    try:
        from app.core.agent_graph_v4 import app_graph

        result = app_graph.invoke(
            {"messages": [HumanMessage(content=query.message)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # Lấy reply từ message cuối (AIMessage)
        last_ai = next(
            (m for m in reversed(result["messages"]) if hasattr(m, "content")),
            None,
        )
        reply = last_ai.content if last_ai else "Đã xảy ra lỗi, vui lòng thử lại."

        # Lấy các field từ state với fallback an toàn
        confidence  = result.get("confidence") or "low"
        query_type  = result.get("query_type") or "general"
        escalate    = bool(result.get("escalate", False))
        raw_sources = result.get("sources") or []

        # Log state
        logger.info(json.dumps({
            "event": "chat_response",
            "user_id": user_id,
            "thread_id": thread_id,
            "confidence": confidence,
            "query_type": query_type,
            "escalate": escalate,
            "sources_count": len(raw_sources),
        }))

        # Khi cần clarification
        if result.get("needs_clarification"):
            confidence = "high"
            escalate   = False

        # Estimate token usage và record cost
        # (mock: 1 word ≈ 2 tokens)
        input_tokens = len(query.message.split()) * 2
        output_tokens = len(reply.split()) * 2
        record_usage_redis(user_id, input_tokens, output_tokens)

        # Chuyển đổi sources sang SourceItem model
        sources = []
        for s in raw_sources:
            if isinstance(s, dict):
                sources.append(SourceItem(
                    title=str(s.get("title", "Tài liệu Xanh SM")),
                    url=str(s.get("url", "")),
                    chunk_id=int(s.get("chunk_id", -1)),
                    rerank_score=float(s.get("rerank_score", 0.0))
                ))
            elif isinstance(s, str):
                sources.append(SourceItem(title=s))

        return ChatResponse(
            reply=reply,
            confidence=str(confidence),
            query_type=str(query_type),
            escalate=escalate,
            sources=sources,
            thread_id=thread_id,
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions (auth, rate limit, etc.)
    except Exception as e:
        logger.error(json.dumps({
            "event": "chat_error",
            "user_id": user_id,
            "thread_id": thread_id,
            "error": str(e),
        }), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý câu hỏi: {str(e)}")


@app.post("/feedback")
async def feedback(
    payload: FeedbackPayload,
    user_id: str = Depends(verify_api_key),   # ✅ Auth required
):
    """
    Spec Path 3: tài xế bấm 'Câu trả lời này không đúng'.
    Log vào error queue để ops team review trong 24h.
    Production: thay logger.info bằng write vào DB hoặc gửi Slack webhook.
    """
    logger.info(json.dumps({
        "event": "feedback",
        "user_id": user_id,
        "thread_id": payload.thread_id,
        "message_index": payload.message_index,
        "reason": payload.reason,
        "detail": payload.detail,
    }))
    return {"status": "received", "message": "Cảm ơn phản hồi của bạn. Chúng tôi sẽ xem xét trong 24h."}


@app.get("/usage")
async def usage(user_id: str = Depends(verify_api_key)):
    """
    Xem usage của user hiện tại.
    Trả về: số requests, tokens đã dùng, budget còn lại.
    """
    return {
        "user_id": user_id,
        "cost": get_usage_redis(user_id),
        "rate_limit": get_rate_limit_stats_redis(user_id),
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add backend_ai to path để import app module
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    import uvicorn
    uvicorn.run(
        "app.main_v3:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
