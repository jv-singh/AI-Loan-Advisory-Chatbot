"""
backend/database/__init__.py
Expose the database client factory and Pydantic models.
"""
from .supabase_client import get_supabase_client
from .models import (
    Applicant,
    CreditBureau,
    LoanApplication,
    ChatRequest,
    ChatResponse,
    EligibilityResultModel,
    EMIResultModel,
)

__all__ = [
    "get_supabase_client",
    "Applicant",
    "CreditBureau",
    "LoanApplication",
    "ChatRequest",
    "ChatResponse",
    "EligibilityResultModel",
    "EMIResultModel",
]