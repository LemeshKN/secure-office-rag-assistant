import pytest

from app.cost.budgets import find_budget
from app.cost.policy import evaluate_policy
from app.models import Project, User


def get_user(db, name: str) -> User:
    return db.query(User).filter(User.username == name).first()


def get_project(db, name: str) -> Project:
    return db.query(Project).filter(Project.name == name).first()


def set_used(db, scope: str, key: str, used: float) -> None:
    find_budget(db, scope, key).amount_used = used
    db.commit()


def priya_with_used(db, used: float = 0.005) -> User:
    user = get_user(db, "priya")
    set_used(db, "user", str(user.id), used)
    return user


# ---------- evaluate_policy unit tests ----------

def test_priya_first_try_warns(seeded_db):
    user = priya_with_used(seeded_db)
    result = evaluate_policy(seeded_db, user, 0.0165, True, None)
    assert result["decision"] == "warn"
    assert result["limiting_scope"] == "user"
    assert result["budget_share"] == pytest.approx(0.66)
    assert result["lowest_remaining"] == pytest.approx(0.025)


def test_priya_after_recommendation_allows(seeded_db):
    user = priya_with_used(seeded_db)
    result = evaluate_policy(seeded_db, user, 0.0081, True, None)
    assert result["decision"] == "allow"
    assert result["budget_share"] == pytest.approx(0.324)


def test_estimate_above_remaining_blocks(seeded_db):
    user = priya_with_used(seeded_db)
    result = evaluate_policy(seeded_db, user, 0.03, True, None)
    assert result["decision"] == "block"
    assert result["limiting_scope"] == "user"
    assert result["budget_share"] > 1


def test_estimate_equal_to_remaining_warns_not_blocks(seeded_db):
    user = priya_with_used(seeded_db)
    remaining = find_budget(seeded_db, "user", str(user.id)).remaining_amount
    result = evaluate_policy(seeded_db, user, remaining, True, None)
    assert result["decision"] == "warn"
    assert result["budget_share"] == pytest.approx(1.0)


def test_estimate_at_exactly_half_warns(seeded_db):
    user = priya_with_used(seeded_db)
    remaining = find_budget(seeded_db, "user", str(user.id)).remaining_amount
    result = evaluate_policy(seeded_db, user, remaining / 2, True, None)
    assert result["decision"] == "warn"
    assert result["budget_share"] == pytest.approx(0.5)


def test_lowest_department_budget_wins(seeded_db):
    user = priya_with_used(seeded_db)
    set_used(seeded_db, "department", "Engineering", 0.295)  # remaining 0.005
    result = evaluate_policy(seeded_db, user, 0.001, True, None)
    assert result["limiting_scope"] == "department"
    assert result["lowest_remaining"] == pytest.approx(0.005)
    assert result["decision"] == "allow"


def test_lowest_project_budget_wins(seeded_db):
    user = priya_with_used(seeded_db)
    apollo = get_project(seeded_db, "Apollo")
    set_used(seeded_db, "project", str(apollo.id), 0.149)  # remaining 0.001
    result = evaluate_policy(seeded_db, user, 0.002, True, apollo.id)
    assert result["limiting_scope"] == "project"
    assert result["decision"] == "block"


def test_tie_picks_user_first(seeded_db):
    user = get_user(seeded_db, "priya")  # user budget 0.03, nothing used
    find_budget(seeded_db, "department", "Engineering").budget_amount = 0.03
    seeded_db.commit()
    result = evaluate_policy(seeded_db, user, 0.001, True, None)
    assert result["limiting_scope"] == "user"


def test_zero_remaining_blocks_without_division_error(seeded_db):
    user = priya_with_used(seeded_db, used=0.03)
    result = evaluate_policy(seeded_db, user, 0.001, True, None)
    assert result["decision"] == "block"
    assert result["lowest_remaining"] == 0
    assert result["budget_share"] is None


def test_no_llm_call_allows_even_with_zero_remaining(seeded_db):
    user = priya_with_used(seeded_db, used=0.03)
    result = evaluate_policy(seeded_db, user, 0.0, False, None)
    assert result["decision"] == "allow"
    assert result["reason"] == "No LLM call needed"


