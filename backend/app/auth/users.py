from sqlalchemy.orm import Session

from app.auth.security import get_password_hash, verify_password
from app.models import ReportingRelationship, User


DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "lemesh", "password": "lemesh123", "role": "agent_developer"},
    {"username": "priya", "password": "priya123", "role": "developer"},
    {"username": "amit", "password": "amit123", "role": "manager"},
    {"username": "khushi", "password": "khushi123", "role": "hr"},
]

# (employee, manager)
DEFAULT_REPORTING = [
    ("lemesh", "amit"),
]


def create_default_users(db: Session) -> None:
    for user_data in DEFAULT_USERS:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if existing:
            continue
        db.add(
            User(
                username=user_data["username"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"],
            )
        )
    db.commit()

    for employee_name, manager_name in DEFAULT_REPORTING:
        employee = db.query(User).filter(User.username == employee_name).first()
        manager = db.query(User).filter(User.username == manager_name).first()
        if employee is None or manager is None:
            continue

        link = (
            db.query(ReportingRelationship)
            .filter(ReportingRelationship.employee_user_id == employee.id)
            .first()
        )
        if link is None:
            db.add(
                ReportingRelationship(
                    employee_user_id=employee.id,
                    manager_user_id=manager.id,
                )
            )
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None