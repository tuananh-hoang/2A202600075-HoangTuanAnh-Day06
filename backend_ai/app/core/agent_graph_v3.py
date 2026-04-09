"""
agent_graph_v3.py
Multi-node LangGraph theo spec: classify → retrieve → answer → escalate
"""

from __future__ import annotations

import json
import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.core import config
from app.prompts.system_prompt import ANSWER_PROMPT, CLASSIFY_PROMPT, ESCALATE_PROMPT
from app.utils.retrieval_advanced import HybridRAGRetriever

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

    # Kết quả từ classify node
    query_type: str              # "policy" | "incident" | "general"
    needs_clarification: bool
    clarification_question: str

    # Kết quả từ retrieve node
    retrieved_context: str       # text ghép sẵn để inject vào prompt
    sources: list                # [{"title": str, "chunk_id": int}]

    # Kết quả từ answer node
    answer: str
    confidence: str              # "high" | "low"
    has_money_figure: bool

    # Flag điều hướng
    escalate: bool


# ──────────────────────────────────────────────
# LLM
# ──────────────────────────────────────────────

llm = ChatOpenAI(
    model=config.LLM_MODEL,
    temperature=config.AI_TEMPERATURE,
)

# ──────────────────────────────────────────────
# RETRIEVER (singleton — load FAISS + reranker 1 lần)
# ──────────────────────────────────────────────

_retriever: HybridRAGRetriever | None = None

def get_retriever() -> HybridRAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRAGRetriever(candidate_k=20, final_k=5)
        logger.info("HybridRAGRetriever initialized.")
    return _retriever


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Parse JSON từ LLM output — xử lý trường hợp LLM bọc trong ```json ... ```.
    """
    text = text.strip()
    # Strip markdown code fences nếu có
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: tìm object JSON đầu tiên trong text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def _get_user_query(state: AgentState) -> str:
    """Lấy câu hỏi mới nhất từ user trong messages."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


# ──────────────────────────────────────────────
# NODE 1: CLASSIFY
# ──────────────────────────────────────────────

def classify_node(state: AgentState) -> dict:
    """
    Phân loại query và quyết định có cần hỏi lại không.
    Trả về JSON: {query_type, needs_clarification, clarification_question}

    Nếu needs_clarification=True → trả câu hỏi làm rõ ngay, kết thúc turn.
    Nếu False → tiếp tục sang retrieve.
    """
    query = _get_user_query(state)

    response = llm.invoke([
        SystemMessage(content=CLASSIFY_PROMPT),
        HumanMessage(content=query),
    ])

    try:
        parsed = _extract_json(response.content)
        query_type          = parsed.get("query_type", "general")
        needs_clarification = bool(parsed.get("needs_clarification", False))
        clarification_q     = parsed.get("clarification_question", "")
    except Exception as e:
        logger.warning("classify_node JSON parse failed: %s", e)
        query_type          = "general"
        needs_clarification = False
        clarification_q     = ""

    logger.info("classify_node: type=%s clarify=%s", query_type, needs_clarification)

    new_state: dict = {
        "query_type": query_type,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_q,
    }

    # Nếu cần làm rõ: ghi câu hỏi vào messages luôn để trả về frontend
    if needs_clarification and clarification_q:
        new_state["messages"] = [AIMessage(content=f"Dạ, {clarification_q}")]

    return new_state


# ──────────────────────────────────────────────
# NODE 2: RETRIEVE
# ──────────────────────────────────────────────

def retrieve_node(state: AgentState) -> dict:
    """
    Hybrid Search (BM25 + FAISS) + Cross-encoder Reranker.
    Trả về context text và danh sách sources kèm metadata.
    """
    query = _get_user_query(state)
    retriever = get_retriever()
    chunks = retriever.retrieve(query)

    # Ghép context để inject vào answer prompt
    parts = []
    sources = []
    for i, chunk in enumerate(chunks, start=1):
        source_title = chunk.metadata.get("source", "Tài liệu Xanh SM")
        parts.append(f"[{i}] {source_title}\n{chunk.page_content}")
        sources.append({
            "title": source_title,
            "chunk_id": chunk.metadata.get("chunk_id", -1),
            "rerank_score": chunk.metadata.get("rerank_score", 0.0),
        })

    context = "\n\n".join(parts) if parts else ""
    logger.info("retrieve_node: %d chunks retrieved", len(chunks))

    return {
        "retrieved_context": context,
        "sources": sources,
    }


