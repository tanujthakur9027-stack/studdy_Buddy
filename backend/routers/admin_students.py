"""
routers/admin_students.py — Admin: student management.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin
from models.db_models import User, StudentProfile, Class

router = APIRouter(prefix="/admin/students", tags=["Admin - Students"])


class StudentProfileOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: str
    student_id: str
    phone: str
    course: str
    branch: str
    semester: str
    section: str
    academic_year: str
    dob: Optional[str]
    profile_photo_url: Optional[str]
    class_id: Optional[str]


@router.get("", response_model=list[StudentProfileOut])
async def list_students(
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    q = (
        select(User, StudentProfile)
        .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
        .where(User.role == "student")
    )
    if search:
        q = q.where(
            User.full_name.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
            | StudentProfile.student_id.ilike(f"%{search}%")
        )
    q = q.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(q)
    rows = result.all()

    out = []
    for user, profile in rows:
        out.append(StudentProfileOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=str(user.created_at),
            student_id=profile.student_id if profile else "",
            phone=profile.phone if profile else "",
            course=profile.course if profile else "",
            branch=profile.branch if profile else "",
            semester=profile.semester if profile else "",
            section=profile.section if profile else "",
            academic_year=profile.academic_year if profile else "",
            dob=profile.dob if profile else None,
            profile_photo_url=profile.profile_photo_url if profile else None,
            class_id=profile.class_id if profile else None,
        ))
    return out


@router.get("/count")
async def student_count(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count()).where(User.role == "student"))
    active = await db.execute(
        select(func.count()).where(User.role == "student", User.is_active == True)  # noqa: E712
    )
    return {"total": total.scalar_one(), "active": active.scalar_one()}


@router.get("/{student_id}", response_model=StudentProfileOut)
async def get_student(
    student_id: str,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User, StudentProfile)
        .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
        .where(User.id == student_id, User.role == "student")
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    user, profile = row
    return StudentProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=str(user.created_at),
        student_id=profile.student_id if profile else "",
        phone=profile.phone if profile else "",
        course=profile.course if profile else "",
        branch=profile.branch if profile else "",
        semester=profile.semester if profile else "",
        section=profile.section if profile else "",
        academic_year=profile.academic_year if profile else "",
        dob=profile.dob if profile else None,
        profile_photo_url=profile.profile_photo_url if profile else None,
        class_id=profile.class_id if profile else None,
    )


class StatusUpdate(BaseModel):
    is_active: bool


@router.patch("/{student_id}/status")
async def update_status(
    student_id: str,
    body: StatusUpdate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == student_id, User.role == "student"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    user.is_active = body.is_active
    await db.commit()
    return {"message": f"Student {'activated' if body.is_active else 'deactivated'}"}


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == student_id, User.role == "student"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    # Soft delete
    user.is_active = False
    await db.commit()
    return {"message": "Student deactivated"}


class ClassAssign(BaseModel):
    class_id: Optional[str] = None  # None = unassign from class


@router.patch("/{student_id}/class")
async def assign_student_to_class(
    student_id: str,
    body: ClassAssign,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign or unassign a student to/from a class."""
    # Verify student exists
    user_result = await db.execute(
        select(User).where(User.id == student_id, User.role == "student")
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")

    # Verify class exists if provided
    if body.class_id:
        class_result = await db.execute(select(Class).where(Class.id == body.class_id))
        if not class_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Class not found")

    # Load or create student profile
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    profile.class_id = body.class_id
    await db.commit()
    return {"message": "Class assignment updated", "class_id": body.class_id}
