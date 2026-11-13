from app.rag.citation import format_context
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval.hybrid_retriever import RetrievedChunk


def build_prompt_parts(question: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
    """Return (system_text, user_text). Every LLM client and the cost estimate use this."""
    return SYSTEM_PROMPT, build_user_prompt(format_context(chunks), question)