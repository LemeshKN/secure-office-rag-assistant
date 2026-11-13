from sqlalchemy.orm import Session

from app.config import get_settings
from app.ingestion.embeddings import get_embedding_provider
from app.models import User
from app.rag.graph import RAGWorkflow
from app.rag.llm_client import get_llm_client
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.keyword_store import KeywordStore
from app.retrieval.reranker import Reranker
from app.retrieval.vector_store import ChromaVectorStore


def build_workflow(db: Session, user: User, model: str = "auto") -> RAGWorkflow:
    settings = get_settings()
    embeddings = get_embedding_provider(settings)
    vector_store = ChromaVectorStore(settings)
    retriever = HybridRetriever(embeddings, vector_store, KeywordStore())
    return RAGWorkflow(
        db=db,
        user=user,
        retriever=retriever,
        reranker=Reranker(settings),
        llm_client=get_llm_client(model, settings),
        settings=settings,
    )