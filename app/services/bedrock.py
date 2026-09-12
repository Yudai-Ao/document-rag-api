import boto3

MODEL_ID = "jp.anthropic.claude-sonnet-4-6"

def generate_answer(question: str) -> str:
    client = boto3.client(
        "bedrock-runtime",
        region_name="ap-northeast-1")

    response = client.converse(
        modelId=MODEL_ID,
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