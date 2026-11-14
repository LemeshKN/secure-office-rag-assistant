from datetime import datetime, timedelta

import pytest

from app.cost.recommendations import apply_recommend_decision, build_recommendations
from app.models import QueryLog, User


def est(**kw):
    base = {"will_call_llm": True, "priced_as": "mock-large",
            "input_tokens": 1000, "top_k": 3, "output_tokens": 300}
    return {**base, **kw}


def pol(**kw):
    base = {"decision": "allow", "reason": "", "limiting_scope": None, "budgets": []}
    return {**base, **kw}


@pytest.fixture
def priya(seeded_db):
    return seeded_db.query(User).filter_by(username="priya").one()


def rules(recs):
    return {r["rule"] for r in recs}


def test_priya_example_first_try(seeded_db, priya):
    recs = build_recommendations(seeded_db, priya, "Summarize the private project notes.",
                                 est(input_tokens=3400, top_k=5, output_tokens=800), pol())
    assert rules(recs) == {"large_context", "long_output"}
    by = {r["rule"]: r for r in recs}
    assert by["large_context"]["suggested"] == {"top_k": 3}
    assert by["long_output"]["suggested"] == {"max_output_tokens": 300}


def test_priya_example_after_applying(seeded_db, priya):
    recs = build_recommendations(seeded_db, priya, "Summarize the private project notes.",
                                 est(input_tokens=2040, top_k=3, output_tokens=300), pol())
    assert recs == []
    assert apply_recommend_decision(pol(), recs)["decision"] == "allow"


def test_simple_question_mock_large(seeded_db, priya):
    recs = build_recommendations(seeded_db, priya, "What is the leave policy?", est(), pol())
    assert rules(recs) == {"simple_question"}


def test_simple_question_not_on_mock_small(seeded_db, priya):
    recs = build_recommendations(seeded_db, priya, "What is the leave policy?",
                                 est(priced_as="mock-small"), pol())
    assert recs == []


def test_whole_word_matching(seeded_db, priya):
    big = est(output_tokens=800)
    assert "long_output" not in rules(build_recommendations(seeded_db, priya, "reporting issues", big, pol()))
    assert "long_output" in rules(build_recommendations(seeded_db, priya, "Report on sales", big, pol()))


def test_large_context_boundary(seeded_db, priya):
    q = "hello there"
    assert build_recommendations(seeded_db, priya, q, est(input_tokens=3000, top_k=5), pol()) == []
    assert rules(build_recommendations(seeded_db, priya, q, est(input_tokens=3001, top_k=5), pol())) == {"large_context"}


def budget_policy(remaining):
    return pol(limiting_scope="user",
               budgets=[{"scope": "user", "budget_amount": 1.0, "remaining_amount": remaining}])


def test_budget_nearly_used_boundary(seeded_db, priya):
    q = "hello there"
    assert build_recommendations(seeded_db, priya, q, est(), budget_policy(0.2)) == []
    recs = build_recommendations(seeded_db, priya, q, est(), budget_policy(0.19))
    assert rules(recs) == {"budget_nearly_used"}


def test_budget_rule_suggests_all_uncheap_settings(seeded_db, priya):
    recs = build_recommendations(seeded_db, priya, "hello there",
                                 est(top_k=5, output_tokens=800), budget_policy(0.1))
    assert recs[0]["suggested"] == {"model": "mock-small", "top_k": 3, "max_output_tokens": 300}


def add_log(db, user_id, question, days_ago):
    db.add(QueryLog(user_id=user_id, question=question, answer="x", model_name="mock-small",
                    created_at=datetime.utcnow() - timedelta(days=days_ago)))
    db.commit()


def test_repeated_question_fires(seeded_db, priya):
    add_log(seeded_db, priya.id, "  Hello   THERE ", 1)
    recs = build_recommendations(seeded_db, priya, "hello there", est(), pol())
    assert rules(recs) == {"repeated_question"}
    assert recs[0]["suggested"] == {}


def test_repeated_question_ignores_other_user(seeded_db, priya):
    amit = seeded_db.query(User).filter_by(username="amit").one()
    add_log(seeded_db, amit.id, "hello there", 1)
    assert build_recommendations(seeded_db, priya, "hello there", est(), pol()) == []


def test_repeated_question_ignores_old_row(seeded_db, priya):
    add_log(seeded_db, priya.id, "hello there", 8)
    assert build_recommendations(seeded_db, priya, "hello there", est(), pol()) == []


def test_no_llm_call_returns_empty(seeded_db, priya):
    recs = build_recommendations(seeded_db, priya, "What is the leave policy?",
                                 est(will_call_llm=False), pol())
    assert recs == []


def test_apply_recommend_decision():
    one = [{"rule": "x", "message": "m", "suggested": {}}]
    out = apply_recommend_decision(pol(), one)
    assert out["decision"] == "recommend"
    assert out["reason"] == "Within budget, but cheaper settings are available."
    assert apply_recommend_decision(pol(decision="warn"), one)["decision"] == "warn"
    assert apply_recommend_decision(pol(decision="block"), one)["decision"] == "block"
    assert apply_recommend_decision(pol(), [])["decision"] == "allow"