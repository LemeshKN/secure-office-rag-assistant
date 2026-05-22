from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.chat_routes import run_rag_request
from app.auth.security import get_current_user
from app.database import get_db
from app.logging_utils.query_logger import log_query
from app.models import User
from app.rag.evaluator import retrieval_precision
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.schemas import EvaluationRequest, EvaluationResponse


router = APIRouter(prefix="/evaluate", tags=["evaluation"])


@router.post("/query", response_model=EvaluationResponse)
def evaluate_query(
    request: EvaluationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EvaluationResponse:
    chat_response = run_rag_request(db, current_user, request.question, request.top_k, request.model)
    precision = retrieval_precision(
        [
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                vector_score=chunk.vector_score,
                keyword_score=chunk.keyword_score,
                combined_score=chunk.combined_score,
                rerank_score=chunk.rerank_score,
            )
            for chunk in chat_response.retrieved_chunks
        ],
        request.expected_doc_ids,
    )
    response = EvaluationResponse(**chat_response.model_dump(), retrieval_precision=precision)
    log_query(db, current_user, request.question, response)
    return response

