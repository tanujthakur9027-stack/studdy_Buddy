"""
services/notification_service.py — Create in-app notifications.
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import Notification


async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    notif_type: str = "general",
    reference_id: Optional[str] = None,
) -> Notification:
    """Create a single in-app notification for a user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notif_type=notif_type,
        reference_id=reference_id,
    )
    db.add(notif)
    await db.flush()
    return notif


async def create_bulk_notifications(
    db: AsyncSession,
    user_ids: list[str],
    title: str,
    message: str,
    notif_type: str = "general",
    reference_id: Optional[str] = None,
) -> int:
    """Create the same notification for multiple users. Returns count created."""
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
    return count
