"""
backend/agents/nodes/emi_calculator.py
────────────────────────────────────────
Node 7: EMI Calculator Agent

Responsibilities:
  1. Extract loan parameters from query entities or eligibility result
  2. Apply the standard reducing-balance EMI formula
  3. Generate a full amortization schedule (month-by-month breakdown)
  4. Compute total interest, effective cost, and prepayment guidance

Formula:
  EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)

  Where:
    P = Principal (loan amount)
    r = Monthly interest rate (annual_rate / 12 / 100)
    n = Number of monthly installments (tenure_years × 12)

This node runs standalone for EMI queries, or after eligibility_checker
when the user asks "what will my EMI be?"
"""

from __future__ import annotations

import math
import structlog
from backend.agents.state import LoanAdvisoryState

log = structlog.get_logger(__name__)


def _compute_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Standard reducing-balance EMI calculation."""
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    if annual_rate == 0:
        return principal / tenure_months

    monthly_rate = annual_rate / 12 / 100
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months
    emi /= (1 + monthly_rate) ** tenure_months - 1
    return round(emi, 2)


def _amortization_schedule(
    principal: float, annual_rate: float, tenure_months: int
) -> list[dict]:
    """
    Full month-by-month amortization schedule.
    Returns first 12 months + last month for readability.
    Full schedule stored for completeness.
    """
    monthly_rate = annual_rate / 12 / 100
    emi = _compute_emi(principal, annual_rate, tenure_months)
    balance = principal
    schedule = []

    for month in range(1, tenure_months + 1):
        interest_component = round(balance * monthly_rate, 2)
        principal_component = round(emi - interest_component, 2)
        balance = round(max(0, balance - principal_component), 2)

        schedule.append({
            "month": month,
            "emi": emi,
            "principal_paid": principal_component,
            "interest_paid": interest_component,
            "balance_remaining": balance,
        })

    return schedule


def run(state: LoanAdvisoryState) -> dict:
    """
    Calculates EMI and amortization for the loan parameters in the query.

    Reads:  state["query_entities"], state["eligibility_result"]
    Writes: state["emi_details"]
    """
    entities = state.get("query_entities", {})
    eligibility = state.get("eligibility_result", {}) or {}

    # Resolve loan parameters — eligibility result takes precedence
    principal = (
        entities.get("loan_amount")
        or eligibility.get("requested_amount")
        or eligibility.get("max_loan_amount")
        or 0
    )
    tenure_years = (
        entities.get("tenure_years")
        or eligibility.get("max_tenure_years")
        or 5
    )
    tenure_months = entities.get("tenure_months") or int(tenure_years * 12)
    annual_rate = (
        entities.get("interest_rate")
        or eligibility.get("interest_rate")
        or 9.5   # default fallback rate
    )

    loan_type = entities.get("loan_type", "personal")

    if principal <= 0:
        return {
            "emi_details": {
                "error": (
                    "Loan amount not specified. Please provide the loan amount "
                    "to calculate EMI."
                )
            }
        }

    log.info(
        "calculating_emi",
        principal=principal,
        rate=annual_rate,
        tenure_months=tenure_months,
    )

    emi = _compute_emi(principal, annual_rate, tenure_months)
    schedule = _amortization_schedule(principal, annual_rate, tenure_months)

    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - principal, 2)
    interest_pct = round(total_interest / principal * 100, 2)

    # ── Breakeven / prepayment insight ────────────────────────────────────────
    # Month at which >50% of principal is repaid
    half_paid_month = next(
        (s["month"] for s in schedule if s["balance_remaining"] <= principal / 2),
        tenure_months,
    )

    # ── Summary schedule for UI (first 12 + last) ─────────────────────────────
    display_schedule = schedule[:12]
    if tenure_months > 12:
        display_schedule.append({"month": "...", "emi": emi, "note": "intermediate months"})
        display_schedule.append(schedule[-1])

    emi_details = {
        "loan_type": loan_type,
        "principal": principal,
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
        "tenure_years": round(tenure_months / 12, 1),
        "monthly_emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "interest_percentage": interest_pct,
        "half_principal_paid_by_month": half_paid_month,
        "amortization_schedule": schedule,         # full schedule
        "display_schedule": display_schedule,       # for UI/synthesis
        "breakdown_summary": (
            f"For a ₹{principal:,.0f} {loan_type} loan at {annual_rate}% p.a. "
            f"over {tenure_months} months:\n"
            f"  • Monthly EMI: ₹{emi:,.2f}\n"
            f"  • Total interest paid: ₹{total_interest:,.2f} ({interest_pct:.1f}% of principal)\n"
            f"  • Total repayment: ₹{total_payment:,.2f}\n"
            f"  • 50% principal repaid by month {half_paid_month}"
        ),
    }

    log.info(
        "emi_calculated",
        emi=emi,
        total_interest=total_interest,
        tenure_months=tenure_months,
    )

    return {"emi_details": emi_details}