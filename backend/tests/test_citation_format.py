from types import SimpleNamespace

from app.config import Settings
from app.rag.citation import build_citations, normalize_citations
from app.rag.llm_client import GeminiClient
from app.rag.prompts import SYSTEM_PROMPT
from app.retrieval.hybrid_retriever import RetrievedChunk


def make_chunk(chunk_id: int) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=3,
        chunk_id=chunk_id,
        filename="notes.txt",
        page_number=None,
        chunk_index=0,
        text="Some text.",
    )


def test_prompt_asks_for_short_citation_form():
    assert "[doc_id:chunk_id]" in SYSTEM_PROMPT
    assert "[3:7]" in SYSTEM_PROMPT


def test_normalize_rewrites_long_form():
    text = "PostgreSQL [doc_id=3 chunk_id=3]. Thursday [doc_id=3, chunk_id=4]."
    assert normalize_citations(text) == "PostgreSQL [3:3]. Thursday [3:4]."


def test_normalize_keeps_short_form():
    assert normalize_citations("Fact [3:7].") == "Fact [3:7]."


def test_answer_without_citation_has_no_sources():
    chunks = [make_chunk(1), make_chunk(2), make_chunk(3)]
    assert build_citations("I do not have enough information.", chunks) == []


def test_only_cited_chunks_become_sources():
    chunks = [make_chunk(1), make_chunk(2), make_chunk(3)]
    citations = build_citations("Fact [3:2].", chunks)
    assert [c.chunk_id for c in citations] == [2]


def test_gemini_client_normalizes_long_citations():
    class Models:
        def generate_content(self, model, contents, config):
            usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5, thoughts_token_count=0)
            return SimpleNamespace(text="Fact [doc_id=3 chunk_id=3].", usage_metadata=usage)

    client = GeminiClient(Settings(), "gemini-3.5-flash-lite", client=SimpleNamespace(models=Models()))
    assert client.generate("q", []).answer == "Fact [3:3]."