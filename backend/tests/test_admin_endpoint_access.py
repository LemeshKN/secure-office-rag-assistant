import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    seed = Session()
    seed.add_all(
        [
            User(id=1, username="admin", password_hash="x", role="admin"),
            User(id=2, username="priya", password_hash="x", role="developer"),
        ]
    )
    seed.commit()
    seed.close()

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def auth(username: str) -> dict[str, str]:
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_logs_rejects_missing_token(client) -> None:
    assert client.get("/logs").status_code == 401


def test_logs_rejects_non_admin(client) -> None:
    assert client.get("/logs", headers=auth("priya")).status_code == 403


def test_logs_allows_admin(client) -> None:
    response = client.get("/logs", headers=auth("admin"))
    assert response.status_code == 200
    assert response.json() == []