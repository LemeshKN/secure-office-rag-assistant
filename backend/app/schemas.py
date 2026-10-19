from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    user_id: Optional[int] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    title: str
    owner_user_id: int
    allowed_roles: list[str]
    allowed_user_ids: list[int]
    file_type: str
    created_at: datetime


class UploadResponse(BaseModel):
    document: DocumentOut
    chunks_created: int


class Citation(BaseModel):
    document_id: int
    chunk_id: int
    filename: str
    page_number: Optional[int] = None
    quoted_text: str
    score: float | None = None


class RetrievedChunkOut(BaseModel):
    document_id: int
    chunk_id: int
    filename: str
    page_number: Optional[int] = None
    chunk_index: int
    text: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: float = 0.0


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    model: str = "auto"


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    evidence_score: float
    groundedness_score: float
    retrieved_chunks: list[RetrievedChunkOut]
    latency_ms: int
    model_name: str
    estimated_cost: float = 0.0
    warning: Optional[str] = None
    unsupported_sentences: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    question: str = Field(min_length=1)
    expected_answer: Optional[str] = None
    expected_doc_ids: Optional[list[int]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    model: str = "auto"


class EvaluationResponse(ChatResponse):
    retrieval_precision: Optional[float] = None


class QueryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    question: str
    answer: str
    cited_chunk_ids: str
    retrieved_chunk_ids: str
    model_name: str
    latency_ms: int
    estimated_cost: float
    groundedness_score: float
    evidence_score: float
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str | dict[str, Any]

