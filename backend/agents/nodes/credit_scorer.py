"""
backend/agents/nodes/credit_scorer.py
───────────────────────────────────────
Node 4: Credit Scoring Agent

Responsibilities:
  1. Fetch applicant's credit bureau data from database
  2. Apply multi-factor credit scoring model
  3. Compute debt-to-income (DTI) ratio
  4. Categorize into risk band and determine base interest rate

Scoring model (simplified CIBIL-aligned approach):
  Credit Score (300–900):
    750–900  → Excellent  → Prime rate        → auto-approve
    700–749  → Good       → Prime + 0.5%      → approve
    650–699  → Fair       → Prime + 1.5%      → conditional approve
    600–649  → Poor       → Prime + 3.0%      → manual review
    <600     → Very Poor  → reject / high rate → escalate

In production: integrates with CIBIL, Experian, or Equifax API.
In prototype: uses synthetic credit_bureau table in Supabase.
"""

from __future__ import annotations

import structlog
from backend.agents.state import LoanAdvisoryState
from backend.database.supabase_client import get_supabase_client

log = structlog.get_logger(__name__)

# ── Scoring configuration ──────────────────────────────────────────────────────
SCORE_BANDS = [
    (750, 900, "excellent", "low",    0.0,   "Auto-approve eligible"),
    (700, 749, "good",      "medium", 0.5,   "Approve with standard docs"),
    (650, 699, "fair",      "medium", 1.5,   "Conditional approval"),
    (600, 649, "poor",      "high",   3.0,   "Manual underwriting required"),
    (300, 599, "very_poor", "high",   5.0,   "High-risk: reject or secured loan only"),
]

BASE_INTEREST_RATE = 8.5  # % p.a. — updated from retrieved_documents in production
MAX_DTI_RATIO = 0.50      # 50% debt-to-income ceiling


def _classify_score(score: int) -> tuple[str, str, float, str]:
    """Returns (band, risk_level, rate_premium, remark)."""
    for low, high, band, risk, premium, remark in SCORE_BANDS:
        if low <= score <= high:
            return band, risk, premium, remark
    return "very_poor", "high", 5.0, "Score out of range"


def _compute_dti(monthly_debt_payments: float, monthly_income: float) -> float:
    """Debt-to-income ratio. Values above 0.5 trigger high-risk flag."""
    if monthly_income <= 0:
        return 1.0
    return monthly_debt_payments / monthly_income


def run(state: LoanAdvisoryState) -> dict:
    """
    Performs credit analysis for the applicant.

    Reads:  state["applicant_id"], state["employment_data"]
    Writes: state["credit_analysis"]
    """
    applicant_id = state.get("applicant_id")

    if not applicant_id:
        return {
            "credit_analysis": {
                "status": "skipped",
                "reason": "No applicant ID for credit check",
            }
        }

    log.info("scoring_credit", applicant_id=applicant_id)

    try:
        client = get_supabase_client()
        result = (
            client.table("credit_bureau")
            .select(
                "applicant_id, credit_score, total_existing_loans, "
                "monthly_debt_payments, credit_history_years, "
                "defaults_count, enquiries_last_6m"
            )
            .eq("applicant_id", applicant_id)
            .single()
            .execute()
        )

        if not result.data:
            log.warning("credit_record_not_found", applicant_id=applicant_id)
            return {
                "credit_analysis": {
                    "status": "missing",
                    "reason": "No credit bureau record found",
                    "score_band": "unscored",
                    "risk_level": "high",
                    "remarks": "First-time borrower or thin file",
                }
            }

        data = result.data
        credit_score = int(data.get("credit_score", 0))
        monthly_debt = float(data.get("monthly_debt_payments", 0))
        defaults = int(data.get("defaults_count", 0))
        enquiries = int(data.get("enquiries_last_6m", 0))
        history_years = float(data.get("credit_history_years", 0))

        # ── Classify score ─────────────────────────────────────────────────────
        band, risk_level, rate_premium, remark = _classify_score(credit_score)
        offered_rate = BASE_INTEREST_RATE + rate_premium

        # ── DTI ratio ─────────────────────────────────────────────────────────
        monthly_income = 0.0
        if emp := state.get("employment_data"):
            monthly_income = float(emp.get("monthly_income", 0))

        dti_ratio = _compute_dti(monthly_debt, monthly_income)

        # ── Negative flags ─────────────────────────────────────────────────────
        flags = []
        if defaults > 0:
            flags.append(f"{defaults} loan default(s) on record")
        if enquiries > 3:
            flags.append(f"{enquiries} credit enquiries in 6 months (possible credit hunger)")
        if dti_ratio > MAX_DTI_RATIO:
            flags.append(f"DTI ratio {dti_ratio:.0%} exceeds max {MAX_DTI_RATIO:.0%}")
        if history_years < 1:
            flags.append("Credit history less than 1 year")

        # Upgrade risk if serious flags
        if flags and risk_level != "high":
            risk_level = "medium" if risk_level == "low" else "high"

        credit_analysis = {
            "applicant_id": applicant_id,
            "credit_score": credit_score,
            "score_band": band,
            "risk_level": risk_level,
            "base_rate": BASE_INTEREST_RATE,
            "rate_premium": rate_premium,
            "offered_rate": round(offered_rate, 2),
            "debt_to_income_ratio": round(dti_ratio, 3),
            "monthly_debt_payments": monthly_debt,
            "defaults_count": defaults,
            "enquiries_last_6m": enquiries,
            "credit_history_years": history_years,
            "flags": flags,
            "remarks": remark,
        }

        log.info(
            "credit_scored",
            applicant_id=applicant_id,
            score=credit_score,
            band=band,
            risk=risk_level,
            dti=round(dti_ratio, 3),
        )

        return {"credit_analysis": credit_analysis}

    except Exception as exc:
        log.error("credit_scoring_failed", error=str(exc))
        return {
            "credit_analysis": {"status": "error", "reason": str(exc)},
            "error": f"Credit scoring error: {exc}",
        }