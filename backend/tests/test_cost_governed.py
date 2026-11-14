import json
from datetime import timedelta

import pytest

from app.auth.rbac import access_metadata
from app.config import Settings
from app.cost.budget_period import current_month_start, is_stale
from app.cost.budgets import find_budget
from app.ingestion.embeddings import HashEmbeddingProvider
from app.models import Budget, Chunk, Document, LLMUsage, QueryLog, User
from app.rag.graph import RAGWorkflow
from app.rag.llm_client import MockLLMClient
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.reranker import Reranker
from app.retrieval.vector_store import InMemoryVectorStore, VectorRecord

ROLES = ["developer", "manager", "hr", "agent_developer"]
QUESTION = "paid leave days"


@pytest.fixture()
def llm_calls(cost_client, session_factory, monkeypatch):
    """Real mock LLM with a call counter, over one small in-memory document."""
    db = session_factory()
    amit = db.query(User).filter_by(username="amit").one()
    db.add(Document(id=10, filename="handbook.txt", title="Handbook", owner_user_id=amit.id,
                    allowed_roles=json.dumps(ROLES), allowed_user_ids="[]",
                    file_type="txt", upload_path="/tmp/handbook.txt"))
    chunk = Chunk(id=100, document_id=10, chunk_index=0,
                  text="Employees receive 24 paid leave days every year.", chroma_id="doc-10-chunk-0")
    db.add(chunk)
    db.commit()

    embeddings = HashEmbeddingProvider()
    store = InMemoryVectorStore("test_governed")
    store.reset()
    metadata = access_metadata(10, amit.id, ROLES, [])
    metadata.update({"chunk_id": 100, "filename": "10.txt", "chunk_index": 0})
    store.upsert([VectorRecord(chroma_id=chunk.chroma_id, text=chunk.text,
                               embedding=embeddings.embed_query(chunk.text), metadata=metadata)])
    db.close()

    calls = []

    class CountingLLM(MockLLMClient):
        def generate(self, question, chunks):
            calls.append(question)
            return super().generate(question, chunks)

    def fake_build_workflow(db, user, model="auto"):
        settings = Settings()
        name = model if model in ("mock-small", "mock-large") else "mock-grounded-llm"
        return RAGWorkflow(db=db, user=user,
                           retriever=HybridRetriever(embeddings, store, KeywordStore()),
                           reranker=Reranker(settings), llm_client=CountingLLM(name), settings=settings)

    monkeypatch.setattr("app.cost.estimate.build_workflow", fake_build_workflow)
    monkeypatch.setattr("app.cost.governed.build_workflow", fake_build_workflow)
    return calls


def rows(db, model):
    db.expire_all()
    return db.query(model).all()


def set_used(db, name, used, period_start=None):
    user = db.query(User).filter_by(username=name).one()
    budget = find_budget(db, "user", str(user.id))
    budget.amount_used = used
    if period_start is not None:
        budget.period_start = period_start
    db.commit()


def user_budget(db, name):
    db.expire_all()
    user = db.query(User).filter_by(username=name).one()
    return find_budget(db, "user", str(user.id))


def chat(client, headers, question=QUESTION, **extra):
    body = {"question": question, "model": "mock-large", **extra}
    return client.post("/chat", json=body, headers=headers("priya"))


def test_estimated_and_actual_saved_once(cost_client, seeded_db, auth_headers, llm_calls):
    response = chat(cost_client, auth_headers)
    assert response.status_code == 200
    assert "answer" in response.json()
    assert len(llm_calls) == 1

    usage = rows(seeded_db, LLMUsage)
    assert len(usage) == 1
    row = usage[0]
    assert row.model_name == "mock-large"
    assert row.estimated_cost > 0
    assert 0 < row.actual_cost < row.estimated_cost  # estimate assumes the full output limit
    assert row.cost_difference == pytest.approx(row.actual_cost - row.estimated_cost)
    assert row.input_tokens > 0 and row.output_tokens > 0

    logs = rows(seeded_db, QueryLog)
    assert len(logs) == 1
    assert row.query_log_id == logs[0].id
    assert user_budget(seeded_db, "priya").amount_used == pytest.approx(row.actual_cost)


def test_block_makes_no_llm_call_and_no_usage_row(cost_client, seeded_db, auth_headers, llm_calls):
    set_used(seeded_db, "priya", 0.025)  # remaining 0.005, estimate is about 0.0088
    data = chat(cost_client, auth_headers, approved=True).json()  # approval is ignored for block
    assert data["decision"] == "block"
    assert data["stopped"] is True
    assert llm_calls == []
    assert rows(seeded_db, LLMUsage) == []
    assert rows(seeded_db, QueryLog) == []