# ──────────────────────────────────────────────
# NODE 3: ANSWER
# ──────────────────────────────────────────────

def answer_node(state: AgentState) -> dict:
    """
    Sinh câu trả lời từ context đã retrieve.
    Trả về JSON: {answer, confidence, has_money_figure}

    Sau node này:
    - confidence=low → sang escalate_node
    - has_money_figure=true + confidence=low → bắt buộc escalate
    - confidence=high → kết thúc
    """
    query   = _get_user_query(state)
    context = state.get("retrieved_context", "")

    if not context:
        # Không có context → escalate ngay, không cần gọi LLM
        return {
            "answer": "",
            "confidence": "low",
            "has_money_figure": False,
            "escalate": True,
        }

    user_msg = (
        f"CONTEXT:\n{context}\n\n"
        f"---\n"
        f"CÂU HỎI: {query}"
    )

    response = llm.invoke([
        SystemMessage(content=ANSWER_PROMPT),
        HumanMessage(content=user_msg),
    ])

    try:
        parsed          = _extract_json(response.content)
        answer          = parsed.get("answer", "")
        confidence      = parsed.get("confidence", "low")
        has_money_figure = bool(parsed.get("has_money_figure", False))
    except Exception as e:
        logger.warning("answer_node JSON parse failed: %s", e)
        answer           = response.content
        confidence       = "low"
        has_money_figure = False

    # Spec: nếu có số tiền nhưng confidence thấp → bắt buộc escalate
    should_escalate = (confidence == "low") or (has_money_figure and confidence != "high")

    logger.info(
        "answer_node: confidence=%s money=%s escalate=%s",
        confidence, has_money_figure, should_escalate,
    )

    return {
        "answer": answer,
        "confidence": confidence,
        "has_money_figure": has_money_figure,
        "escalate": should_escalate,
        "messages": [AIMessage(content=answer)] if not should_escalate else [],
    }


# ──────────────────────────────────────────────
# NODE 4: ESCALATE
# ──────────────────────────────────────────────

def escalate_node(state: AgentState) -> dict:
    """
    Khi confidence thấp hoặc không tìm thấy thông tin:
    - Tóm tắt ngắn những gì tìm được (nếu có)
    - Gợi ý hotline 1900 2088
    - Badge "Cần xác nhận" được xử lý ở frontend dựa vào confidence=low
    """
    query   = _get_user_query(state)
    context = state.get("retrieved_context", "")

    context_hint = (
        f"Thông tin gần nhất tìm được:\n{context[:500]}..."
        if context else
        "Không tìm thấy tài liệu liên quan."
    )

    response = llm.invoke([
        SystemMessage(content=ESCALATE_PROMPT),
        HumanMessage(content=f"Câu hỏi: {query}\n\n{context_hint}"),
    ])

    escalate_answer = response.content
    logger.info("escalate_node: triggered")

    return {
        "answer": escalate_answer,
        "messages": [AIMessage(content=escalate_answer)],
    }


# ──────────────────────────────────────────────
# ROUTERS (điều kiện rẽ nhánh)
# ──────────────────────────────────────────────

def route_after_classify(state: AgentState) -> str:
    """
    Sau classify:
    - needs_clarification=True → dừng lại, trả câu hỏi làm rõ
    - False → retrieve
    """
    if state.get("needs_clarification"):
        return END
    return "retrieve"


def route_after_answer(state: AgentState) -> str:
    """
    Sau answer:
    - escalate=True → escalate_node
    - False → kết thúc
    """
    if state.get("escalate"):
        return "escalate"
    return END


# ──────────────────────────────────────────────
# BUILD GRAPH
# ──────────────────────────────────────────────

workflow = StateGraph(AgentState)

workflow.add_node("classify", classify_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("answer",   answer_node)
workflow.add_node("escalate", escalate_node)

workflow.set_entry_point("classify")

workflow.add_conditional_edges("classify", route_after_classify, {
    END:        END,
    "retrieve": "retrieve",
})
workflow.add_edge("retrieve", "answer")
workflow.add_conditional_edges("answer", route_after_answer, {
    END:        END,
    "escalate": "escalate",
})
workflow.add_edge("escalate", END)

memory    = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)