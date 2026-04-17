"""
agent_graph_v4.py  (fixed)
Multi-node LangGraph: classify → rephrase → retrieve → answer → escalate
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
    REPHRASE_PROMPT,
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
    search_query: str           
    retrieved_context: str
    sources: list
    answer: str
    confidence: str
    has_money_figure: bool
    escalate: bool


# ──────────────────────────────────────────────
# LLM + RETRIEVER
# ──────────────────────────────────────────────

_llm: ChatOpenAI | None = None
_retriever: HybridRAGRetriever | None = None

def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=config.LLM_MODEL, temperature=config.AI_TEMPERATURE)
        logger.info("ChatOpenAI initialized.")
    return _llm

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


def _build_messages_with_history(
    system_prompt: str,
    state: AgentState,
    max_turns: int = 6,
) -> list:
    all_msgs = state["messages"]
    dialogue = [
        m for m in all_msgs
        if isinstance(m, (HumanMessage, AIMessage))
    ]
    recent = dialogue[-(max_turns * 2):]
    return [SystemMessage(content=system_prompt)] + recent


# ──────────────────────────────────────────────
# NODE 1: CLASSIFY
# ──────────────────────────────────────────────

def classify_node(state: AgentState) -> dict:
    messages = _build_messages_with_history(CLASSIFY_PROMPT, state, max_turns=4)
    response = get_llm().invoke(messages)
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
# NODE 1.5: REPHRASE
# ──────────────────────────────────────────────

def rephrase_node(state: AgentState) -> dict:
    messages = _build_messages_with_history(REPHRASE_PROMPT, state, max_turns=4)
    response = get_llm().invoke(messages)
    try:
        parsed = _extract_json(response.content)
        search_query = parsed.get("search_query", _get_user_query(state))
    except:
        search_query = _get_user_query(state)
    logger.info(f"rephrase_node: target_query='{search_query}'")
    return {"search_query": search_query}


# ──────────────────────────────────────────────
# NODE 2: RETRIEVE
# ──────────────────────────────────────────────

def retrieve_node(state: AgentState) -> dict:
    search_query = state.get("search_query") or _get_user_query(state)
    retriever = get_retriever()
    chunks = retriever._get_relevant_documents(search_query, run_manager=None)
    parts: list[str] = []
    sources: list[dict] = []
    for i, chunk in enumerate(chunks, start=1):
        source_title = chunk.metadata.get("source", "Tài liệu Xanh SM")
        parts.append(f"[{i}] {source_title}\n{chunk.page_content}")
        sources.append({
            "title": source_title,
            "url": chunk.metadata.get("url", ""),
            "chunk_id": chunk.metadata.get("chunk_id", -1),
            "rerank_score": chunk.metadata.get("rerank_score", 0.0),
        })
    context = "\n\n".join(parts) if parts else ""
    logger.info("retrieve_node: %d chunks retrieved for query='%.60s'", len(chunks), search_query)
    return {"retrieved_context": context, "sources": sources}


# ──────────────────────────────────────────────
# NODE 3: ANSWER
# ──────────────────────────────────────────────

def answer_node(state: AgentState) -> dict:
    query   = _get_user_query(state)
    context = state.get("retrieved_context", "")
    persona = state.get("user_persona", "driver")

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

    history_messages = _build_messages_with_history(answer_prompt, state, max_turns=4)
    user_msg_with_context = (
        f"CONTEXT:\n{context}\n\n"
        f"---\n"
        f"CÂU HỎI: {query}"
    )
    messages_to_send = history_messages[:-1] + [
        HumanMessage(content=user_msg_with_context)
    ]
    response = get_llm().invoke(messages_to_send)
    try:
        parsed           = _extract_json(response.content)
        answer           = parsed.get("answer", "")
        confidence       = parsed.get("confidence", "low")
        has_money_figure = bool(parsed.get("has_money_figure", False))
    except Exception as e:
        logger.warning("answer_node JSON parse failed: %s", e)
        answer           = response.content
        confidence       = "low"
        has_money_figure = False

    should_escalate = has_money_figure and confidence != "high"
    logger.info("answer_node: persona=%s confidence=%s money=%s escalate=%s", persona, confidence, has_money_figure, should_escalate)

    return {
        "answer": answer,
        "confidence": confidence,
        "has_money_figure": has_money_figure,
        "escalate": should_escalate,
        "messages": [AIMessage(content=answer)],
    }


# ──────────────────────────────────────────────
# NODE 4: ESCALATE
# ──────────────────────────────────────────────

def escalate_node(state: AgentState) -> dict:
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
    messages = _build_messages_with_history(escalate_prompt, state, max_turns=3)
    messages[-1] = HumanMessage(
        content=f"Câu hỏi: {query}\n\n{context_hint}"
    )
    response = get_llm().invoke(messages)
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
    return "rephrase"


def route_after_answer(state: AgentState) -> str:
    if state.get("escalate"):
        return "escalate"
    return END


# ──────────────────────────────────────────────
# BUILD GRAPH
# ──────────────────────────────────────────────

workflow = StateGraph(AgentState)

workflow.add_node("classify", classify_node)
workflow.add_node("rephrase", rephrase_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("answer",   answer_node)
workflow.add_node("escalate", escalate_node)

workflow.set_entry_point("classify")

workflow.add_conditional_edges("classify", route_after_classify, {
    END:        END,
    "rephrase": "rephrase",
})
workflow.add_edge("rephrase", "retrieve")
workflow.add_edge("retrieve", "answer")
workflow.add_conditional_edges("answer", route_after_answer, {
    END:        END,
    "escalate": "escalate",
})
workflow.add_edge("escalate", END)

memory    = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)