from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Resolve .env relative to this file so the server works regardless of the
# working directory it is started from (e.g. project root vs backend/).
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # ── LLM — Groq (primary) ──────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3-27b"

    # ── Groq model rotation (tried in order when the primary is rate-limited) ─
    groq_fallback_models: str = "openai/gpt-oss-20b,openai/gpt-oss-120b"

    # ── LLM — Gemini (fallback when Groq is unavailable) ─────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

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
    rate_limit_per_minute: int = 20

    # ── Observability ─────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # ── Chunk tuning ──────────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 120

    # ── Auth ──────────────────────────────────────────────────────────────────
    secret_key: str = ""
    access_token_expire_minutes: int = 60
    admin_seed_email: str = "admin@studybuddy.com"
    admin_seed_password: str = "Admin@StudyBuddy2024"

    # ── Auth feature flag ─────────────────────────────────────────────────────
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
    def llm_configured(self) -> bool:
        """True when at least one LLM key is present."""
        return bool(self.groq_api_key.strip() or self.gemini_api_key.strip())

    @property
    def llm_provider(self) -> str:
        """Returns 'groq', 'gemini', or 'none'."""
        if self.groq_api_key.strip():
            return "groq"
        if self.gemini_api_key.strip():
            return "gemini"
        return "none"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
