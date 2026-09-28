from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import generate_rag_answer
from app.exceptions import (
    BedrockServiceError, 
    EmbeddingServiceError,
    VectorStoreServiceError)


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    try:
        result = generate_rag_answer(
            question=request.question,
            document_id=request.document_id
        )

    except (BedrockServiceError, EmbeddingServiceError, VectorStoreServiceError):
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable."
        )

    if not result["contexts"]:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    sources = [
        {
            "source": context["source"],
            "chunk_id": context["chunk_id"],
            "distance": context["distance"]
        }
        for context in result["contexts"]
    ]

    return ChatResponse(
        answer=result["answer"],
        sources=sources
    )