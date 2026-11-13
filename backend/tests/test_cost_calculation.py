import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.cost.pricing import DEFAULT_PRICE, calculate_cost, get_price
from app.cost.tokens import count_tokens
from app.database import Base
from app.models import Budget, LLMUsage, User


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_small_model_cost() -> None:
    assert calculate_cost("mock-small", 2000, 500) == pytest.approx(0.0006)


def test_large_model_costs_more_than_small() -> None:
    large = calculate_cost("mock-large", 6000, 800)
    small = calculate_cost("mock-small", 6000, 800)
    assert large == pytest.approx(0.023)
    assert small == pytest.approx(0.00138)
    assert large > small


def test_zero_tokens_cost_nothing() -> None:
    assert calculate_cost("mock-large", 0, 0) == 0.0


def test_negative_tokens_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_cost("mock-small", -1, 10)


def test_provider_prefix_is_ignored() -> None:
    assert get_price("openai/gpt-4o-mini") == get_price("gpt-4o-mini")


def test_unknown_model_uses_default_price() -> None:
    assert get_price("totally-unknown") == DEFAULT_PRICE


def test_token_estimate() -> None:
    assert count_tokens("") == 0
    assert count_tokens("abcd") == 1
    assert count_tokens("abcde") == 2
    assert count_tokens("a" * 400) == 100


def test_cost_tables_store_rows() -> None:
    db = make_session()
    db.add(User(id=1, username="priya", password_hash="x", role="developer"))
    db.add(Budget(scope_type="department", scope_key="Engineering", budget_amount=5.0, amount_used=1.25))
    db.add(
        LLMUsage(
            user_id=1,
            department="Engineering",
            model_name="mock-small",
            input_tokens=2000,
            output_tokens=500,
            estimated_cost=0.0008,
            actual_cost=0.0006,
            cost_difference=-0.0002,
        )
    )
    db.commit()
    budget = db.query(Budget).one()
    assert budget.remaining_amount == pytest.approx(3.75)
    assert db.query(LLMUsage).one().cost_difference == pytest.approx(-0.0002)