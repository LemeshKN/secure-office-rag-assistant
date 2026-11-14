import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings  # ADJUST if your settings object has another name
from app.models import QueryLog  # ADJUST if the class has another name

# ADJUST these three if your query log columns are named differently
LOG_USER_COL = "user_id"
LOG_QUESTION_COL = "question"
LOG_CREATED_COL = "created_at"

SIMPLE_QUESTION_WORDS = (
    "leave", "leaves", "policy", "policies",
    "holiday", "holidays", "benefit", "benefits",
    "salary", "salaries",
)
LONG_OUTPUT_WORDS = ("summarize", "summarise", "in detail", "report", "reports")

CHEAP_MODEL = "mock-small"


def _has_word(text: str, words: tuple[str, ...]) -> bool:
    for word in words:
        if re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE):
            return True
    return False


def _normalize(question: str) -> str:
    return " ".join(question.strip().lower().split())


def _was_asked_recently(db: Session, user, question: str) -> bool:
    settings = get_settings()
    cutoff = datetime.utcnow() - timedelta(days=settings.repeat_window_days)
    user_col = getattr(QueryLog, LOG_USER_COL)
    question_col = getattr(QueryLog, LOG_QUESTION_COL)
    created_col = getattr(QueryLog, LOG_CREATED_COL)
    rows = (
        db.query(question_col)
        .filter(user_col == user.id, created_col >= cutoff)
        .all()
    )
    target = _normalize(question)
    return any(_normalize(r[0] or "") == target for r in rows)


def _limiting_budget(policy: dict) -> dict | None:
    scope = policy.get("limiting_scope")
    if scope is None:
        return None
    for budget in policy.get("budgets", []):
        if budget["scope"] == scope:
            return budget
    return None


def build_recommendations(db: Session, user, question: str, estimate: dict, policy: dict) -> list[dict]:
    settings = get_settings()
    if not estimate.get("will_call_llm"):
        return []

    recs: list[dict] = []

    if _has_word(question, SIMPLE_QUESTION_WORDS) and estimate["priced_as"] != CHEAP_MODEL:
        recs.append({
            "rule": "simple_question",
            "message": "This looks like a simple policy question. mock-small is enough.",
            "suggested": {"model": CHEAP_MODEL},
        })

    if (
        estimate["input_tokens"] > settings.large_context_tokens
        and estimate["top_k"] > settings.recommended_top_k
    ):
        recs.append({
            "rule": "large_context",
            "message": f"The prompt is large ({estimate['input_tokens']} tokens). Use {settings.recommended_top_k} chunks.",
            "suggested": {"top_k": settings.recommended_top_k},
        })

    if (
        _has_word(question, LONG_OUTPUT_WORDS)
        and estimate["output_tokens"] > settings.short_output_tokens
    ):
        recs.append({
            "rule": "long_output",
            "message": f"Limit the answer to {settings.short_output_tokens} output tokens.",
            "suggested": {"max_output_tokens": settings.short_output_tokens},
        })

    if _was_asked_recently(db, user, question):
        recs.append({
            "rule": "repeated_question",
            "message": f"You asked this in the last {settings.repeat_window_days} days. Caching is a future feature.",
            "suggested": {},
        })

    budget = _limiting_budget(policy)
    if budget and budget["budget_amount"] > 0:
        ratio = budget["remaining_amount"] / budget["budget_amount"]
        if ratio < settings.near_budget_ratio:
            suggested: dict = {}
            if estimate["priced_as"] != CHEAP_MODEL:
                suggested["model"] = CHEAP_MODEL
            if estimate["top_k"] > settings.recommended_top_k:
                suggested["top_k"] = settings.recommended_top_k
            if estimate["output_tokens"] > settings.short_output_tokens:
                suggested["max_output_tokens"] = settings.short_output_tokens
            recs.append({
                "rule": "budget_nearly_used",
                "message": f"Your {budget['scope']} budget is almost used. Use cheaper settings.",
                "suggested": suggested,
            })

    return recs


def apply_recommend_decision(policy: dict, recommendations: list[dict]) -> dict:
    if policy["decision"] == "allow" and recommendations:
        return {
            **policy,
            "decision": "recommend",
            "reason": "Within budget, but cheaper settings are available.",
        }
    return policy