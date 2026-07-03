"""
backend/rag/user_document_processor.py
──────────────────────────────────────
Per-user document ingestion and listing.

Why a separate module from `document_processor.py`:
  - Different collection (`user_docs` vs `loan_policies`)
  - Different metadata contract — every chunk carries `user_id` + `doc_id`
  - Different ownership model — list/delete are scoped to the calling user
  - The two ingest paths share loaders, splitter, and embedding factory
    via `backend.rag._common`, so the parsing/chunking logic is identical

Tenancy model:
  ONE shared `user_docs` Chroma collection, scoped by `user_id` metadata.
  NOT one collection per user — that pattern does not scale and forces
  collection-rebuild operations on every new visitor.

API surface:
  ingest_user_file(path, user_id)   -> {doc_id, chunks_indexed, filename}
  list_user_documents(user_id)      -> list[dict]  (one entry per file)
  delete_user_document(doc_id, user_id) -> bool   (False if not owned)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import structlog
from langchain_chroma import Chroma

from backend.config import settings
from backend.llm import get_embeddings
from backend.rag._common import (
    LOADERS,
    file_hash,
    get_text_splitter,
    load_document,
)

log = structlog.get_logger(__name__)

USER_COLLECTION_NAME = "user_docs"


# ── Vector store helpers ───────────────────────────────────────────────────────


def _open_user_vectorstore() -> Chroma:
    """Open the shared user-docs collection. Cheap — reuses the same on-disk
    index that other processes may have written to."""
    return Chroma(
        collection_name=USER_COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


# ── Ingest ─────────────────────────────────────────────────────────────────────


def ingest_user_file(file_path: str | Path, user_id: str) -> dict:
    """
    Parse, chunk, embed, and store a user-uploaded file in `user_docs`.

    Every chunk's metadata is stamped with:
        user_id, doc_id, filename, file_type, file_hash, source, uploaded_at

    Args:
        file_path: path to the uploaded file (caller is responsible for cleanup)
        user_id:   the visitor's UUID (from X-User-Id header)

    Returns:
        {"doc_id": str, "chunks_indexed": int, "filename": str}

    Raises:
        ValueError: if the file extension is not in LOADERS
        RuntimeError: on parse/embed failure
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    ext = file_path.suffix.lower()
    if ext not in LOADERS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Allowed: {sorted(LOADERS)}"
        )

    doc_id = str(uuid.uuid4())
    file_hash_value = file_hash(file_path)
    uploaded_at = datetime.now(timezone.utc).isoformat()

    log.info(
        "user_doc_ingest_start",
        user_id=user_id,
        doc_id=doc_id,
        file=file_path.name,
    )

    raw_docs = load_document(file_path)
    if not raw_docs:
        raise RuntimeError(f"Failed to load any content from {file_path.name}")

    chunks = get_text_splitter().split_documents(raw_docs)
    if not chunks:
        raise RuntimeError(f"Document {file_path.name} produced 0 chunks")

    for chunk in chunks:
        chunk.metadata.update({
            "user_id": user_id,
            "doc_id": doc_id,
            "filename": file_path.name,
            "file_type": ext,
            "file_hash": file_hash_value,
            "uploaded_at": uploaded_at,
        })

    vectorstore = _open_user_vectorstore()
    vectorstore.add_documents(chunks)

    log.info(
        "user_doc_ingested",
        user_id=user_id,
        doc_id=doc_id,
        file=file_path.name,
        chunks=len(chunks),
    )

    return {
        "doc_id": doc_id,
        "chunks_indexed": len(chunks),
        "filename": file_path.name,
    }


# ── List ───────────────────────────────────────────────────────────────────────


def list_user_documents(user_id: str) -> list[dict]:
    """
    Return one entry per uploaded file for this user.

    Implementation: query Chroma for all chunks where user_id matches,
    then group by doc_id in Python. The collection is small relative to
    the global one, so the in-Python aggregation is fine.

    Each entry: {doc_id, filename, file_type, chunks, uploaded_at}
    """
    vectorstore = _open_user_vectorstore()
    raw = vectorstore.get(where={"user_id": user_id})

    if not raw or not raw.get("ids"):
        return []

    grouped: dict[str, dict] = defaultdict(
        lambda: {"chunks": 0, "filename": None, "file_type": None,
                 "uploaded_at": None}
    )

    for meta in raw.get("metadatas", []):
        if not meta:
            continue
        doc_id = meta.get("doc_id")
        if not doc_id:
            continue
        grouped[doc_id]["chunks"] += 1
        # Last-write-wins for filename/uploaded_at (they're identical per doc)
        grouped[doc_id]["filename"] = meta.get("filename") or grouped[doc_id]["filename"]
        grouped[doc_id]["file_type"] = meta.get("file_type") or grouped[doc_id]["file_type"]
        grouped[doc_id]["uploaded_at"] = meta.get("uploaded_at") or grouped[doc_id]["uploaded_at"]

    return [
        {
            "doc_id": doc_id,
            "filename": info["filename"],
            "file_type": info["file_type"],
            "chunks": info["chunks"],
            "uploaded_at": info["uploaded_at"],
        }
        for doc_id, info in sorted(
            grouped.items(),
            key=lambda kv: kv[1]["uploaded_at"] or "",
            reverse=True,
        )
    ]


# ── Delete ─────────────────────────────────────────────────────────────────────


def delete_user_document(doc_id: str, user_id: str) -> bool:
    """
    Delete all chunks belonging to `doc_id` if and only if they belong to
    `user_id`. Returns True if anything was deleted, False otherwise.

    The ownership check is enforced server-side: we read the chunk
    metadata and verify `user_id` matches before issuing the delete.
    """
    if not doc_id or not user_id:
        return False

    vectorstore = _open_user_vectorstore()
    raw = vectorstore.get(where={"doc_id": doc_id})

    if not raw or not raw.get("ids"):
        return False

    # Ownership check — refuse if any chunk has a different user_id.
    # (In practice all chunks of a doc share the same user_id since we set
    # it at ingest time, but verifying is cheap and defensive.)
    owning_ids: list[str] = []
    for cid, meta in zip(raw["ids"], raw.get("metadatas", [])):
        if meta and meta.get("user_id") == user_id:
            owning_ids.append(cid)

    if not owning_ids:
        log.warning(
            "user_doc_delete_denied",
            user_id=user_id,
            doc_id=doc_id,
            reason="not_owner",
        )
        return False

    vectorstore.delete(ids=owning_ids)
    log.info(
        "user_doc_deleted",
        user_id=user_id,
        doc_id=doc_id,
        chunks=len(owning_ids),
    )
    return True
