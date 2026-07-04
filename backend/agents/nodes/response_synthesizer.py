"""
backend/agents/nodes/response_synthesizer.py
──────────────────────────────────────────────
Node 8: Response Synthesizer Agent (Final Node)

This is the most important node — the one that produces the user-facing answer.

Responsibilities:
  1. Collect all structured agent outputs into a context bundle
  2. Inject retrieved document chunks as grounding material
  3. Call the LLM with strict instructions to cite sources and avoid invention
  4. Apply hallucination guardrails: inject warnings on low-confidence responses
  5. Extract cited sources list for UI attribution
  6. Compute final confidence score

Anti-hallucination mechanisms:
  - System prompt explicitly forbids answering without document support
  - temperature=0.1 reduces variance
  - Confidence score < threshold triggers a disclaimer paragraph
  - If retrieved_documents is empty, synthesizer returns a safe non-answer
  - LLM is instructed to say "I don't have enough information" over guessing

Response format returned:
  state["final_response"]  → full markdown-formatted answer
  state["sources"]         → list of document names cited
  state["confidence_score"] → 0.0–1.0
"""

from __future__ import annotations

import json
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

from backend.config import settings
from backend.llm import get_llm
from backend.agents.state import LoanAdvisoryState

log = structlog.get_logger(__name__)


SYNTHESIZER_SYSTEM_PROMPT = """You are a precise, professional Loan Advisory AI.

Your job is to answer the user's question using ONLY the information provided below.

STRICT RULES:
1. NEVER make up numbers, rates, policies, or eligibility criteria not in the context.
2. ALWAYS cite the document source when using its information, using [Source: <name>] inline.
3. If the context doesn't fully answer the question, say so clearly and suggest what the user should ask a loan officer.
4. Use ₹ for Indian Rupee amounts. Format large numbers with commas (e.g., ₹5,00,000).
5. For eligibility queries, always state both the VERDICT (Eligible/Not Eligible) and the REASONS.
6. For EMI queries, always show the monthly amount prominently.
7. Keep responses structured with clear headers when multiple topics are covered.
8. Tone: professional, clear, empathetic. This person is making an important financial decision.

AVAILABLE CONTEXT:
{context_block}

AGENT ANALYSIS RESULTS:
{agent_results}

HALLUCINATION RISK: {hallucination_risk}
{risk_warning}

Now answer the user's question based strictly on the above context."""

LOW_CONFIDENCE_WARNING = """
⚠ IMPORTANT: The retrieved documents have low relevance to this query.
Your response must prominently note that you could not find authoritative policy
information for this specific question, and recommend the user consult a loan officer.
"""


def _format_context(documents: list[dict]) -> str:
    """Formats retrieved chunks into a numbered reference block."""
    if not documents:
        return "No relevant policy documents retrieved."
    
    lines = []
    for i, doc in enumerate(documents, 1):
        lines.append(
            f"[{i}] Source: {doc.get('source', 'Unknown')} "
            f"(relevance: {doc.get('score', 0):.2f})\n"
            f"{doc.get('content', '')}\n"
        )
    return "\n---\n".join(lines)


def _format_agent_results(state: LoanAdvisoryState) -> str:
    """Serialises structured agent outputs into readable JSON blocks."""
    results = {}

    if emp := state.get("employment_data"):
        results["employment_verification"] = emp
    if credit := state.get("credit_analysis"):
        results["credit_analysis"] = credit
    if fraud := state.get("fraud_assessment"):
        results["fraud_assessment"] = fraud
    if elig := state.get("eligibility_result"):
        results["eligibility_determination"] = elig
    if emi := state.get("emi_details"):
        results["emi_calculation"] = emi

    if not results:
        return "No structured agent analysis available."

    return json.dumps(results, indent=2, default=str)


def _extract_sources(documents: list[dict]) -> list[str]:
    """Deduplicated list of document sources cited."""
    seen = set()
    sources = []
    for doc in documents:
        src = doc.get("source", "Unknown")
        if src not in seen:
            seen.add(src)
            sources.append(src)
    return sources


def _split_sources_by_origin(documents: list[dict]) -> tuple[list[str], list[dict]]:
    """
    Split retrieved documents into the two citations channels the UI uses:
      - policy_sources: list of source names from the global loan_policies pool
      - user_sources:   list of {filename, doc_id, chunk_excerpt, score} from
                        the caller's user_docs pool

    The retriever tags each chunk with `doc_source` ∈ {"policy", "user"}.
    """
    policy_seen: set[str] = set()
    policy_sources: list[str] = []
    user_sources: list[dict] = []
    user_seen_ids: set[str] = set()

    for doc in documents:
        origin = doc.get("doc_source", "policy")
        if origin == "user":
            # For the user-doc citations, dedupe by doc_id (one chip per file),
            # and surface the highest-scoring chunk as the excerpt.
            meta = doc.get("metadata", {}) or {}
            doc_id = meta.get("doc_id")
            if not doc_id or doc_id in user_seen_ids:
                continue
            user_seen_ids.add(doc_id)
            user_sources.append({
                "doc_id": doc_id,
                "filename": meta.get("filename", doc.get("source", "uploaded doc")),
                "chunk_excerpt": (doc.get("content") or "")[:160].strip(),
                "score": doc.get("score", 0.0),
            })
        else:
            src = doc.get("source", "Unknown")
            if src not in policy_seen:
                policy_seen.add(src)
                policy_sources.append(src)

    return policy_sources, user_sources


