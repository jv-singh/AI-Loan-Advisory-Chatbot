"""
backend/api/middleware/user_context.py
──────────────────────────────────────
Reads `X-User-Id` from incoming requests and stashes it on
`request.state.user_id` so route handlers can read it via a small
`Depends(get_user_id)`.

This is the single seam between the browser (which generates a UUID
once and stores it in localStorage) and the server (which uses it to
scope RAG retrieval and isolate uploaded documents).

Tenancy scope:
  - The header is TRUSTED for *filtering* (which docs to retrieve).
    A malicious client sending a fake `X-User-Id` could see someone
    else's docs in retrieval, but could not list or delete them
    because the server checks metadata.user_id on every write op.
  - To upgrade to a hard tenancy boundary, swap this for a JWT issued
    at /api/auth/anonymous. The interface (`get_user_id` dep) stays.
"""

from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, Request, status

log = structlog.get_logger(__name__)


# ── Middleware ────────────────────────────────────────────────────────────────


async def user_context_middleware(request: Request, call_next):
    """
    Extract `X-User-Id` from the request and attach it to
    `request.state.user_id`. If the header is missing, set it to None
    — the route handler decides whether to reject or allow.
    """
    user_id = request.headers.get("X-User-Id") or request.headers.get("x-user-id")
    request.state.user_id = user_id.strip() if user_id else None

    if user_id:
        log.debug("user_context_resolved", user_id=user_id[:8] + "...")

    response = await call_next(request)
    return response


# ── Dependency for routes ─────────────────────────────────────────────────────


async def get_user_id_optional(request: Request) -> str | None:
    """
    Dependency that returns the caller's user_id, or None if absent.
    Use this on endpoints that should work even for anonymous
    requesters (e.g. health checks).
    """
    return getattr(request.state, "user_id", None)


async def get_user_id_required(
    user_id: str | None = Depends(get_user_id_optional),
) -> str:
    """
    Dependency that REJECTS the request with 400 if no user_id is
    present. Use this on endpoints that own a resource scoped to a
    user (upload, list, delete, chat that wants personal RAG).
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing X-User-Id header. The frontend sets this from "
                "localStorage. If you're calling the API directly, generate "
                "a UUID v4 and send it as `X-User-Id: <uuid>`."
            ),
        )
    return user_id
