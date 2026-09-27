import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


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
        raise RuntimeError("Failed to upload file to S3") from e