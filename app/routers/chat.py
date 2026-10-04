import logging

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import ErrorResponse
from app.services.rag import generate_rag_answer
from app.exceptions import (
    BedrockServiceError, 
    EmbeddingServiceError,
    VectorStoreServiceError)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat", 
    response_model=ChatResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Document not found."
        },
        503: {
            "model": ErrorResponse,
            "description": "AI service is temporarily unavailable."
        }
    }
)
def chat(request: ChatRequest):

    try:
        result = generate_rag_answer(
            question=request.question,
            document_id=str(request.document_id)
        )

    except (BedrockServiceError, EmbeddingServiceError, VectorStoreServiceError):
        logger.exception(
            "Failed to generate RAG answer."
        )
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