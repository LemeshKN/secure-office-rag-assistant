"""Rebuild the vector index from the chunks already stored in the database.

Run from the backend folder after you change the embedding setup:
    python -m app.ingestion.reembed
It reads the database and writes only to the vector collection of the active embedding setup.
"""
import json

from sqlalchemy.orm import Session

from app.auth.rbac import access_metadata
from app.ingestion.embeddings import EmbeddingProvider
from app.models import Chunk, Document
from app.retrieval.vector_store import VectorRecord


def reembed_all(db: Session, embeddings: EmbeddingProvider, store) -> tuple[int, int]:
    """Embed every stored chunk again and upsert it. Returns (documents, chunks)."""
    document_count = chunk_count = 0
    for document in db.query(Document).order_by(Document.id).all():
        chunks = (
            db.query(Chunk)
            .filter(Chunk.document_id == document.id)
            .order_by(Chunk.chunk_index)
            .all()
        )
        if not chunks:
            continue
        roles = json.loads(document.allowed_roles or "[]")
        user_ids = json.loads(document.allowed_user_ids or "[]")
        vectors = embeddings.embed_documents([chunk.text for chunk in chunks])

        records: list[VectorRecord] = []
        for chunk, vector in zip(chunks, vectors):
            metadata = access_metadata(document.id, document.owner_user_id, roles, user_ids)
            metadata.update(
                {
                    "chunk_id": chunk.id,
                    "filename": document.filename,
                    "page_number": chunk.page_number or 0,
                    "chunk_index": chunk.chunk_index,
                }
            )
            records.append(
                VectorRecord(chroma_id=chunk.chroma_id, text=chunk.text, embedding=vector, metadata=metadata)
            )
        store.upsert(records)
        document_count += 1
        chunk_count += len(records)
    return document_count, chunk_count


def main() -> None:
    from app.config import get_settings
    from app.database import SessionLocal
    from app.ingestion.embeddings import get_embedding_provider
    from app.retrieval.vector_store import ChromaVectorStore

    settings = get_settings()
    embeddings = get_embedding_provider(settings)
    store = ChromaVectorStore(settings)
    if store._fallback is not None:
        raise SystemExit("Chroma is not available, so nothing would be saved.")

    print(f"Embedding model: {embeddings.model_name}")
    print(f"Vector collection: {settings.vector_collection}")
    db = SessionLocal()
    try:
        documents, chunks = reembed_all(db, embeddings, store)
    finally:
        db.close()
    print(f"Done. Re-embedded {documents} documents and {chunks} chunks.")


if __name__ == "__main__":
    main()