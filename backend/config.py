"""
backend/config.py
─────────────────
Central configuration loaded from .env via Pydantic Settings.
All modules import Settings from here — never read os.environ directly.
"""

from functools import lru_cache
from typing import Annotated, List
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Groq (free-tier LLM) ──────────────────────────────────────────────────
    # Groq exposes an OpenAI-compatible chat endpoint, so we route the
    # chat model through `groq_api_key` + `groq_model`. Get a free key at
    # https://console.groq.com/keys
    llm_provider: str = Field("groq", alias="LLM_PROVIDER")
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    groq_model: str = Field("llama-3.1-8b-instant", alias="GROQ_MODEL")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")

    # ── Embeddings (local, free — no API key required) ────────────────────────
    # Groq does not host an embedding model, so we run a local
    # sentence-transformer instead. Override via env if you want OpenAI/HF.
    embedding_provider: str = Field("huggingface", alias="EMBEDDING_PROVIDER")
    hf_embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2", alias="HF_EMBEDDING_MODEL"
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        "text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_key: str = Field(default="", alias="SUPABASE_SERVICE_KEY")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite:///./dev.db", alias="DATABASE_URL"
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = Field("development", alias="APP_ENV")
    app_secret_key: str = Field("dev-secret-change-me", alias="APP_SECRET_KEY")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default=["http://localhost:8501", "http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        """Accept JSON arrays or comma-separated strings from .env.

        NoDecode tells pydantic-settings not to json.loads() the env string,
        so this validator receives the raw string from the .env file.
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                import json
                return json.loads(v)
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, (list, tuple)):
            return list(v)
        return v

    # ── RAG ───────────────────────────────────────────────────────────────────
    chroma_persist_dir: str = Field("./data/chroma_db", alias="CHROMA_PERSIST_DIR")
    chunk_size: int = Field(800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(150, alias="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(5, alias="RETRIEVAL_TOP_K")
    # NOTE: all-MiniLM-L6-v2 is a 384-dim model that produces low absolute
    # cosine similarity scores. A threshold of 0.35 silently drops most
    # genuinely-relevant chunks. 0.20 is a meaningful floor for this model
    # while still filtering out noise. If you swap to a larger embedding
    # model (e.g. text-embedding-3-small), raise this back to ~0.35.
    retrieval_score_threshold: float = Field(0.20, alias="RETRIEVAL_SCORE_THRESHOLD")

    # ── Agent ─────────────────────────────────────────────────────────────────
    max_iterations: int = Field(10, alias="MAX_ITERATIONS")
    temperature: float = Field(0.1, alias="TEMPERATURE")
    hallucination_threshold: float = Field(0.5, alias="HALLUCINATION_THRESHOLD")

    # ── Frontend ──────────────────────────────────────────────────────────────
    backend_url: str = Field("http://localhost:8000", alias="BACKEND_URL")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton. Call get_settings() anywhere in the app."""
    return Settings()


# Convenience alias used across modules
settings = get_settings()