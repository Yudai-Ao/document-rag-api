from app.services.bedrock import generate_answer


def build_evidence_prompt(
    question: str,
    contexts: list[dict]
) -> str:

    evidence_text = "\n\n".join(
        context["text"]
        for context in contexts
    )

    prompt = f"""
    以下のEvidenceだけを根拠として、
    質問に具体的に回答できるか判定してください。

    質問と関連する情報が含まれているだけでは不十分です。
    質問への回答を直接裏付ける情報がEvidenceに含まれている場合のみ、
    SUFFICIENTと判定してください。

    Evidenceに質問への回答が明示されていない場合や、
    推測・一般知識を使わなければ回答できない場合は、
    INSUFFICIENTと判定してください。

    回答は必ず次のどちらか一語だけにしてください。

    SUFFICIENT
    INSUFFICIENT

    【Evidence】
    {evidence_text}

    【質問】
    {question}
    """

    return prompt


def has_sufficient_evidence(
    question: str,
    contexts: list[dict]
) -> bool:

    if not contexts:
        return False

    prompt = build_evidence_prompt(
        question=question,
        contexts=contexts
    )

    result = generate_answer(prompt)

    normalized_result = result.strip().upper()

    return normalized_result == "SUFFICIENT"