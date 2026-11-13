from sqlalchemy.orm import Session

from app.config import get_settings
from app.cost.budgets import find_budget
from app.models import Budget, User, UserProfile


def collect_budgets(db: Session, user: User, project_id: int | None) -> list[tuple[str, Budget]]:
    """Budgets that apply to this request, in the order user, department, project."""
    profile = db.get(UserProfile, user.id)
    department = profile.department if profile else "unassigned"

    lookups = [("user", str(user.id)), ("department", department)]
    if project_id is not None:
        lookups.append(("project", str(project_id)))

    found = []
    for scope, key in lookups:
        budget = find_budget(db, scope, key)
        if budget is not None:
            found.append((scope, budget))
    return found


def evaluate_policy(
    db: Session,
    user: User,
    estimated_cost: float,
    will_call_llm: bool,
    project_id: int | None = None,
) -> dict:
    """Return allow, warn or block. Reads budgets only and writes nothing."""
    settings = get_settings()
    found = collect_budgets(db, user, project_id)
    budgets = [
        {"scope": scope, "budget_amount": b.budget_amount, "remaining_amount": b.remaining_amount}
        for scope, b in found
    ]

    def result(decision, reason, scope=None, remaining=None, share=None) -> dict:
        return {
            "decision": decision,
            "reason": reason,
            "limiting_scope": scope,
            "lowest_remaining": remaining,
            "budget_share": share,
            "budgets": budgets,
        }

    if not will_call_llm:
        return result("allow", "No LLM call needed")
    if not found:
        return result("allow", "No budget configured")

    # min() keeps the first item on a tie, so the order user, department, project decides ties.
    # Rounding to 8 decimals removes float noise such as 0.03 - 0.005.
    scope, budget = min(found, key=lambda item: round(item[1].remaining_amount, 8))
    remaining = round(budget.remaining_amount, 8)
    estimate = round(estimated_cost, 8)

    if remaining <= 0 and estimate > 0:
        return result("block", f"The {scope} budget is used up.", scope, remaining)
    if estimate > remaining:
        return result(
            "block",
            f"Estimated cost ${estimate:.4f} is above the remaining {scope} budget ${remaining:.4f}.",
            scope,
            remaining,
            round(estimate / remaining, 4),
        )
    if remaining <= 0:
        return result("allow", "Estimated cost is zero.", scope, remaining)

    share = estimate / remaining
    if share >= settings.warn_threshold:
        return result(
            "warn",
            f"This request would use {share:.0%} of the remaining {scope} budget.",
            scope,
            remaining,
            round(share, 4),
        )
    return result("allow", "Within budget.", scope, remaining, round(share, 4))