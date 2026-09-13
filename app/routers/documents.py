import os
import tempfile
import uuid

from fastapi import APIRouter, UploadFile, File

from app.schemas.document import DocumentUploadResponse
from app.services.document import extract_text, create_chunks
from app.services.embedding import add_embeddings
from app.services.decument_store import save_chunks


router = APIRouter()


@router.post(
    "/documents",
    response_model=DocumentUploadResponse
)
async def upload_document(
    file: UploadFile = File(...)
):
    contents = await file.read()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name

    try:

        text = extract_text(temp_path)

        chunks = create_chunks(
            text=text,
            source=file.filename
        )    

        chunks = add_embeddings(chunks)

        document_id = str(uuid.uuid4())

        save_chunks(
            document_id=document_id,
            chunks=chunks)

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            chunk_count=len(chunks)
        )

    finally:
        os.remove(temp_path)