import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.exceptions import TextractServiceError


textract_client = boto3.client(
    "textract",
    region_name=settings.aws_region
)

def extract_text_with_textract(
    bucket_name: str,
    object_key: str
) -> str:

    try:
        response = textract_client.start_document_text_detection(
            DocumentLocation={
                "S3Object": {
                    "Bucket": bucket_name,
                    "Name": object_key
                }
            }
        )

        job_id = response["JobId"]

        while True:
            response = textract_client.get_document_text_detection(
                JobId=job_id
            )

            status = response["JobStatus"]

            if status == "SUCCEEDED":
                break

            if status == "FAILED":
                raise TextractServiceError(
                    "Textract document text detection failed."
                )

            time.sleep(1)

    except (ClientError, BotoCoreError) as e:
        print("Textract error repr:", repr(e))

        raise TextractServiceError(
            "Failed to communicate with Textract."
        ) from e

    texts = []

    while True:
        for block in response["Blocks"]:
            if block["BlockType"] == "LINE":
                texts.append(block["Text"])

        next_token = response.get("NextToken")

        if not next_token:
            break

        try:
            response = textract_client.get_document_text_detection(
                JobId=job_id,
                NextToken=next_token
            )
        except (ClientError, BotoCoreError) as e:
            raise TextractServiceError(
                "Failed to get Textract results."
            ) from e

    return "\n".join(texts)