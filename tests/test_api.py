"""
tests/test_api.py
──────────────────
Integration tests for FastAPI endpoints.
Uses httpx AsyncClient — no real LLM calls (LLM is mocked).

Run:
  pytest tests/test_api.py -v
  pytest tests/test_api.py -v --asyncio-mode=auto
"""

from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from backend.main import app


# ── Helpers ────────────────────────────────────────────────────────────────────

MOCK_AGENT_RESPONSE = {
    "final_response": "Based on the policy documents, the minimum credit score for a home loan is 650.",
    "sources": ["home_loan_policy.txt"],
    "confidence_score": 0.82,
    "query_type": "policy",
    "requires_agents": [],
    "hallucination_risk": "low",
    "fallback_triggered": False,
    "error": None,
}


@pytest.fixture
def mock_run_query():
    with patch("backend.api.routes.chat.run_query", new_callable=AsyncMock) as m:
        m.return_value = MOCK_AGENT_RESPONSE
        yield m


# ── Health checks ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Loan Advisory Agent"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/chat/health")
    assert r.status_code == 200


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_valid_query(mock_run_query):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/chat", json={
            "query": "What is the minimum credit score for a home loan?",
            "session_id": "test-session-001",
        })
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert "confidence_score" in data
    assert data["confidence_score"] >= 0.0
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_chat_too_short_query():
    """Query shorter than 3 characters should be rejected by Pydantic."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/chat", json={
            "query": "hi",
            "session_id": "test-session",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_chat_with_applicant_id(mock_run_query):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/chat", json={
            "query": "Am I eligible for a personal loan?",
            "session_id": "test-session-002",
            "applicant_id": "some-uuid-here",
        })
    assert r.status_code == 200
    mock_run_query.assert_called_once()
    call_kwargs = mock_run_query.call_args
    assert call_kwargs.kwargs.get("applicant_id") == "some-uuid-here"


@pytest.mark.asyncio
async def test_chat_stream_returns_501():
    """Streaming endpoint should return 501 until implemented."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/chat/stream", json={
            "query": "What is the EMI?",
            "session_id": "test-session-003",
        })
    assert r.status_code == 501


# ── Document upload endpoint ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_document_upload_unsupported_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("policy.csv", b"col1,col2\n1,2", "text/csv")},
        )
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


# ── Applicants endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_applicants_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/applicants")
    assert r.status_code == 200
    assert "applicants" in r.json()


@pytest.mark.asyncio
async def test_get_unknown_applicant_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/applicants/nonexistent-id-000")
    assert r.status_code == 404