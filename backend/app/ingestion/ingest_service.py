import re
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.auth.rbac import access_metadata, dump_json_list, normalize_roles, normalize_user_ids
from app.config import Settings, get_settings
from app.ingestion.chunking import split_text_blocks
from app.ingestion.embeddings import EmbeddingProvider, get_embedding_provider
from app.ingestion.loaders import SUPPORTED_EXTENSIONS, load_document
from app.models import Chunk, Document, User
from app.retrieval.vector_store import ChromaVectorStore, VectorRecord


class IngestService:
    def __init__(
        self,
        settings: Settings | None = None,
        embeddings: EmbeddingProvider | None = None,
        vector_store: ChromaVectorStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings or get_embedding_provider(self.settings)
        self.vector_store = vector_store or ChromaVectorStore(self.settings)

    def ingest_bytes(
        self,
        db: Session,
        owner: User,
        filename: str,
        content: bytes,
        title: str | None,
        allowed_roles: list[str],
        allowed_user_ids: list[int] | None = None,
    ) -> tuple[Document, int]:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")

        clean_filename = _safe_filename(filename)
        stored_filename = f"{uuid.uuid4().hex}_{clean_filename}"
        upload_path = self.settings.uploads_path / stored_filename
        upload_path.write_bytes(content)

        blocks = load_document(upload_path)
        chunk_candidates = split_text_blocks(blocks)
        if not chunk_candidates:
            raise ValueError("No extractable text was found in the uploaded document.")

        roles = normalize_roles(allowed_roles)
        user_ids = normalize_user_ids(allowed_user_ids)

        document = Document(
            filename=clean_filename,
            title=title or Path(clean_filename).stem,
            owner_user_id=owner.id,
            allowed_roles=dump_json_list(roles),
            allowed_user_ids=dump_json_list(user_ids),
            file_type=suffix.lstrip("."),
            upload_path=str(upload_path),
        )
        db.add(document)
        db.flush()

        chunk_models: list[Chunk] = []
        for candidate in chunk_candidates:
            chunk = Chunk(
                document_id=document.id,
                chunk_index=candidate.chunk_index,
                text=candidate.text,
                page_number=candidate.page_number,
                char_start=candidate.char_start,
                char_end=candidate.char_end,
                chroma_id=f"doc-{document.id}-chunk-{candidate.chunk_index}",
            )
            db.add(chunk)
            chunk_models.append(chunk)
        db.flush()

        embeddings = self.embeddings.embed_documents([chunk.text for chunk in chunk_models])
        records: list[VectorRecord] = []
        for chunk, embedding in zip(chunk_models, embeddings):
            metadata = access_metadata(document.id, owner.id, roles, user_ids)
            metadata.update(
                {
                    "chunk_id": chunk.id,
                    "filename": document.filename,
                    "page_number": chunk.page_number or 0,
                    "chunk_index": chunk.chunk_index,
                }
            )
            records.append(
                VectorRecord(
                    chroma_id=chunk.chroma_id,
                    text=chunk.text,
                    embedding=embedding,
                    metadata=metadata,
                )
            )
        self.vector_store.upsert(records)
        db.commit()
        db.refresh(document)
        return document, len(chunk_models)


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "uploaded_document"
