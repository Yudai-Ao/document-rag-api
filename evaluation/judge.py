
import json

from app.services.bedrock import generate_answer


def build_judge_prompt(
    question: str,
    expected_answer: str,
    generated_answer: str,
    contexts: list[dict]
) -> str:

    evidence_text = "\n\n".join(
        f"[Source: {context['source']}]\n{context['text']}"
        for context in contexts
    )

    return f"""
あなたはRAGシステムの回答品質を評価するJudgeです。

以下の2つの観点で回答を評価してください。

【Correctness】
生成回答が期待回答の重要事項を満たしているか判定してください。
表現の違いは許容します。
期待回答の重要事項に誤りや不足がある場合はfalseです。

【Faithfulness】
生成回答に含まれる実質的な主張が、
Evidenceによって裏付けられているか判定してください。
Evidenceに存在しない情報を一般知識で補完している場合はfalseです。

CorrectnessとFaithfulnessは独立して判定してください。

回答は以下のJSON形式のみで返してください。
Markdownやコードブロックは付けないでください。

{{
  "correctness": {{
    "passed": true,
    "reason": "判定理由"
  }},
  "faithfulness": {{
    "passed": true,
    "reason": "判定理由"
  }}
}}

【質問】
{question}

【期待回答】
{expected_answer}

【生成回答】
{generated_answer}

【Evidence】
{evidence_text}
"""


def judge_answer(
    question: str,
    expected_answer: str,
    generated_answer: str,
    contexts: list[dict]
) -> dict:

    prompt = build_judge_prompt(
        question=question,
        expected_answer=expected_answer,
        generated_answer=generated_answer,
        contexts=contexts
    )

    response = generate_answer(prompt)

    result = json.loads(response)

    for metric in ("correctness", "faithfulness"):
        if metric not in result:
            raise ValueError(
                f"Missing metric: {metric}"
            )

        if not isinstance(result[metric].get("passed"), bool):
            raise ValueError(f"Invalid passed value: {metric}")

        if not isinstance(result[metric].get("reason"), str):
            raise ValueError(f"Invalid reason value: {metric}")

    return result



def main():
    result_file = (
        "evaluation/results/evidence_gate_top3.json"
    )

    with open(result_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    case = next(
        result for result in results
        if result["id"] == "ecs-001"
    )

    judgment = judge_answer(
        question=case["question"],
        expected_answer=case["expected_answer"],
        generated_answer="Application Portは8080番です。",
        contexts=case["sources"]
    )

    print(
        json.dumps(
            judgment,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
