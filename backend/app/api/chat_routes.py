import json
import time
from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import ChatMessage, Conversation, User
from app.rag.workflow_factory import build_workflow
from app.schemas import ChatRequest, ChatResponse
from fastapi.responses import JSONResponse, StreamingResponse
from app.cost.governed import run_governed
from app.rate_limit import rate_limit_chat

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit_chat)])
def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    outcome = run_governed(
        db, current_user, request.question, request.top_k, request.model,
        request.project_id, request.max_output_tokens, request.approved,
    )
    if outcome.card is not None:
        return JSONResponse(outcome.card)
    return outcome.response


def run_rag_request(
    db: Session,
    user: User,
    question: str,
    top_k: int = 5,
    model: str = "auto",
) -> ChatResponse:
    workflow = build_workflow(db, user, model)
    return workflow.run(question, top_k)


@router.post("/conversations/{conversation_id}/messages/stream", dependencies=[Depends(rate_limit_chat)])
def stream_message(
    conversation_id: int,
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
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

    outcome = run_governed(
        db, current_user, request.question, request.top_k, request.model,
        request.project_id, request.max_output_tokens, request.approved,
        conversation_id=conversation.id,
    )
    if outcome.card is not None:
        return JSONResponse(outcome.card)
    response = outcome.response

    answer_text = response.answer
    conversation_id_value = conversation.id

    has_messages = (
        db.query(ChatMessage.id)
        .filter(ChatMessage.conversation_id == conversation_id_value)
        .first()
    )
    if has_messages is None:
        conversation.title = request.question.strip()[:200] or "New chat"


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