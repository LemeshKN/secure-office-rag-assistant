from datetime import datetime

from sqlalchemy.orm import Session

from app.cost.budgets import find_budget
from app.models import Budget, Project, ProjectMember, User, UserProfile


DEPARTMENTS = {
    "priya": "Engineering",
    "lemesh": "Engineering",
    "amit": "Engineering",
    "khushi": "HR",
    "admin": "Platform",
}

PROJECTS = [
    {"name": "Apollo", "department": "Engineering", "members": ["priya", "lemesh", "amit"]},
    {"name": "Internal Tools", "department": "Engineering", "members": ["priya", "amit"]},
    {"name": "HR Onboarding", "department": "HR", "members": ["khushi"]},
    {"name": "Platform Ops", "department": "Platform", "members": ["admin"]},
]

# Budgets are in USD per month and sized in cents so the demo reaches warn and block quickly.
USER_BUDGETS = {"priya": 0.03, "lemesh": 0.05, "amit": 0.05, "khushi": 0.05, "admin": 0.05}
DEPARTMENT_BUDGETS = {"Engineering": 0.30, "HR": 0.20, "Platform": 0.50}
PROJECT_BUDGETS = {"Apollo": 0.15, "Internal Tools": 0.10, "HR Onboarding": 0.10, "Platform Ops": 0.20}


def seed_cost_data(db: Session) -> None:
    """Create missing demo profiles, projects, members and budgets. Existing rows are left alone."""
    users = {user.username: user for user in db.query(User).all()}
    period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for username, department in DEPARTMENTS.items():
        user = users.get(username)
        if user is not None and db.get(UserProfile, user.id) is None:
            db.add(UserProfile(user_id=user.id, department=department))

    projects: dict[str, Project] = {}
    for item in PROJECTS:
        project = db.query(Project).filter(Project.name == item["name"]).first()
        if project is None:
            project = Project(name=item["name"], department=item["department"])
            db.add(project)
            db.flush()
        projects[item["name"]] = project
        for username in item["members"]:
            user = users.get(username)
            if user is not None and db.get(ProjectMember, (project.id, user.id)) is None:
                db.add(ProjectMember(project_id=project.id, user_id=user.id))

    def ensure_budget(scope_type: str, scope_key: str, amount: float) -> None:
        if find_budget(db, scope_type, scope_key) is None:
            db.add(
                Budget(
                    scope_type=scope_type,
                    scope_key=scope_key,
                    budget_amount=amount,
                    period="monthly",
                    period_start=period_start,
                )
            )

    for username, amount in USER_BUDGETS.items():
        user = users.get(username)
        if user is not None:
            ensure_budget("user", str(user.id), amount)
    for department, amount in DEPARTMENT_BUDGETS.items():
        ensure_budget("department", department, amount)
    for name, amount in PROJECT_BUDGETS.items():
        ensure_budget("project", str(projects[name].id), amount)

    db.commit()