def test_project_id_none_skips_project_budget(seeded_db):
    user = get_user(seeded_db, "priya")
    apollo = get_project(seeded_db, "Apollo")
    without = evaluate_policy(seeded_db, user, 0.001, True, None)
    with_project = evaluate_policy(seeded_db, user, 0.001, True, apollo.id)
    assert [b["scope"] for b in without["budgets"]] == ["user", "department"]
    assert [b["scope"] for b in with_project["budgets"]] == ["user", "department", "project"]


def test_no_budget_configured_allows(seeded_db):
    seeded_db.add(User(username="newbie", password_hash="x", role="developer"))
    seeded_db.commit()
    user = get_user(seeded_db, "newbie")
    result = evaluate_policy(seeded_db, user, 0.01, True, None)
    assert result["decision"] == "allow"
    assert result["reason"] == "No budget configured"
    assert result["budgets"] == []


# ---------- POST /cost/estimate route tests ----------

@pytest.fixture()
def fake_estimate(monkeypatch):
    """Replace estimate_request so the route tests need no documents. Records each call."""
    calls = []

    def fake(db, user, question, top_k=5, model="auto", max_output_tokens=None):
        calls.append(question)
        return {
            "model": model,
            "priced_as": "mock-large",
            "input_tokens": 3400,
            "output_tokens": 800,
            "estimated_cost": 0.0165,
            "will_call_llm": True,
            "evidence_score": 0.9,
            "top_k": top_k,
            "retrieved_chunk_ids": [],
        }

    monkeypatch.setattr("app.api.cost_routes.estimate_request", fake)
    return calls


BODY = {"question": "Summarize the private project notes.", "model": "mock-large"}


def test_nearly_used_budget_blocks_and_keeps_estimate(cost_client, seeded_db, auth_headers, fake_estimate):
    priya_with_used(seeded_db, used=0.02)  # remaining 0.01, estimate 0.0165
    response = cost_client.post("/cost/estimate", json=BODY, headers=auth_headers("priya"))
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "block"
    assert data["limiting_scope"] == "user"
    assert data["will_call_llm"] is True
    assert data["estimated_cost"] == 0.0165


def test_member_gets_project_budget_in_list(cost_client, seeded_db, auth_headers, fake_estimate):
    apollo = get_project(seeded_db, "Apollo")
    body = {**BODY, "project_id": apollo.id}
    response = cost_client.post("/cost/estimate", json=body, headers=auth_headers("priya"))
    assert response.status_code == 200
    assert [b["scope"] for b in response.json()["budgets"]] == ["user", "department", "project"]


def test_no_project_id_skips_project_budget(cost_client, auth_headers, fake_estimate):
    response = cost_client.post("/cost/estimate", json=BODY, headers=auth_headers("priya"))
    assert [b["scope"] for b in response.json()["budgets"]] == ["user", "department"]


def test_non_member_gets_403_before_retrieval(cost_client, seeded_db, auth_headers, fake_estimate):
    apollo = get_project(seeded_db, "Apollo")
    body = {**BODY, "project_id": apollo.id}
    response = cost_client.post("/cost/estimate", json=body, headers=auth_headers("khushi"))
    assert response.status_code == 403
    assert fake_estimate == []  # estimate_request was never reached


def test_admin_is_not_exempt_from_project_membership(cost_client, seeded_db, auth_headers, fake_estimate):
    apollo = get_project(seeded_db, "Apollo")
    body = {**BODY, "project_id": apollo.id}
    response = cost_client.post("/cost/estimate", json=body, headers=auth_headers("admin"))
    assert response.status_code == 403


def test_missing_project_gets_404(cost_client, auth_headers, fake_estimate):
    body = {**BODY, "project_id": 99999}
    response = cost_client.post("/cost/estimate", json=body, headers=auth_headers("priya"))
    assert response.status_code == 404
    assert fake_estimate == []


def test_fake_body_fields_do_not_change_result(cost_client, seeded_db, auth_headers, fake_estimate):
    priya_with_used(seeded_db, used=0.02)
    body = {**BODY, "decision": "allow", "estimated_cost": 0.0, "approved": True, "remaining_amount": 99}
    response = cost_client.post("/cost/estimate", json=body, headers=auth_headers("priya"))
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "block"
    assert data["estimated_cost"] == 0.0165