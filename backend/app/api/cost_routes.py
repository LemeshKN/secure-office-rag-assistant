from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.cost.budgets import find_budget
from app.cost.estimate import estimate_request
from app.cost.policy import evaluate_policy
from app.database import get_db
from app.models import Budget, Project, ProjectMember, User, UserProfile
from app.schemas import EstimateRequest, EstimateResponse
from app.cost.recommendations import build_recommendations, apply_recommend_decision
from app.cost.access import check_project_access
from app.cost.budget_period import current_month_start, is_stale, remaining_amount
from app.rate_limit import rate_limit_estimate

router = APIRouter(prefix="/cost", tags=["cost"])


def budget_out(budget: Budget | None) -> dict | None:
    """Shows effective usage for the current month. A past-month budget counts as used 0.

    This only reads. The spending path writes the stored reset.
    """
    if budget is None:
        return None
    stale = is_stale(budget)
    return {
        "budget_amount": budget.budget_amount,
        "period": budget.period,
        "period_start": (current_month_start() if stale else budget.period_start).date().isoformat(),
        "amount_used": 0.0 if stale else budget.amount_used,
        "remaining_amount": remaining_amount(budget),
        "status": budget.status,
    }


@router.get("/me")
def my_cost_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    profile = db.get(UserProfile, current_user.id)
    department = profile.department if profile else "unassigned"

    projects = (
        db.query(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == current_user.id)
        .order_by(Project.name)
        .all()
    )

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "department": department,
        "user_budget": budget_out(find_budget(db, "user", str(current_user.id))),
        "department_budget": budget_out(find_budget(db, "department", department)),
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "budget": budget_out(find_budget(db, "project", str(project.id))),
            }
            for project in projects
        ],
    }


@router.post("/estimate", response_model=EstimateResponse, dependencies=[Depends(rate_limit_estimate)])
def estimate(
    request: EstimateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    check_project_access(db, current_user, request.project_id)
    result = estimate_request(
        db,
        current_user,
        request.question,
        request.top_k,
        request.model,
        request.max_output_tokens,
    )
    policy = evaluate_policy(
        db,
        current_user,
        result["estimated_cost"],
        result["will_call_llm"],
        request.project_id,
    )
    recs = build_recommendations(db, current_user, request.question, result, policy)
    policy = apply_recommend_decision(policy, recs)
    return {**result, **policy, "recommendations": recs}