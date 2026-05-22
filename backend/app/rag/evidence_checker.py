import re
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.retrieval.keyword_store import tokenize


@dataclass(frozen=True)
class EvidenceResult:
    score: float
    should_answer: bool
    reason: str


@dataclass(frozen=True)
class GroundingResult:
    groundedness_score: float
    unsupported_sentences: list[str]


class EvidenceChecker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def check(self, question: str, chunks: list[RetrievedChunk]) -> EvidenceResult:
        if not chunks:
            return EvidenceResult(0.0, False, "No accessible chunks were retrieved.")

        top_chunks = chunks[:3]
        retrieval_component = sum(_chunk_score(chunk) for chunk in top_chunks) / len(top_chunks)
        overlap_component = max(_keyword_overlap(question, chunk.text) for chunk in top_chunks)
        count_component = min(len(chunks) / 3.0, 1.0)

        score = (0.55 * retrieval_component) + (0.35 * overlap_component) + (0.10 * count_component)
        if overlap_component == 0:
            score *= 0.5
        if len(chunks) < 2 and overlap_component < 0.50:
            score = max(0.0, score - 0.10)
        if len(chunks) == 1 and overlap_component >= 0.60:
            score = max(score, 0.50)

        score = round(min(max(score, 0.0), 1.0), 4)
        should_answer = score >= self.settings.evidence_threshold
        reason = (
            "Evidence meets threshold."
            if should_answer
            else "Accessible retrieved evidence is below the configured threshold."
        )
        return EvidenceResult(score, should_answer, reason)


class GroundingChecker:
    def check(self, answer: str, chunks: list[RetrievedChunk]) -> GroundingResult:
        sentences = _claim_sentences(answer)
        if not sentences:
            return GroundingResult(1.0, [])
        if not chunks:
            return GroundingResult(0.0, sentences)

        context = "\n".join(chunk.text for chunk in chunks)
        unsupported: list[str] = []
        for sentence in sentences:
            if _keyword_overlap(sentence, context) < 0.28:
                unsupported.append(sentence)
        supported = len(sentences) - len(unsupported)
        return GroundingResult(round(supported / len(sentences), 4), unsupported)


def _chunk_score(chunk: RetrievedChunk) -> float:
    if chunk.rerank_score:
        return min(max(chunk.rerank_score, 0.0), 1.0)
    return min(max(chunk.combined_score, 0.0), 1.0)


def _keyword_overlap(left: str, right: str) -> float:
    left_tokens = set(tokenize(left)) - _STOPWORDS
    right_tokens = set(tokenize(right)) - _STOPWORDS
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), 1)


def _claim_sentences(answer: str) -> list[str]:
    cleaned = re.sub(r"\[\d+:\d+\]", "", answer or "")
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]
    return [
        sentence
        for sentence in sentences
        if not sentence.lower().startswith("warning:")
        and "do not have enough evidence" not in sentence.lower()
    ]


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "using",
    "with",
}
