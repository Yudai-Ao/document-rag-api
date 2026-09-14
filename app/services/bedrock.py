import boto3

from app.config import settings

def generate_answer(question: str) -> str:
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region)

    response = client.converse(
        modelId=settings.bedrock_model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": question
                     }
                ]
            }
        ]
    )

    return response["output"]["message"]["content"][0]["text"]