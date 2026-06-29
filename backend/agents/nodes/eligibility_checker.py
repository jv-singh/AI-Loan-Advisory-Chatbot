"""
backend/agents/nodes/eligibility_checker.py
────────────────────────────────────────────
Node 6: Eligibility Checker Agent

Responsibilities:
  1. Combine outputs from Employment, Credit, and Fraud agents
  2. Apply loan-type-specific policy rules (from retrieved_documents)
  3. Compute maximum eligible loan amount and best available rate
  4. Return a detailed eligibility verdict with reasons

Decision matrix (simplified):
  ┌─────────────────┬──────────────┬──────────────┬─────────────────────┐
  │ Credit Band     │ DTI          │ Fraud Risk   │ Decision            │
  ├─────────────────┼──────────────┼──────────────┼─────────────────────┤
  │ excellent/good  │ < 50%        │ low          │ Approved            │
  │ excellent/good  │ 50–60%       │ low/medium   │ Conditional         │
  │ fair            │ < 50%        │ low          │ Conditional + docs  │
  │ poor            │ any          │ any          │ Manual review       │
  │ very_poor       │ any          │ any          │ Rejected            │
  │ any             │ any          │ high         │ Rejected            │
  └─────────────────┴──────────────┴──────────────┴─────────────────────┘

In production: rules engine reads from loan_policies table / retrieved docs.
"""

from __future__ import annotations

import structlog
from backend.agents.state import LoanAdvisoryState

log = structlog.get_logger(__name__)

# ── Policy constants (should come from retrieved_documents in prod) ─────────────
LOAN_TYPE_RULES: dict[str, dict] = {
    "home": {
        "min_credit_score": 650,
        "max_dti": 0.50,
        "max_tenure_years": 30,
        "max_loan_multiplier": 80,   # % of property value
        "min_income": 25_000,
        "processing_fee_pct": 0.50,
    },
    "personal": {
        "min_credit_score": 700,
        "max_dti": 0.45,
        "max_tenure_years": 5,
        "max_loan_multiplier": 40,   # x monthly income
        "min_income": 20_000,
        "processing_fee_pct": 1.00,
    },
    "car": {
        "min_credit_score": 680,
        "max_dti": 0.50,
        "max_tenure_years": 7,
        "max_loan_multiplier": 36,
        "min_income": 20_000,
        "processing_fee_pct": 0.50,
    },
    "education": {
        "min_credit_score": 620,
        "max_dti": 0.55,
        "max_tenure_years": 15,
        "max_loan_multiplier": 50,
        "min_income": 0,  # co-applicant income
        "processing_fee_pct": 0.25,
    },
    "business": {
        "min_credit_score": 680,
        "max_dti": 0.55,
        "max_tenure_years": 10,
        "max_loan_multiplier": 60,
        "min_income": 30_000,
        "processing_fee_pct": 1.00,
    },
}
DEFAULT_RULES = LOAN_TYPE_RULES["personal"]


def _get_rules(loan_type: str | None) -> dict:
    return LOAN_TYPE_RULES.get((loan_type or "").lower(), DEFAULT_RULES)


