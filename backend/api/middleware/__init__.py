"""
backend/api/middleware/__init__.py
Expose the user-context middleware.
"""
from .user_context import (
    get_user_id_optional,
    get_user_id_required,
    user_context_middleware,
)

__all__ = [
    "user_context_middleware",
    "get_user_id_optional",
    "get_user_id_required",
]
