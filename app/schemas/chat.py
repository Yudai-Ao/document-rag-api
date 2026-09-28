from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    document_id: str


class SourceInfo(BaseModel):
    source: str
    chunk_id: int
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
