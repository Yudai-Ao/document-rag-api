
from app.services.rag import generate_rag_answer


QUESTION = (
    "ECS TaskはRunningで /health も正常ですが、"
    "/chat が503を返します。"
    "ALBの問題として調査を続けるべきですか？"
)


def main():
    for k in [3, 5]:

        print(f"\n=== Top-{k} ===")

        result = generate_rag_answer(
            question=QUESTION,
            document_id=None,
            top_k=k
        )

        print(f"Abstained: {result['abstained']}")
        print(f"Answer: {result['answer']}")

        for rank, context in enumerate(
            result["contexts"],
            start=1
        ):
            print(
                f"{rank}. {context['source']} "
                f"(distance={context['distance']:.3f})"
            )


if __name__ == "__main__":
    main()
