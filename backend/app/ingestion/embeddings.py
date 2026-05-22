import hashlib
import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import Settings, get_settings


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class EmbeddingProvider(ABC):
    model_name: str

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local fallback that needs no model download."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self.model_name = f"hashing-{dimensions}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.dimensions
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)[0]
        return embedding.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI

        self.model_name = settings.openai_embedding_model
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url or None)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    return _get_embedding_provider_cached(
        provider=settings.embedding_provider.lower(),
        openai_api_key=settings.openai_api_key or "",
        openai_base_url=settings.openai_base_url or "",
        openai_embedding_model=settings.openai_embedding_model,
        local_embedding_model=settings.local_embedding_model,
    )


@lru_cache(maxsize=4)
def _get_embedding_provider_cached(
    provider: str,
    openai_api_key: str,
    openai_base_url: str,
    openai_embedding_model: str,
    local_embedding_model: str,
) -> EmbeddingProvider:
    settings = get_settings().model_copy(
        update={
            "embedding_provider": provider,
            "openai_api_key": openai_api_key or None,
            "openai_base_url": openai_base_url or None,
            "openai_embedding_model": openai_embedding_model,
            "local_embedding_model": local_embedding_model,
        }
    )
    provider = provider.lower()

    if provider in {"auto", "openai"} and settings.openai_api_key:
        try:
            return OpenAIEmbeddingProvider(settings)
        except Exception:
            if provider == "openai":
                raise

    if provider in {"auto", "local", "sentence-transformers"}:
        try:
            return SentenceTransformerEmbeddingProvider(settings.local_embedding_model)
        except Exception:
            if provider in {"local", "sentence-transformers"}:
                raise

    return HashEmbeddingProvider()
