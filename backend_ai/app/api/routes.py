from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.agent_graph import app_graph
from app.core import config

router = APIRouter()

# Schema dữ liệu do Frontend gửi lên
class ChatRequest(BaseModel):
    prompt: str
    thread_id: str = Field(alias=config.USER_IDENTIFIER_KEY, default="default_user")

# Schema dữ liệu Backend trả về
class ChatResponse(BaseModel):
    answer: str
    thread_id: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Cấu hình thread_id để LangGraph nhận diện và nhớ lịch sử khách hàng
        thread_config = {"configurable": {"thread_id": request.thread_id}}
        
        inputs = {"messages": [("human", request.prompt)]}
        
        # Chạy toàn bộ luồng Agent Graph
        final_state = app_graph.invoke(inputs, config=thread_config)
        
        # Lấy nội dung tin nhắn cuối cùng do AI sinh ra
        bot_response = final_state["messages"][-1].content
        
        return ChatResponse(
            answer=bot_response,
            thread_id=request.thread_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống AI: {str(e)}")