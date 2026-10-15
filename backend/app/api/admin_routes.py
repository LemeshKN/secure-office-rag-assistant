from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import QueryLog, User
from app.schemas import QueryLogOut


router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=list[QueryLogOut])
def list_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[QueryLog]:
    return (
        db.query(QueryLog)
        .filter(QueryLog.user_id == current_user.id)
        .order_by(QueryLog.created_at.desc(), QueryLog.id.desc())
        .limit(limit)
        .all()
    )