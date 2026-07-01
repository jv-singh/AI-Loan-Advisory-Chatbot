"""
backend/agents/state.py
────────────────────────
LangGraph State Definition for the Loan Advisory Agent.

This TypedDict is the SINGLE SOURCE OF TRUTH that flows through every node
in the agent graph. Each node reads what it needs and writes only its outputs.

Architecture note:
  - `messages` uses LangGraph's add_messages reducer (append-only conversation)
  - All other fields use the default "last-write-wins" reducer
  - Optional fields start as None and get populated as agents run
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class LoanAdvisoryState(TypedDict):
    """
    Central state that flows through every node in the LangGraph pipeline.

    Field groups:
        INPUT           — what the user sent
        CLASSIFICATION  — what type of query it is and which agents to invoke
        RAG             — retrieved document chunks and confidence
        AGENT OUTPUTS   — structured results from each specialist agent
        CONVERSATION    — full message history (append-only)
        FINAL OUTPUT    — synthesized response with sources
        GUARDRAILS      — quality signals and error tracking

    Usage in a node:
        def run(state: LoanAdvisoryState) -> dict:
            query = state["query"]
            # ... process ...
            return {"employment_data": result}   # only return what changed
    """

    # ── INPUT ──────────────────────────────────────────────────────────────────
    query: str
    """The user's raw natural-language question."""

    applicant_id: Optional[str]
    """Applicant ID if the query is applicant-specific (can be None for policy Qs)."""

    session_id: str
    """Conversation session identifier for memory persistence."""

    # ── CLASSIFICATION ─────────────────────────────────────────────────────────
    query_type: str
    """One of: 'eligibility' | 'emi' | 'policy' | 'fraud_check' | 'general'"""

    requires_agents: list[str]
    """Ordered list of agent node names that must run for this query type."""

    query_entities: dict[str, Any]
    """
    Entities extracted from the query.
    Example: {"loan_amount": 500000, "tenure_years": 5, "loan_type": "home"}
    """

    # ── RAG ────────────────────────────────────────────────────────────────────
    retrieved_documents: list[dict]
    """
    List of retrieved document chunks. Each dict has:
      - content (str): chunk text
      - source (str): document name / page
      - score (float): cosine similarity score
      - metadata (dict): arbitrary metadata
    """

    retrieval_confidence: float
    """Mean similarity score across retrieved chunks. Used by guardrails."""

    # ── AGENT OUTPUTS ──────────────────────────────────────────────────────────
    employment_data: Optional[dict]
    """
    Output of Employment Verifier Agent.
    Keys: employer_name, employment_type, monthly_income, years_employed,
          verification_status ('verified'|'unverified'|'discrepancy')
    """

    credit_analysis: Optional[dict]
    """
    Output of Credit Scorer Agent.
    Keys: credit_score (int), score_band ('excellent'|'good'|'fair'|'poor'),
          risk_level, debt_to_income_ratio, remarks
    """

    fraud_assessment: Optional[dict]
    """
    Output of Fraud Detector Agent.
    Keys: fraud_risk ('low'|'medium'|'high'), flags (list[str]),
          auto_approve (bool), requires_manual_review (bool)
    """

    eligibility_result: Optional[dict]
    """
    Output of Eligibility Checker Agent.
    Keys: is_eligible (bool), max_loan_amount (float),
          interest_rate (float), reasons (list[str]), conditions (list[str])
    """

    emi_details: Optional[dict]
    """
    Output of EMI Calculator Agent.
    Keys: emi_amount (float), total_interest (float), total_payment (float),
          amortization_schedule (list[dict]), breakdown_summary (str)
    """

    # ── CONVERSATION ───────────────────────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]
    """Full message history. Uses LangGraph's append-only add_messages reducer."""

    # ── FINAL OUTPUT ───────────────────────────────────────────────────────────
    final_response: str
    """The grounded, citation-backed answer returned to the user."""

    sources: list[str]
    """Document sources cited in the response. Shown in the UI."""

    confidence_score: float
    """
    Composite reliability score (0–1).
    Derived from retrieval_confidence + agent agreement + hallucination signals.
    """

    # ── GUARDRAILS ─────────────────────────────────────────────────────────────
    hallucination_risk: str
    """'low' | 'medium' | 'high' — triggers disclaimer injection in synthesizer."""

    fallback_triggered: bool
    """True if the agent fell back to a safe non-answer due to low confidence."""

    error: Optional[str]
    """Set by any node on failure. Causes routing to synthesizer for graceful error msg."""

    iteration_count: int
    """Guard against infinite loops in the graph (checked against MAX_ITERATIONS)."""


# ── Default initial state factory ─────────────────────────────────────────────
def initial_state(
    query: str,
    session_id: str,
    applicant_id: Optional[str] = None,
) -> LoanAdvisoryState:
    """
    Create a fresh state dict for a new query.
    All optional agent outputs start as None; defaults are set here.
    """
    return {
        # INPUT
        "query": query,
        "applicant_id": applicant_id,
        "session_id": session_id,
        # CLASSIFICATION
        "query_type": "general",
        "requires_agents": [],
        "query_entities": {},
        # RAG
        "retrieved_documents": [],
        "retrieval_confidence": 0.0,
        # AGENT OUTPUTS
        "employment_data": None,
        "credit_analysis": None,
        "fraud_assessment": None,
        "eligibility_result": None,
        "emi_details": None,
        # CONVERSATION
        "messages": [],
        # FINAL OUTPUT
        "final_response": "",
        "sources": [],
        "confidence_score": 0.0,
        # GUARDRAILS
        "hallucination_risk": "low",
        "fallback_triggered": False,
        "error": None,
        "iteration_count": 0,
    }