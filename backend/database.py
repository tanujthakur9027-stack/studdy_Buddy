"""
database.py — SQLAlchemy async engine + session factory.

Uses SQLite (via aiosqlite) for local development.
Switch to PostgreSQL in production by setting DATABASE_URL in .env:
  DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

# Create async engine — echo=False in prod; set echo=True to debug SQL
engine = create_async_engine(
    settings.database_url,
    echo=False,
    # For SQLite: allow shared connection across threads (needed for async)
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
