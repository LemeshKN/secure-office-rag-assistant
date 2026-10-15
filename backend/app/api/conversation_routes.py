import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import ChatMessage, Conversation, User

from app.api.chat_routes import run_rag_request
from app.schemas import ChatRequest, ChatResponse


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)


@router.post("", status_code=201)
def create_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversation = Conversation(
        user_id=current_user.id,
        title="New chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
    }


@router.get("")
def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .all()
    )

    return [
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
        }
        for conversation in conversations
    ]


@router.get("/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
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
            status_code=404,
            detail="Conversation not found",
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.id)
        .all()
    )

    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "citations": json.loads(message.citations_json),
            "created_at": message.created_at,
        }
        for message in messages
    ]

@router.post(
    "/{conversation_id}/messages",
    response_model=ChatResponse,
)
def send_message(
    conversation_id: int,
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
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
            status_code=404,
            detail="Conversation not found",
        )

    response = run_rag_request(
        db,
        current_user,
        request.question,
        request.top_k,
        request.model,
    )

    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=request.question,
        citations_json="[]",
    )
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response.answer,
        citations_json=json.dumps(
            [
                citation.model_dump(mode="json")
                for citation in response.citations
            ]
        ),
    )

    has_messages = (
        db.query(ChatMessage.id)
        .filter(ChatMessage.conversation_id == conversation.id)
        .first()
    )
    if has_messages is None:
        conversation.title = request.question.strip()[:200] or "New chat"

    db.add(user_message)
    db.flush()
    db.add(assistant_message)
    db.commit()

    return response

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
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
            status_code=404,
            detail="Conversation not found",
        )

    db.delete(conversation)
    db.commit()

    return {"detail": "Conversation deleted"}