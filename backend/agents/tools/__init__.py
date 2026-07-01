"""
backend/agents/tools/__init__.py
──────────────────────────────────
LangGraph-compatible @tool callables.

These tools wrap the deterministic math and DB logic from the agent nodes
so they can be used by a ReAct-style tool-calling agent in future iterations
without rewriting any business logic.

Current usage: imported by nodes for shared utilities.
Future usage:  bind to a chat model (Groq or OpenAI) via .bind_tools([...])
               and let the LLM decide which tools to call rather than
               following a fixed DAG.
"""

from .calculator import (
    compute_emi,
    compute_max_loan_amount,
    compute_dti_ratio,
)
from .db_tools import (
    fetch_applicant_profile,
    fetch_credit_bureau_record,
    fetch_loan_applications,
)

__all__ = [
    "compute_emi",
    "compute_max_loan_amount",
    "compute_dti_ratio",
    "fetch_applicant_profile",
    "fetch_credit_bureau_record",
    "fetch_loan_applications",
]