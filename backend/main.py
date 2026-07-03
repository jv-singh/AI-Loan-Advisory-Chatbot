"""
backend/main.py
────────────────
FastAPI application entry point.

Run with:
  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

On Windows:
  python -m uvicorn backend.main:app --reload
"""

from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.api.routes import chat, documents, applicants
from backend.api.middleware import user_context_middleware
from backend.agents.orchestrator import get_graph

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — runs once on startup and shutdown.
    Warms up the LangGraph agent graph (JIT compile on first invocation is slow).
    Also pre-loads the embedding model so the first user query doesn't pay
    the ~10–30s model load cost.
    """
    log.info("starting_loan_advisory_agent", env=settings.app_env)

    # Pre-compile the agent graph at startup
    graph = get_graph()
    log.info("agent_graph_ready")

    # Pre-load the embedding model so the first /api/chat request is fast
    # (sentence-transformers downloads + loads ~80MB on first use otherwise).
    try:
        from backend.llm import get_embeddings
        log.info("warming_up_embedding_model", model=settings.hf_embedding_model)
        get_embeddings()
        log.info("embedding_model_ready")
    except Exception as exc:
        log.warning("embedding_warmup_failed", error=str(exc))

    yield  # Server runs here

    log.info("shutting_down")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Loan Advisory Agent API",
    description=(
        "Multi-agent AI system for loan eligibility assessment, EMI calculation, "
        "and policy Q&A. Powered by LangGraph + RAG."
    ),
    version="1.0.0",
    docs_url="/docs",       # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
# Starlette processes middleware in REVERSE order of registration (last added
# is outermost). CORS is added LAST so it runs outermost — preflight OPTIONS
# requests are answered by CORS without ever reaching our custom middleware,
# which is what we want.
app.middleware("http")(user_context_middleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(applicants.router)


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "Loan Advisory Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "environment": settings.app_env,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "env": settings.app_env}


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )