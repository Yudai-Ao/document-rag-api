from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.decument_store import get_chunks
from app.services.rag import generate_rag_answer


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    chunks = get_chunks(request.document_id)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    answer = generate_rag_answer(
        question=request.question,
        chunks=chunks
    )

    return ChatResponse(answer=answer)