from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    document_id: str


class ChatResponse(BaseModel):
    answer: str

