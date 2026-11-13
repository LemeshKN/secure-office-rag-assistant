from sqlalchemy.orm import Session

from app.config import get_settings
from app.cost.pricing import MODEL_PRICES, calculate_cost
from app.cost.tokens import count_tokens
from app.models import User
from app.rag.prompt_builder import build_prompt_parts
from app.rag.workflow_factory import build_workflow


def resolve_priced_as(requested_model: str, client_model_name: str) -> str:
    """Price by the requested model if it is in the price table, else by the client's own model name."""
    requested = (requested_model or "auto").lower()
    if requested != "auto" and requested in MODEL_PRICES:
        return requested
    return client_model_name


def estimate_request(
    db: Session,
    user: User,
    question: str,
    top_k: int = 5,
    model: str = "auto",
    max_output_tokens: int | None = None,
) -> dict:
    """Pre-flight estimate. Runs retrieve, rerank and check_evidence only. Never calls the LLM."""
    settings = get_settings()
    output_limit = max_output_tokens or settings.max_output_tokens

    workflow = build_workflow(db, user, model)
    priced_as = resolve_priced_as(model, getattr(workflow.llm_client, "model_name", "mock-grounded-llm"))

    state = {
        "user_id": user.id,
        "user_role": user.role,
        "question": question,
        "top_k": top_k,
    }
    state = workflow.retrieve(state)
    state = workflow.rerank(state)
    state = workflow.check_evidence(state)

    chunks = state.get("reranked_chunks", [])
    result = {
        "model": model,
        "priced_as": priced_as,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost": 0.0,
        "will_call_llm": False,
        "evidence_score": state.get("evidence_score", 0.0),
        "top_k": top_k,
        "retrieved_chunk_ids": [chunk.chunk_id for chunk in chunks],
    }

    if not state.get("should_answer", False):
        return result

    system_text, user_text = build_prompt_parts(question, chunks)
    input_tokens = count_tokens(system_text + "\n\n" + user_text)
    result.update(
        input_tokens=input_tokens,
        output_tokens=output_limit,
        estimated_cost=calculate_cost(priced_as, input_tokens, output_limit),
        will_call_llm=True,
    )
    return result