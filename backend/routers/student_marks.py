"""
routers/student_marks.py — Student: view published marks.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import get_current_user
from models.db_models import Mark, AssessmentCategory, Subject, User
from services.marks_service import calculate_subject_summary

router = APIRouter(prefix="/marks", tags=["Student - Marks"])


@router.get("")
async def get_marks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mark, AssessmentCategory)
        .join(AssessmentCategory, Mark.category_id == AssessmentCategory.id)
        .where(Mark.student_id == current_user.id, Mark.is_published == True)  # noqa: E712
        .order_by(AssessmentCategory.name)
    )
    rows = result.all()
    return [
        {
            "id": m.id,
            "category_id": m.category_id,
            "category_name": cat.name,
            "subject_id": cat.subject_id,
            "obtained_marks": m.obtained_marks,
            "max_marks": cat.max_marks,
            "weightage": cat.weightage,
            "remarks": m.remarks,
            "percentage": round(m.obtained_marks / cat.max_marks * 100, 1) if cat.max_marks else 0,
        }
        for m, cat in rows
    ]


@router.get("/summary")
async def marks_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Overall marks summary grouped by subject."""
    # Get all subjects that have published marks for this student
    result = await db.execute(
        select(AssessmentCategory.subject_id)
        .join(Mark, Mark.category_id == AssessmentCategory.id)
        .where(Mark.student_id == current_user.id, Mark.is_published == True)  # noqa: E712
        .distinct()
    )
    subject_ids = [row[0] for row in result.all()]

    summaries = []
    for sid in subject_ids:
        sub_result = await db.execute(select(Subject).where(Subject.id == sid))
        subject = sub_result.scalar_one_or_none()
        summary = await calculate_subject_summary(current_user.id, sid, db, published_only=True)
        summaries.append({
            "subject_id": sid,
            "subject_name": subject.name if subject else "Unknown",
            **summary,
        })

    overall_obtained = sum(s["total_obtained"] for s in summaries)
    overall_max = sum(s["total_max"] for s in summaries)
    overall_pct = round(overall_obtained / overall_max * 100, 2) if overall_max else 0

    from services.marks_service import calculate_grade
    return {
        "subjects": summaries,
        "overall_obtained": overall_obtained,
        "overall_max": overall_max,
        "overall_percentage": overall_pct,
        "overall_grade": calculate_grade(overall_pct),
    }


@router.get("/subject/{subject_id}")
async def subject_marks(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await calculate_subject_summary(current_user.id, subject_id, db, published_only=True)
