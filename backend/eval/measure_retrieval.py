"""Measure retrieval on sample_documents with the same store the app uses (Chroma).
Makes no LLM call.

Run from the backend folder:
    python eval/measure_retrieval.py --embedding hash
    python eval/measure_retrieval.py --embedding gemini
Add --verbose to see every question.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import Settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.ingestion.embeddings import get_embedding_provider  # noqa: E402
from app.ingestion.ingest_service import IngestService  # noqa: E402
from app.models import User  # noqa: E402
from app.rag.evidence_checker import EvidenceChecker  # noqa: E402
from app.retrieval.hybrid_retriever import HybridRetriever  # noqa: E402
from app.retrieval.keyword_store import KeywordStore  # noqa: E402
from app.retrieval.reranker import Reranker  # noqa: E402
from app.retrieval.vector_store import ChromaVectorStore  # noqa: E402

SAMPLE_DIR = BACKEND.parent / "sample_documents"
QUESTIONS = Path(__file__).with_name("retrieval_questions.json")
ALL_ROLES = ["admin", "agent_developer", "developer", "manager", "hr"]
THRESHOLDS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding", default="hash")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))

    # Temporary folder and in-memory database. The real app.db and Chroma folder are never touched.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        settings = Settings(data_dir=tmp, embedding_provider=args.embedding)
        settings.ensure_directories()

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        admin = User(username="admin", password_hash="x", role="admin")
        db.add(admin)
        db.commit()

        embeddings = get_embedding_provider(settings)
        store = ChromaVectorStore(settings)
        if store._fallback is not None:
            raise SystemExit("Chroma is not available, so the scores would not match the real app.")

        ingest = IngestService(settings, embeddings, store)
        for path in sorted(SAMPLE_DIR.glob("*.txt")):
            ingest.ingest_bytes(db, admin, path.name, path.read_bytes(), None, ALL_ROLES)

        retriever = HybridRetriever(embeddings, store, KeywordStore())
        reranker = Reranker(settings)
        checker = EvidenceChecker(settings)

        def search(question: str):
            chunks = retriever.retrieve(db, admin, question, final_top_k=args.top_k)
            return reranker.rerank(question, chunks)

        print(f"Embedding: {args.embedding} ({embeddings.model_name}), store: Chroma")
        print(f"Evidence threshold now: {settings.evidence_threshold}")

        hits = 0
        answer_scores: list[float] = []
        for item in data["retrieval_questions"]:
            chunks = search(item["question"])
            files = [chunk.filename for chunk in chunks]
            expected = item["expected_file"]
            rank = files.index(expected) + 1 if expected in files else None
            score = checker.check(item["question"], chunks).score
            hits += 1 if rank else 0
            answer_scores.append(score)
            if args.verbose:
                top = files[0] if files else "none"
                print(f"{item['id']:>3} rank={str(rank or '-'):<2} score={score:.2f} top={top} | {item['question']}")

        refuse_scores: list[float] = []
        for item in data["should_refuse"]:
            score = checker.check(item["question"], search(item["question"])).score
            refuse_scores.append(score)
            if args.verbose:
                print(f"{item['id']:>3} score={score:.2f} | {item['question']}")

        total = len(answer_scores)
        print()
        print(f"Correct document in top {args.top_k}: {hits} of {total}")
        print("Scores, questions with an answer (ids 1 to 20):")
        print("  " + " ".join(f"{s:.2f}" for s in answer_scores))
        print("Scores, questions with no answer (ids 101 to 105):")
        print("  " + " ".join(f"{s:.2f}" for s in refuse_scores))
        print()
        print("Threshold  answered (of 20)  refused (of 5)")
        for threshold in THRESHOLDS:
            answered = sum(score >= threshold for score in answer_scores)
            refused = sum(score < threshold for score in refuse_scores)
            print(f"{threshold:<9.2f}  {answered:<16}  {refused}")
        db.close()


if __name__ == "__main__":
    main()