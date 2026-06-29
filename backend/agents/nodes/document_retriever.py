"""
backend/agents/nodes/document_retriever.py
────────────────────────────────────────────
Node 2: Document Retriever Agent (RAG)

Responsibilities:
  1. Embed the user query using the same model used at ingestion time
  2. Query the Chroma vector store for semantically similar chunks
  3. Filter results by similarity score threshold
  4. Attach retrieved context to state for all downstream agents

This node is the FOUNDATION of hallucination prevention.
Every downstream node and the synthesizer use `retrieved_documents`
as the ground truth — they are not allowed to answer without it.

Retrieval strategy:
  - Primary: Vector similarity (cosine) via ChromaDB
  - Reranking: TODO — cross-encoder reranker (MixedBread or Cohere)
  - Fallback: Keyword search on Supabase full-text index
"""

from __future__ import annotations

import structlog
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from backend.config import settings
from backend.agents.state import LoanAdvisoryState

log = structlog.get_logger(__name__)


def _build_enriched_query(state: LoanAdvisoryState) -> str:
    """
    Augment the raw query with extracted entities for better retrieval.
    Example: "Am I eligible?" + entities → "loan eligibility home loan 500000 salaried"
    """
    query = state["query"]
    entities = state.get("query_entities", {})
    query_type = state.get("query_type", "general")

    enrichment_parts = [query]

    if query_type:
        enrichment_parts.append(query_type)

    if loan_type := entities.get("loan_type"):
        enrichment_parts.append(f"{loan_type} loan")

    if loan_amount := entities.get("loan_amount"):
        enrichment_parts.append(f"loan amount {loan_amount}")

    return " ".join(enrichment_parts)


def run(state: LoanAdvisoryState) -> dict:
    """
    Retrieves relevant document chunks from the vector store.

    Reads:  state["query"], state["query_entities"], state["query_type"]
    Writes: state["retrieved_documents"], state["retrieval_confidence"]
    """
    enriched_query = _build_enriched_query(state)
    log.info("retrieving_documents", query=enriched_query[:80])

    try:
        embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

        vectorstore = Chroma(
            collection_name="loan_policies",
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )

        # Retrieve with relevance scores (returns list of (Document, score) tuples)
        results = vectorstore.similarity_search_with_relevance_scores(
            query=enriched_query,
            k=settings.retrieval_top_k,
        )

        # Filter by threshold and format
        retrieved_docs = []
        scores = []

        for doc, score in results:
            if score >= settings.retrieval_score_threshold:
                retrieved_docs.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", "N/A"),
                    "score": round(score, 4),
                    "metadata": doc.metadata,
                })
                scores.append(score)

        avg_confidence = sum(scores) / len(scores) if scores else 0.0

        log.info(
            "documents_retrieved",
            count=len(retrieved_docs),
            avg_score=round(avg_confidence, 3),
            below_threshold=len(results) - len(retrieved_docs),
        )

        # Determine hallucination risk based on retrieval quality
        if avg_confidence >= 0.7:
            hallucination_risk = "low"
        elif avg_confidence >= 0.45:
            hallucination_risk = "medium"
        else:
            hallucination_risk = "high"

        return {
            "retrieved_documents": retrieved_docs,
            "retrieval_confidence": avg_confidence,
            "hallucination_risk": hallucination_risk,
        }

    except Exception as exc:
        log.error("retrieval_failed", error=str(exc))
        # Non-fatal: downstream agents can still run with empty context
        # but synthesizer will surface a low-confidence warning
        return {
            "retrieved_documents": [],
            "retrieval_confidence": 0.0,
            "hallucination_risk": "high",
            "error": f"Document retrieval failed: {exc}",
        }