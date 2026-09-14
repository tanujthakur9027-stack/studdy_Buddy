"""
routers/student_profile.py — Student: view/edit own profile.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import get_current_user
from models.db_models import User, StudentProfile
from services.storage_service import save_file, ALLOWED_PHOTO_TYPES
from config import get_settings

router = APIRouter(prefix="/students", tags=["Student - Profile"])
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
    section: Optional[str] = None
    dob: Optional[str] = None


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileOut(
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
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


@router.patch("/profile", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        profile.phone = body.phone
    if body.section is not None:
        profile.section = body.section
    if body.dob is not None:
        profile.dob = body.dob

    await db.commit()
    await db.refresh(profile)
    return ProfileOut(
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
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
        raise HTTPException(status_code=404, detail="Profile not found")

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
