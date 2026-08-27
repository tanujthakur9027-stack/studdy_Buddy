from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── OpenAI LLM ────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Vector store & file storage ───────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
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
