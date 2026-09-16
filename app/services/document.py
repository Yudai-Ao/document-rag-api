from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import settings
from app.exceptions import PDFProcessingError


def extract_text(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)

        texts = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                texts.append(text)

        return "\n".join(texts)

    except PdfReadError as e:
        raise PDFProcessingError(
            "Failed to process PDF."
        ) from e


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> list[str]:
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]
        chunks.append(chunk)

        start += chunk_size - chunk_overlap

    return chunks


def create_chunks(
    text: str,
    source: str,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap
) -> list[dict]:
    raw_chunks = split_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = []

    for i, chunk in enumerate(raw_chunks):
        chunks.append(
            {
                "text": chunk,
                "source": source,
                "chunk_id": i
            }
        )

    return chunks