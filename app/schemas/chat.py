from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000
    )
    document_id: UUID


class SourceInfo(BaseModel):
    source: str
    chunk_id: int
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
