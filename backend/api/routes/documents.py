"""
backend/api/routes/documents.py
────────────────────────────────
Document management endpoints — split into two ownership scopes:

  1. Global policy ingest (admin / CLI only) — unchanged from the original
     CLI flow that targets the `loan_policies` collection.

  2. Per-user document library — new. Each visitor identified by the
     `X-User-Id` header gets:
       POST   /api/documents/upload  → ingest a file into the user's library
       GET    /api/documents/list    → list THIS user's files
       DELETE /api/documents/{id}    → delete a file the user owns

Tenancy:
  The `user_docs` collection is shared on disk; per-user isolation is
  enforced by the `user_id` metadata field stamped on every chunk at
  ingest time. List and delete verify ownership server-side from
  Chroma metadata, not from the client.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.api.middleware import get_user_id_required
from backend.database.models import (
    DocumentUploadResponse,
    UserDocumentListResponse,
    UserDocumentInfo,
)
from backend.rag.user_document_processor import (
    delete_user_document,
    ingest_user_file,
    list_user_documents,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB = 20


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id_required),
) -> DocumentUploadResponse:
    """
    Upload a document and ingest it into the caller's user_docs library.

    Supports: PDF, DOCX, TXT, MD
    Max size: 20MB

    Requires `X-User-Id` header. Each uploaded file is tagged with the
    caller's user_id so retrieval can scope queries to their own docs.
    """
    # Validate file type
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Validate file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB",
        )

    log.info(
        "document_upload_received",
        user_id=user_id,
        filename=file.filename,
        size_mb=round(size_mb, 2),
    )

    # Save to temp location and ingest
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = ingest_user_file(tmp_path, user_id=user_id)
        finally:
            tmp_path.unlink(missing_ok=True)  # always clean up the temp file

        chunks = result["chunks_indexed"]
        doc_id = result["doc_id"]
        log.info(
            "document_ingested",
            user_id=user_id,
            filename=file.filename,
            doc_id=doc_id,
            chunks=chunks,
        )

        return DocumentUploadResponse(
            filename=file.filename or "unknown",
            chunks_indexed=chunks,
            chunks=chunks,
            doc_id=doc_id,
            source="user",
            status="success",
            message=f"Successfully indexed {chunks} chunks from {file.filename}",
        )

    except ValueError as exc:
        # Validation errors (unsupported type, missing file) → 400
        log.warning("document_validation_failed", filename=file.filename, error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(
            "document_ingestion_failed",
            user_id=user_id,
            filename=file.filename,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@router.get("/list", response_model=UserDocumentListResponse)
async def list_user_docs(
    user_id: str = Depends(get_user_id_required),
) -> UserDocumentListResponse:
    """
    List all documents THIS user has uploaded.

    Returns one entry per file (not per chunk), deduped by doc_id.
    Ownership is enforced by filtering on the `user_id` metadata field
    in the Chroma `user_docs` collection.
    """
    log.info("document_list_requested", user_id=user_id)

    docs = list_user_documents(user_id)
    user_doc_infos = [
        UserDocumentInfo(
            doc_id=d["doc_id"],
            filename=d["filename"],
            file_type=d["file_type"],
            chunks=d["chunks"],
            uploaded_at=d["uploaded_at"],
        )
        for d in docs
    ]

    return UserDocumentListResponse(
        user_documents=user_doc_infos,
        total_user_chunks=sum(d.chunks for d in user_doc_infos),
    )


@router.delete("/{doc_id}")
async def delete_user_doc(
    doc_id: str,
    user_id: str = Depends(get_user_id_required),
) -> dict:
    """
    Delete a document from the caller's library.

    Server-side ownership check: we read the chunk metadata and verify
    `user_id` matches before issuing the delete. Returns 404 if the doc
    doesn't exist, 403 if it's owned by someone else (we return 404 in
    both cases to avoid leaking the existence of other users' docs).
    """
    log.info("document_delete_requested", user_id=user_id, doc_id=doc_id)

    deleted = delete_user_document(doc_id, user_id)
    if not deleted:
        # Don't distinguish "doesn't exist" from "not yours" — both are
        # indistinguishable to the caller. 404 is the safe response.
        raise HTTPException(
            status_code=404,
            detail="Document not found in your library.",
        )

    return {"status": "deleted", "doc_id": doc_id}
