from datetime import datetime, timezone

from app.config import get_settings
from app.models import Document


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


class MustNotRun:
    def __init__(self):
        raise AssertionError("Ingestion must not start for a file that is too large.")


def upload(client, headers, size):
    files = {"file": ("notes.txt", b"a" * size, "text/plain")}
    return client.post("/documents/upload", files=files, headers=headers)


def test_file_over_the_limit_is_rejected_before_ingestion(cost_client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.document_routes.IngestService", MustNotRun)
    limit = get_settings().max_upload_mb * 1024 * 1024
    response = upload(cost_client, auth_headers("priya"), limit + 1)
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]
    assert str(get_settings().max_upload_mb) in response.json()["detail"]


def test_file_exactly_at_the_limit_is_accepted(cost_client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.document_routes.IngestService", FakeIngest)
    limit = get_settings().max_upload_mb * 1024 * 1024
    response = upload(cost_client, auth_headers("priya"), limit)
    assert response.status_code == 201