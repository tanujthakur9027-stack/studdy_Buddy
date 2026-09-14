"""
services/marks_service.py — Mark calculation and grade logic.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import AssessmentCategory, Mark


def calculate_grade(percentage: float) -> str:
    """Return grade letter from percentage (matches existing quiz grade scale)."""
    if percentage >= 90:
        return "S"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    elif percentage >= 50:
        return "D"
    return "F"


async def calculate_subject_summary(
    student_id: str,
    subject_id: str,
    db: AsyncSession,
    published_only: bool = True,
) -> dict:
    """
    Calculate total obtained marks, total max marks, percentage, and grade
    for a student across all assessment categories of a subject.
    """
    cat_result = await db.execute(
        select(AssessmentCategory).where(AssessmentCategory.subject_id == subject_id)
    )
    categories = cat_result.scalars().all()

    if not categories:
        return {"total_obtained": 0, "total_max": 0, "percentage": 0, "grade": "N/A", "categories": []}

    total_obtained = 0.0
    total_max = 0.0
    cat_details = []

    for cat in categories:
        mark_q = select(Mark).where(
            Mark.student_id == student_id,
            Mark.category_id == cat.id,
        )
        if published_only:
            mark_q = mark_q.where(Mark.is_published == True)  # noqa: E712

        mark_result = await db.execute(mark_q)
        mark = mark_result.scalar_one_or_none()

        obtained = mark.obtained_marks if mark else 0.0
        total_obtained += obtained
        total_max += cat.max_marks

        cat_details.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "obtained": obtained,
            "max_marks": cat.max_marks,
            "weightage": cat.weightage,
            "remarks": mark.remarks if mark else "",
            "is_published": mark.is_published if mark else False,
        })

    percentage = (total_obtained / total_max * 100) if total_max > 0 else 0
    return {
        "total_obtained": total_obtained,
        "total_max": total_max,
        "percentage": round(percentage, 2),
        "grade": calculate_grade(percentage),
        "categories": cat_details,
    }
