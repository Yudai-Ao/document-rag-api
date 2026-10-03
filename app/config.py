from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_region: str = "ap-northeast-1"

    bedrock_model_id: str = "jp.anthropic.claude-sonnet-4-6"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    s3_bucket_name: str = "document-rag-api-documents"

    s3_vector_bucket_name: str = "document-rag-api-vectors"
    s3_vector_index_name: str = "document-chunks"

    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k: int = 3

    max_pdf_size_mb: int = 10

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()