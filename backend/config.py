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

    # ── Cloud Object Storage (S3 / Cloudflare R2 / MinIO) ─────────────────────
    storage_backend: str = "auto"   # "auto" | "local" | "s3"
    s3_endpoint_url: str = ""       # e.g. https://<account_id>.r2.cloudflarestorage.com
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = ""
    s3_region_name: str = "auto"
    s3_public_url: str = ""         # e.g. https://pub-xxx.r2.dev or https://bucket.s3.amazonaws.com

    # ── Vector store & file storage ───────────────────────────────────────────
    chroma_persist_dir: str = str((Path(__file__).resolve().parent / "chroma_db"))
    faiss_index_dir: str = str((Path(__file__).resolve().parent / "faiss_indexes"))
    upload_dir: str = str((Path(__file__).resolve().parent / "uploads"))
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
    admin_seed_email: str = "tanujthakur3646@gmail.com"
    admin_seed_password: str = "Admin@StudyBuddy2024"

    # ── Auth feature flag ─────────────────────────────────────────────────────
    auth_required: bool = True
    otp_auth_enabled: bool = True
    otp_expire_minutes: int = 5
    otp_simulation_mode: bool = False

    # ── Email / SMTP ──────────────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = "tanujthakur3646@gmail.com"
    smtp_pass: str = "REDACTED"
    smtp_from: str = "StudyBuddy <tanujthakur3646@gmail.com>"
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

    @property
    def is_s3_configured(self) -> bool:
        """True when S3/R2 bucket credentials are configured."""
        if self.storage_backend == "local":
            return False
        return bool(self.s3_bucket_name.strip() and self.s3_access_key_id.strip() and self.s3_secret_access_key.strip())

    @property
    def resolved_database_url(self) -> str:
        """
        Normalizes database URL:
        - postgres:// or postgresql:// -> postgresql+asyncpg://
        - handles sslmode parameters for asyncpg
        - ensures relative SQLite URLs resolve to the persistent backend/ directory
        """
        url = self.database_url.strip()
        if not url:
            backend_dir = Path(__file__).resolve().parent
            return f"sqlite+aiosqlite:///{(backend_dir / 'studybuddy.db').resolve().as_posix()}"

        # PostgreSQL normalization
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]

        if "asyncpg" in url:
            # asyncpg accepts ssl=... rather than sslmode=...
            url = (
                url.replace("sslmode=require", "ssl=require")
                .replace("sslmode=prefer", "ssl=prefer")
                .replace("sslmode=disable", "ssl=disable")
            )

        # SQLite normalization to guaranteed absolute path
        if "sqlite" in url and ":///:memory:" not in url:
            if ":///./" in url or (url.startswith("sqlite+aiosqlite:///") and not Path(url[len("sqlite+aiosqlite:///"):].split("?")[0]).is_absolute()):
                backend_dir = Path(__file__).resolve().parent
                db_file = (backend_dir / "studybuddy.db").resolve().as_posix()
                url = f"sqlite+aiosqlite:///{db_file}"

        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
