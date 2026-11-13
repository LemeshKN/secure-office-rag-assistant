from sqlalchemy.orm import Session

from app.models import Budget


def find_budget(db: Session, scope_type: str, scope_key: str) -> Budget | None:
    return (
        db.query(Budget)
        .filter(Budget.scope_type == scope_type, Budget.scope_key == scope_key)
        .first()
    )