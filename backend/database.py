"""
database.py — SQLAlchemy async engine + session factory.

Uses SQLite (via aiosqlite) for local development.
Switch to PostgreSQL in production by setting DATABASE_URL in .env:
  DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
"""
from __future__ import annotations

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

_is_sqlite = "sqlite" in settings.database_url

# Create async engine — echo=False in prod; set echo=True to debug SQL
engine = create_async_engine(
    settings.database_url,
    echo=False,
    # For SQLite: allow shared connection across threads (needed for async)
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Pool tuning: keep connections warm, don't spin up a new one per request
    pool_size=5 if not _is_sqlite else None,
    max_overflow=10 if not _is_sqlite else None,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup (idempotent). Enable WAL mode for SQLite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # WAL journal mode allows concurrent reads while a write is in progress.
        # This eliminates "database is locked" errors under concurrent requests
        # and cuts read latency significantly on the free-tier Render instance.
        if _is_sqlite:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA cache_size=-32000"))   # 32 MB page cache
            await conn.execute(text("PRAGMA temp_store=MEMORY"))


async def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
