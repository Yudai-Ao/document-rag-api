from app.services.vector_store import s3_vectors_client
from app.config import settings


document_id = "0a8b0ec9-aefc-429d-b43e-f044f91d01e6"

response = s3_vectors_client.get_vectors(
    vectorBucketName=settings.s3_vector_bucket_name,
    indexName=settings.s3_vector_index_name,
    keys=[
        f"{document_id}-0",
        f"{document_id}-1",
    ],
    returnData=False,
    returnMetadata=True,
)

print(response)