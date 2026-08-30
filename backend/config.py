from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Primary LLM — OpenAI ─────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Fallback LLM — Groq (used when openai_api_key is absent) ─────────────
    groq_api_key: str = ""
    groq_model: str = "groq/compound-mini"

    # ── Groq model rotation (tried in order when the primary is rate-limited) ─
    # All models confirmed present on this Groq account (queried 2025-07-01).
    # groq/compound-mini → groq/compound → openai/gpt-oss-20b → openai/gpt-oss-120b
    groq_fallback_models: str = "groq/compound,openai/gpt-oss-20b,openai/gpt-oss-120b"

    # ── Database ──────────────────────────────────────────────────────────────
    # Use SQLite for local dev; swap to PostgreSQL URL in production:
    #   postgresql+asyncpg://user:pass@host/dbname
    database_url: str = "sqlite+aiosqlite:///./studybuddy.db"

    # ── Vector store & file storage ───────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    faiss_index_dir: str = "./faiss_indexes"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 200

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: str = "*"

    # ── Rate limiting ─────────────────────────────────────────────────────────
    # Max LLM-backed requests per minute per IP (free tier default)
    rate_limit_per_minute: int = 20

    # ── Observability ─────────────────────────────────────────────────────────
    # Set SENTRY_DSN to enable Sentry error tracking in production.
    # Leave empty (default) to disable Sentry — no errors, no traces sent.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1   # 10% of requests traced

    # ── Chunk tuning ──────────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def groq_fallback_models_list(self) -> list[str]:
        return [m.strip() for m in self.groq_fallback_models.split(",") if m.strip()]

    @property
    def llm_provider(self) -> str:
        """Returns 'openai' or 'groq' based on which key is configured."""
        if self.openai_api_key.strip():
            return "openai"
        if self.groq_api_key.strip():
            return "groq"
        return "none"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
