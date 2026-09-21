from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from database import get_db
from models.db_models import User, StudentProfile
from services.auth_service import hash_password, verify_password, create_access_token
from dependencies.auth import get_current_user
from config import get_settings
import re

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    student_id: str
    phone: str = ""
    course: str = ""
    branch: str = ""
    semester: str = ""
    section: str = ""
    academic_year: str = ""
    dob: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check duplicate student ID
    existing_sid = await db.execute(select(StudentProfile).where(StudentProfile.student_id == body.student_id))
    if existing_sid.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Student ID already registered")

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="student",
        is_active=True,
    )
    db.add(user)
    await db.flush()  # get user.id

    profile = StudentProfile(
        user_id=user.id,
        student_id=body.student_id,
        phone=body.phone,
        course=body.course,
        branch=body.branch,
        semester=body.semester,
        section=body.section,
        academic_year=body.academic_year,
        dob=body.dob,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600 * 24)

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=str(user.created_at),
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower().strip()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600 * 24)

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=str(user.created_at),
        ),
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=str(current_user.created_at),
    )


@router.post("/change-password", status_code=200)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password after verifying the current one."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Password changed successfully"}
