import json

from sqlalchemy.orm import Session

from app.models import QueryLog, User
from app.schemas import ChatResponse


def log_query(
    db: Session,
    user: User,
    question: str,
    response: ChatResponse,
) -> QueryLog:
    cited_chunk_ids = [citation.chunk_id for citation in response.citations]
    retrieved_chunk_ids = [chunk.chunk_id for chunk in response.retrieved_chunks]
    log = QueryLog(
        user_id=user.id,
        question=question,
        answer=response.answer,
        cited_chunk_ids=json.dumps(cited_chunk_ids),
        retrieved_chunk_ids=json.dumps(retrieved_chunk_ids),
        model_name=response.model_name,
        latency_ms=response.latency_ms,
        estimated_cost=response.estimated_cost,
        groundedness_score=response.groundedness_score,
        evidence_score=response.evidence_score,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

