from types import SimpleNamespace

import pytest

from app.config import Settings
from app.ingestion.embeddings import EmbeddingError, GeminiEmbeddingProvider, get_embedding_provider


class FakeAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


class FakeModels:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def embed_content(self, model, contents, config):
        self.calls.append(
            {"model": model, "count": len(contents), "task": config.task_type, "dims": config.output_dimensionality}
        )
        if self.error:
            raise self.error
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[3.0, 4.0]) for _ in contents])


def make(error=None):
    fake = SimpleNamespace(models=FakeModels(error))
    return GeminiEmbeddingProvider(Settings(), client=fake), fake.models


def test_documents_and_queries_use_different_task_types():
    provider, models = make()
    provider.embed_documents(["a"])
    provider.embed_query("b")
    assert models.calls[0]["task"] == "RETRIEVAL_DOCUMENT"
    assert models.calls[1]["task"] == "RETRIEVAL_QUERY"


def test_vectors_are_unit_length():
    provider, _ = make()
    assert provider.embed_query("b") == pytest.approx([0.6, 0.8])


def test_large_uploads_are_sent_in_batches():
    provider, models = make()
    vectors = provider.embed_documents(["x"] * 120)
    assert len(vectors) == 120
    assert [call["count"] for call in models.calls] == [50, 50, 20]


def test_dimensions_and_model_are_sent():
    provider, models = make()
    provider.embed_query("b")
    assert models.calls[0]["dims"] == provider.dimensions
    assert models.calls[0]["model"] == Settings().gemini_embedding_model


def test_rate_limit_gives_429_message():
    provider, _ = make(FakeAPIError(429))
    with pytest.raises(EmbeddingError) as info:
        provider.embed_query("b")
    assert info.value.status_code == 429


def test_missing_key_is_an_error_not_a_silent_fallback():
    settings = Settings()
    settings.gemini_api_key = None
    settings.embedding_provider = "gemini"
    with pytest.raises(EmbeddingError) as info:
        get_embedding_provider(settings)
    assert info.value.status_code == 400