import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from app.config import Settings, get_settings
from app.rag.prompt_builder import build_prompt_parts
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.retrieval.keyword_store import tokenize
from app.cost.pricing import calculate_cost
from app.cost.tokens import count_tokens


@dataclass(frozen=True)
class LLMResult:
    answer: str
    model_name: str
    estimated_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    actual_cost: float = 0.0


class LLMClient(ABC):
    @abstractmethod
    def generate(self, question: str, chunks: list[RetrievedChunk], max_output_tokens: int | None = None) -> LLMResult:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    model_name = "mock-grounded-llm"

    def __init__(self, model_name: str | None = None) -> None:
        if model_name:
            self.model_name = model_name

    def generate(self, question: str, chunks: list[RetrievedChunk], max_output_tokens: int | None = None) -> LLMResult:
        if not chunks:
            return LLMResult(
                "I do not have enough evidence in the accessible documents to answer this question.",
                self.model_name,
                0.0,
            )

        query_terms = set(tokenize(question))
        sentences: list[str] = []
        for chunk in chunks[:3]:
            candidates = _split_sentences(chunk.text)
            chosen = _best_sentence(candidates, query_terms) or chunk.text.strip()[:240]
            if chosen:
                sentences.append(f"{chosen.strip()} [{chunk.document_id}:{chunk.chunk_id}]")
        answer = " ".join(sentences)

        system_text, user_text = build_prompt_parts(question, chunks)
        input_tokens = count_tokens(system_text + "\n\n" + user_text)
        output_tokens = count_tokens(answer)
        cost = calculate_cost(self.model_name, input_tokens, output_tokens)
        return LLMResult(answer, self.model_name, 0.0, input_tokens, output_tokens, cost)

class OpenAICompatibleClient(LLMClient):
    def __init__(self, settings: Settings, model_name: str | None = None) -> None:
        from openai import OpenAI

        self.settings = settings
        self.model_name = model_name or settings.openai_model
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url or None)

    def generate(self, question: str, chunks: list[RetrievedChunk], max_output_tokens: int | None = None) -> LLMResult:
        system_text, user_text = build_prompt_parts(question, chunks)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            temperature=0.1,
        )
        answer = response.choices[0].message.content or ""
        cost = _estimate_cost(response.usage.total_tokens if response.usage else 0)
        return LLMResult(answer, self.model_name, cost)


class OllamaClient(LLMClient):
    def __init__(self, settings: Settings, model_name: str | None = None) -> None:
        self.settings = settings
        self.model_name = model_name or settings.ollama_model

    def generate(self, question: str, chunks: list[RetrievedChunk], max_output_tokens: int | None = None) -> LLMResult:
        system_text, user_text = build_prompt_parts(question, chunks)
        prompt = system_text + "\n\n" + user_text
        response = requests.post(
            f"{self.settings.ollama_base_url}/api/generate",
            json={"model": self.model_name, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return LLMResult(response.json().get("response", ""), f"ollama/{self.model_name}", 0.0)

class AnthropicClient(LLMClient):
    def __init__(self, settings: Settings, model_name: str | None = None) -> None:
        import anthropic

        self.settings = settings
        self.model_name = model_name or settings.anthropic_model
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate(self, question: str, chunks: list[RetrievedChunk], max_output_tokens: int | None = None) -> LLMResult:
        system_text, user_text = build_prompt_parts(question, chunks)
        response = self.client.messages.create(
            model=self.model_name,
            system=system_text,
            messages=[{"role": "user", "content": user_text}],
            max_tokens=800,
            temperature=0.1,
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        return LLMResult(text, f"anthropic/{self.model_name}", 0.0)


class GeminiClient(LLMClient):
    def __init__(self, settings: Settings, model_name: str | None = None) -> None:
        import google.generativeai as genai

        self.settings = settings
        self.model_name = model_name or settings.gemini_model
        genai.configure(api_key=settings.gemini_api_key)
        system_text, _ = build_prompt_parts("", [])
        self.model = genai.GenerativeModel(self.model_name, system_instruction=system_text)

    def generate(self, question: str, chunks: list[RetrievedChunk], max_output_tokens: int | None = None) -> LLMResult:
        _, user_text = build_prompt_parts(question, chunks)
        response = self.model.generate_content(user_text)
        return LLMResult(getattr(response, "text", ""), f"gemini/{self.model_name}", 0.0)

def get_llm_client(model: str = "auto", settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    requested = (model or "auto").lower()
    if requested in {"mock-small", "mock-large"}:
        return MockLLMClient(requested)
    known_providers = {"mock", "openai", "ollama", "anthropic", "gemini"}
    provider = settings.llm_provider.lower() if requested == "auto" else requested.split("/", 1)[0]
    requested_model = None if requested in {"auto", *known_providers} else model

    if requested not in {"auto", *known_providers} and "/" not in requested:
        provider = "openai" if settings.openai_api_key else "mock"
    if "/" in requested and provider in known_providers:
        requested_model = model.split("/", 1)[1]

    if provider in {"auto", "openai"} and settings.openai_api_key:
        try:
            return OpenAICompatibleClient(settings, requested_model)
        except Exception:
            if provider == "openai":
                raise
    if provider in {"ollama"}:
        try:
            return OllamaClient(settings, requested_model)
        except Exception:
            if requested != "auto":
                raise
    if provider in {"anthropic"} and settings.anthropic_api_key:
        try:
            return AnthropicClient(settings, requested_model)
        except Exception:
            if requested != "auto":
                raise
    if provider in {"gemini"} and settings.gemini_api_key:
        try:
            return GeminiClient(settings, requested_model)
        except Exception:
            if requested != "auto":
                raise
    return MockLLMClient()


def _split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _best_sentence(sentences: list[str], query_terms: set[str]) -> str:
    if not sentences:
        return ""
    scored = []
    for sentence in sentences:
        terms = set(tokenize(sentence))
        scored.append((len(terms & query_terms), sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _estimate_cost(total_tokens: int) -> float:
    return round((total_tokens / 1_000_000) * 0.15, 6)
