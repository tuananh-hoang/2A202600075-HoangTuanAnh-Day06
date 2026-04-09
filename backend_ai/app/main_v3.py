"""
main.py
FastAPI app — response schema phản ánh đầy đủ spec:
confidence, sources, escalate flag, feedback endpoint.
Đặt tại: backend_ai/app/main.py
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# LIFESPAN
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading RAG agent...")
    from app.core.agent_graph import app_graph, get_retriever  # noqa
    get_retriever()   # trigger FAISS + reranker load ngay khi startup
    logger.info("RAG agent ready.")
    yield


app = FastAPI(title="Chatbot Tài Xế Xanh SM API", lifespan=lifespan)


# ──────────────────────────────────────────────
# SCHEMA
# ──────────────────────────────────────────────

class ChatQuery(BaseModel):
    message: str
    thread_id: str = ""      # giữ lịch sử hội thoại qua MemorySaver


class SourceItem(BaseModel):
    title: str
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
    return {"message": "Chatbot Tài Xế Xanh SM API — RAG enabled"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    if not query.message.strip():
        raise HTTPException(status_code=400, detail="message không được để trống.")

    thread_id = query.thread_id or str(uuid.uuid4())

    try:
        from app.core.agent_graph import app_graph

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

        # Lấy các field từ state
        confidence  = result.get("confidence", "low")
        query_type  = result.get("query_type", "general")
        escalate    = result.get("escalate", False)
        raw_sources = result.get("sources", [])

        # Khi cần clarification: confidence=high, escalate=False nhưng reply là câu hỏi
        if result.get("needs_clarification"):
            confidence = "high"
            escalate   = False

        sources = [
            SourceItem(
                title=s.get("title", ""),
                chunk_id=s.get("chunk_id", -1),
                rerank_score=s.get("rerank_score", 0.0),
            )
            for s in raw_sources
        ]

        return ChatResponse(
            reply=reply,
            confidence=confidence,
            query_type=query_type,
            escalate=escalate,
            sources=sources,
            thread_id=thread_id,
        )

    except Exception as e:
        logger.error("Agent error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi xử lý câu hỏi.")


@app.post("/feedback")
async def feedback(payload: FeedbackPayload):
    """
    Spec Path 3: tài xế bấm 'Câu trả lời này không đúng'.
    Log vào error queue để ops team review trong 24h.
    Production: thay logger.info bằng write vào DB hoặc gửi Slack webhook.
    """
    logger.info(
        "FEEDBACK | thread=%s idx=%d reason=%s detail=%s",
        payload.thread_id,
        payload.message_index,
        payload.reason,
        payload.detail,
    )
    return {"status": "received", "message": "Cảm ơn phản hồi của bạn. Chúng tôi sẽ xem xét trong 24h."}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)