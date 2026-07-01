"""
backend/api/routes/__init__.py
Export all APIRouter instances for registration in main.py.
"""
from .chat import router as chat_router
from .documents import router as documents_router
from .applicants import router as applicants_router

__all__ = ["chat_router", "documents_router", "applicants_router"]