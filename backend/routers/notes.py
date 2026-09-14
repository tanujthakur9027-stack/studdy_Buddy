"""
routers/notes.py — Student: upload, list, download, and delete notes.
"""
from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from config import get_settings
from database import get_db
from dependencies.auth import get_current_user
from models.db_models import Note, StudentProfile, StudentConnection, User
from services.storage_service import save_file, ALLOWED_NOTE_TYPES
from services.notification_service import create_bulk_notifications

router = APIRouter(prefix="/notes", tags=["Notes"])
settings = get_settings()


class NoteOut(BaseModel):
    id: str
    title: str
    description: str
    subject: str
    course: str
    semester: str
    tags: str
    file_url: str
    original_filename: str
    uploaded_by: str
    uploader_name: str
    visibility: str
    created_at: str


@router.post("", response_model=NoteOut, status_code=201)
async def upload_note(
    title: str = Form(...),
    description: str = Form(""),
    subject: str = Form(""),
    course: str = Form(""),
    semester: str = Form(""),
    tags: str = Form(""),
    visibility: str = Form("connections"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if visibility not in ("connections", "class", "public"):
        raise HTTPException(status_code=400, detail="Invalid visibility. Use: connections, class, public")

    try:
        file_url = await save_file(file, "notes",
                                   max_mb=settings.note_file_max_mb,
                                   allowed_types=ALLOWED_NOTE_TYPES)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get student's class
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    note = Note(
        title=title, description=description, subject=subject,
        course=course, semester=semester, tags=tags,
        file_url=file_url, original_filename=file.filename or title,
        uploaded_by=current_user.id, visibility=visibility,
        class_id=profile.class_id if profile else None,
    )
    db.add(note)
    await db.flush()

    # Notify connected students if connections visibility
    if visibility == "connections":
        conn_result = await db.execute(
            select(StudentConnection).where(
                or_(
                    StudentConnection.user_a_id == current_user.id,
                    StudentConnection.user_b_id == current_user.id,
                )
            )
        )
        connections = conn_result.scalars().all()
        other_ids = [
            c.user_b_id if c.user_a_id == current_user.id else c.user_a_id
            for c in connections
        ]
        if other_ids:
            await create_bulk_notifications(
                db, other_ids,
                title="New Note Shared",
                message=f"{current_user.full_name} shared a new note: {title}",
                notif_type="note",
                reference_id=note.id,
            )

    await db.commit()
    await db.refresh(note)
    return NoteOut(
        id=note.id, title=note.title, description=note.description,
        subject=note.subject, course=note.course, semester=note.semester,
        tags=note.tags, file_url=note.file_url, original_filename=note.original_filename,
        uploaded_by=note.uploaded_by, uploader_name=current_user.full_name,
        visibility=note.visibility, created_at=str(note.created_at),
    )


@router.get("", response_model=list[NoteOut])
async def list_notes(
    subject: Optional[str] = None,
    semester: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get connected user IDs
    conn_result = await db.execute(
        select(StudentConnection).where(
            or_(
                StudentConnection.user_a_id == current_user.id,
                StudentConnection.user_b_id == current_user.id,
            )
        )
    )
    connected_ids = set()
    for c in conn_result.scalars().all():
        connected_ids.add(c.user_b_id if c.user_a_id == current_user.id else c.user_a_id)

    # Get student's class
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    class_id = profile.class_id if profile else None

    # Build visibility filter
    visibility_filter = or_(
        Note.visibility == "public",
        and_(Note.visibility == "connections", Note.uploaded_by.in_(connected_ids | {current_user.id})),
        and_(Note.visibility == "class", Note.class_id == class_id) if class_id else Note.visibility == "never",
        Note.uploaded_by == current_user.id,
    )

    q = select(Note, User).join(User, Note.uploaded_by == User.id).where(visibility_filter)

    if subject:
        q = q.where(Note.subject.ilike(f"%{subject}%"))
    if semester:
        q = q.where(Note.semester == semester)
    if search:
        q = q.where(
            or_(Note.title.ilike(f"%{search}%"), Note.tags.ilike(f"%{search}%"))
        )

    q = q.order_by(Note.created_at.desc()).limit(100)
    result = await db.execute(q)

    return [
        NoteOut(
            id=n.id, title=n.title, description=n.description,
            subject=n.subject, course=n.course, semester=n.semester,
            tags=n.tags, file_url=n.file_url, original_filename=n.original_filename,
            uploaded_by=n.uploaded_by, uploader_name=u.full_name,
            visibility=n.visibility, created_at=str(n.created_at),
        )
        for n, u in result.all()
    ]


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Note, User).join(User, Note.uploaded_by == User.id).where(Note.id == note_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    n, u = row
    return NoteOut(
        id=n.id, title=n.title, description=n.description,
        subject=n.subject, course=n.course, semester=n.semester,
        tags=n.tags, file_url=n.file_url, original_filename=n.original_filename,
        uploaded_by=n.uploaded_by, uploader_name=u.full_name,
        visibility=n.visibility, created_at=str(n.created_at),
    )


@router.get("/{note_id}/download")
async def download_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Convert URL to filesystem path
    file_path = Path(settings.upload_dir).parent / note.file_url.lstrip("/")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=note.original_filename,
        media_type="application/octet-stream",
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another student's note")
    await db.delete(note)
    await db.commit()
    return {"message": "Note deleted"}
