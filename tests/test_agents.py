"""
tests/test_agents.py
──────────────────────
Unit tests for each agent node using pure Python — no LLM calls needed.
Tests use synthetic state dicts to validate node logic in isolation.

Run:
  pytest tests/test_agents.py -v
  pytest tests/test_agents.py -v -k "emi"   ← run only EMI tests
"""

import pytest
from backend.agents.nodes import emi_calculator, eligibility_checker


# ── EMI Calculator Tests ──────────────────────────────────────────────────────

class TestEMICalculator:
    """Tests for emi_calculator.run() — pure math, no DB/LLM needed."""

    def _state(self, amount, rate, years, loan_type="personal"):
        return {
            "query": f"EMI for {amount}",
            "query_entities": {
                "loan_amount": amount,
                "interest_rate": rate,
                "tenure_years": years,
                "loan_type": loan_type,
            },
            "eligibility_result": None,
        }

    def test_basic_emi_calculation(self):
        """₹5,00,000 at 10% for 3 years → ~₹16,134/month."""
        state = self._state(500_000, 10.0, 3)
        result = emi_calculator.run(state)
        emi = result["emi_details"]["monthly_emi"]
        assert 16_000 < emi < 16_300, f"EMI out of expected range: {emi}"

    def test_emi_is_higher_with_higher_rate(self):
        """Higher interest rate must produce higher EMI."""
        low = emi_calculator.run(self._state(1_000_000, 8.0, 10))["emi_details"]["monthly_emi"]
        high = emi_calculator.run(self._state(1_000_000, 12.0, 10))["emi_details"]["monthly_emi"]
        assert high > low

    def test_emi_is_lower_with_longer_tenure(self):
        """Longer tenure must reduce monthly EMI."""
        short = emi_calculator.run(self._state(2_000_000, 9.0, 10))["emi_details"]["monthly_emi"]
        long_ = emi_calculator.run(self._state(2_000_000, 9.0, 20))["emi_details"]["monthly_emi"]
        assert long_ < short

    def test_total_interest_positive(self):
        """Total interest must always be positive."""
        result = emi_calculator.run(self._state(3_000_000, 8.5, 20))
        assert result["emi_details"]["total_interest"] > 0

    def test_total_repayment_equals_emi_times_months(self):
        """total_payment = EMI × tenure_months (within rounding tolerance)."""
        state = self._state(1_000_000, 9.5, 5)
        details = emi_calculator.run(state)["emi_details"]
        expected = details["monthly_emi"] * details["tenure_months"]
        assert abs(details["total_payment"] - expected) < 10  # ₹10 rounding tolerance

    def test_zero_loan_amount_returns_error(self):
        """Missing loan amount must return a helpful error, not crash."""
        state = self._state(0, 9.0, 5)
        result = emi_calculator.run(state)
        assert "error" in result["emi_details"]

    def test_amortization_schedule_length(self):
        """Schedule must have one entry per month."""
        state = self._state(500_000, 10.0, 3)  # 36 months
        details = emi_calculator.run(state)["emi_details"]
        assert len(details["amortization_schedule"]) == 36

    def test_last_month_balance_near_zero(self):
        """Remaining balance after final payment must be close to ₹0."""
        state = self._state(1_000_000, 9.0, 10)
        schedule = emi_calculator.run(state)["emi_details"]["amortization_schedule"]
        assert schedule[-1]["balance_remaining"] < 5  # ₹5 tolerance


# ── Eligibility Checker Tests ─────────────────────────────────────────────────

