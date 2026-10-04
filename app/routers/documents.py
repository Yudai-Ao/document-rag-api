import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.document import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentDeleteResponse
)
from app.schemas.common import ErrorResponse
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
    TextractServiceError,
    S3ServiceError
)
from app.config import settings


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid PDF or failed PDF processing."
        },
        413: {
            "model": ErrorResponse,
            "description": "PDF file is too lerge."
        },
        503: {
            "model": ErrorResponse,
            "description": "Document processing service is temporarily unavailable."
        }
    }
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

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="PDF file is empty."
        )

    max_size_bytes = settings.max_pdf_size_mb * 1024 * 1024

    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"PDF file must be {settings.max_pdf_size_mb} MB or smaller."
        )

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
                logger.exception(
                    "Failed to extract text using Textract."
                )
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
            logger.exception(
                "Failed to generate embeddings."
            )
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
            logger.exception(
                "Failed to save document vectors."
            )
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
        logger.exception(
            "Failed to proecss PDF."
        )
        raise HTTPException(
            status_code=400,
            detail="Failed to process PDF."
        )

    except S3ServiceError:
        logger.exception(
            "Failed to access S3 while processing document."
        )
        raise HTTPException(
            status_code=503,
            detail="Storage service is temporarily unavailable."
        )

    finally:
        os.remove(temp_path)


@router.get(
    "/documents",
    response_model=list[DocumentInfo],
    responses={
        503: {
            "model": ErrorResponse,
            "description": "Storage service is temporarily unavailable."
        }
    }
)
def list_documents():
    try:
        return get_document_metadata_list()
    except S3ServiceError:
        logger.exception(
            "Failed to retrieve document list from S3."
        )
        raise HTTPException(
            status_code=503, 
            detail="Storage service is temporarily unavailable."
        )


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Document not found."
        },
        503: {
            "model": ErrorResponse,
            "description": "Storage service is temporarily unavailable."
        }
    }
)
def remove_document(document_id: str):

    try:

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

    except (S3ServiceError, VectorStoreServiceError):
        logger.exception(
            "Failed to delete document."
        )
        raise HTTPException(
            status_code=503,
            detail="Storage service is temporarily unavailable."
        )