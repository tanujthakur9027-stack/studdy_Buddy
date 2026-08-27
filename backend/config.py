from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Groq LLM ──────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Vector store & file storage ───────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    # FAISS in-memory index is kept per-process; this dir is used for optional
    # persistence/serialisation of FAISS indexes to disk between restarts.
    # ⚠️  FAISS is in-memory only — requires --workers 1 (see render.yaml / Dockerfile CMD)
    faiss_index_dir: str = "./faiss_indexes"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 20

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Chunk tuning ──────────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
