import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.rbac import can_access_document, document_roles, document_user_ids, normalize_roles, normalize_user_ids
from app.auth.security import get_current_user
from app.database import get_db
from app.ingestion.ingest_service import IngestService
from app.models import Document, ReportingRelationship, User
from app.schemas import DocumentOut, UploadResponse


router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)

async def upload_document(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    allowed_roles: str = Form(""),
    allowed_user_ids: str = Form(""),
    share_with_manager: bool = Form(False),
) -> UploadResponse:
    try:
        roles = normalize_roles(_parse_list(allowed_roles))
        user_ids = normalize_user_ids(_parse_list(allowed_user_ids))

        # FIXED: Brought manager logic inside the conditional block to prevent crashes
        if share_with_manager:
            reporting = db.get(ReportingRelationship, current_user.id)

            if reporting is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No manager is assigned to your account.",
                )

            manager = db.get(User, reporting.manager_user_id)

            if manager is None or manager.role != "manager":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Your assigned manager is not valid.",
                )

            if manager.id not in user_ids:
                user_ids.append(manager.id)

        # Read file contents asynchronously
        content = await file.read()

        # Ingest document data into the RAG platform database
        document, chunks_created = IngestService().ingest_bytes(
            db=db,
            owner=current_user,
            filename=file.filename or "uploaded.txt",
            content=content,
            title=title,
            allowed_roles=roles,
            allowed_user_ids=user_ids,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return UploadResponse(
        document=_document_out(document), chunks_created=chunks_created
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentOut]:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return [_document_out(document) for document in documents if can_access_document(current_user, document)]


def _parse_list(value: str) -> list:
    if not value:
        return []
    try:
        loaded = json.loads(value)
        if isinstance(loaded, list):
            return loaded
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]


def _document_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        title=document.title,
        owner_user_id=document.owner_user_id,
        allowed_roles=document_roles(document),
        allowed_user_ids=document_user_ids(document),
        file_type=document.file_type,
        created_at=document.created_at,
    )

