"""
backend/llm.py
──────────────
Single source of truth for the LLM and embedding model instances.

Why this exists
───────────────
The project was originally wired to OpenAI for both chat and embeddings.
Groq now provides the chat model (free tier) but does NOT host an embedding
model, so we run a local sentence-transformer for embeddings.

All agent nodes import `get_llm()` / `get_embeddings()` from here so the
provider can be swapped via config without touching call sites.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.config import settings


@lru_cache(maxsize=1)
def get_llm(temperature: float | None = None) -> Any:
    """
    Return the configured chat model.

    Default provider is Groq (free, OpenAI-compatible). Override by setting
    LLM_PROVIDER=openai in .env if you want to use OpenAI instead — you will
    need a valid OPENAI_API_KEY in that case.
    """
    temp = settings.temperature if temperature is None else temperature

    provider = getattr(settings, "llm_provider", "groq")

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temp,
            api_key=settings.openai_api_key,
        )

    # Default: Groq
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=settings.groq_model,
        temperature=temp,
        groq_api_key=settings.groq_api_key,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> Any:
    """
    Return the configured embedding model.

    Default provider is HuggingFace sentence-transformers (local, free).
    Override with EMBEDDING_PROVIDER=openai if you want OpenAI embeddings.
    """
    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

    # Default: local sentence-transformers via HuggingFace
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.hf_embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
