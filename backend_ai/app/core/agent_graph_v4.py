"""
agent_graph_v4.py  (fixed)
Multi-node LangGraph: classify → retrieve → answer → escalate

Fix so với v4 gốc:
  [FIX-1] retrieve_node: retriever.invoke() → _get_relevant_documents()
  [FIX-2] _get_user_query → _build_conversation_context() truyền lịch sử vào LLM
  [FIX-3] answer_node: chỉ escalate khi context rỗng HOẶC has_money_figure+low;
          partial answer vẫn trả về kèm confidence=low (badge ở frontend)
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
from app.prompts.system_prompt_v4 import (
    ANSWER_DRIVER_PROMPT,
    ANSWER_PROSPECT_PROMPT,
    CLASSIFY_PROMPT,
    ESCALATE_DRIVER_PROMPT,
    ESCALATE_PROSPECT_PROMPT,
)
from app.utils.retrieval_advanced import HybridRAGRetriever

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_persona: str
    query_type: str
    needs_clarification: bool
    clarification_question: str
    retrieved_context: str
    sources: list
    answer: str
    confidence: str
    has_money_figure: bool
    escalate: bool


# ──────────────────────────────────────────────
# LLM + RETRIEVER
# ──────────────────────────────────────────────

llm = ChatOpenAI(model=config.LLM_MODEL, temperature=config.AI_TEMPERATURE)

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
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def _get_user_query(state: AgentState) -> str:
    """Lấy câu hỏi mới nhất từ user."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


# ── [FIX-2] Build conversation history để truyền vào LLM ──────────────────

def _build_messages_with_history(
    system_prompt: str,
    state: AgentState,
    max_turns: int = 6,
) -> list:
    """
    Ghép SystemMessage + N turn hội thoại gần nhất vào message list.

    max_turns: số lượng HumanMessage + AIMessage gần nhất giữ lại.
    Giới hạn để tránh tràn context window với corpus policy dài.

    Không giữ ToolMessage / các message nội bộ — chỉ giữ Human + AI
    để LLM hiểu ngữ cảnh hội thoại mà không thấy noise từ raw retrieval.
    """
    all_msgs = state["messages"]

    # Lọc chỉ HumanMessage và AIMessage
    dialogue = [
        m for m in all_msgs
        if isinstance(m, (HumanMessage, AIMessage))
    ]

    # Giữ lại max_turns * 2 message cuối (mỗi turn = 1 Human + 1 AI)
    recent = dialogue[-(max_turns * 2):]

    return [SystemMessage(content=system_prompt)] + recent


# ──────────────────────────────────────────────
# NODE 1: CLASSIFY
# ──────────────────────────────────────────────

def classify_node(state: AgentState) -> dict:
    """
    Phân loại query, xác định persona.
    [FIX-2]: truyền lịch sử hội thoại vào LLM để classify đúng
    với câu hỏi tham chiếu như "cái bạn vừa nói ý".
    """
    # [FIX-2] dùng history thay vì chỉ query đơn lẻ
    messages = _build_messages_with_history(CLASSIFY_PROMPT, state, max_turns=4)

    response = llm.invoke(messages)

    try:
        parsed              = _extract_json(response.content)
        user_persona        = parsed.get("user_persona", "driver")
        query_type          = parsed.get("query_type", "general")
        needs_clarification = bool(parsed.get("needs_clarification", False))
        clarification_q     = parsed.get("clarification_question", "")
    except Exception as e:
        logger.warning("classify_node JSON parse failed: %s", e)
        user_persona        = "driver"
        query_type          = "general"
        needs_clarification = False
        clarification_q     = ""

    logger.info(
        "classify_node: persona=%s type=%s clarify=%s",
        user_persona, query_type, needs_clarification,
    )

    new_state: dict = {
        "user_persona": user_persona,
        "query_type": query_type,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_q,
    }

    if needs_clarification and clarification_q:
        new_state["messages"] = [AIMessage(content=f"Dạ, {clarification_q}")]

    return new_state


# ──────────────────────────────────────────────
# NODE 2: RETRIEVE
# ──────────────────────────────────────────────

def retrieve_node(state: AgentState) -> dict:
    """
    Hybrid Search (BM25 + FAISS) + Cross-encoder Reranker.

    [FIX-1] Dùng _get_relevant_documents() thay vì invoke().
    BaseRetriever không có method invoke() — gọi invoke() trả về
    list rỗng âm thầm hoặc crash, khiến context luôn rỗng
    → answer_node luôn escalate → trả lời ít.
    """
    query = _get_user_query(state)
    retriever = get_retriever()

    # [FIX-1] gọi đúng method
    chunks = retriever._get_relevant_documents(query, run_manager=None)

    parts: list[str] = []
    sources: list[dict] = []
    for i, chunk in enumerate(chunks, start=1):
        source_title = chunk.metadata.get("source", "Tài liệu Xanh SM")
        parts.append(f"[{i}] {source_title}\n{chunk.page_content}")
        sources.append({
            "title": source_title,
            "chunk_id": chunk.metadata.get("chunk_id", -1),
            "rerank_score": chunk.metadata.get("rerank_score", 0.0),
        })

    context = "\n\n".join(parts) if parts else ""
    logger.info("retrieve_node: %d chunks retrieved for query='%.60s'", len(chunks), query)

    return {"retrieved_context": context, "sources": sources}


