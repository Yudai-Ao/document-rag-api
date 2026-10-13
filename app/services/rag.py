
from app.services.bedrock import generate_answer
from app.services.vector_store import search_vectors
from app.services.evidence import has_sufficient_evidence
from app.config import settings


MAX_TOP_K = 5


def build_prompt(
    question: str,
    contexts: list[dict]
) -> str:

    context_text = "\n\n".join(
        f"[source: {context['source']}, "
        f"chunk_id: {context['chunk_id']}]\n"
        f"{context['text']}"
        for context in contexts
    )

    prompt = f"""
    以下の文書だけを参考にして質問に回答してください。
    文書に答えが含まれていない場合は、
    「文書からは分かりません」と回答してください。

    【参考文書】
    {context_text}

    【質問】
    {question}
    """

    return prompt


def generate_rag_answer(
    question: str,
    document_id: str | None = None,
    top_k: int | None = None
) -> dict:

    # 1. Top-Kの設定
    if top_k is None:
        top_k = settings.top_k

    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    # 2. 通常検索（デフォルトTop-3）
    contexts = search_vectors(
        question=question,
        document_id=document_id,
        top_k=top_k
    )

    # 検索結果がない場合
    if not contexts:
        return {
            "answer": "",
            "contexts": [],
            "abstained": True
        }

    # 3. Evidence Gate（1回目）
    sufficient = has_sufficient_evidence(
        question=question,
        contexts=contexts
    )

    # 4. Evidence不足の場合だけTop-Kを拡張
    if not sufficient and top_k < MAX_TOP_K:

        print(
        f"[Adaptive Retrieval] "
        f"Evidence insufficient. "
        f"Retrying with top_k={MAX_TOP_K}"
    )

        contexts = search_vectors(
            question=question,
            document_id=document_id,
            top_k=MAX_TOP_K
        )

        # 再検索後のEvidence Gate
        sufficient = has_sufficient_evidence(
            question=question,
            contexts=contexts
        )

    # 5. Evidence不足なら回答保留
    if not sufficient:
        return {
            "answer": "文書からは分かりません",
            "contexts": contexts,
            "abstained": True
        }

    # 6. Evidence十分なら回答生成
    prompt = build_prompt(
        question=question,
        contexts=contexts
    )

    answer = generate_answer(prompt)

    return {
        "answer": answer,
        "contexts": contexts,
        "abstained": False
    }
