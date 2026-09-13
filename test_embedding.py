from app.services.document import extract_text, create_chunks
from app.services.embedding import add_embeddings
from app.services.vector_search import search_similar_chunks


text = extract_text("sample.pdf")

chunks = create_chunks(
    text,
    source="rebun.pdf",
    chunk_size=200,
    chunk_overlap=50
    )

chunks = add_embeddings(chunks)

results = search_similar_chunks(
    question="礼文島について教えてください",
    chunks=chunks,
    top_k=3
)

for result in results:
    print(f"chunk_id: {result["chunk_id"]}")
    print(f"score: {result["score"]}")
    print(f"text: {result["text"][:100]}")
    print()