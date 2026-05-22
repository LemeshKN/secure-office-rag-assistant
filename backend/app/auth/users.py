from sqlalchemy.orm import Session

from app.auth.security import get_password_hash, verify_password
from app.models import User


DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "manager", "password": "manager123", "role": "manager"},
    {"username": "employee", "password": "employee123", "role": "employee"},
    {"username": "guest", "password": "guest123", "role": "guest"},
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


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

