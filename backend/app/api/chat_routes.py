from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import get_settings
from app.database import get_db
from app.ingestion.embeddings import get_embedding_provider
from app.logging_utils.query_logger import log_query
from app.models import User
from app.rag.graph import RAGWorkflow
from app.rag.llm_client import get_llm_client
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.reranker import Reranker
from app.retrieval.vector_store import ChromaVectorStore
from app.schemas import ChatRequest, ChatResponse


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    response = run_rag_request(db, current_user, request.question, request.top_k, request.model)
    log_query(db, current_user, request.question, response)
    return response


def run_rag_request(
    db: Session,
    user: User,
    question: str,
    top_k: int = 5,
    model: str = "auto",
) -> ChatResponse:
    settings = get_settings()
    embeddings = get_embedding_provider(settings)
    vector_store = ChromaVectorStore(settings)
    retriever = HybridRetriever(embeddings, vector_store, KeywordStore())
    workflow = RAGWorkflow(
        db=db,
        user=user,
        retriever=retriever,
        reranker=Reranker(settings),
        llm_client=get_llm_client(model, settings),
        settings=settings,
    )
    return workflow.run(question, top_k)

