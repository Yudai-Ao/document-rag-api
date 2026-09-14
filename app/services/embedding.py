import json
import boto3

from app.config import settings


MODEL_ID = "amazon.titan-embed-text-v2:0"

def generate_embedding(text: str) -> list[float]:
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region
    )

    body = json.dumps(
        {
            "inputText": text
        }
    )

    response = client.invoke_model(
        modelId=settings.embedding_model_id,
        body=body
    )

    response_body = json.loads(
        response["body"].read()
    )

    return response_body["embedding"]

def add_embeddings(chunks: list[dict]) -> list[dict]:
    for chunk in chunks:
        embedding = generate_embedding(chunk["text"])
        chunk["embedding"] = embedding

    return chunks

