import math
import re
from dataclasses import dataclass
from collections import Counter

from sqlalchemy.orm import Session

from app.auth.rbac import accessible_document_ids
from app.models import Chunk, Document, User


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class KeywordResult:
    chunk_id: int
    document_id: int
    score: float


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class KeywordStore:
    def search(self, db: Session, user: User, question: str, top_k: int = 8) -> list[KeywordResult]:
        document_ids = accessible_document_ids(db, user)
        if not document_ids:
            return []
        chunks = (
            db.query(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .filter(Chunk.document_id.in_(document_ids))
            .all()
        )
        if not chunks:
            return []

        query_terms = tokenize(question)
        if not query_terms:
            return []

        tokenized_chunks = [tokenize(chunk.text) for chunk in chunks]
        scores = self._bm25_scores(query_terms, tokenized_chunks)
        max_score = max(scores) if scores else 0.0
        results: list[KeywordResult] = []
        for chunk, score in zip(chunks, scores):
            if score <= 0:
                continue
            normalized = score / max_score if max_score else 0.0
            results.append(
                KeywordResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    score=normalized,
                )
            )
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

    def _bm25_scores(self, query_terms: list[str], documents: list[list[str]]) -> list[float]:
        try:
            from rank_bm25 import BM25Okapi

            bm25 = BM25Okapi(documents)
            return list(bm25.get_scores(query_terms))
        except Exception:
            return _simple_bm25(query_terms, documents)


def _simple_bm25(query_terms: list[str], documents: list[list[str]]) -> list[float]:
    doc_count = len(documents)
    avg_doc_len = sum(len(document) for document in documents) / max(doc_count, 1)
    document_frequencies: Counter[str] = Counter()
    for document in documents:
        for term in set(document):
            document_frequencies[term] += 1

    scores: list[float] = []
    for document in documents:
        frequencies = Counter(document)
        doc_len = len(document) or 1
        score = 0.0
        for term in query_terms:
            if term not in frequencies:
                continue
            idf = math.log(1 + (doc_count - document_frequencies[term] + 0.5) / (document_frequencies[term] + 0.5))
            numerator = frequencies[term] * 2.2
            denominator = frequencies[term] + 1.2 * (0.25 + 0.75 * doc_len / max(avg_doc_len, 1))
            score += idf * numerator / denominator
        scores.append(score)
    return scores

