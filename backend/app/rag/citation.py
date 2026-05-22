import re
from textwrap import shorten

from app.retrieval.hybrid_retriever import RetrievedChunk
from app.schemas import Citation, RetrievedChunkOut


CITATION_RE = re.compile(r"\[(?P<doc_id>\d+):(?P<chunk_id>\d+)\]")


def format_context(chunks: list[RetrievedChunk]) -> str:
    sections: list[str] = []
    for chunk in chunks:
        page = chunk.page_number if chunk.page_number is not None else "n/a"
        sections.append(
            f"[doc_id={chunk.document_id} chunk_id={chunk.chunk_id} "
            f"filename={chunk.filename} page={page}]\n{chunk.text}"
        )
    return "\n\n".join(sections)


def extract_cited_chunk_ids(answer: str) -> set[int]:
    return {int(match.group("chunk_id")) for match in CITATION_RE.finditer(answer or "")}


def build_citations(answer: str, chunks: list[RetrievedChunk], max_citations: int = 5) -> list[Citation]:
    cited_chunk_ids = extract_cited_chunk_ids(answer)
    selected = [
        chunk for chunk in chunks if not cited_chunk_ids or chunk.chunk_id in cited_chunk_ids
    ][:max_citations]
    return [
        Citation(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            filename=chunk.filename,
            page_number=chunk.page_number,
            quoted_text=shorten(chunk.text.replace("\n", " "), width=280, placeholder="..."),
        )
        for chunk in selected
    ]


def to_retrieved_chunk_out(chunks: list[RetrievedChunk]) -> list[RetrievedChunkOut]:
    return [
        RetrievedChunkOut(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            filename=chunk.filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            vector_score=round(chunk.vector_score, 4),
            keyword_score=round(chunk.keyword_score, 4),
            combined_score=round(chunk.combined_score, 4),
            rerank_score=round(chunk.rerank_score, 4),
        )
        for chunk in chunks
    ]

