"""
backend/agents/orchestrator.py
────────────────────────────────
LangGraph multi-agent graph definition for the Loan Advisory Agent.

This module wires together all specialist agent nodes into a directed graph
with conditional routing. The graph is compiled once at startup and reused
for every query via thread-scoped memory (session_id as thread_id).

Architecture:
  START
    └─► classify_query          (classifies intent, extracts entities)
          └─► retrieve_documents (RAG: fetch relevant policy chunks)
                └─► [router]
                      ├─► verify_employment ──► [router]
                      │     ├─► score_credit ──► [router]
                      │     │     ├─► detect_fraud ──► check_eligibility ──► synthesize
                      │     │     └─► check_eligibility ──► synthesize
                      │     └─► synthesize
                      ├─► calculate_emi ──► synthesize
                      └─► synthesize                        (policy / general Qs)
  END

All nodes return partial state dicts — LangGraph merges them automatically.
"""

from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from .state import LoanAdvisoryState
from .nodes import (
    credit_scorer,
    document_retriever,
    eligibility_checker,
    emi_calculator,
    employment_verifier,
    fraud_detector,
    query_classifier,
    response_synthesizer,
)

log = structlog.get_logger(__name__)


# ── ROUTING FUNCTIONS ──────────────────────────────────────────────────────────


def route_after_retrieval(state: LoanAdvisoryState) -> str:
    """
    Decides which agent to call after document retrieval.
    
    Priority: eligibility full-check > EMI-only > policy/general (direct synthesis)
    """
    if state.get("error"):
        return "synthesize_response"

    requires: list[str] = state.get("requires_agents", [])

    if "employment_verifier" in requires:
        return "verify_employment"
    if "emi_calculator" in requires:
        return "calculate_emi"
    # Default: policy or general question goes straight to synthesis
    return "synthesize_response"


def route_after_employment(state: LoanAdvisoryState) -> str:
    """After employment verification, decide next step."""
    if state.get("error"):
        return "synthesize_response"

    requires: list[str] = state.get("requires_agents", [])
    employment = state.get("employment_data", {}) or {}

    # If employment verification found a discrepancy, skip to synthesis
    if employment.get("verification_status") == "discrepancy":
        log.warning("employment_discrepancy_detected", applicant=state.get("applicant_id"))
        return "synthesize_response"

    if "credit_scorer" in requires:
        return "score_credit"
    return "synthesize_response"


def route_after_credit(state: LoanAdvisoryState) -> str:
    """After credit scoring, decide whether fraud check is needed."""
    if state.get("error"):
        return "synthesize_response"

    requires: list[str] = state.get("requires_agents", [])
    credit = state.get("credit_analysis", {}) or {}

    # High risk credit profile triggers fraud check
    if credit.get("risk_level") == "high" and "fraud_detector" in requires:
        return "detect_fraud"
    if "eligibility_checker" in requires:
        return "check_eligibility"
    return "synthesize_response"


def route_after_fraud(state: LoanAdvisoryState) -> str:
    """After fraud detection, determine if we can proceed to eligibility."""
    if state.get("error"):
        return "synthesize_response"

    fraud = state.get("fraud_assessment", {}) or {}
    requires: list[str] = state.get("requires_agents", [])

    # High fraud risk → skip eligibility, surface in synthesizer
    if fraud.get("fraud_risk") == "high":
        log.warning("high_fraud_risk_detected", applicant=state.get("applicant_id"))
        return "synthesize_response"

    if "eligibility_checker" in requires:
        return "check_eligibility"
    return "synthesize_response"


# ── GRAPH BUILDER ──────────────────────────────────────────────────────────────


