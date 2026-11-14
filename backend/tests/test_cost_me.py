from datetime import timedelta

import pytest

from app.cost.budget_period import current_month_start
from app.cost.budgets import find_budget
from app.models import LLMUsage, User


def set_budget(db, period_start, used):
    user = db.query(User).filter_by(username="priya").one()
    budget = find_budget(db, "user", str(user.id))
    budget.period_start = period_start
    budget.amount_used = used
    db.commit()
    return user


def me(client, headers):
    return client.get("/cost/me", headers=headers("priya")).json()["user_budget"]


def test_current_month_budget_shows_real_usage(cost_client, seeded_db, auth_headers):
    set_budget(seeded_db, current_month_start(), 0.02)
    data = me(cost_client, auth_headers)
    assert data["amount_used"] == pytest.approx(0.02)
    assert data["remaining_amount"] == pytest.approx(0.01)
    assert data["period_start"] == current_month_start().date().isoformat()


def test_past_month_budget_shows_zero_used_and_keeps_history(cost_client, seeded_db, auth_headers):
    user = set_budget(seeded_db, current_month_start() - timedelta(days=40), 0.028)
    seeded_db.add(LLMUsage(user_id=user.id, department="Engineering", model_name="mock-large",
                           estimated_cost=0.03, actual_cost=0.028, cost_difference=-0.002))
    seeded_db.commit()

    data = me(cost_client, auth_headers)
    assert data["amount_used"] == 0.0
    assert data["remaining_amount"] == pytest.approx(0.03)
    assert data["budget_amount"] == 0.03
    assert data["period_start"] == current_month_start().date().isoformat()

    seeded_db.expire_all()
    assert seeded_db.query(LLMUsage).count() == 1  # history is kept
    stored = find_budget(seeded_db, "user", str(user.id))
    assert stored.amount_used == pytest.approx(0.028)  # GET does not write a reset


def test_month_boundary(cost_client, seeded_db, auth_headers):
    set_budget(seeded_db, current_month_start(), 0.02)  # exactly the month start: current
    assert me(cost_client, auth_headers)["amount_used"] == pytest.approx(0.02)

    set_budget(seeded_db, current_month_start() - timedelta(seconds=1), 0.02)  # last second of last month
    assert me(cost_client, auth_headers)["amount_used"] == 0.0