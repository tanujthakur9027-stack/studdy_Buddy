"""
database.py — SQLAlchemy async engine + session factory.

Uses SQLite (via aiosqlite) for local development.
Switch to PostgreSQL in production by setting DATABASE_URL in .env:
  DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

_is_sqlite = "sqlite" in settings.resolved_database_url

from sqlalchemy.pool import NullPool

# Create async engine — echo=False in prod; set echo=True to debug SQL
# NullPool is used for both SQLite (avoids thread affinity locks) and Neon PostgreSQL (avoids
# stale idle connection drops across cloud NAT and PgBouncer connection lifecycles).
_engine_kwargs: dict = {
    "echo": False,
    "poolclass": NullPool,
    "connect_args": {"check_same_thread": False} if _is_sqlite else {
        "ssl": True,
        "statement_cache_size": 0,
        "timeout": 30,
        "command_timeout": 30,
    },
}

engine = create_async_engine(settings.resolved_database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


import models.db_models  # noqa: F401, E402


# ── Column additions that can't be expressed via create_all ──────────────────
# Each ALTER TABLE is idempotent: silently ignored if the column already exists.
_MIGRATIONS_SQLITE = [
    # Phase 1 — per-user privacy
    "ALTER TABLE documents ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE quiz_sessions ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE quiz_results ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE saved_answers ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE chat_sessions ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE flashcard_sessions ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE feynman_results ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE shared_resources ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE SET NULL",
    # Class-Based Management migrations
    "ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT 0",
    "ALTER TABLE notifications ADD COLUMN class_id TEXT",
    "ALTER TABLE assessment_categories ADD COLUMN class_id TEXT",
    "ALTER TABLE marks ADD COLUMN class_id TEXT",
]

_MIGRATIONS_POSTGRES = [
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE quiz_sessions ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE saved_answers ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE flashcard_sessions ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE feynman_results ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE CASCADE",
    "ALTER TABLE shared_resources ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE SET NULL",
    # Class-Based Management migrations
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT FALSE",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS class_id TEXT",
    "ALTER TABLE assessment_categories ADD COLUMN IF NOT EXISTS class_id TEXT",
    "ALTER TABLE marks ADD COLUMN IF NOT EXISTS class_id TEXT",
]


async def _seed_legacy_class_and_roles(conn) -> None:
    """Idempotently create Legacy class and migrate existing users/students."""
    import uuid
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()

    async def _exec_safe(stmt, params=None):
        if not _is_sqlite:
            async with conn.begin_nested():
                return await conn.execute(stmt, params or {})
        else:
            return await conn.execute(stmt, params or {})

    try:
        # 1. Update all existing admin users to is_super_admin = True
        await _exec_safe(
            text("UPDATE users SET is_super_admin = :t WHERE role = 'admin' AND (is_super_admin IS NULL OR is_super_admin = :f)"),
            {"t": True, "f": False}
        )

        # 2. Get an admin id to use as creator
        res = await _exec_safe(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1"))
        row = res.fetchone()
        admin_id = row[0] if row else "system-seed"

        # 3. Create 'Legacy / Unassigned' class if not present
        res_cls = await _exec_safe(text("SELECT id FROM school_classes WHERE id = 'legacy-default-class' OR (name = 'Legacy' AND section = 'General')"))
        legacy_row = res_cls.fetchone()
        if legacy_row:
            legacy_id = legacy_row[0]
        else:
            legacy_id = "legacy-default-class"
            await _exec_safe(
                text("""
                    INSERT INTO school_classes (id, name, section, academic_year, created_by, created_at, is_active)
                    VALUES (:id, 'Legacy', 'General', '2024-2025', :creator, :now, :act)
                """),
                {"id": legacy_id, "creator": admin_id, "now": now_str, "act": True}
            )

        # 4. Migrate any student_profiles that don't have a class_id
        res_stu = await _exec_safe(text("SELECT user_id, student_id FROM student_profiles WHERE class_id IS NULL OR class_id = ''"))
        for uid, sid in res_stu.fetchall():
            await _exec_safe(
                text("UPDATE student_profiles SET class_id = :cls_id WHERE user_id = :uid"),
                {"cls_id": legacy_id, "uid": uid}
            )
            # Check if active enrollment exists
            res_enr = await _exec_safe(
                text("SELECT id FROM class_enrollments WHERE student_id = :uid AND is_active = :act"),
                {"uid": uid, "act": True}
            )
            if not res_enr.fetchone():
                roll = sid if sid else f"ROLL-{uid[:8]}"
                await _exec_safe(
                    text("""
                        INSERT INTO class_enrollments (id, class_id, student_id, roll_number, joined_at, is_active)
                        VALUES (:eid, :cls_id, :uid, :roll, :now, :act)
                    """),
                    {"eid": str(uuid.uuid4()), "cls_id": legacy_id, "uid": uid, "roll": roll, "now": now_str, "act": True}
                )
    except Exception:
        # Table or column might not be ready yet in some test isolation setups; safe to continue
        pass
    except Exception:
        # Table or column might not be ready yet in some test isolation setups; safe to continue
        pass


async def _run_migrations(conn) -> None:
    """Apply idempotent column-addition migrations."""
    migrations = _MIGRATIONS_SQLITE if _is_sqlite else _MIGRATIONS_POSTGRES
    for stmt in migrations:
        try:
            if not _is_sqlite:
                async with conn.begin_nested():
                    await conn.execute(text(stmt))
            else:
                await conn.execute(text(stmt))
        except Exception:
            pass
    if _is_sqlite:
        try:
            # Ensure student_id index is non-unique so roll numbers are scoped per class in class_enrollments
            await conn.execute(text("DROP INDEX IF EXISTS ix_student_profiles_student_id"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_student_profiles_student_id ON student_profiles (student_id)"))
        except Exception:
            pass
    await _seed_legacy_class_and_roles(conn)


async def init_db() -> None:
    """Create all tables on startup (idempotent). Enable WAL mode for SQLite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if _is_sqlite:
            await _run_migrations(conn)
            try:
                await conn.execute(text("PRAGMA journal_mode=WAL"))
                await conn.execute(text("PRAGMA synchronous=NORMAL"))
                await conn.execute(text("PRAGMA cache_size=-32000"))   # 32 MB page cache
                await conn.execute(text("PRAGMA temp_store=MEMORY"))
            except Exception:
                pass
        else:
            await _seed_legacy_class_and_roles(conn)


async def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
