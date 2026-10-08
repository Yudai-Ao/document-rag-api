
from app.services.rag import generate_rag_answer


QUESTIONS = {
    "ecs-001": (
        "Document RAG APIのApplication Portは何番ですか？"
    ),
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

        print(f"\n=== {case_id} ===")

        result = generate_rag_answer(
            question=question,
            document_id=None,
            top_k=3
        )

        print(f"Answer: {result['answer']}")
        print(f"Abstained: {result['abstained']}")
        print(f"Contexts: {len(result['contexts'])}")


if __name__ == "__main__":
    main()
