from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, get_current_user
from app.auth.users import authenticate_user
from app.config import get_settings
from app.database import get_db
from app.models import ReportingRelationship, User
from app.schemas import Token, UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(access_token=token, username=user.username, role=user.role)


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("/me/manager")
def get_my_manager(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    manager = (
        db.query(User)
        .join(
            ReportingRelationship,
            ReportingRelationship.manager_user_id == User.id,
        )
        .filter(ReportingRelationship.employee_user_id == current_user.id)
        .first()
    )

    if manager is None:
        return {"has_manager": False, "manager_username": None}

    return {
        "has_manager": True,
        "manager_username": manager.username,
    }

@router.get("/users")
def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    users = db.query(User).order_by(User.username).all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        }
        for user in users
    ]
