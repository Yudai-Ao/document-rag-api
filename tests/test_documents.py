from fastapi.testclient import TestClient

from app.main import app
from app.exceptions import (
    EmbeddingServiceError, 
    S3ServiceError,
    VectorStoreServiceError
)

client = TestClient(app)


def test_upload_document(monkeypatch):
    def fake_upload_file(file_path, object_key):
        return None

    def fake_extract_text(file_path):
        return "これはテスト用の文書です"

    def fake_add_embeddings(chunks):
        for chunk in chunks:
            chunk["embedding"] = [0.1, 0.2, 0.3]

        return chunks

    def fake_save_chunks_to_vector_store(document_id, chunks):
        return None

    def fake_save_document_metadata(
        document_id,
        filename,
        chunk_count
    ):
        return None

    monkeypatch.setattr(
        "app.routers.documents.upload_file",
        fake_upload_file
    )

    monkeypatch.setattr(
        "app.routers.documents.extract_text",
        fake_extract_text
    )

    monkeypatch.setattr(
        "app.routers.documents.add_embeddings",
        fake_add_embeddings
    )

    monkeypatch.setattr(
        "app.routers.documents.save_chunks_to_vector_store",
        fake_save_chunks_to_vector_store
    )

    monkeypatch.setattr(
        "app.routers.documents.save_document_metadata",
        fake_save_document_metadata
    )

    response = client.post(
        "/documents",
        files={
            "file": (
                "test.pdf",
                b"fake pdf content",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "test.pdf"
    assert data["chunk_count"] == 1
    assert "document_id" in data


def test_upload_non_pdf():
    response = client.post(
        "/documents",
        files={
            "file": (
                "test.pdf",
                b"hello",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Only PDF files are supported."
    }


def test_upload_pdf_with_no_text(monkeypatch):
    def fake_upload_file(file_path, object_key):
        return None

    def fake_extract_text(file_path):
        return ""

    def fake_extract_text_with_textract(bucket_name, object_key):
        return ""

    monkeypatch.setattr(
        "app.routers.documents.upload_file",
        fake_upload_file
    )

    monkeypatch.setattr(
        "app.routers.documents.extract_text",
        fake_extract_text
    )

    monkeypatch.setattr(
        "app.routers.documents.extract_text_with_textract",
        fake_extract_text_with_textract
    )

    response = client.post(
        "/documents",
        files={
            "file": (
                "test.pdf",
                b"fake pdf content",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "No text could be extracted from the PDF."
    }


def test_upload_document_embedding_error(monkeypatch):
    def fake_extract_text(file_path):
        return "これはテスト用の文書です。"

    def fake_add_embeddings(chunks):
        raise EmbeddingServiceError(
            "Failed to genrerate embedding with Bedrock."
        )

    def fake_upload_file(file_path, object_key):
        return None

    monkeypatch.setattr(
        "app.routers.documents.extract_text",
        fake_extract_text
    )

    monkeypatch.setattr(
        "app.routers.documents.add_embeddings",
        fake_add_embeddings
    )

    monkeypatch.setattr(
        "app.routers.documents.upload_file",
        fake_upload_file
    )

    response = client.post(
        "/documents",
        files={
            "file": (
                "test.pdf",
                b"fake pdf content",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Embedding service is temporarily unavailable."
    }


def test_delete_document(monkeypatch):
    def fake_get_document_metadata(document_id):
        return {
            "document_id": document_id,
            "filename": "delete-test.pdf",
            "chunk_count": 1
        }

    def fake_delete_document_vectors(document_id, chunk_count):
        return None

    def fake_delete_document_files(document_id):
        return None

    monkeypatch.setattr(
        "app.routers.documents.get_document_metadata",
        fake_get_document_metadata
    )

    monkeypatch.setattr(
        "app.routers.documents.delete_document_vectors",
        fake_delete_document_vectors
    )

    monkeypatch.setattr(
        "app.routers.documents.delete_document_files",
        fake_delete_document_files
    )

    response = client.delete(
        "/documents/test-delete-id"
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Document deleted.",
        "document_id": "test-delete-id"
    }


def test_delete_document_not_found(monkeypatch):
    def fake_get_document_metadata(document_id):
        return None

    monkeypatch.setattr(
        "app.routers.documents.get_document_metadata",
        fake_get_document_metadata
    )

    response = client.delete(
        "/documents/non-existent-id"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }


def test_list_documents(monkeypatch):
    def fake_get_document_metadata_list():
        return [
            {
                "document_id": "test-document-id",
                "filename": "test.pdf",
                "chunk_count": 1
            }
        ]

    monkeypatch.setattr(
        "app.routers.documents.get_document_metadata_list",
        fake_get_document_metadata_list
    )

    response = client.get("/documents")

    assert response.status_code == 200

    assert response.json() == [
        {
            "document_id": "test-document-id",
            "filename": "test.pdf",
            "chunk_count": 1
        }
    ]


def test_list_documents_s3_error(monkeypatch):
    def fake_get_document_metadata_list():
        raise S3ServiceError(
            "Failed to get document metadata from S3"
        )

    monkeypatch.setattr(
        "app.routers.documents.get_document_metadata_list",
        fake_get_document_metadata_list
    )

    response = client.get("/documents")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Storage service is temporarily unavailable."
    }


def test_upload_empty_pdf():

    response = client.post(
        "/documents",
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "PDF file is empty."
    }


def test_upload_pdf_too_large():

    large_content = b"a" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/documents",
        files={
            "file": (
                "large.pdf",
                large_content,
                "application/pdf"
            )
        }
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "PDF file must be 10 MB or smaller."
    }


def test_delete_document_s3_error(monkeypatch):

    def fake_get_document_metadata(document_id):
        raise S3ServiceError(
            "Failed to get document metadata from S3"
        )

    monkeypatch.setattr(
        "app.routers.documents.get_document_metadata",
        fake_get_document_metadata
    )

    response = client.delete(
        "/documents/550e8400-e29b-41d4-a716-446655440000"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Storage service is temporarily unavailable."
    }


def test_delete_document_vector_store_error(monkeypatch):

    def fake_get_document_metadata(document_id):
        return {
            "document_id": document_id,
            "filename": "test.pdf",
            "chunk_count": 3
        }

    def fake_delete_document_vectors(document_id, chunk_count):
        raise VectorStoreServiceError(
            "Failed to delete vectors from S3 Vectors."
        )

    monkeypatch.setattr(
        "app.routers.documents.get_document_metadata",
        fake_get_document_metadata
    )

    monkeypatch.setattr(
        "app.routers.documents.delete_document_vectors",
        fake_delete_document_vectors
    )

    response = client.delete(
        "/documents/550e8400-e29b-41d4-a716-446655440000"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Storage service is temporarily unavailable."
    }