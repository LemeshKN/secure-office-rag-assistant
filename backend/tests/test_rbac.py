import pytest
from fastapi import HTTPException

from app.auth.rbac import build_chroma_permission_filter, can_access_document
from app.auth.security import ensure_admin_user
from app.models import Document, User


def user(user_id: int, role: str) -> User:
    return User(id=user_id, username=role, role=role, password_hash="x")


def document(owner_user_id: int, allowed_roles: str = "[]", allowed_user_ids: str = "[]") -> Document:
    return Document(
        id=1,
        filename="policy.txt",
        title="Policy",
        owner_user_id=owner_user_id,
        allowed_roles=allowed_roles,
        allowed_user_ids=allowed_user_ids,
        file_type="txt",
        upload_path="/tmp/policy.txt",
    )


def test_admin_can_access_all_documents() -> None:
    assert can_access_document(user(1, "admin"), document(owner_user_id=99, allowed_roles='["guest"]'))


def test_role_and_owner_access_rules() -> None:
    manager_doc = document(owner_user_id=7, allowed_roles='["manager"]')
    assert can_access_document(user(2, "manager"), manager_doc)
    assert not can_access_document(user(3, "employee"), manager_doc)
    assert can_access_document(user(7, "guest"), manager_doc)


def test_allowed_user_ids_grant_access() -> None:
    restricted_doc = document(owner_user_id=7, allowed_roles="[]", allowed_user_ids="[42]")
    assert can_access_document(user(42, "guest"), restricted_doc)
    assert not can_access_document(user(43, "guest"), restricted_doc)


def test_chroma_filter_contains_owner_role_and_explicit_user_paths() -> None:
    permission_filter = build_chroma_permission_filter(user(42, "employee"))
    assert permission_filter == {
        "$or": [{"owner_user_id": 42}, {"role_employee": 1}, {"user_42": 1}]
    }


def test_admin_only_dependency_rejects_non_admin() -> None:
    assert ensure_admin_user(user(1, "admin")).role == "admin"
    with pytest.raises(HTTPException):
        ensure_admin_user(user(2, "employee"))

