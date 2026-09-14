"""
routers/admin_assignments.py — Admin: assignment creation and publishing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin
from models.db_models import Assignment, StudentProfile
from services.storage_service import save_file, ALLOWED_ASSIGNMENT_TYPES
from services.notification_service import create_bulk_notifications
from services.email_service import send_email
from config import get_settings

router = APIRouter(prefix="/admin/assignments", tags=["Admin - Assignments"])
settings = get_settings()


class AssignmentCreate(BaseModel):
    title: str
    subject_id: str
    class_id: str
    section_id: Optional[str] = None
    description: str = ""
    instructions: str = ""
    due_date: str
    due_time: str = "23:59"
    max_marks: int = 100


class AssignmentOut(BaseModel):
    id: str
    title: str
    subject_id: str
    class_id: str
    section_id: Optional[str]
    description: str
    instructions: str
    file_url: Optional[str]
    due_date: str
    due_time: str
    max_marks: int
    is_published: bool
    created_at: str


def _to_out(a: Assignment) -> AssignmentOut:
    return AssignmentOut(
        id=a.id, title=a.title, subject_id=a.subject_id,
        class_id=a.class_id, section_id=a.section_id,
        description=a.description, instructions=a.instructions,
        file_url=a.file_url, due_date=a.due_date, due_time=a.due_time,
        max_marks=a.max_marks, is_published=a.is_published,
        created_at=str(a.created_at),
    )


@router.get("", response_model=list[AssignmentOut])
async def list_assignments(
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assignment).order_by(Assignment.created_at.desc())
    )
    return [_to_out(a) for a in result.scalars()]


@router.post("", response_model=AssignmentOut, status_code=201)
async def create_assignment(
    title: str = Form(...),
    subject_id: str = Form(...),
    class_id: str = Form(...),
    section_id: Optional[str] = Form(None),
    description: str = Form(""),
    instructions: str = Form(""),
    due_date: str = Form(...),
    due_time: str = Form("23:59"),
    max_marks: int = Form(100),
    file: Optional[UploadFile] = File(None),
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    file_url = None
    if file and file.filename:
        try:
            file_url = await save_file(
                file, "assignments",
                max_mb=settings.assignment_file_max_mb,
                allowed_types=ALLOWED_ASSIGNMENT_TYPES,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    assignment = Assignment(
        title=title, subject_id=subject_id, class_id=class_id,
        section_id=section_id or None, description=description,
        instructions=instructions, file_url=file_url,
        due_date=due_date, due_time=due_time, max_marks=max_marks,
        created_by=admin.id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return _to_out(assignment)


@router.patch("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(
    assignment_id: str,
    body: AssignmentCreate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    for k, v in body.model_dump().items():
        setattr(assignment, k, v)
    await db.commit()
    return _to_out(assignment)


@router.post("/{assignment_id}/publish")
async def publish_assignment(
    assignment_id: str,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.is_published = True
    await db.flush()

    # Find affected students
    q = select(StudentProfile).where(StudentProfile.class_id == assignment.class_id)
    if assignment.section_id:
        q = q.where(StudentProfile.section == assignment.section_id)
    profiles_result = await db.execute(q)
    profiles = profiles_result.scalars().all()
    student_ids = [p.user_id for p in profiles]

    if student_ids:
        await create_bulk_notifications(
            db, student_ids,
            title=f"New Assignment: {assignment.title}",
            message=f"A new assignment has been posted. Due: {assignment.due_date} {assignment.due_time}",
            notif_type="assignment",
            reference_id=assignment.id,
        )

    await db.commit()
    return {"message": "Assignment published", "notified": len(student_ids)}


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(assignment)
    await db.commit()
    return {"message": "Assignment deleted"}
