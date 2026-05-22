from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.auth.rbac import build_chroma_permission_filter, can_access_document
from app.ingestion.embeddings import EmbeddingProvider
from app.models import Chunk, Document, User
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.vector_store import ChromaVectorStore, VectorSearchResult


@dataclass
class RetrievedChunk:
    document_id: int
    chunk_id: int
    filename: str
    page_number: int | None
    chunk_index: int
    text: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: float = 0.0


class HybridRetriever:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vector_store: ChromaVectorStore,
        keyword_store: KeywordStore | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.keyword_store = keyword_store or KeywordStore()

    def retrieve(
        self,
        db: Session,
        user: User,
        question: str,
        top_k_vector: int = 8,
        top_k_keyword: int = 8,
        final_top_k: int = 5,
    ) -> list[RetrievedChunk]:
        query_embedding = self.embeddings.embed_query(question)
        permission_filter = build_chroma_permission_filter(user)
        vector_results = self.vector_store.query(query_embedding, top_k_vector, permission_filter)
        vector_chunks = self._hydrate_vector_results(db, user, vector_results)

        keyword_results = self.keyword_store.search(db, user, question, top_k_keyword)
        keyword_chunks = []
        for result in keyword_results:
            hydrated = self._hydrate_chunk(db, user, result.chunk_id)
            if hydrated:
                hydrated.keyword_score = result.score
                keyword_chunks.append(hydrated)

        merged: dict[int, RetrievedChunk] = {}
        for chunk in vector_chunks + keyword_chunks:
            existing = merged.get(chunk.chunk_id)
            if not existing:
                merged[chunk.chunk_id] = chunk
                continue
            existing.vector_score = max(existing.vector_score, chunk.vector_score)
            existing.keyword_score = max(existing.keyword_score, chunk.keyword_score)

        for chunk in merged.values():
            chunk.combined_score = (0.65 * chunk.vector_score) + (0.35 * chunk.keyword_score)

        return sorted(merged.values(), key=lambda item: item.combined_score, reverse=True)[:final_top_k]

    def _hydrate_vector_results(
        self,
        db: Session,
        user: User,
        vector_results: list[VectorSearchResult],
    ) -> list[RetrievedChunk]:
        hydrated: list[RetrievedChunk] = []
        for result in vector_results:
            chunk_id = int(result.metadata.get("chunk_id", 0) or 0)
            chunk = self._hydrate_chunk(db, user, chunk_id)
            if chunk:
                chunk.vector_score = result.score
                hydrated.append(chunk)
        return hydrated

    def _hydrate_chunk(self, db: Session, user: User, chunk_id: int) -> RetrievedChunk | None:
        if not chunk_id:
            return None
        chunk = db.get(Chunk, chunk_id)
        if not chunk:
            return None
        document = db.get(Document, chunk.document_id)
        if not document or not can_access_document(user, document):
            return None
        return RetrievedChunk(
            document_id=document.id,
            chunk_id=chunk.id,
            filename=document.filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
        )

