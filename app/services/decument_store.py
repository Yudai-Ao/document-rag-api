document_store: dict[str, list[dict]] = {}


def save_chunks(
    document_id: str,
    chunks: list[dict]
) -> None:
    document_store[document_id] = chunks

def get_chunks(
    document_id: str
) -> list[dict]:
    return document_store.get(document_id, [])