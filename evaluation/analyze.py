import json
from pathlib import Path

from app.config import settings


BASE_DIR = Path(__file__).parent
BASELINE_FILE = BASE_DIR / "results" / "baseline.json"
METRICS_FILE = BASE_DIR / "results" / "baseline_metrics.json"


def load_results() -> list[dict]:
    with open(
        BASELINE_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def calculate_metrics(
    results: list[dict]
) -> dict:

    answerable = [
        result
        for result in results
        if result["answerable"]
    ]

    unanswerable = [
        result
        for result in results
        if not result["answerable"]
    ]

    source_hits = [
        result
        for result in answerable
        if result["retrieval"]["expected_source_found"]
    ]

    top1_hits = [
        result
        for result in answerable
        if result["retrieval"]["expected_source_rank"] == 1
    ]

    answerable_distances = [
        result["retrieval"]["top1_distance"]
        for result in answerable
        if result["retrieval"]["top1_distance"] is not None
    ]

    unanswerable_distances = [
        result["retrieval"]["top1_distance"]
        for result in unanswerable
        if result["retrieval"]["top1_distance"] is not None
    ]

    return {
        "total_cases": len(results),
        "answerable_cases": len(answerable),
        "unanswerable_cases": len(unanswerable),

        "expected_source_hit_rate": (
            len(source_hits) / len(answerable)
            if answerable
            else 0
        ),

        "expected_source_top1_rate": (
            len(top1_hits) / len(answerable)
            if answerable
            else 0
        ),

        "answerable_avg_top1_distance": (
            sum(answerable_distances)
            / len(answerable_distances)
            if answerable_distances
            else None
        ),

        "unanswerable_avg_top1_distance": (
            sum(unanswerable_distances)
            / len(unanswerable_distances)
            if unanswerable_distances
            else None
        )
    }


def main():
    results = load_results()

    metrics = calculate_metrics(
        results
    )

    print("=== RAG Baseline Evaluation ===")

    print(
        f"Total Cases: {metrics['total_cases']}"
    )

    print(
        f"Answerable Cases: {metrics['answerable_cases']}"
    )

    print(
        f"Unanswerable Cases: {metrics['unanswerable_cases']}"
    )

    print(
        "Expected Source Hit Rate: "
        f"{metrics['expected_source_hit_rate']:.2%}"
    )

    print(
        "Expected Source Top-1 Rate: "
        f"{metrics['expected_source_top1_rate']:.2%}"
    )

    print(
        "Answerable Avg Top-1 Distance: "
        f"{metrics['answerable_avg_top1_distance']:.3f}"
    )

    print(
        "Unanswerable Avg Top-1 Distance: "
        f"{metrics['unanswerable_avg_top1_distance']:.3f}"
    )

    baseline_summary = {
        "configuration": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "top_k": settings.top_k
        },
        "metrics": metrics
    }

    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            baseline_summary,
            f,
            ensure_ascii=False,
            indent=2
        )
    print(
    f"\nBaseline metrics saved to {METRICS_FILE}"
    )

if __name__ == "__main__":
    main()