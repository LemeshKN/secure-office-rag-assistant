"""Add the demo documents from sample_documents/ when the app starts.

Safe to run on every restart: a file whose name is already in the database is skipped.
"""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT, Settings, get_settings
from app.ingestion.ingest_service import IngestService
from app.models import Document, User

logger = logging.getLogger(__name__)

EVERYONE = ["agent_developer", "developer", "manager", "hr"]

# filename: (owner, allowed roles, usernames who can also see it). Admin sees every document.
SAMPLE_ACCESS: dict[str, tuple[str, list[str], list[str]]] = {
    "engineering-code-review-guidelines.txt": ("admin", ["agent_developer", "developer", "manager"], []),
    "engineering-oncall-incident-runbook.txt": ("admin", ["agent_developer", "developer", "manager"], []),
    "ai-model-evaluation-standards.txt": ("admin", ["agent_developer", "developer"], []),
    "manager-performance-review-guide.txt": ("admin", ["manager", "hr"], []),
    "manager-hiring-interview-process.txt": ("admin", ["manager", "hr"], []),
    "private-project-notes.txt": ("priya", [], ["lemesh", "amit"]),
}
DEFAULT_ACCESS = ("admin", EVERYONE, [])


def seed_sample_documents(db: Session, settings: Settings | None = None, ingest=None) -> int:
    """Return how many documents were added."""
    settings = settings or get_settings()
    if not settings.seed_sample_documents:
        return 0

    folder = Path(settings.sample_documents_dir) if settings.sample_documents_dir else PROJECT_ROOT / "sample_documents"
    if not folder.is_dir():
        logger.warning("Sample documents folder not found: %s", folder)
        return 0

    existing = {row[0] for row in db.query(Document.filename).all()}
    missing = [path for path in sorted(folder.glob("*.txt")) if path.name not in existing]
    if not missing:
        return 0

    try:
        ingest = ingest or IngestService(settings)
    except Exception:
        # For example a missing Gemini key. The app must still start.
        logger.exception("Sample documents were not loaded because ingestion could not start.")
        return 0

    added = 0
    for path in missing:
        owner_name, roles, usernames = SAMPLE_ACCESS.get(path.name, DEFAULT_ACCESS)
        owner = db.query(User).filter(User.username == owner_name).first()
        if owner is None:
            continue
        user_ids = (
            [user.id for user in db.query(User).filter(User.username.in_(usernames)).all()] if usernames else []
        )
        try:
            ingest.ingest_bytes(db, owner, path.name, path.read_bytes(), None, roles, user_ids)
            added += 1
        except Exception:
            db.rollback()
            logger.exception("Could not load sample document %s", path.name)
    return added