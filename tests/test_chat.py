from fastapi.testclient import TestClient

from app.main import app
from app.exceptions import BedrockServiceError


client = TestClient(app)

TEST_DOCUMENT_ID = "550e8400-e29b-41d4-a716-446655440000"


def test_chat(monkeypatch):

    def fake_generate_rag_answer(question, document_id):
        return {
            "answer": "東京です。",
            "contexts": [
                {
                    "text": "東京は日本の首都です。",
                    "source": "chat-test.pdf",
                    "chunk_id": 0,
                    "distance": 0.25
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
            "document_id": TEST_DOCUMENT_ID
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "東京です。",
        "sources": [
            {
                "source": "chat-test.pdf",
                "chunk_id": 0,
                "distance": 0.25
            }
        ]
    }


def test_chat_document_not_found(monkeypatch):

    def fake_generate_rag_answer(question, document_id):
        return {
            "answer": "",
            "contexts": []
        }

    monkeypatch.setattr(
        "app.routers.chat.generate_rag_answer",
        fake_generate_rag_answer
    )

    response = client.post(
        "/chat",
        json={
            "question": "日本の首都はどこですか？",
            "document_id": TEST_DOCUMENT_ID
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }


def test_chat_ai_service_error(monkeypatch):

    def fake_generate_rag_answer(question, document_id):
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
            "document_id": TEST_DOCUMENT_ID
        }
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AI service is temporarily unavailable."
    }


def test_chat_invalid_document_id():

    response = client.post(
        "/chat",
        json={
            "question": "この文書を要約してください。",
            "document_id": "invalid-id"
        }
    )

    assert response.status_code == 422


def test_chat_empty_question():

    response = client.post(
        "/chat",
        json={
            "question": "",
            "document_id": TEST_DOCUMENT_ID
        }
    )

    assert response.status_code == 422


def test_chat_question_too_long():

    response = client.post(
        "/chat",
        json={
            "question": "a" * 2001,
            "document_id": TEST_DOCUMENT_ID
        }
    )

    assert response.status_code == 422