import pytest

from app.config import Settings
from app.cost.pricing import calculate_cost
from app.rag.llm_client import LLMError, get_llm_client


def test_missing_gemini_key_gives_clear_error():
    settings = Settings()
    settings.gemini_api_key = None
    with pytest.raises(LLMError) as info:
        get_llm_client("gemini/gemini-3.5-flash-lite", settings)
    assert info.value.status_code == 400
    assert "GEMINI_API_KEY" in str(info.value)


def test_chat_route_returns_readable_error(cost_client, auth_headers, monkeypatch):
    def failing(*args, **kwargs):
        raise LLMError("Gemini rate limit reached. Wait a minute and try again.", 429)

    monkeypatch.setattr("app.api.chat_routes.run_governed", failing)
    response = cost_client.post("/chat", json={"question": "hello"}, headers=auth_headers("priya"))
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"]


def test_failed_stream_saves_no_messages(cost_client, auth_headers, monkeypatch):
    def failing(*args, **kwargs):
        raise LLMError("Gemini could not answer right now. Please try again.", 500)

    monkeypatch.setattr("app.api.chat_routes.run_governed", failing)
    headers = auth_headers("priya")
    conversation_id = cost_client.post("/conversations", headers=headers).json()["id"]

    response = cost_client.post(
        f"/conversations/{conversation_id}/messages/stream",
        json={"question": "hello"},
        headers=headers,
    )
    assert response.status_code == 500

    messages = cost_client.get(f"/conversations/{conversation_id}/messages", headers=headers).json()
    assert messages == []


def test_gemini_models_are_priced():
    assert calculate_cost("gemini/gemini-3.5-flash-lite", 1_000_000, 0) == 0.30
    assert calculate_cost("gemini/gemini-3.8-flash", 0, 1_000_000) == 3.75