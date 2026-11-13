from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.rbac import access_metadata
from app.database import Base
from app.ingestion.embeddings import HashEmbeddingProvider
from app.models import Chunk, Document, User
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.vector_store import InMemoryVectorStore, VectorRecord


def test_developer_role_grant_and_hr_denied() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    owner = User(id=1, username="owner", password_hash="x", role="manager")
    developer = User(id=2, username="dev", password_hash="x", role="developer")
    hr_user = User(id=3, username="hr", password_hash="x", role="hr")
    document = Document(
        id=10,
        filename="dev.txt",
        title="Dev",
        owner_user_id=1,
        allowed_roles='["developer"]',
        allowed_user_ids="[]",
        file_type="txt",
        upload_path="/tmp/dev.txt",
    )
    chunk = Chunk(
        id=100,
        document_id=10,
        chunk_index=0,
        text="Developer onboarding checklist covers repository access.",
        chroma_id="doc-10-chunk-0",
    )
    db.add_all([owner, developer, hr_user, document, chunk])
    db.commit()

    embeddings = HashEmbeddingProvider()
    store = InMemoryVectorStore("test_role_grants")
    store.reset()
    metadata = access_metadata(10, 1, ["developer"], [])
    metadata.update({"chunk_id": 100, "filename": "dev.txt", "chunk_index": 0})
    store.upsert(
        [
            VectorRecord(
                chroma_id=chunk.chroma_id,
                text=chunk.text,
                embedding=embeddings.embed_query(chunk.text),
                metadata=metadata,
            )
        ]
    )
    retriever = HybridRetriever(embeddings, store, KeywordStore())

    question = "developer onboarding repository access"
    dev_results = retriever.retrieve(db, developer, question, final_top_k=5)
    hr_results = retriever.retrieve(db, hr_user, question, final_top_k=5)

    assert [result.document_id for result in dev_results] == [10]
    assert hr_results == []
    