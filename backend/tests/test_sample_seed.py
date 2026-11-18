import pytest

from app.config import Settings
from app.ingestion.embeddings import EmbeddingError
from app.ingestion.sample_seed import EVERYONE, seed_sample_documents
from app.models import Document, User


class FakeIngest:
    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.calls = {}

    def ingest_bytes(self, db, owner, filename, content, title, allowed_roles, allowed_user_ids=None):
        if filename == self.fail_on:
            raise RuntimeError("boom")
        self.calls[filename] = (owner.username, allowed_roles, allowed_user_ids)
        db.add(
            Document(
                filename=filename,
                title=filename,
                owner_user_id=owner.id,
                allowed_roles="[]",
                allowed_user_ids="[]",
                file_type="txt",
                upload_path="x",
            )
        )
        db.commit()
        return None, 1


@pytest.fixture()
def folder(tmp_path):
    for name in ["company-leave-policy.txt", "private-project-notes.txt", "manager-performance-review-guide.txt"]:
        (tmp_path / name).write_text("Some text.", encoding="utf-8")
    return tmp_path


def settings_for(folder):
    return Settings(seed_sample_documents=True, sample_documents_dir=str(folder))


def test_adds_missing_documents_with_access_rules(seeded_db, folder):
    ingest = FakeIngest()
    assert seed_sample_documents(seeded_db, settings_for(folder), ingest) == 3

    owner, roles, user_ids = ingest.calls["private-project-notes.txt"]
    ids = {u.username: u.id for u in seeded_db.query(User).all()}
    assert owner == "priya"
    assert roles == []
    assert sorted(user_ids) == sorted([ids["lemesh"], ids["amit"]])

    assert "developer" not in ingest.calls["manager-performance-review-guide.txt"][1]
    assert ingest.calls["company-leave-policy.txt"][1] == EVERYONE


def test_safe_to_run_on_every_restart(seeded_db, folder):
    seed_sample_documents(seeded_db, settings_for(folder), FakeIngest())
    assert seed_sample_documents(seeded_db, settings_for(folder), FakeIngest()) == 0
    assert seeded_db.query(Document).count() == 3


def test_skips_a_file_that_is_already_uploaded(seeded_db, folder):
    owner = seeded_db.query(User).filter_by(username="priya").one()
    seeded_db.add(
        Document(
            filename="private-project-notes.txt",
            title="Apollo",
            owner_user_id=owner.id,
            allowed_roles="[]",
            allowed_user_ids="[]",
            file_type="txt",
            upload_path="x",
        )
    )
    seeded_db.commit()
    ingest = FakeIngest()
    assert seed_sample_documents(seeded_db, settings_for(folder), ingest) == 2
    assert "private-project-notes.txt" not in ingest.calls


def test_one_failure_does_not_stop_the_others(seeded_db, folder):
    ingest = FakeIngest(fail_on="company-leave-policy.txt")
    assert seed_sample_documents(seeded_db, settings_for(folder), ingest) == 2
    assert seeded_db.query(Document).count() == 2


def test_disabled_setting_does_nothing(seeded_db, folder):
    settings = Settings(seed_sample_documents=False, sample_documents_dir=str(folder))
    assert seed_sample_documents(seeded_db, settings, FakeIngest()) == 0
    assert seeded_db.query(Document).count() == 0


def test_missing_folder_does_not_crash(seeded_db, tmp_path):
    settings = settings_for(tmp_path / "does-not-exist")
    assert seed_sample_documents(seeded_db, settings, FakeIngest()) == 0


def test_ingestion_that_cannot_start_does_not_crash_the_app(seeded_db, folder, monkeypatch):
    class Broken:
        def __init__(self, *args, **kwargs):
            raise EmbeddingError("Gemini embeddings need GEMINI_API_KEY on the server.", 400)

    monkeypatch.setattr("app.ingestion.sample_seed.IngestService", Broken)
    assert seed_sample_documents(seeded_db, settings_for(folder)) == 0