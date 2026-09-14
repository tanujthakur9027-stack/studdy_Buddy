"""
seed_admin.py — Creates the first admin account.
Run: python seed_admin.py
Reads ADMIN_SEED_EMAIL and ADMIN_SEED_PASSWORD from .env
"""
import asyncio
from config import get_settings
from database import AsyncSessionLocal, init_db
from models.db_models import User
from services.auth_service import hash_password
from sqlalchemy import select

settings = get_settings()


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == settings.admin_seed_email))
        if existing.scalar_one_or_none():
            print(f"Admin already exists: {settings.admin_seed_email}")
            return

        admin = User(
            email=settings.admin_seed_email,
            password_hash=hash_password(settings.admin_seed_password),
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Admin account created: {settings.admin_seed_email}")
        print("Login with the configured ADMIN_SEED_PASSWORD")


if __name__ == "__main__":
    asyncio.run(seed())
