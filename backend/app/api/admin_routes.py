from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import require_admin
from app.database import get_db
from app.models import QueryLog, User
from app.schemas import QueryLogOut


router = APIRouter(tags=["admin"])


@router.get("/logs", response_model=list[QueryLogOut])
def list_logs(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 100,
) -> list[QueryLog]:
    return db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit).all()

