from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.decument_store import get_chunks
from app.services.rag import generate_rag_answer
from app.exceptions import BedrockServiceError, EmbeddingServiceError


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    chunks = get_chunks(request.document_id)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    try:
        result = generate_rag_answer(
            question=request.question,
            chunks=chunks
        )

    except (BedrockServiceError, EmbeddingServiceError):
        raise HTTPException(
            status_code=503,
            detail="AI service is temporary unavaiiable."
        )

    sources = [
        {
            "source": context["source"],
            "chunk_id": context["chunk_id"],
            "score": context["score"]
        }
        for context in result["contexts"]
    ]

    return ChatResponse(
        answer=result["answer"],
        sources=sources
    )