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
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from backend.database.models import ChatRequest, ChatResponse, AgentMetadata
from backend.agents.orchestrator import run_query

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a natural language loan query through the multi-agent pipeline.

    The pipeline runs:
      1. Query classification (intent + entity extraction)
      2. Document retrieval (RAG)
      3. Specialist agents (employment / credit / fraud / eligibility / EMI)
      4. Response synthesis with citations

    Args:
        request: ChatRequest with query, session_id, optional applicant_id

    Returns:
        ChatResponse with the grounded answer, sources, and confidence score
    """
    log.info(
        "chat_request_received",
        session=request.session_id,
        applicant_id=request.applicant_id,
        query=request.query[:60],
    )

    try:
        final_state = await run_query(
            query=request.query,
            session_id=request.session_id,
            applicant_id=request.applicant_id,
        )

        # Build agent metadata for debug panel in UI
        metadata = AgentMetadata(
            query_type=final_state.get("query_type", "general"),
            agents_invoked=final_state.get("requires_agents", []),
            hallucination_risk=final_state.get("hallucination_risk", "low"),
            confidence_score=final_state.get("confidence_score", 0.0),
            fallback_triggered=final_state.get("fallback_triggered", False),
        )

        response = ChatResponse(
            session_id=request.session_id,
            response=final_state.get("final_response", "No response generated."),
            sources=final_state.get("sources", []),
            confidence_score=final_state.get("confidence_score", 0.0),
            agent_metadata=metadata,
            error=final_state.get("error"),
        )

        log.info(
            "chat_response_sent",
            session=request.session_id,
            confidence=response.confidence_score,
            sources_count=len(response.sources),
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