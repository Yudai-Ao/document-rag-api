
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).parent

DATASET_FILE = BASE_DIR / "datasets" / "ecs_evaluation.json"
BASELINE_FILE = BASE_DIR / "results" / "baseline.json"


def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """空白・改行などの表記差を吸収する。"""
    return re.sub(r"\s+", "", text).lower()


def is_evidence_hit(
    contexts: list[dict],
    expected_evidence: dict
) -> bool:
    """グループ内AND、グループ間ORで根拠を判定する。"""

    for group in expected_evidence["groups"]:
        group_hit = True

        for evidence in group["evidences"]:
            source = evidence["source"]
            expected_text = normalize_text(
                evidence["evidence_text"]
            )

            matched = any(
                context["source"] == source
                and expected_text in normalize_text(context["text"])
                for context in contexts
            )

            if not matched:
                group_hit = False
                break

        if group_hit:
            return True

    return False


def main():
    dataset = load_json(DATASET_FILE)
    baseline = load_json(BASELINE_FILE)

    case = next(
        item for item in dataset
        if item["id"] == "ecs-001"
    )

    result = next(
        item for item in baseline
        if item["id"] == "ecs-001"
    )

    print(f"Question: {case['question']}")
    print("\n=== Evidence Hit@K ===")

    for k in [1, 2, 3]:
        contexts = result["sources"][:k]

        hit = is_evidence_hit(
            contexts=contexts,
            expected_evidence=case["expected_evidence"]
        )

        print(
            f"Top-{k}: {'HIT' if hit else 'MISS'}"
        )


if __name__ == "__main__":
    main()
