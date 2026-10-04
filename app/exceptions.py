class BedrockServiceError(Exception):
    pass


class EmbeddingServiceError(Exception):
    pass


class PDFProcessingError(Exception):
    pass


class VectorStoreServiceError(Exception):
    """Vector Storeとの通信に失敗した場合の例外"""
    pass


class TextractServiceError(Exception):
    """TextractによるOCR処理に失敗した場合の例外"""
    pass


class S3ServiceError(Exception):
    """S3との通信に失敗した場合の例外"""
    pass