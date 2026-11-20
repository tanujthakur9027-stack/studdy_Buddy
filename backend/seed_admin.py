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
    current_settings = get_settings()
    async with AsyncSessionLocal() as db:
        admin_emails = [current_settings.admin_seed_email, "admin@studybuddy.com"]
        for email in set(admin_emails):
            if not email:
                continue
            existing = await db.execute(select(User).where(User.email == email))
            if not existing.scalar_one_or_none():
                admin = User(
                    email=email,
                    password_hash=hash_password(current_settings.admin_seed_password),
                    full_name="Tanuj Admin" if email == current_settings.admin_seed_email else "Admin",
                    role="admin",
                    is_active=True,
                )
                db.add(admin)
                await db.commit()
                print(f"Admin account created: {email}")


if __name__ == "__main__":
    asyncio.run(seed())
