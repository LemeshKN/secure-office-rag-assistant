from datetime import datetime, timedelta

import pytest

from app.cost.budgets import find_budget
from app.models import LLMUsage, QueryLog, User

PATHS = [
    "summary", "by-user", "by-department", "by-project", "by-model",
    "trend/daily", "trend/monthly", "budgets", "estimated-vs-actual",
    "top-users", "top-conversations",
]


def uid(db, name):
    return db.query(User).filter_by(username=name).one().id


def add_usage(db, user, dept, model, est, actual, conv=None, days_ago=0):
    db.add(LLMUsage(
        user_id=uid(db, user), department=dept, model_name=model,
        input_tokens=100, output_tokens=50, estimated_cost=est, actual_cost=actual,
        cost_difference=round(actual - est, 6), conversation_id=conv,
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    ))


@pytest.fixture()
def usage(seeded_db):
    add_usage(seeded_db, "priya", "Engineering", "mock-large", 0.010, 0.008, conv=1)
    add_usage(seeded_db, "priya", "Engineering", "mock-small", 0.002, 0.001, conv=1)
    add_usage(seeded_db, "khushi", "HR", "mock-small", 0.003, 0.002, conv=2)
    add_usage(seeded_db, "admin", "Platform", "mock-small", 0.001, 0.001)
    add_usage(seeded_db, "priya", "Engineering", "mock-large", 0.600, 0.500, days_ago=60)  # old row
    seeded_db.commit()
    return seeded_db


def get(client, headers, path, **params):
    return client.get(f"/cost/admin/{path}", params=params, headers=headers("admin"))


@pytest.mark.parametrize("path", PATHS)
def test_endpoints_are_admin_only(cost_client, auth_headers, path):
    assert cost_client.get(f"/cost/admin/{path}").status_code == 401
    assert cost_client.get(f"/cost/admin/{path}", headers=auth_headers("priya")).status_code == 403
    assert cost_client.get(f"/cost/admin/{path}", headers=auth_headers("admin")).status_code == 200


def test_summary_this_month_and_all_time(cost_client, auth_headers, usage):
    month = get(cost_client, auth_headers, "summary", this_month=True).json()
    assert month["requests"] == 4
    assert month["input_tokens"] == 400
    assert month["estimated_cost"] == pytest.approx(0.016)
    assert month["actual_cost"] == pytest.approx(0.012)

    assert get(cost_client, auth_headers, "summary").json()["actual_cost"] == pytest.approx(0.512)
    assert get(cost_client, auth_headers, "summary", start="2999-01-01").json()["requests"] == 0


def test_by_department_and_model(cost_client, auth_headers, usage):
    dept = get(cost_client, auth_headers, "by-department", this_month=True).json()
    assert [(d["department"], d["cost"]) for d in dept] == [
        ("Engineering", pytest.approx(0.009)), ("HR", pytest.approx(0.002)), ("Platform", pytest.approx(0.001)),
    ]
    model = {m["model"]: m["cost"] for m in get(cost_client, auth_headers, "by-model", this_month=True).json()}
    assert model == {"mock-large": pytest.approx(0.008), "mock-small": pytest.approx(0.004)}


def test_by_user_and_top_users(cost_client, seeded_db, auth_headers, usage):
    find_budget(seeded_db, "user", str(uid(seeded_db, "priya"))).amount_used = 0.015
    seeded_db.commit()
    top = get(cost_client, auth_headers, "top-users", this_month=True).json()
    assert top[0]["username"] == "priya"
    assert top[0]["cost"] == pytest.approx(0.009)
    assert top[0]["user_budget_used_percent"] == 50.0  # 0.015 of 0.03


def test_estimated_vs_actual(cost_client, auth_headers, usage):
    data = get(cost_client, auth_headers, "estimated-vs-actual", this_month=True).json()
    assert data["difference"] == pytest.approx(-0.004)
    assert data["difference_percent"] == -25.0


def test_top_conversations_skip_rows_without_conversation(cost_client, auth_headers, usage):
    rows = get(cost_client, auth_headers, "top-conversations", this_month=True).json()
    assert [(r["conversation_id"], r["requests"]) for r in rows] == [(1, 2), (2, 1)]
    assert rows[0]["cost"] == pytest.approx(0.009)


def test_trends_add_up(cost_client, auth_headers, usage):
    daily = get(cost_client, auth_headers, "trend/daily", this_month=True).json()
    monthly = get(cost_client, auth_headers, "trend/monthly", this_month=True).json()
    assert sum(d["cost"] for d in daily) == pytest.approx(0.012)
    assert sum(m["cost"] for m in monthly) == pytest.approx(0.012)


def test_budget_utilization(cost_client, seeded_db, auth_headers):
    find_budget(seeded_db, "user", str(uid(seeded_db, "priya"))).amount_used = 0.015
    seeded_db.commit()
    rows = get(cost_client, auth_headers, "budgets").json()
    priya = next(r for r in rows if r["scope"] == "user" and r["name"] == "priya")
    assert priya["utilization_percent"] == 50.0
    assert priya["remaining_amount"] == pytest.approx(0.015)


def test_logs_include_usage_fields(cost_client, seeded_db, auth_headers):
    priya = uid(seeded_db, "priya")
    with_usage = QueryLog(user_id=priya, question="q1", answer="a", model_name="mock-large")
    refusal = QueryLog(user_id=priya, question="q2", answer="a", model_name="mock-large")
    seeded_db.add_all([with_usage, refusal])
    seeded_db.flush()
    seeded_db.add(LLMUsage(user_id=priya, department="Engineering", model_name="mock-large",
                           query_log_id=with_usage.id, input_tokens=120, output_tokens=30,
                           estimated_cost=0.01, actual_cost=0.004, cost_difference=-0.006))
    seeded_db.commit()

    logs = {row["question"]: row for row in cost_client.get("/logs", headers=auth_headers("admin")).json()}
    assert logs["q1"]["input_tokens"] == 120
    assert logs["q1"]["actual_cost"] == 0.004
    assert logs["q1"]["cost_difference"] == -0.006
    assert logs["q1"]["answer"] == "a"  # old fields are kept
    assert logs["q2"]["input_tokens"] is None
    assert logs["q2"]["actual_cost"] is None