"""
backend/rag/__init__.py
Expose the document ingestion pipeline.
"""
from .document_processor import ingest_documents, ingest_single_file
from .user_document_processor import (
    USER_COLLECTION_NAME,
    delete_user_document,
    ingest_user_file,
    list_user_documents,
)

__all__ = [
    "ingest_documents",
    "ingest_single_file",
    "ingest_user_file",
    "list_user_documents",
    "delete_user_document",
    "USER_COLLECTION_NAME",
]