def create_loan_advisory_graph(checkpointer=None):
    """
    Builds and compiles the complete LangGraph agent pipeline.

    Args:
        checkpointer: LangGraph checkpointer for conversation memory.
                      Defaults to MemorySaver (in-process, dev-only).
                      Swap to AsyncPostgresSaver for Supabase-backed persistence.

    Returns:
        CompiledGraph ready to call with .invoke() or .astream()
    """
    builder = StateGraph(LoanAdvisoryState)

    # ── REGISTER NODES ─────────────────────────────────────────────────────────
    builder.add_node("classify_query",      query_classifier.run)
    builder.add_node("retrieve_documents",  document_retriever.run)
    builder.add_node("verify_employment",   employment_verifier.run)
    builder.add_node("score_credit",        credit_scorer.run)
    builder.add_node("detect_fraud",        fraud_detector.run)
    builder.add_node("check_eligibility",   eligibility_checker.run)
    builder.add_node("calculate_emi",       emi_calculator.run)
    builder.add_node("synthesize_response", response_synthesizer.run)

    # ── STATIC EDGES ───────────────────────────────────────────────────────────
    builder.add_edge(START,                  "classify_query")
    builder.add_edge("classify_query",       "retrieve_documents")
    builder.add_edge("check_eligibility",    "synthesize_response")
    builder.add_edge("calculate_emi",        "synthesize_response")
    builder.add_edge("synthesize_response",  END)

    # ── CONDITIONAL ROUTING ────────────────────────────────────────────────────
    builder.add_conditional_edges(
        "retrieve_documents",
        route_after_retrieval,
        {
            "verify_employment":  "verify_employment",
            "calculate_emi":      "calculate_emi",
            "synthesize_response":"synthesize_response",
        },
    )

    builder.add_conditional_edges(
        "verify_employment",
        route_after_employment,
        {
            "score_credit":       "score_credit",
            "synthesize_response":"synthesize_response",
        },
    )

    builder.add_conditional_edges(
        "score_credit",
        route_after_credit,
        {
            "detect_fraud":       "detect_fraud",
            "check_eligibility":  "check_eligibility",
            "synthesize_response":"synthesize_response",
        },
    )

    builder.add_conditional_edges(
        "detect_fraud",
        route_after_fraud,
        {
            "check_eligibility":  "check_eligibility",
            "synthesize_response":"synthesize_response",
        },
    )

    # ── COMPILE ────────────────────────────────────────────────────────────────
    cp = checkpointer or MemorySaver()
    graph = builder.compile(checkpointer=cp)

    log.info("loan_advisory_graph_compiled", nodes=list(builder.nodes.keys()))
    return graph


# ── SINGLETON ─────────────────────────────────────────────────────────────────

_graph = None


def get_graph():
    """
    Returns the compiled singleton graph.
    Safe to call multiple times — builds only once.
    """
    global _graph
    if _graph is None:
        _graph = create_loan_advisory_graph()
    return _graph


# ── RUN HELPERS ───────────────────────────────────────────────────────────────

async def run_query(
    query: str,
    session_id: str,
    applicant_id: str | None = None,
) -> dict:
    """
    High-level async entry point used by the FastAPI chat route.

    Args:
        query:        User's question
        session_id:   Conversation thread ID (maps to checkpointer thread)
        applicant_id: Optional — filters agent lookups to a specific applicant

    Returns:
        Final state dict containing 'final_response', 'sources', 'confidence_score'
    """
    from .state import initial_state

    graph = get_graph()
    state = initial_state(query=query, session_id=session_id, applicant_id=applicant_id)
    config = {"configurable": {"thread_id": session_id}}

    try:
        final_state = await graph.ainvoke(state, config=config)
        log.info(
            "query_completed",
            session=session_id,
            query_type=final_state.get("query_type"),
            confidence=final_state.get("confidence_score"),
        )
        return final_state
    except Exception as exc:
        log.error("graph_execution_failed", error=str(exc), session=session_id)
        return {
            "final_response": (
                "I encountered an error while processing your query. "
                "Please try again or rephrase your question."
            ),
            "sources": [],
            "confidence_score": 0.0,
            "error": str(exc),
        }