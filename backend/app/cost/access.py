from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, User


def check_project_access(db: Session, user: User, project_id: int | None) -> None:
    """404 if the project does not exist, 403 if the user is not a member. Admin gets no exception."""
    if project_id is None:
        return
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db.get(ProjectMember, (project_id, user.id)) is None:
        raise HTTPException(status_code=403, detail="You are not a member of this project")