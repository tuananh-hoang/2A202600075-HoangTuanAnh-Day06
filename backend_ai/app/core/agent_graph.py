"""
agent_graph.py
Đặt tại: backend_ai/app/core/agent_graph.py

Thay đổi so với phiên bản cũ:
- list_of_tools lấy từ retrieval_advanced (Hybrid + Reranker) thay vì vector_tools
- System prompt vẫn ở app/prompts/system_prompt.py
- Giữ nguyên StateGraph + MemorySaver (hỗ trợ thread_id)
"""

from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.core import config
from app.prompts.system_prompt import XANH_SM_SYSTEM_PROMPT

# ── Dùng list_of_tools từ retrieval_advanced thay vì vector_tools ──
from app.utils.retrieval_advanced import get_tools()


# ──────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ──────────────────────────────────────────────
# LLM + TOOLS
# ──────────────────────────────────────────────

llm = ChatOpenAI(
    model=config.LLM_MODEL,
    temperature=config.AI_TEMPERATURE,
).bind_tools(list_of_tools)


# ──────────────────────────────────────────────
# NODES
# ──────────────────────────────────────────────

def call_model(state: AgentState):
    messages = state["messages"]
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=XANH_SM_SYSTEM_PROMPT)] + messages
    response = llm.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(list_of_tools)


# ──────────────────────────────────────────────
# EDGES
# ──────────────────────────────────────────────

def should_continue(state: AgentState):
    if state["messages"][-1].tool_calls:
        return "tools"
    return END


# ──────────────────────────────────────────────
# GRAPH
# ──────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)