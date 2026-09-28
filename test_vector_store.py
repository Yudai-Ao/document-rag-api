from app.services.vector_store import search_vectors


document_id = "0a8b0ec9-aefc-429d-b43e-f044f91d01e6"

results = search_vectors(
    question="このPDFは何について説明していますか？",
    document_id=document_id,
    top_k=2,
)

for result in results:
    print(result)