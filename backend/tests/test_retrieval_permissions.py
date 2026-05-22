from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.rbac import access_metadata
from app.database import Base
from app.ingestion.embeddings import HashEmbeddingProvider
from app.models import Chunk, Document, User
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.vector_store import InMemoryVectorStore, VectorRecord


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed(db):
    users = [
        User(id=1, username="admin", password_hash="x", role="admin"),
        User(id=2, username="manager", password_hash="x", role="manager"),
        User(id=3, username="employee", password_hash="x", role="employee"),
        User(id=4, username="guest", password_hash="x", role="guest"),
    ]
    docs = [
        Document(
            id=10,
            filename="manager.txt",
            title="Manager",
            owner_user_id=2,
            allowed_roles='["manager"]',
            allowed_user_ids="[]",
            file_type="txt",
            upload_path="/tmp/manager.txt",
        ),
        Document(
            id=20,
            filename="employee.txt",
            title="Employee",
            owner_user_id=3,
            allowed_roles='["employee"]',
            allowed_user_ids="[]",
            file_type="txt",
            upload_path="/tmp/employee.txt",
        ),
        Document(
            id=30,
            filename="guest.txt",
            title="Guest",
            owner_user_id=4,
            allowed_roles='["guest"]',
            allowed_user_ids="[]",
            file_type="txt",
            upload_path="/tmp/guest.txt",
        ),
    ]
    chunks = [
        Chunk(
            id=100,
            document_id=10,
            chunk_index=0,
            text="Manager compensation plan includes leadership bonus details.",
            chroma_id="doc-10-chunk-0",
        ),
        Chunk(
            id=200,
            document_id=20,
            chunk_index=0,
            text="Employee handbook includes expense reimbursement rules.",
            chroma_id="doc-20-chunk-0",
        ),
        Chunk(
            id=300,
            document_id=30,
            chunk_index=0,
            text="Guest orientation explains public lobby access.",
            chroma_id="doc-30-chunk-0",
        ),
    ]
    db.add_all(users + docs + chunks)
    db.commit()
    return users, docs, chunks


def build_retriever(docs, chunks):
    embeddings = HashEmbeddingProvider()
    store = InMemoryVectorStore("test_permissions")
    store.reset()
    records = []
    role_map = {10: ["manager"], 20: ["employee"], 30: ["guest"]}
    owner_map = {10: 2, 20: 3, 30: 4}
    for chunk in chunks:
        metadata = access_metadata(chunk.document_id, owner_map[chunk.document_id], role_map[chunk.document_id], [])
        metadata.update({"chunk_id": chunk.id, "filename": f"{chunk.document_id}.txt", "chunk_index": 0})
        records.append(
            VectorRecord(
                chroma_id=chunk.chroma_id,
                text=chunk.text,
                embedding=embeddings.embed_query(chunk.text),
                metadata=metadata,
            )
        )
    store.upsert(records)
    return HybridRetriever(embeddings, store, KeywordStore())


def test_guest_cannot_retrieve_employee_only_chunks() -> None:
    db = make_session()
    users, docs, chunks = seed(db)
    retriever = build_retriever(docs, chunks)
    results = retriever.retrieve(db, users[3], "employee expense reimbursement", final_top_k=5)
    assert all(result.document_id != 20 for result in results)
    assert {result.document_id for result in results} <= {30}


def test_employee_cannot_retrieve_manager_only_chunks() -> None:
    db = make_session()
    users, docs, chunks = seed(db)
    retriever = build_retriever(docs, chunks)
    results = retriever.retrieve(db, users[2], "manager compensation bonus", final_top_k=5)
    assert all(result.document_id != 10 for result in results)
    assert {result.document_id for result in results} <= {20}


def test_manager_can_retrieve_manager_chunks() -> None:
    db = make_session()
    users, docs, chunks = seed(db)
    retriever = build_retriever(docs, chunks)
    results = retriever.retrieve(db, users[1], "manager compensation bonus", final_top_k=5)
    assert [result.document_id for result in results][:1] == [10]


def test_admin_retrieves_all_authorized_by_admin_role() -> None:
    db = make_session()
    users, docs, chunks = seed(db)
    retriever = build_retriever(docs, chunks)
    results = retriever.retrieve(db, users[0], "manager employee guest access", final_top_k=5)
    assert {result.document_id for result in results} == {10, 20, 30}

