from types import SimpleNamespace

import pytest

from app.config import Settings, get_settings
from app.cost.budgets import find_budget
from app.cost.governed import run_governed
from app.cost.tokens import count_tokens
from app.models import LLMUsage, User
from app.rag.llm_client import GeminiClient, LLMError
from app.rag.prompt_builder import build_prompt_parts

MODEL = "gemini-3.5-flash-lite"


class FakeAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


class FakeModels:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeClient:
    def __init__(self, outcome):
        self.models = FakeModels(outcome)


def reply(text="Answer [1:2]", prompt=1000, candidates=100, thoughts=50):
    usage = SimpleNamespace(
        prompt_token_count=prompt,
        candidates_token_count=candidates,
        thoughts_token_count=thoughts,
    )
    return SimpleNamespace(text=text, usage_metadata=usage)


def make(outcome):
    fake = FakeClient(outcome)
    return GeminiClient(Settings(), MODEL, client=fake), fake


def test_uses_reported_tokens_and_counts_thinking_as_output():
    client, _ = make(reply(prompt=1000, candidates=100, thoughts=50))
    result = client.generate("q", [])
    assert result.input_tokens == 1000
    assert result.output_tokens == 150
    assert result.model_name == f"gemini/{MODEL}"
    assert result.actual_cost == round(1000 / 1e6 * 0.30 + 150 / 1e6 * 2.50, 6)


def test_output_cap_is_sent_to_gemini():
    client, fake = make(reply())
    client.generate("q", [], 300)
    client.generate("q", [])
    assert fake.models.calls[0]["config"].max_output_tokens == 300
    assert fake.models.calls[1]["config"].max_output_tokens == get_settings().max_output_tokens


def test_missing_usage_falls_back_to_local_counter():
    client, _ = make(SimpleNamespace(text="hello [1:2]", usage_metadata=None))
    result = client.generate("q", [])
    system_text, user_text = build_prompt_parts("q", [])
    assert result.input_tokens == count_tokens(system_text + "\n\n" + user_text)
    assert result.output_tokens == count_tokens("hello [1:2]")


def test_rate_limit_gives_429_message():
    client, _ = make(FakeAPIError(429))
    with pytest.raises(LLMError) as info:
        client.generate("q", [])
    assert info.value.status_code == 429
    assert "rate limit" in str(info.value)


def test_other_failure_gives_clear_message_without_raw_error():
    client, _ = make(FakeAPIError(500))
    with pytest.raises(LLMError) as info:
        client.generate("q", [])
    assert info.value.status_code == 500
    assert "error 500" not in str(info.value)


def test_empty_reply_is_a_failure():
    client, _ = make(reply(text=""))
    with pytest.raises(LLMError):
        client.generate("q", [])


def test_failed_call_saves_no_usage_and_charges_no_budget(seeded_db, monkeypatch):
    class FailingWorkflow:
        def run(self, question, top_k=5, max_output_tokens=None):
            raise LLMError("Gemini rate limit reached.", 429)

    def fake_estimate(db, user, question, top_k=5, model="auto", max_output_tokens=None):
        return {
            "model": model,
            "priced_as": "mock-small",
            "input_tokens": 100,
            "output_tokens": 800,
            "estimated_cost": 0.001,
            "will_call_llm": True,
            "evidence_score": 0.9,
            "top_k": top_k,
            "retrieved_chunk_ids": [],
        }

    monkeypatch.setattr("app.cost.governed.build_workflow", lambda db, user, model="auto": FailingWorkflow())
    monkeypatch.setattr("app.cost.governed.estimate_request", fake_estimate)

    priya = seeded_db.query(User).filter_by(username="priya").one()
    budget = find_budget(seeded_db, "user", str(priya.id))
    before = budget.amount_used

    with pytest.raises(LLMError):
        run_governed(seeded_db, priya, "q")
    seeded_db.rollback()

    assert seeded_db.query(LLMUsage).count() == 0
    seeded_db.refresh(budget)
    assert budget.amount_used == before