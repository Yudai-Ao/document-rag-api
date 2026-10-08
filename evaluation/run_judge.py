
import json
import time
from pathlib import Path

from evaluation.judge import judge_answer


BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "results" / "evidence_gate_top3.json"
OUTPUT_FILE = BASE_DIR / "results" / "judge_top3.json"

DELAY_SECONDS = 5


def load_json(file_path: Path) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results: list[dict]) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(temporary_file, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    temporary_file.replace(OUTPUT_FILE)


def main():
    cases = load_json(INPUT_FILE)

    # 回答生成されたAnswerableのみ評価
    target_cases = [
        case
        for case in cases
        if case["answerable"] and not case["abstained"]
    ]

    # 途中結果があれば再利用
    results = (
        load_json(OUTPUT_FILE)
        if OUTPUT_FILE.exists()
        else []
    )

    completed_ids = {
        result["id"]
        for result in results
    }

    remaining_cases = [
        case
        for case in target_cases
        if case["id"] not in completed_ids
    ]

    print(f"Target cases: {len(target_cases)}")
    print(f"Completed: {len(results)}")
    print(f"Remaining: {len(remaining_cases)}")

    for index, case in enumerate(remaining_cases):
        print(f"\n[{case['id']}] {case['question']}")

        judgment = judge_answer(
            question=case["question"],
            expected_answer=case["expected_answer"],
            generated_answer=case["answer"],
            contexts=case["sources"]
        )

        evaluation_result = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected_answer": case["expected_answer"],
            "generated_answer": case["answer"],
            "judgment": judgment
        }

        results.append(evaluation_result)
        save_results(results)

        print(
            json.dumps(
                judgment,
                ensure_ascii=False,
                indent=2
            )
        )

        print(
            f"Progress: {len(results)}/{len(target_cases)}"
        )

        if index < len(remaining_cases) - 1:
            time.sleep(DELAY_SECONDS)

    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
