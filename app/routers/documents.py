import os
import tempfile
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.document import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentDeleteResponse
)
from app.services.document import extract_text, create_chunks
from app.services.embedding import add_embeddings
from app.services.decument_store import (
    save_chunks,
    get_documents,
    delete_document

)


router = APIRouter()


@router.post(
    "/documents",
    response_model=DocumentUploadResponse
)
async def upload_document(
    file: UploadFile = File(...)
):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="only PDF files are supported."
        )
    
    contents = await file.read()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name

    try:

        text = extract_text(temp_path)

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the PDF."
            )

        chunks = create_chunks(
            text=text,
            source=file.filename
        )    

        chunks = add_embeddings(chunks)

        document_id = str(uuid.uuid4())

        save_chunks(
            document_id=document_id,
            filename=file.filename,
            chunks=chunks)

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            chunk_count=len(chunks)
        )

    finally:
        os.remove(temp_path)


@router.get(
    "/documents",
    response_model=list[DocumentInfo]
)
def list_documents():
    return get_documents()


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse
)
def remove_document(document_id: str):

    deleted = delete_document(document_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return DocumentDeleteResponse(
        message="Document deleted.",
        documenet_id=document_id
    )