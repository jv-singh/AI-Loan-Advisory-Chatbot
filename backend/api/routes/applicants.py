"""
backend/api/routes/applicants.py
──────────────────────────────────
Applicant data management endpoints.

Endpoints:
  GET  /api/applicants           → List all applicants (paginated)
  GET  /api/applicants/{id}      → Get a specific applicant's profile
  POST /api/applicants           → Create a new applicant record
  GET  /api/applicants/{id}/summary → Full profile + credit + applications
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query
from backend.database.supabase_client import get_supabase_client

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/applicants", tags=["applicants"])


@router.get("")
async def list_applicants(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
):
    """List applicants with pagination."""
    try:
        client = get_supabase_client()
        offset = (page - 1) * per_page
        result = (
            client.table("applicants")
            .select("id, full_name, email, employment_type, monthly_income, city")
            .limit(per_page)
            .execute()
        )
        return {
            "applicants": result.data or [],
            "page": page,
            "per_page": per_page,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{applicant_id}")
async def get_applicant(applicant_id: str):
    """Fetch a specific applicant's full profile."""
    try:
        client = get_supabase_client()
        result = (
            client.table("applicants")
            .select("*")
            .eq("id", applicant_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{applicant_id}/summary")
async def get_applicant_summary(applicant_id: str):
    """
    Full applicant summary: profile + credit bureau + loan applications.
    Used by the UI sidebar to show applicant context alongside chat.
    """
    try:
        client = get_supabase_client()

        profile = client.table("applicants").select("*").eq("id", applicant_id).single().execute()
        if not profile.data:
            raise HTTPException(status_code=404, detail="Applicant not found")

        credit = client.table("credit_bureau").select("*").eq("applicant_id", applicant_id).single().execute()
        applications = (
            client.table("loan_applications")
            .select("*")
            .eq("applicant_id", applicant_id)
            .order("applied_at", desc=True)
            .limit(5)
            .execute()
        )

        return {
            "profile": profile.data,
            "credit_bureau": credit.data,
            "recent_applications": applications.data or [],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))