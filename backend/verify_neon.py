"""
verify_neon.py — Diagnostic utility to test and verify real-time Neon PostgreSQL connection.
Usage:
    & "backend\\.venv\\Scripts\\python.exe" backend/verify_neon.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import get_settings
from database import engine, init_db, AsyncSessionLocal
from sqlalchemy import text


async def test_neon_connection():
    settings = get_settings()
    url = settings.resolved_database_url
    print("=" * 60)
    print("           NEON DATABASE REAL-TIME VERIFIER           ")
    print("=" * 60)
    
    # Hide password in output
    masked_url = url
    if "@" in url and "://" in url:
        prefix = url.split("://")[0]
        rest = url.split("://")[1]
        user_pass, host_part = rest.split("@", 1)
        user = user_pass.split(":")[0] if ":" in user_pass else user_pass
        masked_url = f"{prefix}://{user}:****@{host_part}"
    
    print(f"Target Database URL: {masked_url}")
    is_postgres = "postgres" in url
    print(f"Database Engine:     {'PostgreSQL (Neon)' if is_postgres else 'SQLite (Local)'}")
    
    if not is_postgres:
        print("\n[NOTE] You are currently connected to SQLite.")
        print("To connect to your real-time Neon database:")
        print("1. Open backend/.env")
        print("2. Set DATABASE_URL to your Neon connection string:")
        print("   DATABASE_URL=postgresql://<user>:<password>@<neon-host>/<dbname>?sslmode=require")
        print("=" * 60)
        return

    print("\nConnecting to Neon PostgreSQL...")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT version();"))
            ver = res.scalar()
            print(f"✓ Connected successfully to Neon!")
            print(f"  PostgreSQL Version: {ver[:60]}...")
            
        print("\nInitializing database schema and running migrations on Neon...")
        await init_db()
        print("✓ All tables and migrations verified on Neon!")
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
            ))
            tables = [row[0] for row in res.fetchall()]
            print(f"\n✓ Found {len(tables)} tables in Neon public schema:")
            for t in tables[:10]:
                print(f"   - {t}")
            if len(tables) > 10:
                print(f"   ... and {len(tables) - 10} more tables.")
                
        print("\n" + "=" * 60)
        print("   ✓ NEON DATABASE IS READY AND FULLY OPERATIONAL!    ")
        print("=" * 60)

    except Exception as exc:
        print(f"\n❌ Error connecting to Neon database: {exc}")
        print("\nTroubleshooting tips:")
        print("- Verify username, password, and host in backend/.env")
        print("- Ensure '?sslmode=require' is appended to the connection string")
        print("- Check that your IP is allowed or Neon compute is active (not paused)")


if __name__ == "__main__":
    asyncio.run(test_neon_connection())
