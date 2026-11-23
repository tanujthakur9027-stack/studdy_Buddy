"""
seed_admin.py — Creates the first admin account.
Run: python seed_admin.py
Reads ADMIN_SEED_EMAIL and ADMIN_SEED_PASSWORD from environment / .env.
"""
import asyncio
import logging
from config import get_settings
from database import AsyncSessionLocal, init_db
from models.db_models import User
from services.auth_service import hash_password
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def seed():
    await init_db()
    current_settings = get_settings()
    email = current_settings.admin_seed_email.strip().lower()
    password = current_settings.admin_seed_password.strip()

    if not email or not password:
        logger.warning(
            "Admin seeding skipped: ADMIN_SEED_EMAIL or ADMIN_SEED_PASSWORD not configured in environment."
        )
        return

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if not existing.scalar_one_or_none():
            admin = User(
                email=email,
                password_hash=hash_password(password),
                full_name="Administrator",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("Admin account seeded successfully: %s", email)


if __name__ == "__main__":
    asyncio.run(seed())
