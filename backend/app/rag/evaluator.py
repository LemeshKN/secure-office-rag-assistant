from app.retrieval.hybrid_retriever import RetrievedChunk


def retrieval_precision(chunks: list[RetrievedChunk], expected_doc_ids: list[int] | None) -> float | None:
    if not expected_doc_ids:
        return None
    if not chunks:
        return 0.0
    expected = set(expected_doc_ids)
    relevant = sum(1 for chunk in chunks if chunk.document_id in expected)
    return round(relevant / len(chunks), 4)

