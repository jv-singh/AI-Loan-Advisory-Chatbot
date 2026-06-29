"""
backend/agents/nodes/fraud_detector.py
───────────────────────────────────────
Node 5: Fraud Detection Agent

Responsibilities:
  1. Run rule-based anomaly detection on applicant data
  2. Cross-check declared income against credit bureau records
  3. Flag suspicious patterns (e.g., multiple applications, sudden income jumps)
  4. Return risk verdict: low / medium / high

In production: integrates with ML fraud model, bureau shared-fraud databases,
government ID verification APIs (Aadhaar, PAN).
In prototype: deterministic rule engine on synthetic applicant data.

Detection categories:
  - Income fraud:     declared income vs bureau data mismatch
  - Identity fraud:   name/DOB inconsistencies across records
  - Collusion risk:   same employer + same guarantor across multiple apps
  - Application fraud:multiple applications in short window
  - Document fraud:   inconsistencies in submitted documents (TODO: NLP check)
"""

from __future__ import annotations

import structlog
from backend.agents.state import LoanAdvisoryState
from backend.database.supabase_client import get_supabase_client

log = structlog.get_logger(__name__)

# ── Fraud rule thresholds ──────────────────────────────────────────────────────
MAX_INCOME_MISMATCH_PCT  = 25   # beyond this → income fraud flag
MAX_APPS_IN_30_DAYS      = 2    # more than this → application fraud
MIN_EMPLOYER_TENURE_FOR_HIGH_LOAN = 2  # years; short tenure + big loan = flag
HIGH_LOAN_INCOME_MULTIPLIER_THRESHOLD = 55  # loan > 55x income = suspicious


def _income_mismatch_pct(declared: float, bureau: float) -> float:
    if bureau == 0:
        return 100.0
    return abs(declared - bureau) / bureau * 100


def run(state: LoanAdvisoryState) -> dict:
    """
    Runs fraud detection checks on the applicant.

    Reads:  state["applicant_id"], state["employment_data"], state["credit_analysis"]
    Writes: state["fraud_assessment"]
    """
    applicant_id = state.get("applicant_id")

    if not applicant_id:
        return {
            "fraud_assessment": {
                "fraud_risk": "low",
                "flags": [],
                "auto_approve": True,
                "requires_manual_review": False,
                "reason": "Policy query; no fraud check needed",
            }
        }

    log.info("running_fraud_detection", applicant_id=applicant_id)

    flags: list[str] = []
    risk_score = 0  # points accumulate; threshold determines verdict

    try:
        client = get_supabase_client()

        # ── Load application history ───────────────────────────────────────────
        apps_result = (
            client.table("loan_applications")
            .select("id, applied_at, loan_amount, status")
            .eq("applicant_id", applicant_id)
            .order("applied_at", desc=True)
            .limit(10)
            .execute()
        )
        recent_apps = apps_result.data or []

        # Rule: multiple applications in 30 days
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)
        recent_count = sum(
            1 for app in recent_apps
            if app.get("applied_at") and
            datetime.fromisoformat(app["applied_at"].replace("Z", "+00:00")) > cutoff
        )
        if recent_count > MAX_APPS_IN_30_DAYS:
            flags.append(f"⚠ {recent_count} applications submitted in last 30 days")
            risk_score += 30

        # ── Cross-check income ─────────────────────────────────────────────────
        emp = state.get("employment_data") or {}
        credit = state.get("credit_analysis") or {}

        declared_income = emp.get("monthly_income", 0)
        entities = state.get("query_entities", {})
        query_declared_income = entities.get("monthly_income", 0)
        bureau_dti = credit.get("debt_to_income_ratio", 0)

        if query_declared_income and declared_income:
            mismatch = _income_mismatch_pct(query_declared_income, declared_income)
            if mismatch > MAX_INCOME_MISMATCH_PCT:
                flags.append(f"⚠ Declared income mismatch: {mismatch:.1f}%")
                risk_score += 25

        # Rule: very short tenure + large loan request
        loan_amount = entities.get("loan_amount", 0)
        years_employed = emp.get("years_employed", 10)
        if (
            loan_amount > 0
            and declared_income > 0
            and loan_amount / (declared_income or 1) > HIGH_LOAN_INCOME_MULTIPLIER_THRESHOLD
            and years_employed < MIN_EMPLOYER_TENURE_FOR_HIGH_LOAN
        ):
            flags.append(
                f"⚠ High loan-to-income ratio ({loan_amount/declared_income:.0f}x) "
                f"with short employment ({years_employed:.1f}yr)"
            )
            risk_score += 20

        # Rule: credit score very low + large loan
        credit_score = credit.get("credit_score", 750)
        if credit_score < 600 and loan_amount > 1_000_000:
            flags.append("⚠ Low credit score (<600) combined with large loan request")
            risk_score += 20

        # Rule: many defaults
        defaults = credit.get("defaults_count", 0)
        if defaults >= 2:
            flags.append(f"⚠ {defaults} prior loan defaults on record")
            risk_score += 25

        # ── Compute verdict ────────────────────────────────────────────────────
        if risk_score >= 60:
            fraud_risk = "high"
            auto_approve = False
            requires_manual_review = True
        elif risk_score >= 25:
            fraud_risk = "medium"
            auto_approve = False
            requires_manual_review = True
        else:
            fraud_risk = "low"
            auto_approve = True
            requires_manual_review = False

        fraud_assessment = {
            "applicant_id": applicant_id,
            "fraud_risk": fraud_risk,
            "risk_score": risk_score,
            "flags": flags,
            "auto_approve": auto_approve,
            "requires_manual_review": requires_manual_review,
            "recent_application_count": recent_count,
        }

        log.info(
            "fraud_assessed",
            applicant_id=applicant_id,
            risk=fraud_risk,
            score=risk_score,
            flags=len(flags),
        )

        return {"fraud_assessment": fraud_assessment}

    except Exception as exc:
        log.error("fraud_detection_failed", error=str(exc))
        return {
            "fraud_assessment": {
                "fraud_risk": "medium",
                "flags": [f"Detection error: {exc}"],
                "auto_approve": False,
                "requires_manual_review": True,
            },
            "error": f"Fraud detection error: {exc}",
        }