import json

import boto3


MODEL_ID = "amazon.titan-embed-text-v2:0"

def generate_embedding(text: str) -> list[float]:
    client = boto3.client(
        "bedrock-runtime",
        region_name="ap-northeast-1"
    )

    body = json.dumps(
        {
            "inputText": text
        }
    )

    response = client.invoke_model(
        modelId=MODEL_ID,
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

