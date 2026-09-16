import boto3

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.exceptions import BedrockServiceError


def generate_answer(question: str) -> str:
    try:
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

    except (ClientError, BotoCoreError) as e:
        raise BedrockServiceError(
            "Failed to generate an answer with Bedrock."
        ) from e