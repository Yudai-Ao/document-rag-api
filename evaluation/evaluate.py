
import argparse
import json
import time
from pathlib import Path

from app.services.rag import generate_rag_answer


BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "datasets"
RESULTS_DIR = BASE_DIR / "results"

DATASET_FILES = [
    "ecs_evaluation.json",
    "alb_evaluation.json",
    "iam_evaluation.json",
    "s3_evaluation.json",
    "bedrock_evaluation.json",
    "unanswerable_evaluation.json",
]


def load_dataset(file_name: str) -> list[dict]:
    file_path = DATASET_DIR / file_name

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_evaluation_cases() -> list[dict]:
    cases = []

    for file_name in DATASET_FILES:
        cases.extend(
            load_dataset(file_name)
        )

    return cases


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
        "abstained": rag_result["abstained"],
        "sources": contexts,
        "retrieval": {
            "expected_source_found": expected_source_found,
            "expected_source_rank": expected_source_rank,
            "top1_distance": top1_distance
        }
    }


def save_results(
    results: list[dict],
    output_file: Path
) -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # 書き込み途中で停止しても既存結果を壊しにくくする
    temporary_file = output_file.with_suffix(".tmp")

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    temporary_file.replace(output_file)


def load_existing_results(
    output_file: Path
) -> list[dict]:

    if not output_file.exists():
        return []

    with open(
        output_file,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        type=str,
        default="evidence_gate_v2.json"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=5.0
    )

    parser.add_argument(
        "--resume",
        action="store_true"
    )

    args = parser.parse_args()

    # 保存先はresultsディレクトリ内のファイル名に限定
    output_name = Path(args.output)

    if (
        output_name.name != args.output
        or output_name.suffix != ".json"
        or output_name.name in {
            "baseline.json",
            "baseline_metrics.json",
            "evidence_gate_v1.json"
        }
    ):
        parser.error(
            "Invalid output filename or protected evaluation file."
        )

    if args.delay < 0:
        parser.error("--delay must be zero or greater.")

    output_file = RESULTS_DIR / output_name

    evaluation_cases = load_evaluation_cases()

    print(
        f"{len(evaluation_cases)} evaluation cases loaded."
    )

    if args.resume:
        results = load_existing_results(output_file)
    else:
        if output_file.exists():
            parser.error(
                f"{output_file} already exists. "
                "Use --resume or choose another filename."
            )
        results = []

    completed_ids = {
        result["id"]
        for result in results
    }

    remaining_cases = [
        case
        for case in evaluation_cases
        if case["id"] not in completed_ids
    ]

    print(f"Completed cases: {len(results)}")
    print(f"Remaining cases: {len(remaining_cases)}")

    for index, case in enumerate(remaining_cases):

        print(
            f"\n[{case['id']}] {case['question']}",
            flush=True
        )

        # 失敗時は例外を伝播させ、未完了の質問を保存しない
        result = generate_rag_answer(
            question=case["question"],
            document_id=None,
            top_k=3
        )

        evaluation_result = build_evaluate_result(
            case=case,
            rag_result=result
        )

        results.append(evaluation_result)

        # 1問完了するたびに保存
        save_results(
            results=results,
            output_file=output_file
        )

        print(
            f"Answer: {result['answer']}",
            flush=True
        )

        print(
            f"Contexts: {len(result['contexts'])}"
        )

        print(
            f"Abstained: {result['abstained']}"
        )

        print(
            f"Progress: {len(results)}/{len(evaluation_cases)}"
        )

        # 最後の質問の後は待機しない
        if index < len(remaining_cases) - 1:
            time.sleep(args.delay)

    print(
        f"\nEvaluation results saved to {output_file}"
    )

    print(
        f"Total completed cases: {len(results)}"
    )


if __name__ == "__main__":
    main()