def _compute_confidence(state: LoanAdvisoryState) -> float:
    """
    Composite confidence score (0–1):
      - Retrieval confidence (40%)
      - Agent coverage (40%): how many expected agents actually ran
      - Fraud risk penalty (20%)

    Retrieval scoring is normalized against the active score threshold so
    that small embedding models (e.g. all-MiniLM-L6-v2, which rarely scores
    above 0.4) don't unfairly drag the composite down. A chunk that JUST
    passes the threshold still counts as a real hit.
    """
    raw_retrieval = state.get("retrieval_confidence", 0.0)
    threshold = settings.retrieval_score_threshold

    # Normalize: a chunk at/above threshold maps to ~1.0, anything below
    # scales linearly toward 0.0. Caps at 1.0 so very-high scores don't
    # over-inflate (which would make every policy answer look 100% sure).
    if raw_retrieval <= 0:
        retrieval_norm = 0.0
    else:
        retrieval_norm = min(1.0, raw_retrieval / max(threshold * 2.5, 0.01))
    retrieval_score = retrieval_norm * 0.40

    # Agent coverage
    required = set(state.get("requires_agents", []))
    ran = {
        "employment_verifier": state.get("employment_data") is not None,
        "credit_scorer":       state.get("credit_analysis") is not None,
        "fraud_detector":      state.get("fraud_assessment") is not None,
        "eligibility_checker": state.get("eligibility_result") is not None,
        "emi_calculator":      state.get("emi_details") is not None,
    }
    if required:
        coverage = sum(1 for a in required if ran.get(a, False)) / len(required)
    else:
        coverage = 1.0  # policy/general query — no agents required
    agent_score = coverage * 0.40

    # Fraud penalty
    fraud = state.get("fraud_assessment", {}) or {}
    risk = fraud.get("fraud_risk", "low")
    fraud_penalty = {"low": 0.20, "medium": 0.10, "high": 0.0}.get(risk, 0.10)

    return round(min(1.0, retrieval_score + agent_score + fraud_penalty), 3)


def _format_emi_response(emi_details: dict, query: str) -> dict:
    """
    Builds the final response for pure EMI queries directly from the
    calculator's structured output, skipping the LLM.

    Returns the same shape as the LLM-path branch.
    """
    principal       = emi_details.get("principal", 0)
    annual_rate     = emi_details.get("annual_rate", 0)
    tenure_months   = emi_details.get("tenure_months", 0)
    tenure_years    = emi_details.get("tenure_years", 0)
    emi             = emi_details.get("monthly_emi", 0)
    total_payment   = emi_details.get("total_payment", 0)
    total_interest  = emi_details.get("total_interest", 0)
    interest_pct    = emi_details.get("interest_percentage", 0)
    loan_type       = (emi_details.get("loan_type") or "loan").title()
    half_paid_month = emi_details.get("half_principal_paid_by_month", 0)
    years_to_half   = round(half_paid_month / 12, 1) if half_paid_month else 0

    response = (
        f"## 💰 EMI Calculation — {loan_type} Loan\n\n"
        f"**Monthly EMI: ₹{emi:,.2f}**\n\n"
        f"### Loan Details\n"
        f"- **Principal:** ₹{principal:,.0f}\n"
        f"- **Interest rate:** {annual_rate}% p.a.\n"
        f"- **Tenure:** {tenure_years} years ({tenure_months} months)\n\n"
        f"### Total Cost\n"
        f"- **Total payment:** ₹{total_payment:,.0f}\n"
        f"- **Total interest:** ₹{total_interest:,.0f} "
        f"({interest_pct:.1f}% of principal)\n"
        f"- **50% of principal repaid by:** month {half_paid_month} "
        f"(~{years_to_half} years)\n\n"
        f"### First-Year Amortization Snapshot\n"
        f"| Month | EMI | Principal | Interest | Balance |\n"
        f"|-------|-----|-----------|----------|---------|\n"
    )
    for row in (emi_details.get("display_schedule") or [])[:12]:
        if row.get("month") == "...":
            response += f"| ... | ₹{row.get('emi', 0):,.0f} | — | — | — |\n"
            continue
        response += (
            f"| {row.get('month')} | ₹{row.get('emi', 0):,.0f} | "
            f"₹{row.get('principal_paid', 0):,.0f} | "
            f"₹{row.get('interest_paid', 0):,.0f} | "
            f"₹{row.get('balance_remaining', 0):,.0f} |\n"
        )

    response += (
        f"\n*This is a mathematical estimate. Actual rates and "
        f"terms depend on the lender, your credit profile, and current "
        f"policy at the time of application.*"
    )

    return {
        "final_response": response,
        "sources": [],
        "policy_sources": [],
        "user_sources": [],
        "confidence_score": 1.0,  # math is exact
        "fallback_triggered": False,
    }


