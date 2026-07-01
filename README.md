# 🏦 Loan Advisory Agent

> A production-grade multi-agent AI system for loan eligibility assessment, EMI calculation, and policy Q&A — built with **LangGraph**, **FastAPI**, **RAG**, and **Supabase**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38-red?logo=streamlit)](https://streamlit.io)

---

## What This Is

A loan advisory AI agent that answers natural-language questions about loans by orchestrating **8 specialized AI agents** through a LangGraph state machine. Every response is grounded in retrieved policy documents — the system explicitly cannot make up interest rates, eligibility rules, or approval decisions.

**Who it serves:** Loan officers, underwriters, and financial advisors who need instant, policy-backed answers without digging through 50-page PDF guidelines.

---

## Architecture at a Glance

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              LangGraph Agent Graph               │  │
│  │                                                  │  │
│  │  [1] Query Classifier  →  intent + entities      │  │
│  │         │                                        │  │
│  │  [2] Document Retriever  →  RAG (ChromaDB)       │  │
│  │         │                                        │  │
│  │         ├──► [3] Employment Verifier             │  │
│  │         │           │                            │  │
│  │         │    [4] Credit Scorer                   │  │
│  │         │           │                            │  │
│  │         │    [5] Fraud Detector                  │  │
│  │         │           │                            │  │
│  │         │    [6] Eligibility Checker             │  │
│  │         │                                        │  │
│  │         ├──► [7] EMI Calculator                  │  │
│  │         │                                        │  │
│  │         └──► [8] Response Synthesizer ──► Answer │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Database: Supabase/SQLite    Vector DB: ChromaDB       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Streamlit Frontend (chat UI)
```

---

## Quick Start (Windows)

### Prerequisites
- Python 3.11+
- **Groq API key (free)** — get one at https://console.groq.com/keys

### 1. Clone & setup
```bash
git clone https://github.com/yourname/loan-advisory-agent
cd loan-advisory-agent

python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure environment
```bash
copy .env.example .env
# Edit .env and add your GROQ_API_KEY (free from https://console.groq.com/keys)
```

### 3. Generate synthetic data
```bash
python data/synthetic/generate_data.py
```

### 4. Ingest policy documents into vector store
```bash
python -m backend.rag.document_processor --docs-dir ./data/synthetic/documents
```

### 5. Start the backend
```bash
python -m uvicorn backend.main:app --reload
# API docs at http://localhost:8000/docs
```

### 6. Start the frontend (new terminal)
```bash
venv\Scripts\activate
streamlit run frontend/app.py
# Opens at http://localhost:8501
```

---

## Example Queries

| Query | Agents Invoked |
|-------|----------------|
| "What credit score do I need for a home loan?" | RAG → Synthesizer |
| "Calculate EMI for ₹30L at 8.5% for 20 years" | EMI Calculator |
| "Am I eligible for a personal loan?" | Full pipeline (5 agents) |
| "What documents are required for a car loan?" | RAG → Synthesizer |
| "Flag suspicious activity for applicant A123" | Credit + Fraud |

---

## Project Structure

See **`guide.md`** for a full explanation of every file and folder.

---

## Running Tests

```bash
pytest tests/ -v
pytest tests/test_agents.py -v   # agent unit tests (no LLM needed)
```

---

## Swapping to Production Data

This prototype uses synthetic data. To connect real data:
1. Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`
2. Run `data/schema.sql` on your Supabase instance
3. Replace `data/synthetic/documents/` with real policy PDFs
4. Re-run the document ingestion pipeline
5. Everything else is unchanged ✓

---

*Built as an AI engineering internship prototype. Not financial advice.*