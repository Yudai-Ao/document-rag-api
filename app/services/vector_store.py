import boto3

from app.config import settings


s3_vectors_client = boto3.client(
    "s3vectors",
    region_name=settings.aws_region
)


def put_vector(
    key: str,
    embedding: list[float],
    metadata: dict
) -> None:
    s3_vectors_client.put_vectors(
        vectorBucketName=settings.s3_vector_bucket_name,
        indexName=settings.s3_vector_index_name,
        vectors=[
            {
                "key": key,
                "data": {
                    "float32": embedding
                },
                "metadata": metadata
            }
        ]
    )


def save_chunks_to_vector_store(
    document_id: str,
    chunks: list[dict]
) -> None:
    for index, chunk in enumerate(chunks):
        put_vector(
            key=f"{document_id}-{index}",
            embedding=chunk["embedding"],
            metadata={
                "document_id": document_id,
                "text": chunk["text"],
                "chunk_index": index,
            }
        )