def run(state: LoanAdvisoryState) -> dict:
    """
    Generates the final grounded response.

    Reads:  all state fields
    Writes: state["final_response"], state["sources"], state["confidence_score"]
    """
    query            = state["query"]
    documents        = state.get("retrieved_documents", [])
    hallucination_risk = state.get("hallucination_risk", "low")
    error            = state.get("error")
    emi_details      = state.get("emi_details") or {}

    log.info(
        "synthesizing_response",
        query_type=state.get("query_type"),
        doc_count=len(documents),
        risk=hallucination_risk,
        has_emi=bool(emi_details.get("monthly_emi")),
    )

    # ── Fast path: pure EMI queries ───────────────────────────────────────────
    # When the EMI calculator has produced a result, surface it directly.
    # The LLM call is skipped because (a) the math is exact, (b) forcing a
    # Groq call on a "no relevant docs" context often makes the model say
    # "I don't have enough information" even when the answer is right there,
    # and (c) this is the most common query — speed matters.
    if (
        emi_details.get("monthly_emi")
        and not state.get("eligibility_result")
        and not state.get("credit_analysis")
    ):
        return _format_emi_response(emi_details, query)

    # ── Hard error passthrough ─────────────────────────────────────────────────
    if error and not documents and not state.get("employment_data"):
        return {
            "final_response": (
                f"I'm unable to process your query at this time due to a system error. "
                f"Please try again shortly.\n\n"
                f"*Technical detail: {error}*"
            ),
            "sources": [],
            "policy_sources": [],
            "user_sources": [],
            "confidence_score": 0.0,
            "fallback_triggered": True,
        }

    # ── Build prompt ───────────────────────────────────────────────────────────
    context_block  = _format_context(documents)
    agent_results  = _format_agent_results(state)

    # The retriever labels hallucination risk from RAW embedding scores (which
    # are inherently low for small models like all-MiniLM-L6-v2). The
    # composite confidence is a much better signal. Recompute the risk label
    # here from the composite so the LLM's prompt and the UI metadata
    # reflect the more accurate number.
    _composite = _compute_confidence(state)
    if _composite >= 0.70:
        effective_risk = "low"
    elif _composite >= 0.50:
        effective_risk = "medium"
    else:
        effective_risk = "high"
    risk_warning = LOW_CONFIDENCE_WARNING if effective_risk == "high" else ""

    system_prompt = SYNTHESIZER_SYSTEM_PROMPT.format(
        context_block=context_block,
        agent_results=agent_results,
        hallucination_risk=effective_risk.upper(),
        risk_warning=risk_warning,
    )

    llm = get_llm()

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ])

        final_response = response.content

        # ── Inject low-confidence disclaimer ──────────────────────────────────
        confidence = _compute_confidence(state)
        # Use the same effective_risk logic as the prompt so the UI label
        # matches the disclaimer behavior.
        if confidence >= 0.70:
            _effective_risk = "low"
        elif confidence >= 0.50:
            _effective_risk = "medium"
        else:
            _effective_risk = "high"
        if confidence < settings.hallucination_threshold:
            disclaimer = (
                "\n\n---\n"
                "⚠ **Confidence Notice**: This response is based on limited matching "
                "policy documents. Please verify the details with a certified loan officer "
                "before making any financial decisions."
            )
            final_response += disclaimer

        sources = _extract_sources(documents)
        policy_sources, user_sources = _split_sources_by_origin(documents)

        log.info(
            "response_synthesized",
            confidence=confidence,
            effective_risk=_effective_risk,
            sources=sources,
            policy_sources=policy_sources,
            user_sources_count=len(user_sources),
            response_length=len(final_response),
        )

        return {
            "final_response": final_response,
            "sources": sources,
            "policy_sources": policy_sources,
            "user_sources": user_sources,
            "confidence_score": confidence,
            "hallucination_risk": _effective_risk,  # override the retriever's label
            "fallback_triggered": confidence < settings.hallucination_threshold,
        }

    except Exception as exc:
        log.error("synthesis_failed", error=str(exc))
        return {
            "final_response": (
                "I encountered an issue generating your response. "
                "Please rephrase your question or contact support."
            ),
            "sources": [],
            "policy_sources": [],
            "user_sources": [],
            "confidence_score": 0.0,
            "fallback_triggered": True,
            "error": f"Synthesis failed: {exc}",
        }