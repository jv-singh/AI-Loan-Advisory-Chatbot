"""
backend/api/routes/chat.py
───────────────────────────
FastAPI chat endpoint — the primary interface for the frontend.

Endpoints:
  POST /api/chat           → Run a query through the full agent pipeline
  GET  /api/chat/history   → Retrieve conversation history for a session
  DELETE /api/chat/session → Clear session memory
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.database.models import ChatRequest, ChatResponse, AgentMetadata
from backend.agents.orchestrator import run_query
from backend.api.middleware import get_user_id_optional

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str | None = Depends(get_user_id_optional),
) -> ChatResponse:
    """
    Process a natural language loan query through the multi-agent pipeline.

    The pipeline runs:
      1. Query classification (intent + entity extraction)
      2. Document retrieval (RAG) — combines global policy + caller's user docs
      3. Specialist agents (employment / credit / fraud / eligibility / EMI)
      4. Response synthesis with citations

    Args:
        request: ChatRequest with query, session_id, optional applicant_id
        user_id: Optional, read from the `X-User-Id` header. When present,
                 retrieval also queries the caller's user_docs collection.

    Returns:
        ChatResponse with the grounded answer, split policy/user sources,
        and a confidence score.
    """
    log.info(
        "chat_request_received",
        session=request.session_id,
        applicant_id=request.applicant_id,
        user_id=(user_id[:8] + "...") if user_id else None,
        query=request.query[:60],
    )

    try:
        final_state = await run_query(
            query=request.query,
            session_id=request.session_id,
            applicant_id=request.applicant_id,
            user_id=user_id,
        )

        # Build agent metadata for debug panel in UI
        metadata = AgentMetadata(
            query_type=final_state.get("query_type", "general"),
            agents_invoked=final_state.get("requires_agents", []),
            hallucination_risk=final_state.get("hallucination_risk", "low"),
            confidence_score=final_state.get("confidence_score", 0.0),
            fallback_triggered=final_state.get("fallback_triggered", False),
        )

        # The synthesizer emits both a combined `sources` list (backward compat)
        # and the split `policy_sources` / `user_sources`. We pass all three
        # through to the frontend so existing UIs keep working and the new
        # docs panel can use the split view.
        combined_sources = final_state.get("sources", [])
        policy_sources = final_state.get("policy_sources", combined_sources)
        user_sources = final_state.get("user_sources", [])

        response = ChatResponse(
            session_id=request.session_id,
            response=final_state.get("final_response", "No response generated."),
            sources=combined_sources,
            policy_sources=policy_sources,
            user_sources=user_sources,
            confidence_score=final_state.get("confidence_score", 0.0),
            agent_metadata=metadata,
            error=final_state.get("error"),
        )

        log.info(
            "chat_response_sent",
            session=request.session_id,
            confidence=response.confidence_score,
            policy_sources_count=len(response.policy_sources),
            user_sources_count=len(response.user_sources),
        )

        return response

    except Exception as exc:
        log.error("chat_endpoint_error", error=str(exc), session=request.session_id)
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {exc}")


@router.get("/health")
async def health_check():
    """Quick health check for the agent pipeline."""
    return {
        "status": "ok",
        "agent": "LoanAdvisoryAgent",
        "version": "1.0.0",
    }


# ── TODO: Implement streaming endpoint ────────────────────────────────────────
@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    TODO: Streaming version of /api/chat using SSE.

    Use LangGraph's .astream_events() to yield chunks as the pipeline runs.
    This makes the UI feel much more responsive for longer queries.

    Implementation skeleton:
        async def generate():
            async for event in graph.astream_events(state, config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    yield f"data: {json.dumps({'chunk': chunk})}\\n\\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    """
    raise HTTPException(
        status_code=501,
        detail="Streaming not yet implemented. Use POST /api/chat instead.",
    )
