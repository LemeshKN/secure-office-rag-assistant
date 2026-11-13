from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


# USD per 1M tokens. Edit these when provider prices change.
MODEL_PRICES: dict[str, ModelPrice] = {
    "mock-small": ModelPrice(0.15, 0.60),
    "mock-large": ModelPrice(2.50, 10.00),
    "mock-grounded-llm": ModelPrice(0.15, 0.60),
    "gpt-4o-mini": ModelPrice(0.15, 0.60),
    "claude-3-5-sonnet-latest": ModelPrice(3.00, 15.00),
    "gemini-1.5-flash": ModelPrice(0.075, 0.30),
    "llama3.1": ModelPrice(0.0, 0.0),
}

# Unknown models are priced high on purpose, so budgets err on the safe side.
DEFAULT_PRICE = ModelPrice(2.50, 10.00)


def get_price(model_name: str) -> ModelPrice:
    key = (model_name or "").lower().split("/", 1)[-1]
    return MODEL_PRICES.get(key, DEFAULT_PRICE)


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative")
    price = get_price(model_name)
    cost = (input_tokens / 1_000_000) * price.input_per_million
    cost += (output_tokens / 1_000_000) * price.output_per_million
    return round(cost, 6)