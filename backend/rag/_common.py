"""
backend/rag/_common.py
──────────────────────
Shared building blocks for the RAG ingest pipeline.

Both the global policy ingester (`document_processor.py`) and the
per-user document ingester (`user_document_processor.py`) use the same
loaders, hash function, and text-splitter factory. Keeping them in one
place means a new file type or chunking change only has to be made once.

This module deliberately has no top-level side effects — it does not
open the vector store. Functions that touch ChromaDB live in the
ingester modules.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import structlog
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

from backend.config import settings

log = structlog.get_logger(__name__)


# ── Supported file types ───────────────────────────────────────────────────────
# Add new extensions here and both the global and per-user ingesters pick
# them up automatically. Keep the file_type string lowercase + dotted.
LOADERS: dict[str, type] = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt":  TextLoader,
    ".md":   TextLoader,
}


def file_hash(path: Path) -> str:
    """
    SHA-256 hex digest of a file's contents.
    Used to dedup re-uploads of the same bytes.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_document(path: Path) -> list:
    """
    Load a file using the loader mapped to its extension.
    Tags each returned Document with `source`, `full_path`, `file_type`
    metadata. Returns [] on unsupported extension or load failure.
    """
    ext = path.suffix.lower()
    loader_cls = LOADERS.get(ext)
    if not loader_cls:
        log.warning("unsupported_file_type", path=str(path), ext=ext)
        return []

    try:
        docs = loader_cls(str(path)).load()
        for doc in docs:
            doc.metadata.update({
                "source": path.name,
                "full_path": str(path),
                "file_type": ext,
            })
        log.info("document_loaded", file=path.name, pages=len(docs))
        return docs
    except Exception as exc:
        log.error("document_load_failed", path=str(path), error=str(exc))
        return []


@lru_cache(maxsize=1)
def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """
    Singleton text splitter. Cached so we don't rebuild the regex state
    on every chunking call.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
