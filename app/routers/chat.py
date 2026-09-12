from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.bedrock import generate_answer


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer = generate_answer(request.question)

    return ChatResponse(
        answer=answer
    )