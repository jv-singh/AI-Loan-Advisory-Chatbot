"""
backend/agents/nodes/document_retriever.py
────────────────────────────────────────────
Node 2: Document Retriever Agent (RAG)

Responsibilities:
  1. Embed the user query using the same model used at ingestion time
  2. Query TWO Chroma collections:
       - `loan_policies`           (global, shared, always-on)
       - `user_docs`               (per-visitor, filtered by state["user_id"])
  3. Merge the two result sets, dedupe by content, sort by score
  4. Filter by similarity score threshold
  5. Attach retrieved context to state for all downstream agents
  6. Tag each result with `source` ∈ {"policy", "user"} so the synthesizer
     and the UI can label citations differently

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
from langchain_chroma import Chroma

from backend.config import settings
from backend.llm import get_embeddings
from backend.agents.state import LoanAdvisoryState
from backend.rag import USER_COLLECTION_NAME

log = structlog.get_logger(__name__)


# ── Query enrichment ──────────────────────────────────────────────────────────


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


# ── Single-collection search ──────────────────────────────────────────────────


def _search_collection(
    vectorstore: Chroma,
    enriched_query: str,
    where: dict | None,
    k: int,
) -> list[tuple]:
    """
    Run similarity search with relevance scores.
    Returns raw (Document, score) tuples from the underlying API.
    The langchain-chroma wrapper signature is stable across the 1.x line.
    """
    kwargs = {"query": enriched_query, "k": k}
    if where:
        kwargs["filter"] = where
    return vectorstore.similarity_search_with_relevance_scores(**kwargs)


# ── Main node ─────────────────────────────────────────────────────────────────


def run(state: LoanAdvisoryState) -> dict:
    """
    Retrieves relevant document chunks from BOTH the global policy
    collection and the caller's user_docs collection, then merges and
    sorts by similarity score.

    Reads:  state["query"], state["query_entities"], state["query_type"],
            state["user_id"]
    Writes: state["retrieved_documents"], state["retrieval_confidence"],
            state["hallucination_risk"]
    """
    enriched_query = _build_enriched_query(state)
    user_id = state.get("user_id")
    log.info(
        "retrieving_documents",
        query=enriched_query[:80],
        user_id=(user_id[:8] + "...") if user_id else None,
    )

    try:
        embeddings = get_embeddings()
        k = settings.retrieval_top_k

        # ── Open both collections (shared on-disk index) ───────────────────────
        policy_store = Chroma(
            collection_name="loan_policies",
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )
        user_store = Chroma(
            collection_name=USER_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )

        # ── Query global policy collection ────────────────────────────────────
        policy_results = _search_collection(policy_store, enriched_query, None, k)
        log.info("policy_chunks_retrieved", count=len(policy_results))

        # ── Query user_docs collection (only if user_id is present) ───────────
        user_results: list[tuple] = []
        if user_id:
            try:
                user_results = _search_collection(
                    user_store,
                    enriched_query,
                    where={"user_id": user_id},
                    k=k,
                )
                log.info(
                    "user_chunks_retrieved",
                    count=len(user_results),
                    user_id=user_id[:8] + "...",
                )
            except Exception as user_exc:
                # User-store errors must NOT break the global path — log and
                # continue with policy results only.
                log.warning(
                    "user_doc_retrieval_failed",
                    error=str(user_exc),
                    user_id=user_id,
                )

        # ── Merge, dedupe, sort ───────────────────────────────────────────────
        # Tag each result with its source before merging so downstream
        # nodes can distinguish citations.
        tagged: list[tuple] = []
        for doc, score in policy_results:
            tagged.append((doc, score, "policy"))
        for doc, score in user_results:
            tagged.append((doc, score, "user"))

        # Dedupe by (source, page_content) — sometimes a policy doc is
        # reloaded and ends up duplicated in the same collection.
        seen_content: set[str] = set()
        deduped: list[tuple] = []
        for doc, score, source in tagged:
            content = doc.page_content.strip()
            key = f"{source}::{content[:200]}"  # 200 chars is plenty for dedupe
            if key in seen_content:
                continue
            seen_content.add(key)
            deduped.append((doc, score, source))

        # Sort by score desc, take top k.
        deduped.sort(key=lambda x: x[1], reverse=True)
        top = deduped[:k]

        # ── Apply score threshold + format ────────────────────────────────────
        retrieved_docs = []
        scores = []
        below_threshold = 0

        for doc, score, source in top:
            if score < settings.retrieval_score_threshold:
                below_threshold += 1
                continue
            retrieved_docs.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "N/A"),
                "score": round(score, 4),
                "metadata": doc.metadata,
                "doc_source": source,  # "policy" | "user"  ← key new field
            })
            scores.append(score)

        avg_confidence = sum(scores) / len(scores) if scores else 0.0

        log.info(
            "documents_retrieved",
            count=len(retrieved_docs),
            avg_score=round(avg_confidence, 3),
            below_threshold=below_threshold,
            policy_chunks=sum(1 for d in retrieved_docs if d["doc_source"] == "policy"),
            user_chunks=sum(1 for d in retrieved_docs if d["doc_source"] == "user"),
        )

        # ── Hallucination risk (unchanged) ────────────────────────────────────
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
        # but synthesizer will surface a low-confidence warning.
        return {
            "retrieved_documents": [],
            "retrieval_confidence": 0.0,
            "hallucination_risk": "high",
            "error": f"Document retrieval failed: {exc}",
        }
