from app.config import get_settings
from app.rag.evidence_checker import EvidenceChecker, GroundingChecker
from app.retrieval.hybrid_retriever import RetrievedChunk


def test_weak_evidence_refuses_answer() -> None:
    checker = EvidenceChecker(get_settings())
    result = checker.check("What is the vacation policy?", [])
    assert not result.should_answer
    assert result.score == 0.0


def test_single_high_overlap_chunk_can_answer() -> None:
    checker = EvidenceChecker(get_settings())
    chunk = RetrievedChunk(
        document_id=1,
        chunk_id=1,
        filename="policy.txt",
        page_number=None,
        chunk_index=0,
        text="Remote work policy: Managers may approve remote work up to three days per week.",
        combined_score=0.35,
        keyword_score=1.0,
    )
    result = checker.check("What is the remote work policy?", [chunk])
    assert result.should_answer
    assert result.score >= 0.45


def test_grounding_checker_marks_unsupported_sentence() -> None:
    chunk = RetrievedChunk(
        document_id=1,
        chunk_id=1,
        filename="policy.txt",
        page_number=None,
        chunk_index=0,
        text="Employees may expense meals during approved business travel.",
    )
    result = GroundingChecker().check(
        "Employees may expense meals during approved business travel. The company pays for private vacations.",
        [chunk],
    )
    assert result.groundedness_score == 0.5
    assert "private vacations" in result.unsupported_sentences[0]
