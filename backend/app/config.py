from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise RAG Agent Platform"
    environment: str = "local"
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    data_dir: str = str(PROJECT_ROOT / "data")
    database_url: Optional[str] = None
    chroma_collection: str = "enterprise_rag_chunks"

    embedding_provider: str = "auto"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768

    llm_provider: str = "auto"
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = "claude-3-5-sonnet-latest"
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = "gemini-1.5-flash-lite"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    enable_cross_encoder: bool = False
    evidence_threshold: float = 0.45
    max_output_tokens: int = 800
    max_upload_mb: int = 10
    seed_sample_documents: bool = True
    sample_documents_dir: str = ""
    admin_password: str = "admin123"
    rate_limit_chat_per_minute: int = 10
    rate_limit_estimate_per_minute: int = 20
    rate_limit_upload_per_hour: int = 10
    warn_threshold: float = 0.50
    large_context_tokens: int = 3000
    recommended_top_k: int = 3
    short_output_tokens: int = 300
    near_budget_ratio: float = 0.20
    repeat_window_days: int = 7

    cors_origins: str = "*"

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def uploads_path(self) -> Path:
        return self.data_path / "uploads"

    @property
    def chroma_path(self) -> Path:
        return self.data_path / "chroma"

    @property
    def sqlite_path(self) -> Path:
        return self.data_path / "sqlite"

    @property
    def vector_collection(self) -> str:
        """Chroma collection for the active embedding setup. Gemini vectors never share one with hash vectors."""
        if self.embedding_provider.lower() == "gemini":
            return f"{self.chroma_collection}_{self.gemini_embedding_model}_{self.gemini_embedding_dimensions}"
        return self.chroma_collection

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.sqlite_path / 'app.db'}"

    def ensure_directories(self) -> None:
        self.uploads_path.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.mkdir(parents=True, exist_ok=True)

    def check_production_safety(self) -> None:
        """Refuse to start a production server with the default secrets."""
        if self.environment.lower() != "production":
            return
        problems = []
        if self.secret_key == "change-me-in-production" or len(self.secret_key) < 32:
            problems.append("SECRET_KEY (at least 32 characters)")
        if self.admin_password == "admin123":
            problems.append("ADMIN_PASSWORD")
        if problems:
            raise RuntimeError("Set " + " and ".join(problems) + " before running in production.")

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings

