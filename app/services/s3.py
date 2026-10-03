import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.exceptions import S3ServiceError


s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region
)


def upload_file(file_path: str, object_key: str) -> None:
    """ローカルファイルをS3へアップロードする。"""
    try:
        s3_client.upload_file(
            file_path,
            settings.s3_bucket_name,
            object_key
        )
    except (ClientError, BotoCoreError) as e:
        raise S3ServiceError("Failed to upload file to S3") from e


def save_document_metadata(
    document_id: str,
    filename: str,
    chunk_count: int
) -> None:
    """文書のメタデータをS3へ保存する。"""

    metadata = {
        "document_id": document_id,
        "filename": filename,
        "chunk_count": chunk_count
    }

    object_key = f"documents/{document_id}/metadata.json"

    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=json.dumps(metadata),
            ContentType="application/json"
        )
    except (ClientError, BotoCoreError) as e:
        raise S3ServiceError(
            "Failed to save document metadata to S3"
        ) from e


def get_document_metadata_list() -> list[dict]:
    """S3に保存されている文書メタデータの一覧を取得する。"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=settings.s3_bucket_name,
            Prefix="documents/"
        )

        documents = []

        for obj in response.get("Contents", []):
            object_key = obj["Key"]

            if not object_key.endswith("/metadata.json"):
                continue

            metadata_response = s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=object_key
            )

            metadata = json.loads(
                metadata_response["Body"].read()
            )

            documents.append(metadata)

        return documents

    except (ClientError, BotoCoreError) as e:
        raise S3ServiceError(
            "Failed to get document metadata from S3"
        ) from e


def get_document_metadata(document_id: str) -> dict | None:
    """指定した文書のメタデータをS3から取得する"""

    object_key = f"documents/{document_id}/metadata.json"

    try:
        response = s3_client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key
        )

        return json.loads(
            response["Body"].read()
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code in ("NoSuchKey", "404"):
            return None

        raise S3ServiceError(
            "Failed to get document metadata from S3"
        ) from e

    except BotoCoreError as e:
        raise S3ServiceError(
            "Failed to get document metadata from S3"
        ) from e


def delete_document_files(document_id: str) -> None:
    """指定した文書のPDFとメタデータをS3から削除する。"""

    try:
        s3_client.delete_objects(
            Bucket=settings.s3_bucket_name,
            Delete={
                "Objects": [
                    {
                        "Key": f"documents/{document_id}/original.pdf"
                    },
                    {
                        "Key": f"documents/{document_id}/metadata.json"
                    }
                ]
            }
        )

    except (ClientError, BotoCoreError) as e:
        raise S3ServiceError(
            "Failed to delete document files from S3"
        ) from e