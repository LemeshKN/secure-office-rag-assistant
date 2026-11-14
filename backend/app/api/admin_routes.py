from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.security import require_admin
from app.database import get_db
from app.models import LLMUsage, QueryLog, User
from app.schemas import QueryLogOut


router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=list[QueryLogOut])
def list_logs(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[QueryLogOut]:
    rows = (
        db.query(QueryLog, LLMUsage)
        .outerjoin(LLMUsage, LLMUsage.query_log_id == QueryLog.id)
        .order_by(QueryLog.created_at.desc(), QueryLog.id.desc())
        .limit(limit)
        .all()
    )
    result = []
    for log, usage in rows:
        item = QueryLogOut.model_validate(log)
        if usage is not None:  # no usage row (refusal or old log) leaves the four fields null
            item.input_tokens = usage.input_tokens
            item.output_tokens = usage.output_tokens
            item.actual_cost = usage.actual_cost
            item.cost_difference = usage.cost_difference
        result.append(item)
    return result