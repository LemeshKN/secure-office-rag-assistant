import json

from app.auth.rbac import access_metadata
from app.config import Settings
from app.ingestion.embeddings import HashEmbeddingProvider
from app.ingestion.reembed import reembed_all
from app.models import Chunk, Document, User
from app.retrieval.vector_store import InMemoryVectorStore


def add_documents(db):
    owner = db.query(User).filter_by(username="amit").one()
    db.add_all(
        [
            Document(
                id=10,
                filename="a.txt",
                title="A",
                owner_user_id=owner.id,
                allowed_roles=json.dumps(["hr"]),
                allowed_user_ids="[]",
                file_type="txt",
                upload_path="/tmp/a.txt",
            ),
            Chunk(id=100, document_id=10, chunk_index=0, text="First chunk.", chroma_id="doc-10-chunk-0"),
            Chunk(id=101, document_id=10, chunk_index=1, text="Second chunk.", chroma_id="doc-10-chunk-1"),
        ]
    )
    db.commit()
    return owner


def fresh_store():
    store = InMemoryVectorStore("test_reembed")
    store.reset()
    return store


def test_reembed_rebuilds_every_chunk_with_permission_metadata(seeded_db):
    owner = add_documents(seeded_db)
    store = fresh_store()

    assert reembed_all(seeded_db, HashEmbeddingProvider(), store) == (1, 2)

    by_id = {record.chroma_id: record for record in store.records}
    expected = access_metadata(10, owner.id, ["hr"], [])
    expected.update({"chunk_id": 100, "filename": "a.txt", "page_number": 0, "chunk_index": 0})
    assert by_id["doc-10-chunk-0"].metadata == expected
    assert by_id["doc-10-chunk-1"].metadata["chunk_id"] == 101


def test_reembed_is_safe_to_repeat(seeded_db):
    add_documents(seeded_db)
    store = fresh_store()
    reembed_all(seeded_db, HashEmbeddingProvider(), store)
    reembed_all(seeded_db, HashEmbeddingProvider(), store)
    assert len(store.records) == 2


def test_gemini_uses_its_own_vector_collection():
    hash_settings = Settings(embedding_provider="auto")
    gemini_settings = Settings(embedding_provider="gemini")
    assert hash_settings.vector_collection == hash_settings.chroma_collection
    assert gemini_settings.vector_collection != hash_settings.vector_collection
    assert "gemini-embedding" in gemini_settings.vector_collection