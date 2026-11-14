from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import require_admin
from app.cost import reports
from app.database import get_db

router = APIRouter(
    prefix="/cost/admin",
    tags=["cost-admin"],
    dependencies=[Depends(require_admin)],  # every endpoint here is admin only
)


def date_filters(start: date | None = None, end: date | None = None, this_month: bool = False) -> list:
    return reports.build_filters(start, end, this_month)


Filters = Annotated[list, Depends(date_filters)]
DB = Annotated[Session, Depends(get_db)]


@router.get("/summary")
def summary(db: DB, conds: Filters) -> dict:
    return reports.summary(db, conds)


@router.get("/by-user")
def by_user(db: DB, conds: Filters) -> list[dict]:
    return reports.by_user(db, conds)


@router.get("/by-department")
def by_department(db: DB, conds: Filters) -> list[dict]:
    return reports.by_department(db, conds)


@router.get("/by-project")
def by_project(db: DB, conds: Filters) -> list[dict]:
    return reports.by_project(db, conds)


@router.get("/by-model")
def by_model(db: DB, conds: Filters) -> list[dict]:
    return reports.by_model(db, conds)


@router.get("/trend/daily")
def trend_daily(db: DB, conds: Filters) -> list[dict]:
    return reports.trend(db, conds, monthly=False)


@router.get("/trend/monthly")
def trend_monthly(db: DB, conds: Filters) -> list[dict]:
    return reports.trend(db, conds, monthly=True)


@router.get("/budgets")
def budgets(db: DB) -> list[dict]:
    return reports.budget_utilization(db)


@router.get("/estimated-vs-actual")
def estimated_vs_actual(db: DB, conds: Filters) -> dict:
    return reports.estimated_vs_actual(db, conds)


@router.get("/top-users")
def top_users(db: DB, conds: Filters) -> list[dict]:
    return reports.top_users(db, conds)


@router.get("/top-conversations")
def top_conversations(db: DB, conds: Filters) -> list[dict]:
    return reports.top_conversations(db, conds)