"""
tests/conftest.py
──────────────────
Shared pytest fixtures. These build minimal state dicts and mock
database responses so agent node tests never need a live DB or LLM.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch


# ── State factories ────────────────────────────────────────────────────────────

@pytest.fixture
def base_state():
    """Minimal valid LoanAdvisoryState for testing individual nodes."""
    return {
        "query": "Am I eligible for a home loan?",
        "applicant_id": "test-applicant-001",
        "session_id": "test-session-001",
        "query_type": "eligibility",
        "requires_agents": ["employment_verifier", "credit_scorer", "fraud_detector", "eligibility_checker"],
        "query_entities": {"loan_type": "home", "loan_amount": 3_000_000, "tenure_years": 20},
        "retrieved_documents": [],
        "retrieval_confidence": 0.75,
        "employment_data": None,
        "credit_analysis": None,
        "fraud_assessment": None,
        "eligibility_result": None,
        "emi_details": None,
        "messages": [],
        "final_response": "",
        "sources": [],
        "confidence_score": 0.0,
        "hallucination_risk": "low",
        "fallback_triggered": False,
        "error": None,
        "iteration_count": 0,
    }


@pytest.fixture
def strong_applicant_state(base_state):
    """State with a fully verified, high-credit-score applicant."""
    state = base_state.copy()
    state.update({
        "employment_data": {
            "applicant_id": "test-applicant-001",
            "full_name": "Priya Sharma",
            "employer_name": "Infosys Ltd",
            "employment_type": "salaried",
            "monthly_income": 120_000.0,
            "annual_income": 1_440_000.0,
            "years_employed": 8.0,
            "max_eligible_loan": 7_200_000.0,
            "verification_status": "verified",
            "flags": [],
        },
        "credit_analysis": {
            "credit_score": 780,
            "score_band": "excellent",
            "risk_level": "low",
            "base_rate": 8.5,
            "rate_premium": 0.0,
            "offered_rate": 8.5,
            "debt_to_income_ratio": 0.22,
            "monthly_debt_payments": 26_400.0,
            "defaults_count": 0,
            "enquiries_last_6m": 1,
            "credit_history_years": 7.0,
            "flags": [],
            "remarks": "Auto-approve eligible",
        },
        "fraud_assessment": {
            "fraud_risk": "low",
            "risk_score": 0,
            "flags": [],
            "auto_approve": True,
            "requires_manual_review": False,
            "recent_application_count": 0,
        },
    })
    return state


@pytest.fixture
def weak_applicant_state(base_state):
    """State with a poor-credit, high-DTI applicant — should be rejected."""
    state = base_state.copy()
    state.update({
        "employment_data": {
            "monthly_income": 30_000.0,
            "years_employed": 0.5,
            "verification_status": "verified",
            "flags": [],
        },
        "credit_analysis": {
            "credit_score": 580,
            "score_band": "very_poor",
            "risk_level": "high",
            "offered_rate": 13.5,
            "debt_to_income_ratio": 0.62,
            "defaults_count": 2,
            "enquiries_last_6m": 7,
            "flags": ["2 loan default(s) on record", "DTI ratio 62% exceeds max 50%"],
        },
        "fraud_assessment": {
            "fraud_risk": "low",
            "risk_score": 10,
            "flags": [],
            "auto_approve": False,
            "requires_manual_review": False,
        },
    })
    return state


# ── Mock DB client ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_client():
    """
    Returns a MagicMock that mimics the Supabase client interface.
    Use in node tests that hit the database.

    Example:
        def test_employment(mock_db_client, base_state, monkeypatch):
            mock_db_client.table().select().eq().single().execute.return_value.data = {...}
            monkeypatch.setattr("backend.agents.nodes.employment_verifier.get_supabase_client",
                                lambda: mock_db_client)
    """
    client = MagicMock()
    # Chain returns self for the builder pattern
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.single.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.order.return_value = table_mock
    client.table.return_value = table_mock
    return client