def run(state: LoanAdvisoryState) -> dict:
    """
    Aggregates all agent results and delivers an eligibility verdict.

    Reads:  state["employment_data"], state["credit_analysis"],
            state["fraud_assessment"], state["query_entities"]
    Writes: state["eligibility_result"]
    """
    entities    = state.get("query_entities", {})
    employment  = state.get("employment_data", {}) or {}
    credit      = state.get("credit_analysis", {}) or {}
    fraud       = state.get("fraud_assessment", {}) or {}
    applicant_id = state.get("applicant_id")

    loan_type   = entities.get("loan_type", "personal")
    loan_amount = entities.get("loan_amount", 0)
    tenure_yrs  = entities.get("tenure_years", 5)
    rules       = _get_rules(loan_type)

    log.info("checking_eligibility", applicant_id=applicant_id, loan_type=loan_type)

    reasons: list[str]    = []
    conditions: list[str] = []
    is_eligible           = True

    # ── Hard stops ────────────────────────────────────────────────────────────
    if fraud.get("fraud_risk") == "high":
        return {
            "eligibility_result": {
                "is_eligible": False,
                "decision": "rejected",
                "reasons": ["Application flagged for high fraud risk. Manual review required."],
                "conditions": [],
                "max_loan_amount": 0,
                "interest_rate": 0,
            }
        }

    credit_score = credit.get("credit_score", 0)
    if credit_score > 0 and credit_score < rules["min_credit_score"]:
        is_eligible = False
        reasons.append(
            f"Credit score {credit_score} is below minimum {rules['min_credit_score']} "
            f"for {loan_type} loan."
        )

    monthly_income = employment.get("monthly_income", 0)
    if monthly_income < rules["min_income"]:
        is_eligible = False
        reasons.append(
            f"Monthly income ₹{monthly_income:,.0f} below minimum ₹{rules['min_income']:,} "
            f"for {loan_type} loan."
        )

    dti = credit.get("debt_to_income_ratio", 0)
    if dti > rules["max_dti"]:
        is_eligible = False
        reasons.append(
            f"Debt-to-income ratio {dti:.0%} exceeds maximum {rules['max_dti']:.0%}."
        )

    employment_status = employment.get("verification_status", "verified")
    if employment_status == "discrepancy":
        is_eligible = False
        reasons.append("Employment data discrepancy detected. Verification required.")

    # ── Soft conditions (approve with caveats) ────────────────────────────────
    if is_eligible:
        credit_band = credit.get("score_band", "good")
        if credit_band in ("fair", "poor"):
            conditions.append("Additional income proof (6-month bank statements) required")
        if fraud.get("fraud_risk") == "medium":
            conditions.append("Manual verification by underwriting team required")
        if tenure_yrs and tenure_yrs > rules["max_tenure_years"]:
            conditions.append(
                f"Requested tenure {tenure_yrs}yr exceeds max {rules['max_tenure_years']}yr; "
                f"tenure will be capped."
            )
            tenure_yrs = rules["max_tenure_years"]

        reasons.append(f"Credit profile is {credit_band} — eligible for {loan_type} loan.")

    # ── Compute limits ────────────────────────────────────────────────────────
    max_by_income = monthly_income * rules["max_loan_multiplier"]
    # If specific loan amount was requested, validate it
    if loan_amount and loan_amount > max_by_income:
        is_eligible = False
        reasons.append(
            f"Requested loan ₹{loan_amount:,.0f} exceeds maximum eligible "
            f"₹{max_by_income:,.0f} based on income."
        )

    interest_rate = credit.get("offered_rate", 9.0) if is_eligible else 0.0
    processing_fee = (loan_amount or max_by_income) * rules["processing_fee_pct"] / 100

    decision = "approved" if is_eligible and not conditions else \
               ("conditional" if is_eligible else "rejected")

    eligibility_result = {
        "applicant_id": applicant_id,
        "is_eligible": is_eligible,
        "decision": decision,
        "loan_type": loan_type,
        "max_loan_amount": round(max_by_income, 2) if is_eligible else 0,
        "requested_amount": loan_amount,
        "interest_rate": round(interest_rate, 2),
        "max_tenure_years": int(tenure_yrs or rules["max_tenure_years"]),
        "processing_fee": round(processing_fee, 2),
        "reasons": reasons,
        "conditions": conditions,
        "credit_score_used": credit_score,
        "income_considered": monthly_income,
    }

    log.info(
        "eligibility_determined",
        applicant_id=applicant_id,
        decision=decision,
        max_amount=eligibility_result["max_loan_amount"],
        rate=interest_rate,
    )

    return {"eligibility_result": eligibility_result}