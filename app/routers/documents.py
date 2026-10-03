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
from app.services.vector_store import (
    save_chunks_to_vector_store,
    delete_document_vectors
)
from app.services.textract import extract_text_with_textract
from app.services.s3 import (
    upload_file, 
    save_document_metadata,
    get_document_metadata_list,
    get_document_metadata,
    delete_document_files)
from app.services.embedding import add_embeddings

from app.exceptions import (
    EmbeddingServiceError,
    PDFProcessingError,
    VectorStoreServiceError,
    TextractServiceError
)
from app.config import settings


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
            detail="Only PDF files are supported."
        )

    contents = await file.read()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name

    document_id = str(uuid.uuid4())

    try:
        object_key = f"documents/{document_id}/original.pdf"

        upload_file(
            file_path=temp_path,
            object_key=object_key
        )
        text = extract_text(temp_path)

        # pypdfで文字を取得できなかった場合のみTextractを使用
        if not text.strip():
            try:
                text = extract_text_with_textract(
                    bucket_name=settings.s3_bucket_name,
                    object_key=object_key
                )
            except TextractServiceError:
                raise HTTPException(
                    status_code=503,
                    detail="OCR service is temporarily unavailable."
                )

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the PDF."
            )

        chunks = create_chunks(
            text=text,
            source=file.filename
        )

        try:
            chunks = add_embeddings(chunks)
        except EmbeddingServiceError:
            raise HTTPException(
                status_code=503,
                detail="Embedding service is temporarily unavailable."
            )

        try:
            save_chunks_to_vector_store(
                document_id=document_id,
                chunks=chunks
            )
        except VectorStoreServiceError:
            raise HTTPException(
                status_code=503,
                detail="Vector store is temporarily unavailable."
            )

        save_document_metadata(
            document_id=document_id,
            filename=file.filename,
            chunk_count=len(chunks)
        )

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            chunk_count=len(chunks)
        )

    except PDFProcessingError:
        raise HTTPException(
            status_code=400,
            detail="Failed to process PDF."
        )

    finally:
        os.remove(temp_path)


@router.get(
    "/documents",
    response_model=list[DocumentInfo]
)
def list_documents():
    return get_document_metadata_list()


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse
)
def remove_document(document_id: str):

    # S3からメタデータを取得
    metadata = get_document_metadata(document_id)

    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    # S3 Vectorsからベクトルを削除
    delete_document_vectors(
        document_id=document_id,
        chunk_count=metadata["chunk_count"]
        )

    # S3からPDFとmetadataを削除
    delete_document_files(document_id)

    return DocumentDeleteResponse(
        message="Document deleted.",
        document_id=document_id
    )