class TestEligibilityChecker:
    """Tests for eligibility_checker.run() — rule engine, no LLM/DB."""

    def _state(self, credit_score, income, dti, loan_type="personal",
                loan_amount=0, fraud_risk="low", employment_status="verified"):
        return {
            "applicant_id": "test-001",
            "query_entities": {
                "loan_type": loan_type,
                "loan_amount": loan_amount,
                "tenure_years": 5,
            },
            "employment_data": {
                "monthly_income": income,
                "years_employed": 3,
                "verification_status": employment_status,
            },
            "credit_analysis": {
                "credit_score": credit_score,
                "score_band": "good" if credit_score >= 700 else "fair" if credit_score >= 650 else "poor",
                "risk_level": "low" if credit_score >= 700 else "medium",
                "debt_to_income_ratio": dti,
                "offered_rate": 10.75,
                "defaults_count": 0,
            },
            "fraud_assessment": {
                "fraud_risk": fraud_risk,
                "flags": [],
            },
        }

    def test_eligible_applicant(self):
        """Strong profile (score 750, income 80k, DTI 30%) → approved."""
        result = eligibility_checker.run(self._state(750, 80_000, 0.30))
        assert result["eligibility_result"]["is_eligible"] is True
        assert result["eligibility_result"]["decision"] in ("approved", "conditional")

    def test_low_credit_score_rejected(self):
        """Credit score below personal loan minimum (700) → rejected."""
        result = eligibility_checker.run(self._state(650, 60_000, 0.30, loan_type="personal"))
        assert result["eligibility_result"]["is_eligible"] is False

    def test_high_dti_rejected(self):
        """DTI ratio 60% exceeds 50% max → rejected."""
        result = eligibility_checker.run(self._state(720, 50_000, 0.60))
        assert result["eligibility_result"]["is_eligible"] is False
        reasons_text = " ".join(result["eligibility_result"]["reasons"])
        assert "Debt-to-income" in reasons_text

    def test_high_fraud_risk_always_rejected(self):
        """High fraud risk must block approval regardless of credit score."""
        result = eligibility_checker.run(
            self._state(800, 100_000, 0.20, fraud_risk="high")
        )
        assert result["eligibility_result"]["is_eligible"] is False
        assert result["eligibility_result"]["decision"] == "rejected"

    def test_employment_discrepancy_blocks_approval(self):
        """Unresolved employment discrepancy → rejected."""
        result = eligibility_checker.run(
            self._state(730, 60_000, 0.30, employment_status="discrepancy")
        )
        assert result["eligibility_result"]["is_eligible"] is False

    def test_max_loan_amount_computed(self):
        """Eligible applicant gets a max_loan_amount > 0."""
        result = eligibility_checker.run(self._state(750, 80_000, 0.25))
        assert result["eligibility_result"]["max_loan_amount"] > 0

    def test_home_loan_has_lower_min_score_than_personal(self):
        """Home loan minimum (650) < Personal loan minimum (700)."""
        home_result = eligibility_checker.run(
            self._state(660, 50_000, 0.35, loan_type="home")
        )
        personal_result = eligibility_checker.run(
            self._state(660, 50_000, 0.35, loan_type="personal")
        )
        # Home loan should pass, personal should fail at score 660
        assert home_result["eligibility_result"]["is_eligible"] is True
        assert personal_result["eligibility_result"]["is_eligible"] is False

    def test_loan_amount_exceeding_income_limit_rejected(self):
        """Requested loan > 40x monthly income (personal limit) → rejected."""
        result = eligibility_checker.run(
            self._state(750, 30_000, 0.25, loan_amount=5_000_000)  # >166x income
        )
        assert result["eligibility_result"]["is_eligible"] is False


# ── Query Classifier Tests ────────────────────────────────────────────────────

class TestQueryClassifierMapping:
    """Tests for the AGENT_PIPELINES routing map (no LLM call)."""

    def test_eligibility_pipeline(self):
        from backend.agents.nodes.query_classifier import AGENT_PIPELINES
        pipeline = AGENT_PIPELINES["eligibility"]
        assert "employment_verifier" in pipeline
        assert "credit_scorer" in pipeline
        assert "eligibility_checker" in pipeline

    def test_emi_pipeline_is_isolated(self):
        from backend.agents.nodes.query_classifier import AGENT_PIPELINES
        pipeline = AGENT_PIPELINES["emi"]
        assert pipeline == ["emi_calculator"]

    def test_policy_pipeline_is_empty(self):
        from backend.agents.nodes.query_classifier import AGENT_PIPELINES
        assert AGENT_PIPELINES["policy"] == []
        assert AGENT_PIPELINES["general"] == []