import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.services.embedding import generate_embedding
from app.exceptions import VectorStoreServiceError


s3_vectors_client = boto3.client(
    "s3vectors",
    region_name=settings.aws_region
)


def put_vector(
    key: str,
    embedding: list[float],
    metadata: dict
) -> None:
    try:
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
    except (ClientError, BotoCoreError) as e:
        raise VectorStoreServiceError(
            "Failed to save vector to S3 Vectors."
        ) from e


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
                "source": chunk["source"],
                "chunk_index": index,
            }
        )


def search_vectors(
    question: str,
    document_id: str,
    top_k: int,
) -> list[dict]:

    query_embedding = generate_embedding(question)

    try:
        response = s3_vectors_client.query_vectors(
            vectorBucketName=settings.s3_vector_bucket_name,
            indexName=settings.s3_vector_index_name,
            queryVector={
                "float32": query_embedding
            },
            topK=top_k,
            filter={
                "document_id": {
                    "$eq": document_id
                }
            },
            returnMetadata=True,
            returnDistance=True
        )

    except (ClientError, BotoCoreError) as e:
        raise VectorStoreServiceError(
            "Failed to search vectors in S3 Vectors."
        ) from e
 
    contexts = []

    for vector in response["vectors"]:
        metadata = vector["metadata"]

        contexts.append(
            {
                "text": metadata["text"],
                "source": metadata.get("source", ""),
                "chunk_id": metadata["chunk_index"],
                "distance": vector["distance"]
            }
        )

    return contexts