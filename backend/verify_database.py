"""
verify_database.py — Diagnostic tool to check database status, tables, and records.
Supports testing both current active database and any target PostgreSQL connection.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from config import get_settings
from database import engine, Base, init_db, AsyncSessionLocal
import models.db_models  # Ensure all tables are registered


async def check_database():
    settings = get_settings()
    url = settings.resolved_database_url
    # Mask password for secure logging
    masked_url = url
    if "@" in masked_url and ":" in masked_url:
        prefix, rest = masked_url.split("://", 1)
        user_pass, host_db = rest.split("@", 1)
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            masked_url = f"{prefix}://{user}:****@{host_db}"

    print("==================================================")
    print("      STUDYBUDDY DATABASE DIAGNOSTIC REPORT       ")
    print("==================================================")
    print(f"Engine Type: {'SQLite' if 'sqlite' in url else 'PostgreSQL'}")
    print(f"Connection URL: {masked_url}")
    print("--------------------------------------------------")

    try:
        # Initialize tables
        print("[1/4] Checking and applying schema migrations...")
        await init_db()
        print("  ✓ Schema synchronized successfully.")

        # Inspect tables
        print("[2/4] Inspecting database tables...")
        async with AsyncSessionLocal() as session:
            if "sqlite" in url:
                res = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"))
                tables = [r[0] for r in res.fetchall() if not r[0].startswith("sqlite_")]
            else:
                res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"))
                tables = [r[0] for r in res.fetchall()]

            print(f"  Found {len(tables)} tables registered:")
            for t in tables:
                cnt_res = await session.execute(text(f"SELECT COUNT(*) FROM \"{t}\"" if not "sqlite" in url else f"SELECT COUNT(*) FROM `{t}`"))
                count = cnt_res.scalar()
                print(f"    - {t:<26} : {count:>4} rows")

        # Inspect Admin and Student Accounts
        print("[3/4] Verifying Users and Student Profiles...")
        async with AsyncSessionLocal() as session:
            users_res = await session.execute(
                text("SELECT id, email, role, is_active FROM users ORDER BY created_at ASC")
            )
            users = users_res.fetchall()
            print(f"  Found {len(users)} user account(s):")
            for u in users:
                prof_res = await session.execute(
                    text("SELECT student_id, course, semester, section FROM student_profiles WHERE user_id = :uid"),
                    {"uid": u[0]}
                )
                prof = prof_res.fetchone()
                prof_str = f" | StudentID: {prof[0]} ({prof[1]} Sem {prof[2]} Sec {prof[3]})" if prof else " | Profile: None"
                print(f"    • [{u[2].upper()}] {u[1]} (id: {u[0][:8]}...){prof_str}")

        # Check OTP system
        print("[4/4] Verifying 2-Factor OTP Configuration...")
        print(f"  OTP Enabled: {settings.otp_auth_enabled}")
        print(f"  OTP Expiry: {settings.otp_expire_minutes} minutes")
        print(f"  SMTP Host: {settings.smtp_host or '[SIMULATION MODE - OTPs surfaced to UI for local dev]'}")

        print("--------------------------------------------------")
        print("✓ All database systems are operational and ready.")
        print("==================================================")

    except Exception as exc:
        print(f"❌ Database error: {exc}", file=sys.stderr)
        raise exc


if __name__ == "__main__":
    asyncio.run(check_database())
