from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: str