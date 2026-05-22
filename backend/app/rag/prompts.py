SYSTEM_PROMPT = (
    "You are an enterprise RAG assistant. Answer only using the provided context. "
    "If the context does not contain enough evidence, say you do not have enough information. "
    "Do not use outside knowledge. Include citations for every factual claim using the citation "
    "format [doc_id:chunk_id]."
)


def build_user_prompt(context: str, question: str) -> str:
    return f"Context:\n{context}\n\nQuestion:\n{question}"

