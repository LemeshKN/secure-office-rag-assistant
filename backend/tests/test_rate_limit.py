from datetime import datetime, timezone

from app.config import get_settings
from app.cost.governed import GovernedOutcome
from app.models import Document
from app.rate_limit import RateLimiter


def post_chat(client, headers):
    return client.post("/chat", json={"question": "hello"}, headers=headers)


def stub_chat(monkeypatch):
    monkeypatch.setattr(
        "app.api.chat_routes.run_governed", lambda *args, **kwargs: GovernedOutcome(card={"stopped": True})
    )


def test_chat_is_limited_per_minute(cost_client, auth_headers, monkeypatch):
    stub_chat(monkeypatch)
    monkeypatch.setattr(get_settings(), "rate_limit_chat_per_minute", 2)
    headers = auth_headers("priya")
    assert post_chat(cost_client, headers).status_code == 200
    assert post_chat(cost_client, headers).status_code == 200
    response = post_chat(cost_client, headers)
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]
    assert int(response.headers["Retry-After"]) >= 1


def test_limit_is_per_user(cost_client, auth_headers, monkeypatch):
    stub_chat(monkeypatch)
    monkeypatch.setattr(get_settings(), "rate_limit_chat_per_minute", 1)
    assert post_chat(cost_client, auth_headers("priya")).status_code == 200
    assert post_chat(cost_client, auth_headers("priya")).status_code == 429
    assert post_chat(cost_client, auth_headers("amit")).status_code == 200


def test_zero_turns_the_limit_off(cost_client, auth_headers, monkeypatch):
    stub_chat(monkeypatch)
    monkeypatch.setattr(get_settings(), "rate_limit_chat_per_minute", 0)
    headers = auth_headers("priya")
    assert all(post_chat(cost_client, headers).status_code == 200 for _ in range(5))


def test_upload_is_limited(cost_client, auth_headers, monkeypatch):
    class FakeIngest:
        def ingest_bytes(self, **kwargs):
            document = Document(
                id=1,
                filename="a.txt",
                title="A",
                owner_user_id=1,
                allowed_roles="[]",
                allowed_user_ids="[]",
                file_type="txt",
                upload_path="x",
                created_at=datetime.now(timezone.utc),
            )
            return document, 1

    monkeypatch.setattr("app.api.document_routes.IngestService", FakeIngest)
    monkeypatch.setattr(get_settings(), "rate_limit_upload_per_hour", 1)
    headers = auth_headers("priya")
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    assert cost_client.post("/documents/upload", files=files, headers=headers).status_code == 201
    assert cost_client.post("/documents/upload", files=files, headers=headers).status_code == 429


def test_window_expires():
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    assert limiter.check("k", 2, 60) == 0
    assert limiter.check("k", 2, 60) == 0
    assert limiter.check("k", 2, 60) == 60
    now[0] = 61.0
    assert limiter.check("k", 2, 60) == 0