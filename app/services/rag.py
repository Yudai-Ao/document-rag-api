from app.services.bedrock import generate_answer
from app.services.vector_search import search_similar_chunks
from app.config import settings


def build_prompt(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join(
        [
            f"[source: {context["source"]}, chunk_id: {context["chunk_id"]}]\n{context["text"]}"
            for context in contexts
        ]
    )

    prompt = f"""
    以下の文書だけを参考にして質問に回答してください。
    文書に答えが含まれていない場合は、「文書からは分かりません」と回答してください。

    【参考文書】
    {context_text}

    【質問】
    {question}
    """

    return prompt


def generate_rag_answer(
    question: str,
    chunks: list[dict],
    top_k: int = settings.top_k
) -> dict:
    contexts = search_similar_chunks(
        question=question,
        chunks=chunks,
        top_k=top_k
    )

    prompt = build_prompt(
        question=question,
        contexts=contexts
    )

    answer = generate_answer(prompt)

    return {
        "answer": answer,
        "contexts": contexts
    }
