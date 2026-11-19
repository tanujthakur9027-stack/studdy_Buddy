"""
routers/admin_students.py — Admin: student management.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import require_admin
from models.db_models import Class, StudentProfile, User

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


class StudentAdminUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    student_id: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("", response_model=list[StudentProfileOut])
async def list_students(
    page: int = 1,
    page_size: int = 100,
    search: str = "",
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page_size = min(max(page_size, 1), 500)
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
            full_name=user.full_name or "",
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
        full_name=user.full_name or "",
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
    return {"message": f"Student {'activated' if body.is_active else 'deactivated'}", "is_active": user.is_active}


@router.patch("/{student_id}", response_model=StudentProfileOut)
async def update_student(
    student_id: str,
    body: StudentAdminUpdate,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin update student details (name, email, course, semester, etc.)."""
    user_res = await db.execute(select(User).where(User.id == student_id, User.role == "student"))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    profile_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    profile = profile_res.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=student_id, student_id=f"STU-{student_id[:6].upper()}")
        db.add(profile)

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None and body.email.strip():
        user.email = body.email.strip().lower()
    if body.is_active is not None:
        user.is_active = body.is_active

    if body.student_id is not None:
        profile.student_id = body.student_id
    if body.phone is not None:
        profile.phone = body.phone
    if body.course is not None:
        profile.course = body.course
    if body.branch is not None:
        profile.branch = body.branch
    if body.semester is not None:
        profile.semester = body.semester
    if body.section is not None:
        profile.section = body.section
    if body.academic_year is not None:
        profile.academic_year = body.academic_year

    await db.commit()
    await db.refresh(user)
    await db.refresh(profile)

    return StudentProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name or "",
        is_active=user.is_active,
        created_at=str(user.created_at),
        student_id=profile.student_id,
        phone=profile.phone,
        course=profile.course,
        branch=profile.branch,
        semester=profile.semester,
        section=profile.section,
        academic_year=profile.academic_year,
        dob=profile.dob,
        profile_photo_url=profile.profile_photo_url,
        class_id=profile.class_id,
    )


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    permanent: bool = False,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate or permanently delete a student record.
    permanent=false -> soft delete (is_active = False)
    permanent=true -> hard delete from database
    """
    result = await db.execute(select(User).where(User.id == student_id, User.role == "student"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    if permanent:
        await db.delete(user)
        await db.commit()
        return {"message": "Student record permanently deleted", "permanent": True}

    user.is_active = False
    await db.commit()
    return {"message": "Student deactivated", "permanent": False}


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
    user_result = await db.execute(
        select(User).where(User.id == student_id, User.role == "student")
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")

    if body.class_id:
        class_result = await db.execute(select(Class).where(Class.id == body.class_id))
        if not class_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Class not found")

    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=student_id, student_id=f"STU-{student_id[:6].upper()}")
        db.add(profile)

    profile.class_id = body.class_id
    await db.commit()
    return {"message": "Class assignment updated", "class_id": body.class_id}
