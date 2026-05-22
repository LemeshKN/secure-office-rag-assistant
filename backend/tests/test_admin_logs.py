import pytest
from fastapi import HTTPException

from app.auth.security import ensure_admin_user
from app.models import User


def test_logs_are_admin_only() -> None:
    admin = User(id=1, username="admin", password_hash="x", role="admin")
    employee = User(id=2, username="employee", password_hash="x", role="employee")

    assert ensure_admin_user(admin) is admin
    with pytest.raises(HTTPException) as exc:
        ensure_admin_user(employee)
    assert exc.value.status_code == 403

