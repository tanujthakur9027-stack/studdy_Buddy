"""
routers/student_assignments.py — Student: view assignments and submit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional

from database import get_db
from dependencies.auth import get_current_user
from models.db_models import Assignment, AssignmentSubmission, StudentProfile, User
from services.storage_service import save_file, ALLOWED_ASSIGNMENT_TYPES
from config import get_settings

router = APIRouter(prefix="/assignments", tags=["Student - Assignments"])
settings = get_settings()


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
    submission_status: Optional[str] = None


class SubmissionOut(BaseModel):
    id: str
    assignment_id: str
    file_url: Optional[str]
    notes: str
    submitted_at: str
    marks_obtained: Optional[float]
    feedback: str
    is_evaluated: bool
    status: str


@router.get("", response_model=list[AssignmentOut])
async def list_my_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get student's class
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    # If student has no class assigned, return empty list — not all assignments
    if not profile or not profile.class_id:
        return []

    q = (
        select(Assignment)
        .where(Assignment.is_published == True, Assignment.class_id == profile.class_id)  # noqa: E712
    )

    result = await db.execute(q.order_by(Assignment.due_date.asc()))
    assignments = result.scalars().all()

    # Get submission statuses for this student
    sub_result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.student_id == current_user.id
        )
    )
    submissions = {s.assignment_id: s.status for s in sub_result.scalars()}

    return [
        AssignmentOut(
            id=a.id, title=a.title, subject_id=a.subject_id,
            class_id=a.class_id, section_id=a.section_id,
            description=a.description, instructions=a.instructions,
            file_url=a.file_url, due_date=a.due_date, due_time=a.due_time,
            max_marks=a.max_marks, is_published=a.is_published,
            created_at=str(a.created_at),
            submission_status=submissions.get(a.id),
        )
        for a in assignments
    ]


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify student belongs to a class
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile or not profile.class_id:
        raise HTTPException(status_code=403, detail="You are not assigned to any class")

    result = await db.execute(
        select(Assignment).where(
            and_(
                Assignment.id == assignment_id,
                Assignment.is_published == True,  # noqa: E712
                Assignment.class_id == profile.class_id,
            )
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")

    sub_result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )
    sub = sub_result.scalar_one_or_none()

    return AssignmentOut(
        id=a.id, title=a.title, subject_id=a.subject_id,
        class_id=a.class_id, section_id=a.section_id,
        description=a.description, instructions=a.instructions,
        file_url=a.file_url, due_date=a.due_date, due_time=a.due_time,
        max_marks=a.max_marks, is_published=a.is_published,
        created_at=str(a.created_at),
        submission_status=sub.status if sub else None,
    )


@router.post("/{assignment_id}/submit", response_model=SubmissionOut, status_code=201)
async def submit_assignment(
    assignment_id: str,
    notes: str = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify student belongs to a class
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile or not profile.class_id:
        raise HTTPException(status_code=403, detail="You are not assigned to any class")

    asgn_result = await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.is_published == True,  # noqa: E712
            Assignment.class_id == profile.class_id,
        )
    )
    assignment = asgn_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check already submitted
    existing = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already submitted")

    file_url = None
    if file and file.filename:
        try:
            file_url = await save_file(
                file, "submissions",
                max_mb=settings.assignment_file_max_mb,
                allowed_types=ALLOWED_ASSIGNMENT_TYPES,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Determine if late
    now = datetime.now(timezone.utc)
    try:
        due_dt = datetime.strptime(f"{assignment.due_date} {assignment.due_time}", "%Y-%m-%d %H:%M")
        is_late = now.date() > due_dt.date()
    except Exception:
        is_late = False

    submission = AssignmentSubmission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        file_url=file_url,
        notes=notes,
        status="late" if is_late else "submitted",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return SubmissionOut(
        id=submission.id,
        assignment_id=submission.assignment_id,
        file_url=submission.file_url,
        notes=submission.notes,
        submitted_at=str(submission.submitted_at),
        marks_obtained=submission.marks_obtained,
        feedback=submission.feedback,
        is_evaluated=submission.is_evaluated,
        status=submission.status,
    )


@router.get("/{assignment_id}/submission", response_model=SubmissionOut)
async def get_my_submission(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No submission found")
    return SubmissionOut(
        id=sub.id,
        assignment_id=sub.assignment_id,
        file_url=sub.file_url,
        notes=sub.notes,
        submitted_at=str(sub.submitted_at),
        marks_obtained=sub.marks_obtained,
        feedback=sub.feedback,
        is_evaluated=sub.is_evaluated,
        status=sub.status,
    )
