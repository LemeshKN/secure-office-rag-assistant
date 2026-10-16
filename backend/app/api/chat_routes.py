import json
import time
from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import get_settings
from app.database import get_db
from app.ingestion.embeddings import get_embedding_provider
from app.logging_utils.query_logger import log_query
from app.models import ChatMessage, Conversation, User
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



@router.post("/conversations/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: int,
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    response = run_rag_request(
        db,
        current_user,
        request.question,
        request.top_k,
        request.model,
    )

    answer_text = response.answer
    conversation_id_value = conversation.id

    has_messages = (
        db.query(ChatMessage.id)
        .filter(ChatMessage.conversation_id == conversation_id_value)
        .first()
    )
    if has_messages is None:
        conversation.title = request.question.strip()[:200] or "New chat"

    log_query(db, current_user, request.question, response)

    user_message = ChatMessage(
        conversation_id=conversation_id_value,
        role="user",
        content=request.question,
        citations_json="[]",
    )
    db.add(user_message)

    assistant_message = ChatMessage(
        conversation_id=conversation_id_value,
        role="assistant",
        content=answer_text,
        citations_json=json.dumps(
            [citation.model_dump(mode="json") for citation in response.citations]
        ),
    )
    db.add(assistant_message)
    db.commit()

    def save_and_stream() -> Generator[str, None, None]:
        words = answer_text.split()

        for index, word in enumerate(words):
            content = word if index == 0 else f" {word}"
            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            time.sleep(0.03)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        save_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )