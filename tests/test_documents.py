from fastapi.testclient import TestClient

from app.main import app
from app.exceptions import EmbeddingServiceError
from app.services.decument_store import save_chunks, get_chunks


client = TestClient(app)


def test_upload_document(monkeypatch):
    def fake_extract_text(file_path):
        return "これはテスト用の文書です"

    def fake_add_embeddings(chunks):
        for chunk in chunks:
            chunk["embedding"] = [0.1, 0.2, 0.3]

        return chunks

    monkeypatch.setattr(
        "app.routers.documents.extract_text",
        fake_extract_text
    )

    monkeypatch.setattr(
        "app.routers.documents.add_embeddings",
        fake_add_embeddings
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

    assert data["filename"] == 'test.pdf'
    assert data["chunk_count"] == 1
    assert "document_id" in data


def test_uploa_non_pdf():
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
    def fake_extract_text(file_path):
        return ""

    monkeypatch.setattr(
        "app.routers.documents.extract_text",
        fake_extract_text
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

    monkeypatch.setattr(
        "app.routers.documents.extract_text",
        fake_extract_text
    )

    monkeypatch.setattr(
            "app.routers.documents.add_embeddings",
            fake_add_embeddings
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


def test_list_documents():
    save_chunks(
        document_id="test-document-id",
        filename="test.pdf",
        chunks=[
            {
                "text": "テスト文書",
                "source": "test.pdf",
                "chunk_id": 0,
                "embeddin": [0.1, 0.2, 0.3]
            }
        ]
    )

    response = client.get("/documents")

    assert response.status_code == 200

    data = response.json()

    assert any(
        document["document_id"] == "test-document-id"
        and document["filename"] == "test.pdf"
        and document["chunk_count"] == 1
        for document in data
    )


def test_delete_document():
    save_chunks(
        document_id="test-delete-id",
        filename="delete-test.pdf",
        chunks=[
            {
                "text": "削除テスト用文書",
                "source": "delete-test.pdf",
                "chunk_id": 0,
                "embedding": [0.1, 0.2, 0.3]
            }
        ]
    )

    response = client.delete(
        "/documents/test-delete-id",
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Document deleted.",
        "document_id": "test-delete-id"
    }


def test_delete_document_not_found():
    response = client.delete(
        "/documents/non-existent-id"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }