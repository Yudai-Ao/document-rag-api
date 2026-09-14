document_store: dict[str, dict] = {}


def save_chunks(
    document_id: str,
    filename: str,
    chunks: list[dict]
) -> None:
    document_store[document_id] = {
        "filename": filename,
        "chunks": chunks
    }

def get_chunks(
    document_id: str
) -> list[dict]:
    document = document_store.get(document_id)

    if document is None:
        return []

    return document["chunks"]

def get_documents() -> list[dict]:
    return [
        {
            "document_id": document_id,
            "filename": document["filename"],
            "chunk_count": len(document["chunks"])
        }
        for document_id, document in document_store.items()
    ]


def delete_document(document_id: str) -> bool:
    if document_id not in document_store:
        return False

    del document_store[document_id]

    return True