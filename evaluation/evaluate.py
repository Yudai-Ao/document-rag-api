import json
from pathlib import Path

from app.services.rag import generate_rag_answer


BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "datasets"
RESULTS_DIR = BASE_DIR / "results"
BASELINE_FILE = RESULTS_DIR / "baseline.json"


def load_dataset(file_name: str) -> list[dict]:
    file_path = DATASET_DIR / file_name

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def build_evaluate_result(
    case: dict,
    rag_result: dict
) -> dict:

    contexts = rag_result["contexts"]

    top1_distance = (
        contexts[0]["distance"]
        if contexts
        else None
    )

    expected_source_found = None
    expected_source_rank = None

    if case["answerable"]:
        expected_sources = case["expected_sources"]

        for rank, context in enumerate(
            contexts,
            start=1
        ):
            if context["source"] in expected_sources:
                expected_source_found = True
                expected_source_rank = rank
                break

        if expected_source_rank is None:
            expected_source_found = False

    return {
        "id": case["id"],
        "question": case["question"],
        "category": case["category"],
        "answerable": case["answerable"],
        "expected_answer": case["expected_answer"],
        "expected_sources": case["expected_sources"],
        "answer": rag_result["answer"],
        "sources": contexts,
        "retrieval": {
            "expected_source_found": expected_source_found,
            "expected_source_rank": expected_source_rank,
            "top1_distance": top1_distance
        }
    }
        


def main():
    ecs_cases = load_dataset("ecs_evaluation.json")

    alb_cases = load_dataset("alb_evaluation.json")

    iam_cases = load_dataset("iam_evaluation.json")

    s3_cases = load_dataset("s3_evaluation.json")

    bedrock_cases = load_dataset("bedrock_evaluation.json")

    unanswerable_cases = load_dataset("unanswerable_evaluation.json")

    evaluation_cases = (
        ecs_cases
        + alb_cases
        + iam_cases
        + s3_cases
        + bedrock_cases
        + unanswerable_cases
    )

    print(
        f"{len(evaluation_cases)} evaluation cases loaded."
    )

    results = []

    for case in evaluation_cases:
        print(
            f"\n[{case['id']}] {case['question']}"
        )

        result = generate_rag_answer(
            question=case["question"],
            document_id=None
        )

        evaluation_result = build_evaluate_result(
            case=case,
            rag_result=result
        )

        results.append(evaluation_result)

        print(
            f"Answer: {result['answer']}"
        )

        print(
            f"Contexts: {len(result['contexts'])}"
        )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        BASELINE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"\nEvaluation results saved to {BASELINE_FILE}"
    )

if __name__ == "__main__":
    main()