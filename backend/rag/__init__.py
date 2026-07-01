"""
backend/rag/__init__.py
Expose the document ingestion pipeline.
"""
from .document_processor import ingest_documents, ingest_single_file

__all__ = ["ingest_documents", "ingest_single_file"]