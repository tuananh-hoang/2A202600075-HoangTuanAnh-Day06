from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from app.utils.vector_tools import list_of_tools
from app.prompts.system_prompt import XANH_SM_SYSTEM_PROMPT
from app.core import config

# 1. Định nghĩa bộ nhớ (State) chứa danh sách tin nhắn
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 2. Khởi tạo LLM và gắn các công cụ (Tools) vào
llm = ChatOpenAI(
    model=config.LLM_MODEL, 
    temperature=config.AI_TEMPERATURE
).bind_tools(list_of_tools)

# 3. Node LLM: Hàm kích hoạt "Bộ não"
def call_model(state: AgentState):
    messages = state["messages"]
    
    # Luôn đảm bảo System Prompt nằm ở đầu danh sách tin nhắn
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=XANH_SM_SYSTEM_PROMPT)] + messages
        
    response = llm.invoke(messages)
    return {"messages": [response]}

# 4. Node Tool: Hàm kích hoạt "Tay chân" (Truy xuất FAISS)
tool_node = ToolNode(list_of_tools)

# 5. Logic rẽ nhánh (Edges)
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    # Nếu LLM quyết định dùng tool (gọi hàm), chuyển sang node tools
    if last_message.tool_calls:
        return "tools"
    # Nếu LLM tự trả lời được, kết thúc luồng
    return END

# 6. Xây dựng Sơ đồ (Graph)
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# Cài đặt Checkpointer (MemorySaver) để nhớ lịch sử chat theo thread_id
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)