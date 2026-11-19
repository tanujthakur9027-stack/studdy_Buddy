"""
routers/student_profile.py — Student: view/edit own profile.
Supports both /api/students/profile and /api/profile.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from dependencies.auth import get_current_user
from models.db_models import StudentProfile, User
from services.storage_service import ALLOWED_PHOTO_TYPES, save_file

router = APIRouter(prefix="/students", tags=["Student - Profile"])
profile_alias_router = APIRouter(prefix="", tags=["Student - Profile"])
settings = get_settings()


class ProfileOut(BaseModel):
    user_id: str
    email: str
    full_name: str
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


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    dob: Optional[str] = None


async def _handle_get_profile(current_user: User, db: AsyncSession) -> ProfileOut:
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    return ProfileOut(
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name or "",
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


async def _handle_update_profile(body: ProfileUpdate, current_user: User, db: AsyncSession) -> ProfileOut:
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=current_user.id, student_id=f"STU-{current_user.id[:6].upper()}")
        db.add(profile)

    if body.full_name is not None:
        current_user.full_name = body.full_name
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
    if body.dob is not None:
        profile.dob = body.dob

    await db.commit()
    await db.refresh(current_user)
    await db.refresh(profile)
    return await _handle_get_profile(current_user, db)


# ── Routes for /api/students/profile ──────────────────────────────────────────
@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_get_profile(current_user, db)


@router.patch("/profile", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_update_profile(body, current_user, db)


@router.post("/profile/photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=current_user.id, student_id=f"STU-{current_user.id[:6].upper()}")
        db.add(profile)

    try:
        url = await save_file(
            file, "photos",
            max_mb=settings.profile_photo_max_mb,
            allowed_types=ALLOWED_PHOTO_TYPES,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    profile.profile_photo_url = url
    await db.commit()
    return {"profile_photo_url": url}


# ── Direct aliases for /api/profile ───────────────────────────────────────────
@profile_alias_router.get("/profile", response_model=ProfileOut)
async def get_profile_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_get_profile(current_user, db)


@profile_alias_router.patch("/profile", response_model=ProfileOut)
async def update_profile_alias(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_update_profile(body, current_user, db)
