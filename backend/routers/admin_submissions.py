"""
routers/admin_submissions.py — Admin: view and grade submissions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin
from models.db_models import AssignmentSubmission, Assignment, User
from services.notification_service import create_notification
from services.email_service import send_email

router = APIRouter(prefix="/admin/submissions", tags=["Admin - Submissions"])


class SubmissionOut(BaseModel):
    id: str
    assignment_id: str
    student_id: str
    student_name: str
    student_email: str
    file_url: Optional[str]
    notes: str
    submitted_at: str
    marks_obtained: Optional[float]
    feedback: str
    is_evaluated: bool
    status: str


class GradeRequest(BaseModel):
    marks_obtained: float
    feedback: str = ""


@router.get("", response_model=list[SubmissionOut])
async def list_submissions(
    assignment_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page_size = min(page_size, 200)
    offset = (page - 1) * page_size

    q = (
        select(AssignmentSubmission, User)
        .join(User, User.id == AssignmentSubmission.student_id)
        .order_by(AssignmentSubmission.submitted_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    if assignment_id:
        q = q.where(AssignmentSubmission.assignment_id == assignment_id)
    if status:
        q = q.where(AssignmentSubmission.status == status)

    result = await db.execute(q)
    rows = result.all()

    return [
        SubmissionOut(
            id=sub.id,
            assignment_id=sub.assignment_id,
            student_id=sub.student_id,
            student_name=user.full_name,
            student_email=user.email,
            file_url=sub.file_url,
            notes=sub.notes,
            submitted_at=str(sub.submitted_at),
            marks_obtained=sub.marks_obtained,
            feedback=sub.feedback,
            is_evaluated=sub.is_evaluated,
            status=sub.status,
        )
        for sub, user in rows
    ]


@router.patch("/{submission_id}/grade")
async def grade_submission(
    submission_id: str,
    body: GradeRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AssignmentSubmission).where(AssignmentSubmission.id == submission_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Validate marks
    asgn_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    assignment = asgn_result.scalar_one_or_none()
    if assignment and body.marks_obtained > assignment.max_marks:
        raise HTTPException(
            status_code=400,
            detail=f"Marks cannot exceed max marks ({assignment.max_marks})"
        )

    sub.marks_obtained = body.marks_obtained
    sub.feedback = body.feedback
    sub.is_evaluated = True
    sub.status = "evaluated"
    await db.flush()

    # Notify student
    await create_notification(
        db, sub.student_id,
        title="Assignment Evaluated",
        message=f"Your assignment has been evaluated. Marks: {body.marks_obtained}/{assignment.max_marks if assignment else '?'}",
        notif_type="submission",
        reference_id=sub.assignment_id,
    )

    await db.commit()
    return {"message": "Submission graded", "marks_obtained": body.marks_obtained}
