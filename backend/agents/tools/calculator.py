"""
backend/agents/tools/calculator.py
────────────────────────────────────
LangGraph @tool wrappers for financial calculations.

Each function is decorated with @tool so it can be registered with a
chat model (Groq or OpenAI) for tool-calling. The underlying math is
identical to what emi_calculator.py and eligibility_checker.py perform —
extracted here so both nodes and a future ReAct agent share the same
implementation.
"""

from __future__ import annotations
from langchain_core.tools import tool


@tool
def compute_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> dict:
    """
    Calculate the monthly EMI for a loan using the reducing-balance formula.

    Args:
        principal: Loan amount in INR.
        annual_rate_pct: Annual interest rate as a percentage (e.g., 8.5 for 8.5%).
        tenure_months: Total number of monthly instalments.

    Returns:
        dict with monthly_emi, total_payment, total_interest, interest_percentage.
    """
    if principal <= 0 or tenure_months <= 0:
        return {"error": "Principal and tenure must be positive."}
    if annual_rate_pct == 0:
        emi = round(principal / tenure_months, 2)
        return {
            "monthly_emi": emi,
            "total_payment": round(emi * tenure_months, 2),
            "total_interest": 0.0,
            "interest_percentage": 0.0,
        }

    r = annual_rate_pct / 12 / 100
    emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    emi = round(emi, 2)
    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - principal, 2)

    return {
        "monthly_emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "interest_percentage": round(total_interest / principal * 100, 2),
    }


@tool
def compute_max_loan_amount(monthly_income: float, loan_type: str = "personal") -> dict:
    """
    Compute the maximum loan amount an applicant is eligible for based on income.

    Args:
        monthly_income: Verified monthly income in INR.
        loan_type: One of 'home', 'personal', 'car', 'education', 'business'.

    Returns:
        dict with max_loan_amount and the income_multiplier applied.
    """
    MULTIPLIERS = {
        "home":      80,
        "personal":  40,
        "car":       36,
        "education": 50,
        "business":  60,
    }
    multiplier = MULTIPLIERS.get(loan_type.lower(), 40)
    return {
        "max_loan_amount": round(monthly_income * multiplier, 2),
        "income_multiplier": multiplier,
        "loan_type": loan_type,
        "monthly_income_used": monthly_income,
    }


@tool
def compute_dti_ratio(monthly_debt_payments: float, monthly_income: float) -> dict:
    """
    Compute the Debt-to-Income (DTI) ratio.

    Args:
        monthly_debt_payments: Total existing monthly debt obligations in INR.
        monthly_income: Gross monthly income in INR.

    Returns:
        dict with dti_ratio (0–1), dti_percentage, and risk_flag.
    """
    if monthly_income <= 0:
        return {"error": "Monthly income must be positive.", "dti_ratio": 1.0}
    dti = monthly_debt_payments / monthly_income
    return {
        "dti_ratio": round(dti, 4),
        "dti_percentage": round(dti * 100, 2),
        "risk_flag": "high" if dti > 0.50 else "medium" if dti > 0.35 else "low",
    }