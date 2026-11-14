from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.cost.budget_period import KOLKATA, current_month_start, is_stale
from app.cost.budgets import find_budget
from app.models import Budget, Conversation, LLMUsage, Project, User, UserProfile

UTC = timezone.utc


def money(value) -> float:
    return round(float(value or 0), 6)


def _kolkata_day_to_utc(day: date) -> datetime:
    local = datetime.combine(day, time.min, tzinfo=KOLKATA)
    return local.astimezone(UTC).replace(tzinfo=None)


def build_filters(start: date | None, end: date | None, this_month: bool) -> list:
    """Date filters in Asia/Kolkata days. created_at is stored in UTC."""
    if this_month and start is None:
        start = current_month_start().date()
    conds = []
    if start:
        conds.append(LLMUsage.created_at >= _kolkata_day_to_utc(start))
    if end:
        conds.append(LLMUsage.created_at < _kolkata_day_to_utc(end + timedelta(days=1)))
    return conds


def summary(db: Session, conds: list) -> dict:
    r = (
        db.query(
            func.count(LLMUsage.id),
            func.coalesce(func.sum(LLMUsage.input_tokens), 0),
            func.coalesce(func.sum(LLMUsage.output_tokens), 0),
            func.coalesce(func.sum(LLMUsage.estimated_cost), 0.0),
            func.coalesce(func.sum(LLMUsage.actual_cost), 0.0),
        )
        .filter(*conds)
        .one()
    )
    return {
        "requests": r[0],
        "input_tokens": int(r[1]),
        "output_tokens": int(r[2]),
        "total_tokens": int(r[1]) + int(r[2]),
        "estimated_cost": money(r[3]),
        "actual_cost": money(r[4]),
    }


def _grouped(db: Session, conds: list, column, limit: int | None = None) -> list[dict]:
    cost = func.coalesce(func.sum(LLMUsage.actual_cost), 0.0)
    query = (
        db.query(
            column,
            func.count(LLMUsage.id),
            func.coalesce(func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens), 0),
            cost,
        )
        .filter(*conds)
        .group_by(column)
        .order_by(cost.desc())
    )
    if limit:
        query = query.limit(limit)
    return [
        {"key": key, "requests": n, "tokens": int(tokens), "cost": money(total)}
        for key, n, tokens, total in query.all()
    ]


def by_department(db: Session, conds: list) -> list[dict]:
    return [{"department": r["key"], **{k: v for k, v in r.items() if k != "key"}}
            for r in _grouped(db, conds, LLMUsage.department)]


def by_model(db: Session, conds: list) -> list[dict]:
    return [{"model": r["key"], **{k: v for k, v in r.items() if k != "key"}}
            for r in _grouped(db, conds, LLMUsage.model_name)]


def by_user(db: Session, conds: list, limit: int | None = None) -> list[dict]:
    names = {u.id: u.username for u in db.query(User).all()}
    depts = {p.user_id: p.department for p in db.query(UserProfile).all()}
    out = []
    for r in _grouped(db, conds, LLMUsage.user_id, limit):
        out.append({
            "user_id": r["key"],
            "username": names.get(r["key"], "unknown"),
            "department": depts.get(r["key"], "unassigned"),
            "requests": r["requests"],
            "tokens": r["tokens"],
            "cost": r["cost"],
        })
    return out


def by_project(db: Session, conds: list) -> list[dict]:
    names = {p.id: p.name for p in db.query(Project).all()}
    return [
        {
            "project_id": r["key"],
            "project": names.get(r["key"], "No project"),
            "requests": r["requests"],
            "tokens": r["tokens"],
            "cost": r["cost"],
        }
        for r in _grouped(db, conds, LLMUsage.project_id)
    ]


def _used_percent(budget: Budget | None) -> float | None:
    if budget is None or not budget.budget_amount:
        return None
    used = 0.0 if is_stale(budget) else budget.amount_used
    return round(used / budget.budget_amount * 100, 1)


def top_users(db: Session, conds: list, limit: int = 5) -> list[dict]:
    rows = by_user(db, conds, limit)
    for row in rows:
        row["user_budget_used_percent"] = _used_percent(find_budget(db, "user", str(row["user_id"])))
    return rows


def top_conversations(db: Session, conds: list, limit: int = 5) -> list[dict]:
    names = {u.id: u.username for u in db.query(User).all()}
    rows = _grouped(db, conds + [LLMUsage.conversation_id.isnot(None)], LLMUsage.conversation_id, limit)
    out = []
    for r in rows:
        conversation = db.get(Conversation, r["key"])
        out.append({
            "conversation_id": r["key"],
            "username": names.get(conversation.user_id) if conversation else None,
            "requests": r["requests"],
            "cost": r["cost"],
        })
    return out


def trend(db: Session, conds: list, monthly: bool) -> list[dict]:
    rows = (
        db.query(LLMUsage.created_at, LLMUsage.actual_cost, LLMUsage.input_tokens + LLMUsage.output_tokens)
        .filter(*conds)
        .all()
    )
    buckets: dict[str, dict] = {}
    for created, cost, tokens in rows:
        local = created.replace(tzinfo=UTC).astimezone(KOLKATA)
        key = local.strftime("%Y-%m" if monthly else "%Y-%m-%d")
        bucket = buckets.setdefault(key, {"period": key, "requests": 0, "tokens": 0, "cost": 0.0})
        bucket["requests"] += 1
        bucket["tokens"] += int(tokens or 0)
        bucket["cost"] += cost or 0.0
    return [{**b, "cost": money(b["cost"])} for _, b in sorted(buckets.items())]


def budget_utilization(db: Session) -> list[dict]:
    users = {str(u.id): u.username for u in db.query(User).all()}
    projects = {str(p.id): p.name for p in db.query(Project).all()}
    out = []
    for budget in db.query(Budget).order_by(Budget.scope_type, Budget.scope_key).all():
        used = 0.0 if is_stale(budget) else budget.amount_used  # stale month counts as 0
        names = users if budget.scope_type == "user" else projects if budget.scope_type == "project" else {}
        out.append({
            "scope": budget.scope_type,
            "name": names.get(budget.scope_key, budget.scope_key),
            "budget_amount": budget.budget_amount,
            "amount_used": round(used, 6),
            "remaining_amount": round(max(budget.budget_amount - used, 0.0), 6),
            "utilization_percent": _used_percent(budget),
            "status": budget.status,
        })
    return out


def estimated_vs_actual(db: Session, conds: list) -> dict:
    s = summary(db, conds)
    difference = round(s["actual_cost"] - s["estimated_cost"], 6)  # actual minus estimated
    percent = round(difference / s["estimated_cost"] * 100, 1) if s["estimated_cost"] else None
    return {
        "estimated_cost": s["estimated_cost"],
        "actual_cost": s["actual_cost"],
        "difference": difference,
        "difference_percent": percent,
        "requests": s["requests"],
    }