"""
backend/api/routes/documents.py
────────────────────────────────
Document management endpoints — allows loan officers to upload
new policy documents that get ingested into the RAG vector store.

Endpoints:
  POST /api/documents/upload  → Upload and ingest a policy document
  GET  /api/documents/list    → List all indexed documents
  DELETE /api/documents/{id}  → Remove a document from the index
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.database.models import DocumentUploadResponse
from backend.rag.document_processor import ingest_single_file

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB = 20


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """
    Upload a policy document and ingest it into the vector store.
    
    Supports: PDF, DOCX, TXT, MD
    Max size: 20MB
    """
    # Validate file type
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Validate file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB",
        )

    log.info("document_upload_received", filename=file.filename, size_mb=round(size_mb, 2))

    # Save to temp location and ingest
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        chunks = ingest_single_file(tmp_path)
        tmp_path.unlink(missing_ok=True)  # Clean up temp file

        log.info("document_ingested", filename=file.filename, chunks=chunks)

        return DocumentUploadResponse(
            filename=file.filename or "unknown",
            chunks_indexed=chunks,
            status="success",
            message=f"Successfully indexed {chunks} chunks from {file.filename}",
        )

    except Exception as exc:
        log.error("document_ingestion_failed", filename=file.filename, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@router.get("/list")
async def list_documents():
    """
    List all documents currently indexed in the vector store.
    
    TODO: Query ChromaDB collection metadata to return actual document list.
    """
    # TODO: implement ChromaDB metadata query
    return {
        "documents": [
            {"name": "home_loan_policy_v3.pdf", "chunks": 42, "indexed_at": "2024-01-15"},
            {"name": "personal_loan_guidelines.pdf", "chunks": 28, "indexed_at": "2024-01-15"},
            {"name": "eligibility_criteria.pdf", "chunks": 35, "indexed_at": "2024-01-15"},
            {"name": "interest_rate_schedule.pdf", "chunks": 15, "indexed_at": "2024-01-15"},
        ],
        "total_chunks": 120,
        "note": "Replace with real ChromaDB query in production",
    }