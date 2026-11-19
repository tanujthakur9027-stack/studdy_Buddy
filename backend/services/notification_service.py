"""
services/notification_service.py — Create in-app notifications and auto-dispatch email alerts.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import Notification, User
from services.email_service import send_email

logger = logging.getLogger(__name__)


async def _dispatch_email_bg(email: str, subject: str, body: str) -> None:
    """Safely deliver email notification in the background without blocking."""
    try:
        await send_email(to=email, subject=subject, body=body)
    except Exception as exc:
        logger.warning("notification_email_dispatch_error", extra={"email": email, "error": str(exc)})


async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    notif_type: str = "general",
    reference_id: Optional[str] = None,
) -> Notification:
    """Create a single in-app notification for a user and trigger email notification."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notif_type=notif_type,
        reference_id=reference_id,
    )
    db.add(notif)
    await db.flush()

    # Automatically notify student via email
    try:
        user_res = await db.execute(select(User.email).where(User.id == user_id))
        user_email = user_res.scalar_one_or_none()
        if user_email:
            asyncio.create_task(_dispatch_email_bg(user_email, f"[StudyBuddy] {title}", message))
    except Exception as exc:
        logger.debug("email_lookup_skipped", extra={"error": str(exc)})

    return notif


async def create_bulk_notifications(
    db: AsyncSession,
    user_ids: list[str],
    title: str,
    message: str,
    notif_type: str = "general",
    reference_id: Optional[str] = None,
) -> int:
    """Create the same notification for multiple users and trigger email delivery to each."""
    count = 0
    for user_id in user_ids:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notif_type=notif_type,
            reference_id=reference_id,
        )
        db.add(notif)
        count += 1
    await db.flush()

    # Automatically notify all students via email in background
    if user_ids:
        try:
            users_res = await db.execute(select(User.email).where(User.id.in_(user_ids)))
            emails = [em for em in users_res.scalars().all() if em]
            for em in emails:
                asyncio.create_task(_dispatch_email_bg(em, f"[StudyBuddy] {title}", message))
        except Exception as exc:
            logger.debug("bulk_email_lookup_skipped", extra={"error": str(exc)})

    return count
