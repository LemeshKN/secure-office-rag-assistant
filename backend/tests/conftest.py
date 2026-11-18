import os

os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["EVIDENCE_THRESHOLD"] = "0.45"
os.environ["GEMINI_API_KEY"] = ""
os.environ["SEED_SAMPLE_DOCUMENTS"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token
from app.cost.seed import seed_cost_data
from app.database import Base, get_db
from app.main import app
from app.models import User


DEMO_USERS = [
    ("admin", "admin"),
    ("lemesh", "agent_developer"),
    ("priya", "developer"),
    ("amit", "manager"),
    ("khushi", "hr"),
]


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture()
def seeded_db(session_factory):
    db = session_factory()
    db.add_all([User(username=name, password_hash="x", role=role) for name, role in DEMO_USERS])
    db.commit()
    seed_cost_data(db)
    yield db
    db.close()


@pytest.fixture()
def cost_client(session_factory, seeded_db):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    def build(username: str) -> dict[str, str]:
        token = create_access_token({"sub": username})
        return {"Authorization": f"Bearer {token}"}

    return build