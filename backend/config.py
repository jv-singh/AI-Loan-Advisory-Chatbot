"""
backend/config.py
─────────────────
Central configuration loaded from .env via Pydantic Settings.
All modules import Settings from here — never read os.environ directly.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
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
    cors_origins: list[str] = Field(
        default=["http://localhost:8501", "http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    # ── RAG ───────────────────────────────────────────────────────────────────
    chroma_persist_dir: str = Field("./data/chroma_db", alias="CHROMA_PERSIST_DIR")
    chunk_size: int = Field(800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(150, alias="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(5, alias="RETRIEVAL_TOP_K")
    retrieval_score_threshold: float = Field(0.35, alias="RETRIEVAL_SCORE_THRESHOLD")

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