def test_warn_needs_approval_then_runs_once(cost_client, seeded_db, auth_headers, llm_calls):
    set_used(seeded_db, "priya", 0.015)  # estimate is about 58% of the remaining 0.015
    first = chat(cost_client, auth_headers).json()
    assert first["decision"] == "warn"
    assert first["stopped"] is True
    assert llm_calls == [] and rows(seeded_db, LLMUsage) == []

    second = chat(cost_client, auth_headers, approved=True).json()
    assert "answer" in second
    assert len(llm_calls) == 1
    assert len(rows(seeded_db, LLMUsage)) == 1


def test_recommend_runs_at_once(cost_client, auth_headers, llm_calls):
    data = chat(cost_client, auth_headers).json()  # "leave" on mock-large gives a recommendation
    assert "answer" in data
    assert data["decision"] == "recommend"
    assert data["recommendations"]


def test_weak_evidence_makes_no_usage_row(cost_client, seeded_db, auth_headers, llm_calls):
    data = chat(cost_client, auth_headers, question="zzzz qqqq").json()
    assert "answer" in data
    assert llm_calls == []
    assert rows(seeded_db, LLMUsage) == []
    assert len(rows(seeded_db, QueryLog)) == 1


def test_send_message_writes_log_and_usage(cost_client, seeded_db, auth_headers, llm_calls):
    headers = auth_headers("priya")
    conversation_id = cost_client.post("/conversations", headers=headers).json()["id"]
    response = cost_client.post(f"/conversations/{conversation_id}/messages",
                                json={"question": QUESTION, "model": "mock-large"}, headers=headers)
    assert response.status_code == 200
    usage = rows(seeded_db, LLMUsage)
    assert len(usage) == 1
    assert usage[0].conversation_id == conversation_id
    assert len(rows(seeded_db, QueryLog)) == 1


def test_stream_writes_usage_and_blocks_without_saving(cost_client, seeded_db, auth_headers, llm_calls):
    headers = auth_headers("priya")
    conversation_id = cost_client.post("/conversations", headers=headers).json()["id"]
    url = f"/conversations/{conversation_id}/messages/stream"

    ok = cost_client.post(url, json={"question": QUESTION, "model": "mock-large"}, headers=headers)
    assert "data:" in ok.text
    assert len(rows(seeded_db, LLMUsage)) == 1

    set_used(seeded_db, "priya", 0.029)
    stopped = cost_client.post(url, json={"question": QUESTION, "model": "mock-large"}, headers=headers)
    assert stopped.json()["decision"] == "block"
    assert len(rows(seeded_db, LLMUsage)) == 1
    messages = cost_client.get(f"/conversations/{conversation_id}/messages", headers=headers).json()
    assert len(messages) == 2  # only the first, allowed request was saved


def test_evaluate_writes_usage(cost_client, seeded_db, auth_headers, llm_calls):
    response = cost_client.post("/evaluate/query", json={"question": QUESTION, "model": "mock-large"},
                                headers=auth_headers("priya"))
    assert response.status_code == 200
    assert len(rows(seeded_db, LLMUsage)) == 1
    assert len(rows(seeded_db, QueryLog)) == 1


def test_non_member_gets_403_before_any_work(cost_client, seeded_db, auth_headers, llm_calls):
    project = seeded_db.query(Budget).filter_by(scope_type="project").first()
    response = cost_client.post("/chat", json={"question": QUESTION, "project_id": int(project.scope_key)},
                                headers=auth_headers("khushi"))
    assert response.status_code == 403
    assert llm_calls == []


def test_stale_budget_resets_and_counts_as_zero(cost_client, seeded_db, auth_headers, llm_calls):
    old = current_month_start() - timedelta(days=40)
    set_used(seeded_db, "priya", 0.029, period_start=old)  # would block if it still counted
    data = chat(cost_client, auth_headers).json()
    assert "answer" in data

    budget = user_budget(seeded_db, "priya")
    row = rows(seeded_db, LLMUsage)[0]
    assert budget.period_start == current_month_start()
    assert budget.amount_used == pytest.approx(row.actual_cost)  # 0.029 was cleared, not carried
    assert budget.budget_amount == 0.03


def test_month_start_helpers(seeded_db):
    assert current_month_start().day == 1
    budget = user_budget(seeded_db, "priya")
    assert is_stale(budget) is False
    budget.period_start = current_month_start() - timedelta(days=1)
    assert is_stale(budget) is True