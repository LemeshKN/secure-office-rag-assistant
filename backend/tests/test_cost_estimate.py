import json

import pytest

from app.auth.rbac import access_metadata
from app.config import Settings, get_settings
from app.cost.pricing import calculate_cost
from app.ingestion.embeddings import HashEmbeddingProvider
from app.models import Chunk, Document, User
from app.rag.graph import RAGWorkflow
from app.rag.llm_client import LLMClient
from app.rag.citation import format_context
from app.rag.prompt_builder import build_prompt_parts
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval.hybrid_retriever import HybridRetriever, RetrievedChunk
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.reranker import Reranker
from app.retrieval.vector_store import InMemoryVectorStore, VectorRecord


class FailingLLM(LLMClient):
    model_name = "mock-grounded-llm"

    def generate(self, question, chunks, max_output_tokens=None):
        raise AssertionError("The LLM must not be called during an estimate.")


STRONG_QUESTION = "paid leave days"
WEAK_QUESTION = "zzzz qqqq"


@pytest.fixture()
def estimate_client(cost_client, session_factory, monkeypatch):
    db = session_factory()
    users = {user.username: user for user in db.query(User).all()}
    access = {
        10: (users["amit"].id, ["developer", "manager", "hr", "agent_developer"]),
        20: (users["khushi"].id, ["hr"]),
    }
    docs = [
        Document(
            id=10,
            filename="handbook.txt",
            title="Handbook",
            owner_user_id=access[10][0],
            allowed_roles=json.dumps(access[10][1]),
            allowed_user_ids="[]",
            file_type="txt",
            upload_path="/tmp/handbook.txt",
        ),
        Document(
            id=20,
            filename="hr_private.txt",
            title="HR private",
            owner_user_id=access[20][0],
            allowed_roles=json.dumps(access[20][1]),
            allowed_user_ids="[]",
            file_type="txt",
            upload_path="/tmp/hr_private.txt",
        ),
    ]
    chunks = [
        Chunk(
            id=100,
            document_id=10,
            chunk_index=0,
            text="Employees receive 24 paid leave days every year.",
            chroma_id="doc-10-chunk-0",
        ),
        Chunk(
            id=200,
            document_id=20,
            chunk_index=0,
            text="Confidential: paid leave payout for HR staff is reviewed every March.",
            chroma_id="doc-20-chunk-0",
        ),
    ]
    db.add_all(docs + chunks)
    db.commit()

    embeddings = HashEmbeddingProvider()
    store = InMemoryVectorStore("test_estimate")
    store.reset()
    records = []
    for chunk in chunks:
        owner_id, roles = access[chunk.document_id]
        metadata = access_metadata(chunk.document_id, owner_id, roles, [])
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
    db.close()

    def fake_build_workflow(db, user, model="auto"):
        settings = Settings()
        return RAGWorkflow(
            db=db,
            user=user,
            retriever=HybridRetriever(embeddings, store, KeywordStore()),
            reranker=Reranker(settings),
            llm_client=FailingLLM(),
            settings=settings,
        )

    monkeypatch.setattr("app.cost.estimate.build_workflow", fake_build_workflow)
    return cost_client


def post_estimate(client, headers, **body):
    payload = {"question": STRONG_QUESTION, **body}
    return client.post("/cost/estimate", json=payload, headers=headers)


def test_prompt_builder_matches_existing_prompt() -> None:
    chunks = [
        RetrievedChunk(
            document_id=1,
            chunk_id=2,
            filename="a.txt",
            page_number=None,
            chunk_index=0,
            text="Sample text.",
        )
    ]
    system_text, user_text = build_prompt_parts("What is this?", chunks)
    assert system_text == SYSTEM_PROMPT
    assert user_text == build_user_prompt(format_context(chunks), "What is this?")


def test_estimate_never_calls_llm(estimate_client, auth_headers) -> None:
    response = post_estimate(estimate_client, auth_headers("priya"))
    assert response.status_code == 200
    body = response.json()
    assert body["will_call_llm"] is True
    assert body["estimated_cost"] > 0


def test_private_chunk_hidden_from_other_users_but_visible_to_admin(estimate_client, auth_headers) -> None:
    priya = post_estimate(estimate_client, auth_headers("priya")).json()
    assert 100 in priya["retrieved_chunk_ids"]
    assert 200 not in priya["retrieved_chunk_ids"]

    admin = post_estimate(estimate_client, auth_headers("admin")).json()
    assert 200 in admin["retrieved_chunk_ids"]


def test_estimated_cost_matches_calculate_cost(estimate_client, auth_headers) -> None:
    body = post_estimate(estimate_client, auth_headers("priya"), model="mock-large").json()
    assert body["priced_as"] == "mock-large"
    assert body["estimated_cost"] == calculate_cost(
        body["priced_as"], body["input_tokens"], body["output_tokens"]
    )

    small = post_estimate(estimate_client, auth_headers("priya"), model="mock-small").json()
    assert small["priced_as"] == "mock-small"
    assert small["estimated_cost"] < body["estimated_cost"]


def test_weak_evidence_returns_zero_cost(estimate_client, auth_headers) -> None:
    body = post_estimate(estimate_client, auth_headers("priya"), question=WEAK_QUESTION).json()
    assert body["will_call_llm"] is False
    assert body["input_tokens"] == 0
    assert body["output_tokens"] == 0
    assert body["estimated_cost"] == 0.0


def test_max_output_tokens_default_and_override(estimate_client, auth_headers) -> None:
    default = post_estimate(estimate_client, auth_headers("priya")).json()
    assert default["output_tokens"] == get_settings().max_output_tokens

    custom = post_estimate(estimate_client, auth_headers("priya"), max_output_tokens=300).json()
    assert custom["output_tokens"] == 300


def test_invalid_input_returns_422(estimate_client, auth_headers) -> None:
    headers = auth_headers("priya")
    assert post_estimate(estimate_client, headers, top_k=0).status_code == 422
    assert post_estimate(estimate_client, headers, top_k=21).status_code == 422
    assert post_estimate(estimate_client, headers, max_output_tokens=5000).status_code == 422
    assert post_estimate(estimate_client, headers, max_output_tokens=0).status_code == 422
    assert post_estimate(estimate_client, headers, question="").status_code == 422


def test_estimate_requires_login(estimate_client) -> None:
    response = estimate_client.post("/cost/estimate", json={"question": STRONG_QUESTION})
    assert response.status_code == 401