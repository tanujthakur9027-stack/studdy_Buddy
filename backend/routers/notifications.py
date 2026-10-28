"""
routers/notifications.py — In-app notification endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional
from database import get_db
from dependencies.auth import get_current_user, require_admin
from models.db_models import Notification, User, StudentProfile
from services.notification_service import create_notification, create_bulk_notifications
from services.email_service import send_email
from config import get_settings

settings = get_settings()

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    notif_type: str
    reference_id: str | None
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    q = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(q)
    notifs = result.scalars().all()
    return [
        NotificationOut(
            id=n.id,
            title=n.title,
            message=n.message,
            notif_type=n.notif_type,
            reference_id=n.reference_id,
            is_read=n.is_read,
            created_at=str(n.created_at),
        )
        for n in notifs
    ]


@router.get("/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    count = result.scalar_one()
    return {"count": count}


@router.patch("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.patch("/{notif_id}/read")
async def mark_read(
    notif_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"message": "Marked as read"}


# ── Contact Admin / Support ───────────────────────────────────────────────────

class ContactAdminRequest(BaseModel):
    title: str
    message: str
    category: str = "general"  # academic | technical | doubt | general


@router.post("/contact-admin", status_code=201)
async def contact_admin(
    body: ContactAdminRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allow students to send a contact inquiry / message directly to the administrators."""
    # Find all active admin accounts
    admin_result = await db.execute(
        select(User).where(User.role == "admin", User.is_active == True)  # noqa: E712
    )
    admins = admin_result.scalars().all()
    if not admins:
        raise HTTPException(status_code=503, detail="No active administrator is currently available.")

    admin_ids = [a.id for a in admins]
    admin_emails = [a.email for a in admins if a.email]

    # Create notifications for all administrators
    full_subject = f"[{body.category.upper()}] {body.title}"
    full_message = f"From: {current_user.full_name} ({current_user.email})\n\n{body.message}"

    await create_bulk_notifications(
        db=db,
        user_ids=admin_ids,
        title=f"Student Contact: {body.title}",
        message=full_message,
        notif_type="contact",
        reference_id=current_user.id,
    )

    # Confirmation notification for the sender
    await create_notification(
        db=db,
        user_id=current_user.id,
        title="Inquiry Delivered",
        message=f"Your message '{body.title}' was sent to the administration team. We will review it shortly.",
        notif_type="general",
    )

    await db.commit()

    # Optional email dispatch if SMTP is configured
    email_dispatched = False
    if settings.smtp_host and admin_emails:
        try:
            email_dispatched = await send_email(
                to=admin_emails,
                subject=f"[StudyBuddy Support] {full_subject}",
                template_name="registration_confirmation.html",
                context={
                    "app_name": "StudyBuddy Administration",
                    "student_name": current_user.full_name,
                    "message": body.message,
                    "student_email": current_user.email,
                },
            )
        except Exception:
            pass

    return {
        "message": "Message successfully submitted to administration.",
        "admins_alerted": len(admin_ids),
        "email_sent": email_dispatched,
    }


# ── Admin: Broadcast Notifications & Email ────────────────────────────────────

class BroadcastRequest(BaseModel):
    title: str
    message: str
    target: str = "all"  # "all" | "class" | "student"
    target_id: Optional[str] = None  # class_id if target==class, user_id if target==student
    send_email: bool = False


@router.post("/broadcast", status_code=201)
async def broadcast_notification(
    body: BroadcastRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Broadcast in-app notifications and optional emails to students."""
    recipient_users: list[User] = []

    if body.target == "student" and body.target_id:
        res = await db.execute(select(User).where(User.id == body.target_id, User.is_active == True))  # noqa: E712
        user = res.scalar_one_or_none()
        if user:
            recipient_users = [user]
    elif body.target == "class" and body.target_id:
        res = await db.execute(
            select(User)
            .join(StudentProfile, StudentProfile.user_id == User.id)
            .where(StudentProfile.class_id == body.target_id, User.is_active == True)  # noqa: E712
        )
        recipient_users = list(res.scalars().all())
    else:
        # Default: all active students
        res = await db.execute(
            select(User).where(User.role == "student", User.is_active == True)  # noqa: E712
        )
        recipient_users = list(res.scalars().all())

    if not recipient_users:
        raise HTTPException(status_code=404, detail="No matching recipients found for the target.")

    user_ids = [u.id for u in recipient_users]
    emails = [u.email for u in recipient_users if u.email]

    await create_bulk_notifications(
        db=db,
        user_ids=user_ids,
        title=body.title,
        message=body.message,
        notif_type="announcement",
        reference_id=admin.id,
    )
    await db.commit()

    email_sent_count = 0
    if body.send_email and settings.smtp_host and emails:
        for em in emails:
            try:
                sent = await send_email(
                    to=em,
                    subject=f"[StudyBuddy Notice] {body.title}",
                    template_name="registration_confirmation.html",
                    context={"app_name": "StudyBuddy", "message": body.message},
                )
                if sent:
                    email_sent_count += 1
            except Exception:
                pass

    return {
        "message": f"Broadcast delivered to {len(user_ids)} student(s).",
        "in_app_count": len(user_ids),
        "emails_sent": email_sent_count,
    }


# ── Admin: View Inquiries / Contacts ──────────────────────────────────────────

class ContactInquiryOut(BaseModel):
    id: str
    title: str
    message: str
    is_read: bool
    created_at: str
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    student_id: Optional[str] = None


@router.get("/admin/contacts", response_model=list[ContactInquiryOut])
async def list_admin_contacts(
    page: int = 1,
    page_size: int = 50,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Retrieve all contact requests and inquiries submitted by students."""
    offset = (page - 1) * page_size
    q = (
        select(Notification)
        .where(Notification.notif_type == "contact")
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(q)
    notifs = res.scalars().all()

    out: list[ContactInquiryOut] = []
    for n in notifs:
        sender_name = "Student"
        sender_email = "student@studybuddy.com"
        sid = ""
        if n.reference_id:
            u_res = await db.execute(select(User).where(User.id == n.reference_id))
            user = u_res.scalar_one_or_none()
            if user:
                sender_name = user.full_name
                sender_email = user.email
            p_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == n.reference_id))
            prof = p_res.scalar_one_or_none()
            if prof:
                sid = prof.student_id

        out.append(
            ContactInquiryOut(
                id=n.id,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                created_at=str(n.created_at),
                sender_id=n.reference_id,
                sender_name=sender_name,
                sender_email=sender_email,
                student_id=sid,
            )
        )
    return out
