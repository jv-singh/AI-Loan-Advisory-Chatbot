"""
backend/agents/nodes/query_classifier.py
──────────────────────────────────────────
Node 1: Query Classifier Agent

Responsibilities:
  1. Classify the user's intent into one of 5 query types
  2. Extract financial entities (loan_amount, tenure, loan_type, etc.)
  3. Determine which downstream agents are required
  4. Set the `requires_agents` list that drives graph routing

This is the CHEAPEST node — uses a fast structured output call with
minimal tokens. No RAG needed here.

Query types:
  eligibility   → full pipeline (employment → credit → fraud → eligibility)
  emi           → EMI calculator only
  policy        → RAG + synthesizer (no agent pipeline)
  fraud_check   → credit + fraud pipeline
  general       → RAG + synthesizer (no agent pipeline)
"""

from __future__ import annotations

import json
import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings
from backend.llm import get_llm
from backend.agents.state import LoanAdvisoryState

log = structlog.get_logger(__name__)

# ── Agent routing map ─────────────────────────────────────────────────────────
AGENT_PIPELINES: dict[str, list[str]] = {
    "eligibility":  ["employment_verifier", "credit_scorer", "fraud_detector", "eligibility_checker"],
    "emi":          ["emi_calculator"],
    "fraud_check":  ["credit_scorer", "fraud_detector"],
    "policy":       [],   # RAG + synthesis only
    "general":      [],   # RAG + synthesis only
}

CLASSIFIER_SYSTEM_PROMPT = """You are a financial query classifier for a loan advisory system.

Classify the user's query into exactly one of these types:
- eligibility: questions about whether someone qualifies for a loan
- emi: questions about monthly installments, payment amounts, or repayment schedules
- policy: questions about loan rules, interest rates, documentation requirements
- fraud_check: requests to verify or flag suspicious applicant information
- general: any other loan-related question

Also extract financial entities mentioned in the query.

Respond ONLY with valid JSON in this exact format:
{
  "query_type": "<type>",
  "confidence": <0.0-1.0>,
  "requires_applicant_data": <true|false>,
  "entities": {
    "loan_amount": <number or null>,
    "tenure_years": <number or null>,
    "tenure_months": <number or null>,
    "interest_rate": <number or null>,
    "loan_type": "<home|personal|car|business|education or null>",
    "applicant_age": <number or null>,
    "monthly_income": <number or null>,
    "credit_score": <number or null>,
    "down_payment": <number or null>
  },
  "reasoning": "<one sentence>"
}

No markdown. No explanation. JSON only."""


def run(state: LoanAdvisoryState) -> dict:
    """
    Classifies the query and sets routing metadata.

    Reads:  state["query"]
    Writes: state["query_type"], state["requires_agents"], state["query_entities"]
    """
    query = state["query"]
    log.info("classifying_query", query=query[:80])

    llm = get_llm(temperature=0.0)  # deterministic classification

    try:
        response = llm.invoke([
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=f"Query: {query}"),
        ])

        raw = response.content.strip()
        # Strip markdown fences if model adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        
        parsed = json.loads(raw)
        query_type = parsed.get("query_type", "general")
        entities = parsed.get("entities", {})
        # Remove null values
        entities = {k: v for k, v in entities.items() if v is not None}

        requires_agents = AGENT_PIPELINES.get(query_type, [])

        log.info(
            "query_classified",
            type=query_type,
            confidence=parsed.get("confidence"),
            entities=entities,
            agents_required=requires_agents,
        )

        return {
            "query_type": query_type,
            "requires_agents": requires_agents,
            "query_entities": entities,
        }

    except (json.JSONDecodeError, KeyError) as exc:
        log.warning("classifier_parse_failed", error=str(exc), fallback="general")
        return {
            "query_type": "general",
            "requires_agents": [],
            "query_entities": {},
        }
    except Exception as exc:
        log.error("classifier_failed", error=str(exc))
        return {
            "query_type": "general",
            "requires_agents": [],
            "query_entities": {},
            "error": f"Classification failed: {exc}",
        }