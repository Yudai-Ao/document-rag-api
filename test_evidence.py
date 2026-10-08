
from app.services.vector_store import search_vectors


QUESTIONS = {
    "ecs-002": (
        "障害調査を開始してから何分以内に"
        "原因を特定できなければエスカレーションしますか？"
    ),
    "ecs-003": (
        "Document RAG APIのECS Taskは"
        "どのCPUアーキテクチャを使用しますか？"
    )
}


def main():

    for case_id, question in QUESTIONS.items():

        contexts = search_vectors(
            question=question,
            top_k=10,
            document_id=None
        )

        print(f"\n=== {case_id} ===")

        for rank, context in enumerate(
            contexts,
            start=1
        ):
            print(
                f"\nRank: {rank}"
                f"\nSource: {context['source']}"
                f"\nDistance: {context['distance']:.3f}"
                f"\nText:\n{context['text']}"
            )


if __name__ == "__main__":
    main()
