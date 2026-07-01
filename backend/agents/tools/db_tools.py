"""
backend/agents/tools/db_tools.py
──────────────────────────────────
LangGraph @tool wrappers for database lookups.

In a ReAct-style agent these become callable tools the LLM can invoke.
In the current fixed-DAG architecture they serve as shared utilities
for the employment_verifier, credit_scorer, and fraud_detector nodes,
ensuring a single point of truth for DB query logic.
"""

from __future__ import annotations
import structlog
from langchain_core.tools import tool
from backend.database.supabase_client import get_supabase_client

log = structlog.get_logger(__name__)


@tool
def fetch_applicant_profile(applicant_id: str) -> dict:
    """
    Fetch an applicant's profile from the database.

    Args:
        applicant_id: The applicant's UUID.

    Returns:
        dict with full applicant profile, or error key on failure.
    """
    try:
        client = get_supabase_client()
        result = (
            client.table("applicants")
            .select(
                "id, full_name, employer_name, employment_type, designation, "
                "monthly_income, years_employed, city, state, residential_status"
            )
            .eq("id", applicant_id)
            .single()
            .execute()
        )
        return result.data or {"error": f"No applicant found: {applicant_id}"}
    except Exception as exc:
        log.error("fetch_applicant_failed", applicant_id=applicant_id, error=str(exc))
        return {"error": str(exc)}


@tool
def fetch_credit_bureau_record(applicant_id: str) -> dict:
    """
    Fetch the credit bureau record for an applicant.

    Args:
        applicant_id: The applicant's UUID.

    Returns:
        dict with credit score, DTI data, and history, or error key on failure.
    """
    try:
        client = get_supabase_client()
        result = (
            client.table("credit_bureau")
            .select(
                "applicant_id, credit_score, total_existing_loans, "
                "monthly_debt_payments, credit_history_years, "
                "defaults_count, enquiries_last_6m, score_last_updated"
            )
            .eq("applicant_id", applicant_id)
            .single()
            .execute()
        )
        return result.data or {"error": f"No credit record found: {applicant_id}"}
    except Exception as exc:
        log.error("fetch_credit_failed", applicant_id=applicant_id, error=str(exc))
        return {"error": str(exc)}


@tool
def fetch_loan_applications(applicant_id: str, limit: int = 10) -> dict:
    """
    Fetch recent loan applications for an applicant.

    Args:
        applicant_id: The applicant's UUID.
        limit: Maximum number of recent applications to return.

    Returns:
        dict with 'applications' list, or error key on failure.
    """
    try:
        client = get_supabase_client()
        result = (
            client.table("loan_applications")
            .select("id, loan_type, requested_amount, tenure_years, purpose, applied_at, status")
            .eq("applicant_id", applicant_id)
            .order("applied_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"applications": result.data or [], "count": len(result.data or [])}
    except Exception as exc:
        log.error("fetch_applications_failed", applicant_id=applicant_id, error=str(exc))
        return {"error": str(exc), "applications": []}