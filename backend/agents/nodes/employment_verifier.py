"""
backend/agents/nodes/employment_verifier.py
─────────────────────────────────────────────
Node 3: Employment Verification Agent

Responsibilities:
  1. Fetch applicant's stated employment data from database
  2. Cross-check income figures against loan policy limits
  3. Flag discrepancies between declared and verified income
  4. Return structured employment verdict for downstream agents

In production: integrates with payroll APIs, employer verification
services, or income tax return (ITR) data.
In prototype: uses synthetic applicant records from Supabase/local DB.

Verification statuses:
  verified        → all checks pass
  unverified      → data present but external verification not available
  discrepancy     → mismatch detected between declared vs computed values
  missing_data    → no employment record found for applicant_id
"""

from __future__ import annotations

import structlog
from backend.agents.state import LoanAdvisoryState
from backend.database.supabase_client import get_supabase_client

log = structlog.get_logger(__name__)

# Policy constants (source: retrieved_documents in production)
MIN_EMPLOYMENT_YEARS = 1
MIN_MONTHLY_INCOME = 15_000   # INR
INCOME_MULTIPLIER_MAX = 60    # max loan = 60x monthly income


def _compute_income_discrepancy(declared: float, computed: float) -> float:
    """Returns percentage difference between declared and computed income."""
    if computed == 0:
        return 100.0
    return abs(declared - computed) / computed * 100


def run(state: LoanAdvisoryState) -> dict:
    """
    Verifies employment data for the applicant in the query.

    Reads:  state["applicant_id"], state["query_entities"]
    Writes: state["employment_data"]
    """
    applicant_id = state.get("applicant_id")

    if not applicant_id:
        log.info("no_applicant_id_skipping_employment_check")
        return {
            "employment_data": {
                "verification_status": "skipped",
                "reason": "No applicant ID provided; policy-level query",
            }
        }

    log.info("verifying_employment", applicant_id=applicant_id)

    try:
        # ── Fetch from database ────────────────────────────────────────────────
        client = get_supabase_client()
        result = (
            client.table("applicants")
            .select(
                "id, full_name, employer_name, employment_type, "
                "monthly_income, years_employed, designation"
            )
            .eq("id", applicant_id)
            .single()
            .execute()
        )

        if not result.data:
            log.warning("applicant_not_found", applicant_id=applicant_id)
            return {
                "employment_data": {
                    "verification_status": "missing_data",
                    "reason": f"No record found for applicant_id={applicant_id}",
                }
            }

        applicant = result.data
        monthly_income = float(applicant.get("monthly_income", 0))
        years_employed = float(applicant.get("years_employed", 0))
        employment_type = applicant.get("employment_type", "unknown")

        # ── Validation checks ──────────────────────────────────────────────────
        flags = []

        if monthly_income < MIN_MONTHLY_INCOME:
            flags.append(f"Income ₹{monthly_income:,.0f} below minimum ₹{MIN_MONTHLY_INCOME:,}")

        if years_employed < MIN_EMPLOYMENT_YEARS:
            flags.append(
                f"Employment duration {years_employed:.1f}yr below "
                f"required {MIN_EMPLOYMENT_YEARS}yr"
            )

        # Check against query-declared income if provided
        declared_income = state.get("query_entities", {}).get("monthly_income")
        if declared_income and declared_income > 0:
            discrepancy_pct = _compute_income_discrepancy(declared_income, monthly_income)
            if discrepancy_pct > 20:
                flags.append(
                    f"Declared income ₹{declared_income:,.0f} differs "
                    f"{discrepancy_pct:.1f}% from records"
                )

        # ── Determine status ───────────────────────────────────────────────────
        if flags:
            verification_status = "discrepancy"
        elif employment_type in ("salaried", "self_employed_professional"):
            verification_status = "verified"
        else:
            verification_status = "unverified"

        employment_data = {
            "applicant_id": applicant_id,
            "full_name": applicant.get("full_name"),
            "employer_name": applicant.get("employer_name"),
            "employment_type": employment_type,
            "designation": applicant.get("designation"),
            "monthly_income": monthly_income,
            "annual_income": monthly_income * 12,
            "years_employed": years_employed,
            "max_eligible_loan": monthly_income * INCOME_MULTIPLIER_MAX,
            "verification_status": verification_status,
            "flags": flags,
        }

        log.info(
            "employment_verified",
            applicant_id=applicant_id,
            status=verification_status,
            flags_count=len(flags),
        )

        return {"employment_data": employment_data}

    except Exception as exc:
        log.error("employment_verification_failed", error=str(exc))
        return {
            "employment_data": {
                "verification_status": "error",
                "reason": str(exc),
            },
            "error": f"Employment verification error: {exc}",
        }