# ──────────────────────────────────────────────
# NODE 3: ANSWER
# ──────────────────────────────────────────────

def answer_node(state: AgentState) -> dict:
    """
    Sinh câu trả lời từ context.

    [FIX-2] Truyền lịch sử hội thoại vào LLM — giúp trả lời
    đúng câu hỏi tham chiếu như "cái bạn vừa nói" hay "điều khoản đó".

    [FIX-3] Logic escalate được nới lỏng:
    - Context rỗng hoàn toàn → escalate (không có gì để trả lời)
    - has_money_figure=True + confidence=low → escalate (zero hallucination về tiền)
    - Còn lại (kể cả confidence=low) → trả lời partial + giữ confidence=low
      để frontend hiện badge "Cần xác nhận", KHÔNG escalate
    """
    query   = _get_user_query(state)
    context = state.get("retrieved_context", "")
    persona = state.get("user_persona", "driver")

    # [FIX-3] Chỉ escalate ngay khi không có context gì
    if not context:
        logger.info("answer_node: no context → escalate")
        return {
            "answer": "",
            "confidence": "low",
            "has_money_figure": False,
            "escalate": True,
        }

    answer_prompt = (
        ANSWER_PROSPECT_PROMPT if persona == "prospect"
        else ANSWER_DRIVER_PROMPT
    )

    # [FIX-2] Truyền lịch sử + context vào LLM
    history_messages = _build_messages_with_history(answer_prompt, state, max_turns=4)

    # Inject context + query mới nhất vào message cuối
    # Thay HumanMessage cuối bằng version có context đính kèm
    user_msg_with_context = (
        f"CONTEXT:\n{context}\n\n"
        f"---\n"
        f"CÂU HỎI: {query}"
    )
    # Giữ nguyên history nhưng override message cuối
    messages_to_send = history_messages[:-1] + [
        HumanMessage(content=user_msg_with_context)
    ]

    response = llm.invoke(messages_to_send)

    try:
        parsed           = _extract_json(response.content)
        answer           = parsed.get("answer", "")
        confidence       = parsed.get("confidence", "low")
        has_money_figure = bool(parsed.get("has_money_figure", False))
    except Exception as e:
        logger.warning("answer_node JSON parse failed: %s — dùng raw content", e)
        answer           = response.content
        confidence       = "low"
        has_money_figure = False

    # [FIX-3] Chỉ escalate khi có số tiền không chắc chắn
    # Với confidence=low nhưng không có số tiền → vẫn trả lời + badge ở frontend
    should_escalate = has_money_figure and confidence != "high"

    logger.info(
        "answer_node: persona=%s confidence=%s money=%s escalate=%s",
        persona, confidence, has_money_figure, should_escalate,
    )

    return {
        "answer": answer,
        "confidence": confidence,
        "has_money_figure": has_money_figure,
        "escalate": should_escalate,
        # Luôn ghi answer vào messages dù confidence thấp
        # Frontend dùng confidence để hiện badge, không phải để ẩn answer
        "messages": [AIMessage(content=answer)],
    }


# ──────────────────────────────────────────────
# NODE 4: ESCALATE
# ──────────────────────────────────────────────

def escalate_node(state: AgentState) -> dict:
    """
    Chỉ chạy khi: context rỗng, hoặc has_money_figure=True + confidence=low.
    [FIX-2] Truyền lịch sử để escalate message không bị lặp câu hỏi.
    """
    query   = _get_user_query(state)
    context = state.get("retrieved_context", "")
    persona = state.get("user_persona", "driver")

    context_hint = (
        f"Thông tin gần nhất tìm được:\n{context[:500]}..."
        if context else
        "Không tìm thấy tài liệu liên quan."
    )

    escalate_prompt = (
        ESCALATE_PROSPECT_PROMPT if persona == "prospect"
        else ESCALATE_DRIVER_PROMPT
    )

    # [FIX-2] truyền history vào escalate
    messages = _build_messages_with_history(escalate_prompt, state, max_turns=3)
    messages[-1] = HumanMessage(
        content=f"Câu hỏi: {query}\n\n{context_hint}"
    )

    response = llm.invoke(messages)
    escalate_answer = response.content
    logger.info("escalate_node: persona=%s triggered", persona)

    return {
        "answer": escalate_answer,
        "messages": [AIMessage(content=escalate_answer)],
    }


# ──────────────────────────────────────────────
# ROUTERS
# ──────────────────────────────────────────────

def route_after_classify(state: AgentState) -> str:
    if state.get("needs_clarification"):
        return END
    return "retrieve"


def route_after_answer(state: AgentState) -> str:
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