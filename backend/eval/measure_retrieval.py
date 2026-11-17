"""Measure retrieval on sample_documents. Makes no LLM call and no internet call.

Run from the backend folder:
    python eval/measure_retrieval.py --embedding hash
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

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
from app.retrieval.vector_store import InMemoryVectorStore  # noqa: E402

SAMPLE_DIR = BACKEND.parent / "sample_documents"
QUESTIONS = Path(__file__).with_name("retrieval_questions.json")
ALL_ROLES = ["admin", "agent_developer", "developer", "manager", "hr"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding", default="hash")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))

    # Temporary folder and in-memory database. The real app.db and Chroma folder are never touched.
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_dir=tmp, embedding_provider=args.embedding)
        settings.ensure_directories()

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        admin = User(username="admin", password_hash="x", role="admin")
        db.add(admin)
        db.commit()

        embeddings = get_embedding_provider(settings)
        store = InMemoryVectorStore("measure_retrieval")
        store.reset()

        ingest = IngestService(settings, embeddings, store)
        for path in sorted(SAMPLE_DIR.glob("*.txt")):
            ingest.ingest_bytes(db, admin, path.name, path.read_bytes(), None, ALL_ROLES)

        retriever = HybridRetriever(embeddings, store, KeywordStore())
        reranker = Reranker(settings)
        checker = EvidenceChecker(settings)

        def search(question: str):
            chunks = retriever.retrieve(db, admin, question, final_top_k=args.top_k)
            return reranker.rerank(question, chunks)

        print(f"Embedding: {args.embedding} ({embeddings.model_name})")
        print(f"Evidence threshold: {settings.evidence_threshold}")
        print()
        print("RETRIEVAL QUESTIONS")
        hits = answered = 0
        for item in data["retrieval_questions"]:
            chunks = search(item["question"])
            files = [chunk.filename for chunk in chunks]
            expected = item["expected_file"]
            rank = files.index(expected) + 1 if expected in files else None
            evidence = checker.check(item["question"], chunks)
            hits += 1 if rank else 0
            answered += 1 if evidence.should_answer else 0
            top = files[0] if files else "none"
            verdict = "answer" if evidence.should_answer else "REFUSE"
            print(
                f"{item['id']:>3} rank={str(rank or '-'):<2} evidence={evidence.score:.2f} "
                f"{verdict:<6} top={top} | {item['question']}"
            )

        print()
        print("QUESTIONS NO DOCUMENT ANSWERS")
        refused = 0
        for item in data["should_refuse"]:
            chunks = search(item["question"])
            evidence = checker.check(item["question"], chunks)
            refused += 0 if evidence.should_answer else 1
            verdict = "answer" if evidence.should_answer else "REFUSE"
            print(f"{item['id']:>3} evidence={evidence.score:.2f} {verdict:<6} | {item['question']}")

        total = len(data["retrieval_questions"])
        print()
        print(f"Correct document in top {args.top_k}: {hits} of {total}")
        print(f"Would answer: {answered} of {total}")
        print(f"Would refuse the unanswerable ones: {refused} of {len(data['should_refuse'])}")
        db.close()


if __name__ == "__main__":
    main()