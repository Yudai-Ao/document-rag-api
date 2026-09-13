from app.services.document import extract_text, create_chunks
from app.services.embedding import add_embeddings
from app.services.rag import generate_rag_answer


text = extract_text("sample.pdf")

chunks = create_chunks(
    text=text,
    source="rebun.pdf"
)

chunks = add_embeddings(chunks)

answer = generate_rag_answer(
    question="このpdfについて教えてください",
    chunks=chunks
)

print(answer)