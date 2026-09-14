"""
routers/admin_marks.py — Admin: assessment categories and marks entry.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin
from models.db_models import AssessmentCategory, Mark, StudentProfile, User
from services.notification_service import create_bulk_notifications
from services.email_service import send_email
from services.marks_service import calculate_grade

router = APIRouter(prefix="/admin", tags=["Admin - Marks"])


# ── Assessment Categories ─────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    subject_id: str
    max_marks: float = 100.0
    weightage: float = 100.0


class CategoryOut(BaseModel):
    id: str
    name: str
    subject_id: str
    max_marks: float
    weightage: float
    created_at: str


@router.get("/assessment-categories", response_model=list[CategoryOut])
async def list_categories(
    subject_id: Optional[str] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(AssessmentCategory)
    if subject_id:
        q = q.where(AssessmentCategory.subject_id == subject_id)
    result = await db.execute(q.order_by(AssessmentCategory.name))
    return [CategoryOut(id=c.id, name=c.name, subject_id=c.subject_id,
                        max_marks=c.max_marks, weightage=c.weightage,
                        created_at=str(c.created_at)) for c in result.scalars()]


@router.post("/assessment-categories", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cat = AssessmentCategory(
        name=body.name, subject_id=body.subject_id,
        max_marks=body.max_marks, weightage=body.weightage,
        created_by=admin.id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryOut(id=cat.id, name=cat.name, subject_id=cat.subject_id,
                       max_marks=cat.max_marks, weightage=cat.weightage,
                       created_at=str(cat.created_at))


@router.patch("/assessment-categories/{cat_id}", response_model=CategoryOut)
async def update_category(
    cat_id: str, body: CategoryCreate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AssessmentCategory).where(AssessmentCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.name = body.name
    cat.max_marks = body.max_marks
    cat.weightage = body.weightage
    await db.commit()
    return CategoryOut(id=cat.id, name=cat.name, subject_id=cat.subject_id,
                       max_marks=cat.max_marks, weightage=cat.weightage,
                       created_at=str(cat.created_at))


@router.delete("/assessment-categories/{cat_id}")
async def delete_category(cat_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AssessmentCategory).where(AssessmentCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
    return {"message": "Category deleted"}


# ── Marks Entry ───────────────────────────────────────────────────────────────

class MarkEntry(BaseModel):
    student_id: str
    category_id: str
    obtained_marks: float
    remarks: str = ""

    @field_validator("obtained_marks")
    @classmethod
    def non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Marks cannot be negative")
        return v


class MarkOut(BaseModel):
    id: str
    student_id: str
    category_id: str
    obtained_marks: float
    remarks: str
    is_published: bool


@router.post("/marks", response_model=list[MarkOut], status_code=201)
async def enter_marks(
    entries: list[MarkEntry],
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for entry in entries:
        # Validate obtained <= max
        cat_result = await db.execute(
            select(AssessmentCategory).where(AssessmentCategory.id == entry.category_id)
        )
        cat = cat_result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail=f"Category {entry.category_id} not found")
        if entry.obtained_marks > cat.max_marks:
            raise HTTPException(
                status_code=400,
                detail=f"Obtained {entry.obtained_marks} exceeds max {cat.max_marks} for '{cat.name}'"
            )

        # Upsert
        existing = await db.execute(
            select(Mark).where(
                Mark.student_id == entry.student_id,
                Mark.category_id == entry.category_id,
            )
        )
        mark = existing.scalar_one_or_none()
        if mark:
            mark.obtained_marks = entry.obtained_marks
            mark.remarks = entry.remarks
        else:
            mark = Mark(
                student_id=entry.student_id,
                category_id=entry.category_id,
                obtained_marks=entry.obtained_marks,
                remarks=entry.remarks,
            )
            db.add(mark)
        await db.flush()
        results.append(mark)

    await db.commit()
    return [MarkOut(id=m.id, student_id=m.student_id, category_id=m.category_id,
                    obtained_marks=m.obtained_marks, remarks=m.remarks,
                    is_published=m.is_published) for m in results]


@router.patch("/marks/{mark_id}", response_model=MarkOut)
async def update_mark(
    mark_id: str,
    obtained_marks: float,
    remarks: str = "",
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Mark).where(Mark.id == mark_id))
    mark = result.scalar_one_or_none()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")

    cat_result = await db.execute(
        select(AssessmentCategory).where(AssessmentCategory.id == mark.category_id)
    )
    cat = cat_result.scalar_one_or_none()
    if cat and obtained_marks > cat.max_marks:
        raise HTTPException(status_code=400, detail=f"Obtained exceeds max {cat.max_marks}")

    mark.obtained_marks = obtained_marks
    mark.remarks = remarks
    await db.commit()
    return MarkOut(id=mark.id, student_id=mark.student_id, category_id=mark.category_id,
                   obtained_marks=mark.obtained_marks, remarks=mark.remarks,
                   is_published=mark.is_published)


class PublishRequest(BaseModel):
    category_id: Optional[str] = None
    subject_id: Optional[str] = None


@router.post("/marks/publish")
async def publish_marks(
    body: PublishRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(Mark).where(Mark.is_published == False)  # noqa: E712
    if body.category_id:
        q = q.where(Mark.category_id == body.category_id)
    elif body.subject_id:
        cat_ids_result = await db.execute(
            select(AssessmentCategory.id).where(AssessmentCategory.subject_id == body.subject_id)
        )
        cat_ids = [row[0] for row in cat_ids_result.all()]
        q = q.where(Mark.category_id.in_(cat_ids))

    result = await db.execute(q)
    marks = result.scalars().all()
    student_ids = list({m.student_id for m in marks})

    for m in marks:
        m.is_published = True

    if student_ids:
        await create_bulk_notifications(
            db, student_ids,
            title="Marks Published",
            message="Your marks have been published. Check the Marks section.",
            notif_type="marks",
        )
        email_q = select(User.email, User.full_name).where(User.id.in_(student_ids))
        email_result = await db.execute(email_q)
        for email, full_name in email_result.all():
            await send_email(
                to=email,
                subject="Your Marks Have Been Published",
                template_name="marks_published.html",
                context={"student_name": full_name},
            )

    await db.commit()
    return {"message": f"Published marks for {len(marks)} entries"}


@router.get("/marks/report")
async def marks_report(
    subject_id: Optional[str] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Class-wide marks overview."""
    q = (
        select(Mark, AssessmentCategory, User)
        .join(AssessmentCategory, Mark.category_id == AssessmentCategory.id)
        .join(User, Mark.student_id == User.id)
    )
    if subject_id:
        q = q.where(AssessmentCategory.subject_id == subject_id)
    result = await db.execute(q)
    rows = result.all()

    out = []
    for mark, cat, user in rows:
        out.append({
            "student_id": mark.student_id,
            "student_name": user.full_name,
            "category": cat.name,
            "obtained": mark.obtained_marks,
            "max": cat.max_marks,
            "percentage": round(mark.obtained_marks / cat.max_marks * 100, 1) if cat.max_marks else 0,
            "is_published": mark.is_published,
        })
    return out
