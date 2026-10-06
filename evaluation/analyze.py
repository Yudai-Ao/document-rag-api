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


def print_retrieval_failures(
    results: list[dict]
) -> None:

    failures = [
        result
        for result in results
        if (
            result["answerable"]
            and result["retrieval"]["expected_source_rank"] != 1
        )
    ]

    print("\n=== Top-1 Retrieval Failures ===")

    if not failures:
        print("No failures.")
        return

    for result in failures:
        print(
            f"\n[{result['id']}] "
            f"{result['question']}"
        )

        print(
            "Expected Sources: "
            f"{result['expected_sources']}"
        )

        print("Retrieved Sources:")

        for rank, source in enumerate(
            result["sources"],
            start=1
        ):
            print(
                f"  {rank}. "
                f"{source['source']} "
                f"(distance={source['distance']:.3f})"
            )


def print_unanswerable_distances(
    results: list[dict]
) -> None:

    cases = [
        result
        for result in results
        if not result["answerable"]
    ]

    cases = sorted(
        cases,
        key=lambda result:
            result["retrieval"]["top1_distance"]
    )

    print("\n=== Unanswerable Top-1 Distances ===")

    for result in cases:
        print(
            f"{result['id']}: "
            f"{result['retrieval']['top1_distance']:.3f} "
            f"- {result['question']}"
        )


def print_category_metrics(
    results: list[dict]
) -> None:

    categories = sorted(
        {
            result["category"]
            for result in results
        }
    )

    print("\n=== Metrics by Category ===")

    for category in categories:
        cases = [
            result
            for result in results
            if result["category"] == category
        ]

        answerable_cases = [
            result
            for result in cases
            if result["answerable"]
        ]

        top1_hits = [
            result
            for result in answerable_cases
            if result["retrieval"]["expected_source_rank"] == 1
        ]

        source_hits = [
            result
            for result in answerable_cases
            if result["retrieval"]["expected_source_found"]
        ]

        distances = [
            result["retrieval"]["top1_distance"]
            for result in cases
            if result["retrieval"]["top1_distance"] is not None
        ]

        print(
            f"\nCategory: {category}"
        )

        print(
            f"Cases: {len(cases)}"
        )

        if answerable_cases:
            print(
                "Hit Rate: "
                f"{len(source_hits) / len(answerable_cases):.2%}"
            )

            print(
                "Top-1 Rate: "
                f"{len(top1_hits) / len(answerable_cases):.2%}"
            )

        if distances:
            print(
                "Avg Top-1 Distance: "
                f"{sum(distances) / len(distances):.3f}"
            )


def print_top_k_comparison(
    results: list[dict]
) -> None:

    answerable_cases = [
        result
        for result in results
        if result["answerable"]
    ]

    print("\n=== Top-K Comparison ===")

    for top_k in [1, 2, 3]:
        hits = 0

        for result in answerable_cases:
            expected_sources = set(
                result["expected_sources"]
            )

            retrieved_sources = {
                source["source"]
                for source in result["sources"][:top_k]
            }

            if retrieved_sources & expected_sources:
                hits += 1

        hit_rate = (
            hits / len(answerable_cases)
            if answerable_cases
            else 0
        )

        print(
            f"Top-{top_k}: "
            f"{hits}/{len(answerable_cases)} "
            f"({hit_rate:.2%})"
        )


def main():
    results = load_results()

    metrics = calculate_metrics(
        results
    )

    print(
        "=== RAG Baseline Evaluation ==="
    )

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

    print_retrieval_failures(
        results
    )

    print_unanswerable_distances(
        results
    )

    print_category_metrics(
        results
    )

    print_top_k_comparison(
        results
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