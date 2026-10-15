import json
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Document, User


ROLES = ("admin", "agent_developer", "developer", "manager", "hr")


def normalize_roles(roles: Iterable[str] | None) -> list[str]:
    clean: list[str] = []
    for role in roles or []:
        role_value = role.strip().lower()
        if role_value in ROLES and role_value not in clean:
            clean.append(role_value)
    return clean


def normalize_user_ids(user_ids: Iterable[int | str] | None) -> list[int]:
    clean: list[int] = []
    for value in user_ids or []:
        if value in ("", None):
            continue
        user_id = int(value)
        if user_id not in clean:
            clean.append(user_id)
    return clean


def dump_json_list(values: Iterable[str | int] | None) -> str:
    return json.dumps(list(values or []))


def load_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    except json.JSONDecodeError:
        return [item.strip() for item in value.split(",") if item.strip()]


def document_roles(document: Document) -> list[str]:
    return normalize_roles(load_json_list(document.allowed_roles))


def document_user_ids(document: Document) -> list[int]:
    return normalize_user_ids(load_json_list(document.allowed_user_ids))


def can_access_document(user: User, document: Document) -> bool:
    if document.owner_user_id == user.id:
        return True
    if user.role in document_roles(document):
        return True
    return user.id in document_user_ids(document)


def accessible_document_ids(db: Session, user: User) -> list[int]:
    documents = db.query(Document).all()
    return [
        document.id
        for document in documents
        if can_access_document(user, document)
    ]



def build_chroma_permission_filter(user: User) -> dict:
    """Restrict retrieval to owned or explicitly shared documents."""
    return {
        "$or": [
            {"owner_user_id": user.id},
            {f"role_{user.role}": 1},
            {f"user_{user.id}": 1},
        ]
    }


def access_metadata(
    document_id: int,
    owner_user_id: int,
    allowed_roles: Iterable[str],
    allowed_user_ids: Iterable[int],
) -> dict:
    roles = normalize_roles(allowed_roles)
    user_ids = normalize_user_ids(allowed_user_ids)
    metadata: dict[str, int | str] = {
        "document_id": document_id,
        "owner_user_id": owner_user_id,
        "allowed_roles": ",".join(roles),
        "allowed_user_ids": ",".join(str(user_id) for user_id in user_ids),
    }
    for role in ROLES:
        metadata[f"role_{role}"] = 1 if role in roles else 0
    for user_id in user_ids:
        metadata[f"user_{user_id}"] = 1
    return metadata

