"""
backend/rag/document_processor.py
───────────────────────────────────
RAG Pipeline: Document Ingestion

Handles:
  1. Loading PDFs, DOCX, and plain text files
  2. Chunking with RecursiveCharacterTextSplitter (preserves sentence boundaries)
  3. Embedding and indexing chunks into ChromaDB
  4. Tracking ingested documents to avoid re-processing

Run this once before starting the server to populate the vector store:
  python -m backend.rag.document_processor --docs-dir ./data/synthetic/documents

The same pipeline runs at runtime when loan officers upload new policy docs
via the /api/documents/upload endpoint.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import structlog
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_chroma import Chroma

from backend.config import settings
from backend.llm import get_embeddings

log = structlog.get_logger(__name__)

# ── Supported file types ───────────────────────────────────────────────────────
LOADERS: dict[str, type] = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt":  TextLoader,
    ".md":   TextLoader,
}


def _file_hash(path: Path) -> str:
    """SHA256 hash of file content — used to skip already-ingested files."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_document(path: Path) -> list:
    """Load a document using the appropriate loader for its extension."""
    ext = path.suffix.lower()
    loader_cls = LOADERS.get(ext)
    if not loader_cls:
        log.warning("unsupported_file_type", path=str(path), ext=ext)
        return []

    try:
        loader = loader_cls(str(path))
        docs = loader.load()
        # Tag each chunk with source metadata
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


def ingest_documents(docs_dir: str | Path, force_reingest: bool = False) -> int:
    """
    Ingests all supported documents from docs_dir into ChromaDB.

    Args:
        docs_dir: Directory containing policy PDFs / docs
        force_reingest: If True, re-embeds even already-indexed docs

    Returns:
        Number of chunks indexed
    """
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        log.error("docs_directory_not_found", path=str(docs_dir))
        return 0

    # ── Set up embedding + vector store ───────────────────────────────────────
    embeddings = get_embeddings()
    vectorstore = Chroma(
        collection_name="loan_policies",
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )

    # ── Text splitter ──────────────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks = []
    processed_files = 0

    for file_path in sorted(docs_dir.rglob("*")):
        if file_path.suffix.lower() not in LOADERS:
            continue

        file_hash = _file_hash(file_path)

        # Check if already indexed (metadata-based dedup)
        if not force_reingest:
            existing = vectorstore.get(where={"file_hash": file_hash})
            if existing and existing.get("ids"):
                log.info("document_already_indexed_skipping", file=file_path.name)
                continue

        raw_docs = _load_document(file_path)
        if not raw_docs:
            continue

        chunks = splitter.split_documents(raw_docs)

        # Add hash to each chunk's metadata
        for chunk in chunks:
            chunk.metadata["file_hash"] = file_hash

        all_chunks.extend(chunks)
        processed_files += 1
        log.info(
            "document_chunked",
            file=file_path.name,
            chunks=len(chunks),
        )

    if not all_chunks:
        log.info("no_new_documents_to_index")
        return 0

    # ── Batch embed and store ──────────────────────────────────────────────────
    log.info("embedding_chunks", total=len(all_chunks), files=processed_files)
    vectorstore.add_documents(all_chunks)
    log.info("ingestion_complete", chunks_indexed=len(all_chunks))

    return len(all_chunks)


def ingest_single_file(file_path: str | Path) -> int:
    """
    Ingests a single uploaded file. Called by the /api/documents/upload endpoint.
    Returns number of chunks indexed.
    """
    return ingest_documents(Path(file_path).parent, force_reingest=True)


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    from rich.console import Console

    console = Console()

    parser = argparse.ArgumentParser(description="Ingest documents into vector store")
    parser.add_argument(
        "--docs-dir",
        default="./data/synthetic/documents",
        help="Directory containing policy documents",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even already-indexed documents",
    )
    args = parser.parse_args()

    console.print(f"[bold]Ingesting documents from:[/bold] {args.docs_dir}")
    count = ingest_documents(args.docs_dir, force_reingest=args.force)
    console.print(f"[green]✓ Indexed {count} chunks into ChromaDB[/green]")