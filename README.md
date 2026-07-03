# Loan Advisory Agent

A multi-agent AI system for loan eligibility assessment, EMI calculation, and policy Q&A. Built with LangGraph for agent orchestration, ChromaDB for retrieval-augmented generation, Groq (free tier) as the LLM provider, and a React + Vite frontend.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [Agent Pipeline](#agent-pipeline)
  - [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Python Environment](#2-python-environment)
  - [3. Environment Configuration](#3-environment-configuration)
  - [4. Generate Synthetic Data](#4-generate-synthetic-data)
  - [5. Ingest Documents into Vector Store](#5-ingest-documents-into-vector-store)
  - [6. Start the Backend](#6-start-the-backend)
  - [7. Start the Frontend](#7-start-the-frontend)
- [API Reference](#api-reference)
- [Configuration Reference](#configuration-reference)
- [Database Schema](#database-schema)
- [Current Features](#current-features)
- [Limitations](#limitations)
- [Running Tests](#running-tests)
- [Production Deployment](#production-deployment)

---

## Overview

The Loan Advisory Agent is a conversational AI assistant designed for loan officers and applicants. It answers natural-language questions about loan eligibility, calculates EMIs, explains policy documents, and flags potential fraud, all grounded in retrieved policy documents to minimise hallucination.

A user submits a question in natural language. The system classifies the intent, retrieves relevant policy chunks from a local ChromaDB vector store, routes the query through a chain of specialist agent nodes (employment verifier, credit scorer, fraud detector, eligibility checker, EMI calculator), and synthesises a grounded, citation-backed response.

---

## Architecture

### Agent Pipeline

Every query passes through the following directed graph. Routing is conditional based on the classified intent and agent outputs at each step.

```
START
  |
  +--> classify_query           (intent classification, entity extraction)
         |
         +--> retrieve_documents (RAG: fetch relevant policy chunks from ChromaDB)
                |
                +--> [router]
                       |
                       +--> verify_employment --> [router]
                       |          |
                       |          +--> score_credit --> [router]
                       |          |        |
                       |          |        +--> detect_fraud --> check_eligibility --> synthesize_response
                       |          |        |
                       |          |        +--> check_eligibility --> synthesize_response
                       |          |
                       |          +--> synthesize_response
                       |
                       +--> calculate_emi --> synthesize_response
                       |
                       +--> synthesize_response   (policy / general questions)
END
```

**Routing decisions:**

- Eligibility queries activate: employment verifier -> credit scorer -> (fraud detector if high risk) -> eligibility checker -> synthesizer.
- EMI queries route directly to the EMI calculator, skipping the eligibility chain.
- Policy and general questions bypass all specialist agents and go straight to synthesis after retrieval.
- An employment discrepancy or high fraud risk score short-circuits the pipeline, routing directly to the synthesizer which surfaces the issue in the response.

### Project Structure

```
loan-advisory-agent/
|-- backend/
|   |-- main.py                         # FastAPI app: lifespan hooks, CORS, route registration
|   |-- config.py                       # Pydantic Settings, all config loaded from .env
|   |-- llm.py                          # LLM + embedding factory (Groq / OpenAI / HuggingFace)
|   |-- agents/
|   |   |-- orchestrator.py             # LangGraph graph builder, routing functions, run_query()
|   |   |-- state.py                    # LoanAdvisoryState TypedDict, single source of truth
|   |   |-- nodes/
|   |   |   |-- query_classifier.py     # Intent classification + entity extraction
|   |   |   |-- document_retriever.py   # RAG retrieval (global policy pool + per-user docs)
|   |   |   |-- employment_verifier.py  # Employment verification against the database
|   |   |   |-- credit_scorer.py        # Credit score analysis and risk banding
|   |   |   |-- fraud_detector.py       # Rule-based fraud risk flagging
|   |   |   |-- eligibility_checker.py  # Loan eligibility decision logic
|   |   |   |-- emi_calculator.py       # EMI + amortisation schedule calculation
|   |   |   +-- response_synthesizer.py # Grounded response generation with citations
|   |   +-- tools/
|   |       |-- calculator.py           # Pure EMI / financial math utilities
|   |       +-- db_tools.py             # SQLite / Supabase database query helpers
|   |-- api/
|   |   |-- routes/
|   |   |   |-- chat.py                 # POST /api/chat, GET /api/chat/health
|   |   |   |-- documents.py            # POST /api/documents/upload, GET /api/documents/list
|   |   |   +-- applicants.py           # GET /api/applicants, GET /api/applicants/{id}
|   |   +-- middleware/                 # X-User-Id header extraction, user context injection
|   |-- rag/
|   |   |-- document_processor.py       # Bulk ingestion: PDF/DOCX/TXT -> ChromaDB (global pool)
|   |   |-- user_document_processor.py  # Per-user document ingestion (scoped by user_id)
|   |   +-- _common.py                  # Shared loaders, text splitter, file-hash deduplication
|   +-- database/
|       |-- models.py                   # Pydantic request/response models + DB entity schemas
|       +-- supabase_client.py          # Supabase client (falls back to SQLite in development)
|-- data/
|   |-- dev.db                          # SQLite database (generated by generate_data.py)
|   |-- schema.sql                      # Production PostgreSQL / Supabase schema
|   |-- chroma_db/                      # ChromaDB vector store (generated by document_processor)
|   +-- synthetic/
|       |-- generate_data.py            # Synthetic applicant + loan data generator
|       |-- applicants.json             # JSON export of generated applicant profiles
|       |-- loan_policies.json          # Sample loan policy rules
|       +-- documents/                  # Policy PDFs / DOCX files for vector ingestion
|-- frontend/
|   |-- index.html
|   |-- vite.config.js
|   |-- package.json
|   +-- src/
|       |-- main.jsx                    # React app entry point
|       |-- App.jsx                     # Router configuration
|       |-- components/
|       |   |-- ChatInterface.jsx       # Main chat UI with document source panel
|       |   +-- Layout.jsx              # App shell and navigation
|       |-- pages/
|       |   |-- LandingPage.jsx
|       |   |-- Dashboard.jsx           # Primary chat dashboard
|       |   |-- Features.jsx
|       |   |-- HowToUse.jsx
|       |   |-- Limitations.jsx
|       |   |-- Roadmap.jsx
|       |   +-- WhyOryn.jsx
|       +-- services/                   # Axios API client wrappers
|-- tests/
|   |-- conftest.py                     # Pytest fixtures and test client setup
|   |-- test_agents.py                  # Unit tests for agent nodes
|   +-- test_api.py                     # Integration tests for FastAPI endpoints
|-- .env.example                        # Environment variable template
+-- requirements.txt                    # Python dependencies
```

---

## Tech Stack

**Backend**

| Component | Technology |
|---|---|
| Web framework | FastAPI 0.115 + Uvicorn |
| Agent orchestration | LangGraph 1.2 |
| LLM (primary) | Groq API, llama-3.1-8b-instant (free tier) |
| LLM (optional) | OpenAI, gpt-4o-mini |
| Embeddings | Sentence-Transformers all-MiniLM-L6-v2 (local, no API key) |
| Vector store | ChromaDB 1.3 (local persistence) |
| LangChain | langchain-core, langchain-groq, langchain-huggingface, langchain-chroma, langchain-community |
| Database (dev) | SQLite via SQLAlchemy |
| Database (prod) | PostgreSQL via Supabase |
| Validation | Pydantic v2 + pydantic-settings |
| Logging | structlog |
| Document parsing | pypdf, python-docx, docx2txt, unstructured |

**Frontend**

| Component | Technology |
|---|---|
| Framework | React 19 + Vite 8 |
| 3D / Animation | React Three Fiber, Three.js, GSAP |
| Routing | React Router v7 |
| HTTP client | Axios |
| Markdown rendering | react-markdown |

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher and npm
- A free Groq API key, available at https://console.groq.com/keys
- Git

Optional for production:

- A Supabase project (PostgreSQL persistence and row-level security)
- An OpenAI API key (if you prefer OpenAI over Groq)

---

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd loan-advisory-agent
```

### 2. Python Environment

Create and activate a virtual environment, then install all Python dependencies.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

The first install will download the `sentence-transformers/all-MiniLM-L6-v2` embedding model (approximately 80 MB) from HuggingFace on first server startup.

### 3. Environment Configuration

Copy the example environment file and fill in your values.

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
GROQ_API_KEY=gsk_...your-key-here...
```

All other variables have sensible defaults for local development. See the Configuration Reference section below for the full list.

### 4. Generate Synthetic Data

This step seeds the SQLite database with realistic synthetic applicant profiles, credit bureau records, and loan applications. It also exports the JSON files used by the RAG ingestion pipeline.

Run from the project root with your virtual environment activated:

```bash
python data/synthetic/generate_data.py
```

**Output produced:**

| File | Description |
|---|---|
| `data/dev.db` | SQLite database with all tables populated |
| `data/synthetic/applicants.json` | JSON export of applicant profiles |
| `data/synthetic/loan_policies.json` | Sample policy rules for RAG |

### 5. Ingest Documents into Vector Store

This step reads all supported document files (PDF, DOCX, TXT) from the specified directory, splits them into overlapping chunks, embeds each chunk with the local sentence-transformer model, and indexes them into ChromaDB. The embedding model is downloaded automatically on first run.

```bash
python -m backend.rag.document_processor --docs-dir ./data/synthetic/documents
```

**Available flags:**

| Flag | Default | Description |
|---|---|---|
| `--docs-dir PATH` | `./data/synthetic/documents` | Directory to scan for documents |
| `--force` | off | Re-ingest documents already indexed. Without this, files are deduplicated by content hash and skipped if already present. |

**Output produced:** `data/chroma_db/` -- persisted ChromaDB vector store

This command is idempotent. Re-running without `--force` will skip already-indexed files.

### 6. Start the Backend

Open Terminal 1 and run:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

On startup the server will:

1. Compile the LangGraph agent graph (done once at startup, reused for every request)
2. Pre-load the sentence-transformer embedding model into memory

The backend is ready when the log emits `agent_graph_ready` and `embedding_model_ready`.

| URL | Description |
|---|---|
| http://localhost:8000 | API root, returns version and status JSON |
| http://localhost:8000/docs | Swagger UI, interactive API documentation |
| http://localhost:8000/redoc | ReDoc API documentation |
| http://localhost:8000/health | Health check endpoint |

### 7. Start the Frontend

Open Terminal 2. Navigate to the frontend directory, install dependencies on first run, then start the dev server:

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at http://localhost:5173.

---

## API Reference

Full interactive documentation is available at http://localhost:8000/docs. Key endpoints:

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Submit a query through the full multi-agent pipeline |
| `GET` | `/api/chat/health` | Health check for the agent pipeline |

**POST /api/chat, Request body:**

```json
{
  "query": "Am I eligible for a home loan of 50 lakhs?",
  "session_id": "optional-uuid-for-conversation-continuity",
  "applicant_id": "optional-applicant-uuid"
}
```

- `query` is required, between 3 and 2000 characters.
- `session_id` is optional. If omitted, a new UUID is generated. Pass the same value across requests to maintain conversation memory within a session.
- `applicant_id` is optional. When supplied, agent database lookups are scoped to that applicant.
- Pass an `X-User-Id` header to include documents uploaded by that user in retrieval alongside the global policy pool.

**POST /api/chat, Response:**

```json
{
  "session_id": "...",
  "response": "Based on your profile and our home loan policy...",
  "sources": ["home_loan_policy.pdf, page 3"],
  "policy_sources": ["home_loan_policy.pdf, page 3"],
  "user_sources": [],
  "confidence_score": 0.82,
  "agent_metadata": {
    "query_type": "eligibility",
    "agents_invoked": ["employment_verifier", "credit_scorer", "eligibility_checker"],
    "hallucination_risk": "low",
    "confidence_score": 0.82,
    "fallback_triggered": false
  },
  "error": null,
  "timestamp": "2026-07-03T08:00:00Z"
}
```

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload a PDF, DOCX, or TXT file for per-user RAG retrieval |
| `GET` | `/api/documents/list` | List documents uploaded by the current user, identified by X-User-Id |

### Applicants

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/applicants` | List all applicants in the database |
| `GET` | `/api/applicants/{id}` | Retrieve a single applicant full profile |

---

## Configuration Reference

All configuration is read from `.env` through Pydantic Settings. No code changes are needed to swap providers or tune behaviour.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Chat LLM provider. `groq` or `openai` |
| `GROQ_API_KEY` | required | Groq API key. Free tier at https://console.groq.com/keys |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model. Alternatives: `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` |
| `OPENAI_API_KEY` | empty | Required only when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `EMBEDDING_PROVIDER` | `huggingface` | `huggingface` (local, free) or `openai` |
| `HF_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace model for local embeddings |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model, used when EMBEDDING_PROVIDER=openai |
| `SUPABASE_URL` | empty | Supabase project URL, production only |
| `SUPABASE_ANON_KEY` | empty | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | empty | Supabase service role key for server-side writes |
| `DATABASE_URL` | `sqlite:///./dev.db` | Database connection string |
| `APP_ENV` | `development` | `development` or `production` |
| `APP_SECRET_KEY` | `dev-secret-change-me` | Must be changed before any public deployment |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `CORS_ORIGINS` | `http://localhost:8501,http://localhost:3000` | Comma-separated list of allowed CORS origins |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | Directory where ChromaDB persists its vector index |
| `CHUNK_SIZE` | `800` | Maximum characters per document chunk |
| `CHUNK_OVERLAP` | `150` | Character overlap between consecutive chunks |
| `RETRIEVAL_TOP_K` | `5` | Number of top chunks returned per retrieval query |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.35` | Minimum cosine similarity for a chunk to be included in context |
| `MAX_ITERATIONS` | `10` | Maximum agent graph iterations per query, loop guard |
| `TEMPERATURE` | `0.1` | LLM temperature. Lower values produce more deterministic output |
| `HALLUCINATION_THRESHOLD` | `0.5` | Confidence below this triggers a disclaimer in the response |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL referenced by the frontend |

---

## Database Schema

The development environment uses SQLite (`data/dev.db`). The production schema targets PostgreSQL on Supabase and is defined in `data/schema.sql`.

| Table | Description |
|---|---|
| `applicants` | Personal details, employment type, monthly income, residential status |
| `credit_bureau` | Credit score (300 to 900), debt payments, credit history, defaults, recent enquiries |
| `loan_applications` | Loan type, requested amount, tenure, and status: pending, approved, rejected, or disbursed |
| `chat_sessions` | Conversation session records, optionally linked to an applicant |
| `chat_messages` | Per-message history with role, content, confidence score, and sources stored as JSONB in PostgreSQL |

The Supabase schema enables Row Level Security on all tables. The backend service role has full access; the anonymous role has no access.

---

## Current Features

**Agent Capabilities**

- Natural language query understanding with intent classification into five types: eligibility, emi, policy, fraud_check, general
- Structured entity extraction from free-form queries, including loan amount, tenure, loan type, and applicant identifiers
- Employment verification checked against the applicant database, with explicit discrepancy detection
- Credit scoring with four risk bands: excellent, good, fair, poor
- Fraud risk assessment triggered automatically on high-risk credit profiles using rule-based signal aggregation
- Loan eligibility determination returning maximum loan amount, applicable interest rate, tenure cap, reasons, and required conditions
- EMI calculation with a full month-by-month amortisation schedule
- Retrieval-augmented generation over policy documents with cosine similarity scoring. Chunks below the configured threshold are excluded from the context window
- Per-user document upload and isolated retrieval. User-uploaded documents are stored in a separate ChromaDB collection and retrieved alongside the global policy pool when an X-User-Id header is present
- Hallucination risk scoring with automatic disclaimer injection when the confidence score falls below the configured threshold
- Graceful fallback responses when no relevant context is retrieved
- Conversation memory per session using LangGraph in-process MemorySaver
- Structured logging throughout with structlog

**API and Infrastructure**

- Interactive Swagger UI at /docs and ReDoc at /redoc
- Health endpoint at /health
- CORS support configurable via CORS_ORIGINS
- Global exception handler returning structured JSON error responses
- Embedding model and agent graph pre-warmed at startup to eliminate first-request latency
- File-hash-based deduplication in the document ingestion pipeline. Re-ingestion of unchanged files is skipped automatically

**Frontend**

- React 19 + Vite with React Three Fiber 3D elements on the landing page
- Chat interface with a split document source panel showing global policy sources and user-uploaded sources separately
- Agent metadata panel displaying which agents ran, the confidence score, and hallucination risk level
- Document upload interface for per-user RAG ingestion
- Multi-page application covering Landing, Dashboard, Features, How-To-Use, Limitations, and Roadmap

---

## Limitations

**LLM and Rate Limits**

- The default configuration uses Groq free tier (llama-3.1-8b-instant). Free-tier rate limits will cause request failures under sustained or concurrent load. Upgrading to a paid Groq plan or switching to LLM_PROVIDER=openai resolves this.
- Groq does not provide an embedding API. Embeddings always run locally via sentence-transformers on CPU. Embedding large document batches is slow. For production-scale ingestion, use EMBEDDING_PROVIDER=openai or a GPU-accelerated deployment.

**Retrieval Quality**

- Retrieval quality is bounded by the documents that have been ingested. Questions on topics not covered in the vector store receive a fallback disclaimer response rather than a fabricated answer.
- CHUNK_SIZE and CHUNK_OVERLAP are applied at ingestion time. Changing these values after ingestion requires re-running the document processor with --force to rebuild the index.

**Agent Decisions**

- Agent decisions are heuristic-based and operate on synthetic data generated by Faker. They are not connected to real financial systems, credit bureaus, or regulatory frameworks.
- The fraud detector applies static rule-based flags, not a trained classification model. False positives and false negatives should be expected in a real deployment context.
- Eligibility criteria are simplified approximations for demonstration purposes. They do not reflect the full regulatory requirements of any specific institution or jurisdiction.

**Persistence and Scalability**

- Conversation memory uses LangGraph in-process MemorySaver. All session state is lost when the server restarts. For durable memory, replace MemorySaver in backend/agents/orchestrator.py with AsyncPostgresSaver backed by Supabase.
- The system is not designed for horizontal scaling. The in-process checkpointer and local ChromaDB are single-node. Running multiple Uvicorn workers will result in sessions not being shared across workers.
- SQLite is not suitable for concurrent writes in production. Switch to PostgreSQL via DATABASE_URL.

**Streaming**

- The /api/chat/stream endpoint exists in the router but returns HTTP 501 Not Implemented. Streaming responses via Server-Sent Events are a planned future feature.

**Security**

- The X-User-Id header used to scope per-user document retrieval is accepted directly from the client without verification. In a production deployment this value must be derived from a verified server-side session token.
- The default APP_SECRET_KEY must be replaced with a strong random secret before any public-facing deployment.

---

## Running Tests

The test suite uses pytest with async support via pytest-asyncio and an httpx test client. Activate your virtual environment before running.

Run all tests:

```bash
pytest tests/ -v
```

Run a specific test file:

```bash
pytest tests/test_api.py -v
pytest tests/test_agents.py -v
```

Test fixtures, the FastAPI test client, and shared utilities are defined in `tests/conftest.py`.

---

## Production Deployment

**Backend**

1. Set `APP_ENV=production` and generate a strong `APP_SECRET_KEY`.
2. Provision a Supabase project and run `data/schema.sql` in the Supabase SQL Editor.
3. Set `DATABASE_URL` to your Supabase PostgreSQL connection string and configure `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_KEY`.
4. Replace `MemorySaver` in `backend/agents/orchestrator.py` with `AsyncPostgresSaver` for durable conversation memory across restarts.
5. Run the document processor to populate the vector store before starting the server.
6. Serve with Uvicorn behind a reverse proxy such as nginx, Railway, or Render:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Use `--workers 1` while the in-process MemorySaver is active. Increase workers only after migrating to a shared external checkpointer.

**Frontend**

Build the production bundle from the frontend directory:

```bash
cd frontend
npm run build
```

The compiled assets are written to `frontend/dist/`. Deploy this directory to any static host such as Vercel, Netlify, or nginx. Set `BACKEND_URL` in `.env` to your deployed backend URL before building.
