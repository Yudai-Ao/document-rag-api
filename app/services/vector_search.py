import math
from app.services.embedding import generate_embedding


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    norm_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    return dot_product / (norm_a * norm_b)


def search_similar_chunks(
    question: str,
    chunks: list[dict],
    top_k: int = 3
) -> list[dict]:

    question_embedding = generate_embedding(question)

    results = []

    for chunk in chunks:
        score = cosine_similarity(
            question_embedding,
            chunk["embedding"]
        )

        results.append(
            {
                **chunk,
                "score" : score
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:top_k]

