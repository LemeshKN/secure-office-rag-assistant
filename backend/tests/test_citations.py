from app.rag.citation import build_citations, format_context
from app.retrieval.hybrid_retriever import RetrievedChunk


def test_context_and_citation_formatting() -> None:
    chunk = RetrievedChunk(
        document_id=12,
        chunk_id=45,
        filename="policy.pdf",
        page_number=3,
        chunk_index=0,
        text="The policy requires manager approval for expenses above 500 dollars.",
    )
    context = format_context([chunk])
    assert "[doc_id=12 chunk_id=45 filename=policy.pdf page=3]" in context

    citations = build_citations("Approval is required [12:45].", [chunk])
    assert citations[0].document_id == 12
    assert citations[0].chunk_id == 45
    assert "manager approval" in citations[0].quoted_text

