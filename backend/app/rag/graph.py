import time
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import User
from app.rag.citation import build_citations, to_retrieved_chunk_out
from app.rag.evidence_checker import EvidenceChecker, GroundingChecker
from app.rag.llm_client import LLMClient
from app.retrieval.hybrid_retriever import HybridRetriever, RetrievedChunk
from app.retrieval.reranker import Reranker
from app.schemas import ChatResponse


class RAGState(TypedDict, total=False):
    user_id: int
    user_role: str
    question: str
    top_k: int
    retrieved_chunks: list[RetrievedChunk]
    reranked_chunks: list[RetrievedChunk]
    evidence_score: float
    answer: str
    citations: list
    groundedness_score: float
    unsupported_sentences: list[str]
    should_answer: bool
    refusal_reason: str
    latency_ms: int
    model_name: str
    estimated_cost: float
    warning: str | None


class RAGWorkflow:
    def __init__(
        self,
        db: Session,
        user: User,
        retriever: HybridRetriever,
        reranker: Reranker,
        llm_client: LLMClient,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.user = user
        self.retriever = retriever
        self.reranker = reranker
        self.llm_client = llm_client
        self.settings = settings or get_settings()
        self.graph = self._build_graph()

    def run(self, question: str, top_k: int = 5) -> ChatResponse:
        started = time.perf_counter()
        initial: RAGState = {
            "user_id": self.user.id,
            "user_role": self.user.role,
            "question": question,
            "top_k": top_k,
        }
        if self.graph is not None:
            state = dict(self.graph.invoke(initial))
        else:
            state = self._run_sequential(initial)
        state["latency_ms"] = int((time.perf_counter() - started) * 1000)
        state = self.finalize_response(state)
        return ChatResponse(
            answer=state.get("answer", ""),
            citations=state.get("citations", []),
            evidence_score=state.get("evidence_score", 0.0),
            groundedness_score=state.get("groundedness_score", 0.0),
            retrieved_chunks=to_retrieved_chunk_out(state.get("reranked_chunks", [])),
            latency_ms=state.get("latency_ms", 0),
            model_name=state.get("model_name", "unknown"),
            estimated_cost=state.get("estimated_cost", 0.0),
            warning=state.get("warning"),
            unsupported_sentences=state.get("unsupported_sentences", []),
        )

    def retrieve(self, state: RAGState) -> RAGState:
        chunks = self.retriever.retrieve(
            self.db,
            self.user,
            state["question"],
            final_top_k=state.get("top_k", 5),
        )
        return {**state, "retrieved_chunks": chunks}

    def rerank(self, state: RAGState) -> RAGState:
        chunks = self.reranker.rerank(state["question"], state.get("retrieved_chunks", []))
        return {**state, "reranked_chunks": chunks}

    def check_evidence(self, state: RAGState) -> RAGState:
        result = EvidenceChecker(self.settings).check(state["question"], state.get("reranked_chunks", []))
        return {
            **state,
            "evidence_score": result.score,
            "should_answer": result.should_answer,
            "refusal_reason": result.reason,
        }

    def generate_answer(self, state: RAGState) -> RAGState:
        if not state.get("should_answer"):
            return state
        result = self.llm_client.generate(state["question"], state.get("reranked_chunks", []))
        return {
            **state,
            "answer": result.answer,
            "model_name": result.model_name,
            "estimated_cost": result.estimated_cost,
        }

    def verify_grounding(self, state: RAGState) -> RAGState:
        if not state.get("should_answer"):
            return {
                **state,
                "answer": "I do not have enough evidence in the accessible documents to answer this question.",
                "model_name": getattr(self.llm_client, "model_name", "mock-grounded-llm"),
                "estimated_cost": 0.0,
                "groundedness_score": 1.0,
                "unsupported_sentences": [],
            }
        result = GroundingChecker().check(state.get("answer", ""), state.get("reranked_chunks", []))
        warning = None
        if result.groundedness_score < 0.60:
            warning = "Warning: some parts of this answer may not be fully supported by the retrieved documents."
        return {
            **state,
            "groundedness_score": result.groundedness_score,
            "unsupported_sentences": result.unsupported_sentences,
            "warning": warning,
        }

    def finalize_response(self, state: RAGState) -> RAGState:
        if not state.get("should_answer", False):
            return {**state, "citations": []}

        if "citations" in state:
            return state

        chunks = state.get("reranked_chunks", [])
        citations = build_citations(state.get("answer", ""), chunks)
        return {**state, "citations": citations}

    def _run_sequential(self, state: RAGState) -> RAGState:
        state = self.retrieve(state)
        state = self.rerank(state)
        state = self.check_evidence(state)
        if state.get("should_answer"):
            state = self.generate_answer(state)
        state = self.verify_grounding(state)
        return state

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph

            workflow = StateGraph(RAGState)
            workflow.add_node("retrieve", self.retrieve)
            workflow.add_node("rerank", self.rerank)
            workflow.add_node("check_evidence", self.check_evidence)
            workflow.add_node("generate_answer", self.generate_answer)
            workflow.add_node("verify_grounding", self.verify_grounding)
            workflow.add_node("finalize_response", self.finalize_response)
            workflow.set_entry_point("retrieve")
            workflow.add_edge("retrieve", "rerank")
            workflow.add_edge("rerank", "check_evidence")
            workflow.add_conditional_edges(
                "check_evidence",
                lambda state: "generate_answer" if state.get("should_answer") else "verify_grounding",
                {
                    "generate_answer": "generate_answer",
                    "verify_grounding": "verify_grounding",
                },
            )
            workflow.add_edge("generate_answer", "verify_grounding")
            workflow.add_edge("verify_grounding", "finalize_response")
            workflow.add_edge("finalize_response", END)
            return workflow.compile()
        except Exception:
            return None
