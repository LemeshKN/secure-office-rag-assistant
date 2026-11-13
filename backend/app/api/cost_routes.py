from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.cost.budgets import find_budget
from app.database import get_db
from app.models import Budget, Project, ProjectMember, User, UserProfile
from app.cost.estimate import estimate_request
from app.schemas import EstimateRequest, EstimateResponse


router = APIRouter(prefix="/cost", tags=["cost"])


def budget_out(budget: Budget | None) -> dict | None:
    if budget is None:
        return None
    return {
        "budget_amount": budget.budget_amount,
        "period": budget.period,
        "amount_used": budget.amount_used,
        "remaining_amount": budget.remaining_amount,
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

@router.post("/estimate", response_model=EstimateResponse)
def estimate(
    request: EstimateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    # project_id is accepted but not checked until Level 4.
    return estimate_request(
        db,
        current_user,
        request.question,
        request.top_k,
        request.model,
        request.max_output_tokens,
    )