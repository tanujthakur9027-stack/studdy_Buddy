from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Resolve .env relative to this file so the server works regardless of the
# working directory it is started from (e.g. project root vs backend/).
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # ── Primary LLM — OpenAI ─────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Fallback LLM — Groq (used when openai_api_key is absent) ─────────────
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"

    # ── Groq model rotation (tried in order when the primary is rate-limited) ─
    # Models verified available on this Groq account via /models endpoint.
    # qwen/qwen3.8-27b → openai/gpt-oss-20b → openai/gpt-oss-120b
    groq_fallback_models: str = "openai/gpt-oss-20b,openai/gpt-oss-120b"

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

    # ── Auth ──────────────────────────────────────────────────────────────────
    # secret_key MUST be set via env var in production; default only used for
    # local dev. Application startup will refuse to start if this equals the
    # sentinel string below AND the env says we're in production.
    secret_key: str = ""   # Fail-secure: empty = no default; env var required
    access_token_expire_minutes: int = 60
    admin_seed_email: str = "admin@studybuddy.com"
    admin_seed_password: str = "Admin@StudyBuddy2024"

    # ── Auth feature flag ─────────────────────────────────────────────────────
    # AUTH_REQUIRED=false → all AI endpoints accept unauthenticated requests
    # (anonymous user). Keeps the legacy Next.js frontend working without tokens.
    # AUTH_REQUIRED=true  → every AI endpoint requires a valid JWT.
    auth_required: bool = True

    # ── Email / SMTP ──────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@studybuddy.com"
    app_base_url: str = "http://localhost:3000"

    # ── File limits ───────────────────────────────────────────────────────────
    assignment_file_max_mb: int = 50
    note_file_max_mb: int = 50
    profile_photo_max_mb: int = 5

    # ── Timetable ─────────────────────────────────────────────────────────────
    period_duration_minutes: int = 45
    lunch_duration_minutes: int = 45

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

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
