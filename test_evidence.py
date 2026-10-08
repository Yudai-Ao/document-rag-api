from app.services.vector_store import search_vectors


def main():
    question = (
        "Document RAG APIのECS Taskは"
        "どのCPUアーキテクチャを使用しますか？"
    )

    contexts = search_vectors(
        question=question,
        top_k=2,
        document_id=None
    )

    for rank, context in enumerate(contexts, start=1):
        print(f"\nRank: {rank}")
        print(f"Source: {context['source']}")
        print(f"Distance: {context['distance']:.3f}")
        print(f"Text:\n{context['text']}")


if __name__ == "__main__":
    main()