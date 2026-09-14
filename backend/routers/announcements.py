"""
routers/announcements.py — Announcements for admin and students.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin, get_current_user
from models.db_models import Announcement, User, StudentProfile
from services.notification_service import create_bulk_notifications

# Student-facing router
router = APIRouter(prefix="/announcements", tags=["Announcements"])
# Admin router
admin_router = APIRouter(prefix="/admin/announcements", tags=["Admin - Announcements"])


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    class_id: Optional[str] = None
    section_id: Optional[str] = None


class AnnouncementOut(BaseModel):
    id: str
    title: str
    content: str
    created_by: str
    author_name: str
    class_id: Optional[str]
    section_id: Optional[str]
    created_at: str


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("", response_model=list[AnnouncementOut])
async def admin_list(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Announcement, User)
        .join(User, Announcement.created_by == User.id)
        .order_by(Announcement.created_at.desc())
    )
    return [_to_out(a, u) for a, u in result.all()]


@admin_router.post("", response_model=AnnouncementOut, status_code=201)
async def admin_create(
    body: AnnouncementCreate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ann = Announcement(
        title=body.title, content=body.content,
        created_by=admin.id, class_id=body.class_id, section_id=body.section_id,
    )
    db.add(ann)
    await db.flush()

    # Notify affected students
    q = select(StudentProfile.user_id)
    if body.class_id:
        q = q.where(StudentProfile.class_id == body.class_id)
    student_ids_result = await db.execute(q)
    student_ids = [row[0] for row in student_ids_result.all()]

    if student_ids:
        await create_bulk_notifications(
            db, student_ids,
            title=f"Announcement: {body.title}",
            message=body.content[:200],
            notif_type="announcement",
            reference_id=ann.id,
        )

    await db.commit()
    result = await db.execute(
        select(Announcement, User)
        .join(User, Announcement.created_by == User.id)
        .where(Announcement.id == ann.id)
    )
    row = result.first()
    return _to_out(row[0], row[1])


@admin_router.patch("/{ann_id}", response_model=AnnouncementOut)
async def admin_update(
    ann_id: str,
    body: AnnouncementCreate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    ann.title = body.title
    ann.content = body.content
    await db.commit()
    result2 = await db.execute(
        select(Announcement, User)
        .join(User, Announcement.created_by == User.id)
        .where(Announcement.id == ann_id)
    )
    row = result2.first()
    return _to_out(row[0], row[1])


@admin_router.delete("/{ann_id}")
async def admin_delete(ann_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    await db.delete(ann)
    await db.commit()
    return {"message": "Deleted"}


# ── Student endpoints ─────────────────────────────────────────────────────────

@router.get("", response_model=list[AnnouncementOut])
async def student_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    class_id = profile.class_id if profile else None

    q = select(Announcement, User).join(User, Announcement.created_by == User.id)
    if class_id:
        q = q.where(
            or_(Announcement.class_id == None, Announcement.class_id == class_id)  # noqa: E711
        )
    else:
        q = q.where(Announcement.class_id == None)  # noqa: E711

    result = await db.execute(q.order_by(Announcement.created_at.desc()))
    return [_to_out(a, u) for a, u in result.all()]


def _to_out(a: Announcement, u: User) -> AnnouncementOut:
    return AnnouncementOut(
        id=a.id, title=a.title, content=a.content,
        created_by=a.created_by, author_name=u.full_name,
        class_id=a.class_id, section_id=a.section_id,
        created_at=str(a.created_at),
    )
