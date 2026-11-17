import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.cost.access import check_project_access
from app.cost.budget_period import add_spend
from app.cost.estimate import estimate_request
from app.cost.policy import collect_budgets, evaluate_policy
from app.cost.recommendations import apply_recommend_decision, build_recommendations
from app.logging_utils.query_logger import log_query
from app.models import LLMUsage, User, UserProfile
from app.rag.workflow_factory import build_workflow
from app.schemas import ChatResponse
from app.config import get_settings


@dataclass
class GovernedOutcome:
    response: ChatResponse | None = None
    card: dict | None = None  # set when the request was stopped before the LLM


def run_governed(
    db: Session,
    user: User,
    question: str,
    top_k: int = 5,
    model: str = "auto",
    project_id: int | None = None,
    max_output_tokens: int | None = None,
    approved: bool = False,
    conversation_id: int | None = None,
) -> GovernedOutcome:
    check_project_access(db, user, project_id)

    # The server recalculates everything. Nothing cost-related comes from the browser.
    estimate = estimate_request(db, user, question, top_k, model, max_output_tokens)
    policy = evaluate_policy(db, user, estimate["estimated_cost"], estimate["will_call_llm"], project_id)
    recs = build_recommendations(db, user, question, estimate, policy)
    policy = apply_recommend_decision(policy, recs)
    decision = policy["decision"]

    # Block is never run, even with approved=True. Warn needs approval. Recommend and allow run.
    if decision == "block" or (decision == "warn" and not approved):
        return GovernedOutcome(card={**estimate, **policy, "recommendations": recs, "stopped": True})

    cap = max_output_tokens or get_settings().max_output_tokens
    response = build_workflow(db, user, model).run(question, top_k, cap)
    response.estimated_cost = estimate["estimated_cost"]
    response.decision = decision
    response.recommendations = recs

    log = log_query(db, user, question, response, commit=False)

    if response.llm_called:
        profile = db.get(UserProfile, user.id)
        db.add(
            LLMUsage(
                user_id=user.id,
                department=profile.department if profile else "unassigned",
                project_id=project_id,
                conversation_id=conversation_id,
                query_log_id=log.id,
                model_name=response.model_name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                estimated_cost=estimate["estimated_cost"],
                actual_cost=response.actual_cost,
                cost_difference=round(response.actual_cost - estimate["estimated_cost"], 6),
                retrieved_chunk_ids=json.dumps([c.chunk_id for c in response.retrieved_chunks]),
            )
        )
        budget_ids = [budget.id for _, budget in collect_budgets(db, user, project_id)]
        add_spend(db, budget_ids, response.actual_cost)

    db.commit()  # query log, usage row and budget update land together
    return GovernedOutcome(response=response)