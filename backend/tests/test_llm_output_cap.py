from types import SimpleNamespace

from app.config import get_settings
from app.cost.governed import run_governed
from app.models import User
from app.rag.graph import RAGWorkflow
from app.rag.llm_client import LLMClient, LLMResult
from app.schemas import ChatResponse


class RecordingLLM(LLMClient):
    model_name = "mock-small"

    def __init__(self):
        self.caps = []

    def generate(self, question, chunks, max_output_tokens=None):
        self.caps.append(max_output_tokens)
        return LLMResult("ok", self.model_name)


def test_workflow_passes_cap_to_llm():
    llm = RecordingLLM()
    workflow = RAGWorkflow(
        db=None,
        user=SimpleNamespace(id=1, role="developer"),
        retriever=None,
        reranker=None,
        llm_client=llm,
    )
    state = {"question": "q", "should_answer": True, "reranked_chunks": [], "max_output_tokens": 300}
    workflow.generate_answer(state)
    assert llm.caps == [300]


def test_run_governed_passes_default_and_custom_cap(seeded_db, monkeypatch):
    seen = []

    class FakeWorkflow:
        def run(self, question, top_k=5, max_output_tokens=None):
            seen.append(max_output_tokens)
            return ChatResponse(
                answer="ok",
                citations=[],
                evidence_score=0.0,
                groundedness_score=1.0,
                retrieved_chunks=[],
                latency_ms=1,
                model_name="mock-small",
            )

    def fake_estimate(db, user, question, top_k=5, model="auto", max_output_tokens=None):
        return {
            "model": model,
            "priced_as": "mock-small",
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "will_call_llm": False,
            "evidence_score": 0.0,
            "top_k": top_k,
            "retrieved_chunk_ids": [],
        }

    monkeypatch.setattr("app.cost.governed.build_workflow", lambda db, user, model="auto": FakeWorkflow())
    monkeypatch.setattr("app.cost.governed.estimate_request", fake_estimate)

    priya = seeded_db.query(User).filter_by(username="priya").one()
    run_governed(seeded_db, priya, "q")
    run_governed(seeded_db, priya, "q", max_output_tokens=300)

    assert seen == [get_settings().max_output_tokens, 300]