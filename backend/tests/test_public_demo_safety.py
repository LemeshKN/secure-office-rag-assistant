import pytest

from app.auth.users import authenticate_user, create_default_users
from app.config import Settings, get_settings

GOOD_KEY = "k" * 40


def production(**changes) -> Settings:
    settings = Settings()
    settings.environment = "production"
    settings.secret_key = GOOD_KEY
    settings.admin_password = "a-strong-password"
    for name, value in changes.items():
        setattr(settings, name, value)
    return settings


def test_production_refuses_the_default_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        production(secret_key="change-me-in-production").check_production_safety()


def test_production_refuses_a_short_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        production(secret_key="short").check_production_safety()


def test_production_refuses_the_default_admin_password():
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        production(admin_password="admin123").check_production_safety()


def test_production_with_real_secrets_starts():
    production().check_production_safety()


def test_local_never_refuses():
    settings = production(secret_key="change-me-in-production", admin_password="admin123")
    settings.environment = "local"
    settings.check_production_safety()


def test_admin_password_comes_from_the_setting(session_factory, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "a-strong-password")
    db = session_factory()
    create_default_users(db)
    assert authenticate_user(db, "admin", "a-strong-password") is not None
    assert authenticate_user(db, "admin", "admin123") is None
    assert authenticate_user(db, "priya", "priya123") is not None
    db.close()