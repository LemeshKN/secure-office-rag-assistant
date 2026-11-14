import pytest

from app.cost.budgets import find_budget
from app.models import User


@pytest.fixture()
def fake(monkeypatch):
    cfg = {"cost": 0.0165, "input_tokens": 3400, "calls": []}

    def _fake(db, user, question, top_k=5, model="auto", max_output_tokens=None):
        cfg["calls"].append(question)
        return {
            "model": model, "priced_as": "mock-large",
            "input_tokens": cfg["input_tokens"],
            "output_tokens": max_output_tokens or 800,
            "estimated_cost": cfg["cost"], "will_call_llm": True,
            "evidence_score": 0.9, "top_k": top_k, "retrieved_chunk_ids": [],
        }

    monkeypatch.setattr("app.api.cost_routes.estimate_request", _fake)
    return cfg


BODY = {"question": "Summarize the private project notes.", "model": "mock-large"}


def priya_used(db, used):
    user = db.query(User).filter_by(username="priya").one()
    find_budget(db, "user", str(user.id)).amount_used = used
    db.commit()


def post(client, headers, body=BODY):
    return client.post("/cost/estimate", json=body, headers=headers("priya"))


def test_allowed_but_rule_matches_gives_recommend(cost_client, auth_headers, fake):
    fake["cost"] = 0.005  # 17% of 0.03, so policy says allow
    data = post(cost_client, auth_headers).json()
    assert data["decision"] == "recommend"
    assert {r["rule"] for r in data["recommendations"]} == {"large_context", "long_output"}
    assert len(fake["calls"]) == 1


def test_warn_keeps_warn_and_has_recommendations(cost_client, auth_headers, fake):
    data = post(cost_client, auth_headers).json()  # 0.0165 of 0.03 = 55%
    assert data["decision"] == "warn"
    assert data["recommendations"]


def test_block_keeps_block_and_has_recommendations(cost_client, seeded_db, auth_headers, fake):
    priya_used(seeded_db, 0.02)
    data = post(cost_client, auth_headers).json()
    assert data["decision"] == "block"
    assert data["recommendations"]


def test_fake_body_fields_are_ignored(cost_client, seeded_db, auth_headers, fake):
    priya_used(seeded_db, 0.02)
    body = {**BODY, "decision": "allow", "recommendations": [], "estimated_cost": 0.0}
    data = post(cost_client, auth_headers, body).json()
    assert data["decision"] == "block"
    assert data["estimated_cost"] == 0.0165
    assert data["recommendations"]


def test_priya_after_recommendation_is_allow(cost_client, seeded_db, auth_headers, fake):
    priya_used(seeded_db, 0.005)
    fake.update(cost=0.0081, input_tokens=2040)
    body = {**BODY, "top_k": 3, "max_output_tokens": 300}
    data = post(cost_client, auth_headers, body).json()
    assert data["decision"] == "allow"
    assert data["recommendations"] == []