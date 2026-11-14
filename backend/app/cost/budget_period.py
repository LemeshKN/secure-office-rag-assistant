from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Budget

KOLKATA = ZoneInfo("Asia/Kolkata")


def current_month_start() -> datetime:
    """First day of the current month in Asia/Kolkata, stored as a naive datetime."""
    now = datetime.now(KOLKATA)
    return datetime(now.year, now.month, 1)


def is_stale(budget: Budget) -> bool:
    return budget.period_start < current_month_start()


def remaining_amount(budget: Budget) -> float:
    """A budget from a past month counts as used 0."""
    if is_stale(budget):
        return budget.budget_amount
    return budget.remaining_amount


def add_spend(db: Session, budget_ids: list[int], cost: float) -> None:
    """Reset stale budgets, then add the cost. Both run in the caller's transaction.

    The add happens in SQL (amount_used = amount_used + cost), so two requests
    cannot overwrite each other. The caller commits.
    """
    month = current_month_start()
    for budget_id in budget_ids:
        db.execute(
            update(Budget)
            .where(Budget.id == budget_id, Budget.period_start < month)
            .values(amount_used=0.0, period_start=month)
        )
        db.execute(
            update(Budget)
            .where(Budget.id == budget_id)
            .values(amount_used=Budget.amount_used + cost)
        )