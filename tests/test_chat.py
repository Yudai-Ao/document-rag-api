from fastapi.testclient import TestClient

from app.main import app
from app.services.decument_store import save_chunks
from app.exceptions import BedrockServiceError


client = TestClient(app)


def test_chat(monkeypatch):
    save_chunks(
        document_id="test-chat-id",
        filename="chat-test.pdf",
        chunks=[
            {
                "text": "東京は日本の首都です。",
                "source": "chat-test.pdf",
                "chunk_id": 0,
                "embedding": [0.1, 0.2, 0.3]
            }
        ]
    )

    def fake_generate_rag_answer(question, chunks):
        return {
            "answer": "東京です。",
            "contexts": [
                {
                    "text": "東京は日本の首都です。",
                    "source": "chat-test.pdf",
                    "chunk_id": 0,
                    "embedding": [0.1, 0.2, 0.3],
                    "score": 0.95
                }
            ]
        }

    monkeypatch.setattr(
        "app.routers.chat.generate_rag_answer",
        fake_generate_rag_answer
    )

    response = client.post(
        "/chat",
        json={
            "question": "日本の首都はどこですか？",
            "document_id": "test-chat-id"
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "東京です。",
        "sources": [
            {
                "source": "chat-test.pdf",
                "chunk_id": 0,
                "score": 0.95
            }
        ]
    }


def test_chat_document_not_found():
    response = client.post(
        "/chat",
        json={
            "question": "日本の首都はどこですか？",
            "document_id": "non-existent-id"
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }


def test_chat_ai_service_error(monkeypatch):
    save_chunks(
        document_id="test-error-id",
        filename="error-test.pdf",
            chunks=[
                {
                    "text": "テスト用文書です。",
                    "source": "error-test.pdf",
                    "chunk_id": 0,
                    "embedding": [0.1, 0.2, 0.3]
                }
            ]
    )

    def fake_generate_rag_answer(question, chunks):
        raise BedrockServiceError(
            "Failed to generate an answer with Bedrock"
        )

    monkeypatch.setattr(
        "app.routers.chat.generate_rag_answer",
        fake_generate_rag_answer
    )

    response = client.post(
        "/chat",
        json={
            "question": "この文書について教えてください。",
            "document_id": "test-error-id"
        }
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AI service is temporarily unavailable."
    }
