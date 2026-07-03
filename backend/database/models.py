"""
backend/database/models.py
────────────────────────────
Pydantic models for API request/response validation and DB schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid


# ── Request Models ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming query from the frontend."""
    query: str = Field(..., min_length=3, max_length=2000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    applicant_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class DocumentUploadResponse(BaseModel):
    """Response after document ingestion."""
    filename: str
    chunks_indexed: int
    status: str  # "success" | "error"
    message: str
    # New: identifies the uploaded doc so the UI can show it in the docs panel
    doc_id: Optional[str] = None
    source: str = "user"  # "user" | "global" (only "user" in v1)
    chunks: int = 0       # alias of chunks_indexed for frontend convenience


class UserDocumentInfo(BaseModel):
    """One entry per user-uploaded file, returned by GET /api/documents/list."""
    doc_id: str
    filename: str
    file_type: str  # ".pdf" | ".docx" | ".txt" | ".md"
    chunks: int
    uploaded_at: str  # ISO 8601 UTC


class UserDocumentListResponse(BaseModel):
    """Response shape for GET /api/documents/list."""
    user_documents: list[UserDocumentInfo] = Field(default_factory=list)
    total_user_chunks: int = 0
    note: Optional[str] = None


# ── Response Models ────────────────────────────────────────────────────────────

class AgentMetadata(BaseModel):
    """Metadata about which agents ran and their outputs (for debug UI)."""
    query_type: str
    agents_invoked: list[str]
    hallucination_risk: str
    confidence_score: float
    fallback_triggered: bool


class ChatResponse(BaseModel):
    """Full response sent back to the frontend."""
    session_id: str
    response: str
    sources: list[str] = Field(
        default_factory=list,
        description="Combined list of all cited sources (policy + user). "
                    "Kept for backward compatibility with the existing UI.",
    )
    policy_sources: list[str] = Field(
        default_factory=list,
        description="Sources that came from the global loan_policies collection.",
    )
    user_sources: list[dict] = Field(
        default_factory=list,
        description="Sources that came from the caller's user_docs collection. "
                    "Each entry: {filename, doc_id, chunk_excerpt, score}.",
    )
    confidence_score: float
    agent_metadata: Optional[AgentMetadata] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Applicant / Loan DB Schemas ────────────────────────────────────────────────

class Applicant(BaseModel):
    """Matches the `applicants` table schema."""
    id: str
    full_name: str
    email: str
    phone: str
    date_of_birth: str
    pan_number: str
    aadhaar_last4: str
    employer_name: str
    employment_type: str  # salaried | self_employed | business
    designation: str
    monthly_income: float
    years_employed: float
    residential_status: str  # owned | rented
    city: str
    state: str


class CreditBureau(BaseModel):
    """Matches the `credit_bureau` table schema."""
    applicant_id: str
    credit_score: int = Field(..., ge=300, le=900)
    total_existing_loans: int
    monthly_debt_payments: float
    credit_history_years: float
    defaults_count: int
    enquiries_last_6m: int
    score_last_updated: str


class LoanApplication(BaseModel):
    """Matches the `loan_applications` table schema."""
    id: str
    applicant_id: str
    loan_type: str  # home | personal | car | education | business
    requested_amount: float
    tenure_years: int
    purpose: str
    applied_at: str
    status: str  # pending | approved | rejected | disbursed


class EligibilityResultModel(BaseModel):
    """Structured eligibility result returned to the API."""
    is_eligible: bool
    decision: str
    loan_type: str
    max_loan_amount: float
    interest_rate: float
    max_tenure_years: int
    reasons: list[str]
    conditions: list[str]


class EMIResultModel(BaseModel):
    """Structured EMI result returned to the API."""
    principal: float
    annual_rate: float
    tenure_months: int
    monthly_emi: float
    total_payment: float
    total_interest: float
    interest_percentage: float
    breakdown_summary: str