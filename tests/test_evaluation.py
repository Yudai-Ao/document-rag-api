from evaluation.evaluate import build_evaluate_result


def test_build_evaluate_result_accepts_multiple_expected_sourcs():
    case = {
        "id": "ecs-001",
        "question": "Application Portは何番ですか？",
        "category": "direct",
        "answerable": True,
        "expected_answer": "8000",
        "expected_sources": [
            "ecs-troubleshooting.pdf",
            "alb-troubleshooting.pdf"
        ]
    }

    rag_result = {
        "answer": "Application Portは8000番です。",
        "abstained": False,
        "contexts": [
            {
                "source": "alb-troubleshooting.pdf",
                "chunk_id": 1,
                "distance": 0.4
            },
            {
                "source": "ecs-troubleshooting.pdf",
                "chunk_id": 1,
                "distance": 0.5
            }
        ]
    }

    result = build_evaluate_result(
        case=case,
        rag_result=rag_result
    )

    assert result["retrieval"]["expected_source_found"] is True
    assert result["retrieval"]["expected_source_rank"] == 1
    assert result["retrieval"]["top1_distance"] == 0.4
    assert result["abstained"] is False
