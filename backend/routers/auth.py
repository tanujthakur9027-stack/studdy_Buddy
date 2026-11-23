from __future__ import annotations
from datetime import datetime, timezone, timedelta
import re
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from dependencies.auth import get_current_user
from models.db_models import AuthOTP, Class, StudentProfile, User
from services.auth_service import create_access_token, hash_password, verify_password
from services.email_service import send_email

settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.environment.lower() not in ("test", "testing"),
)

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
    student_id: Optional[str] = None
    phone: str = ""
    course: str = ""
    branch: str = ""
    semester: str = ""
    section: str = ""
    academic_year: str = ""
    dob: Optional[str] = None
    role: Optional[str] = "student"
    admin_key: Optional[str] = None

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


class RegisterAdminRequest(BaseModel):
    email: str
    password: str
    full_name: str
    admin_key: Optional[str] = None
    phone: Optional[str] = ""
    student_id: Optional[str] = ""
    role: Optional[str] = "admin"

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
    otp_code: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str


class ResendOTPRequest(BaseModel):
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    student_id: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    dob: Optional[str] = None
    profile_photo_url: Optional[str] = None
    class_id: Optional[str] = None
    class_name: Optional[str] = None

    model_config = {"from_attributes": True}


async def _build_user_response(user: User, db: AsyncSession) -> UserResponse:
    profile_result = await db.execute(
        select(StudentProfile, Class.name)
        .join(Class, StudentProfile.class_id == Class.id, isouter=True)
        .where(StudentProfile.user_id == user.id)
    )
    row = profile_result.first()
    profile: Optional[StudentProfile] = row[0] if row else None
    class_name: Optional[str] = row[1] if row else None

    # Derive student_id identifier for display
    sid = ""
    if profile and profile.student_id:
        sid = profile.student_id
    elif user.role == "admin":
        sid = f"ADMIN-{user.id[:6].upper()}"
    elif user.role == "student":
        sid = f"STU-{user.id[:6].upper()}"
        try:
            profile = StudentProfile(user_id=user.id, student_id=sid)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        except Exception:
            pass

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=str(user.created_at),
        student_id=sid,
        phone=profile.phone if profile else "",
        course=profile.course if profile else "",
        branch=profile.branch if profile else "",
        semester=profile.semester if profile else "",
        section=profile.section if profile else "",
        academic_year=profile.academic_year if profile else "",
        dob=profile.dob if profile else None,
        profile_photo_url=profile.profile_photo_url if profile else None,
        class_id=profile.class_id if profile else None,
        class_name=class_name,
    )


class AuthResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
    otp_required: bool = False
    email: Optional[str] = None
    message: Optional[str] = None
    simulation_otp: Optional[str] = None


def _get_otp_dispatch_message(email_sent: bool, acc_desc: str = "", sim_active: bool = False) -> str:
    prefix = f"{acc_desc} " if acc_desc else ""
    if sim_active:
        return f"{prefix}Security code generated below for instant access (Development Mode)."
    if email_sent:
        return f"{prefix}A 6-digit verification code has been dispatched to your email. Please check your inbox."
    return f"{prefix}Unable to dispatch verification email. Please check email settings or try again later."


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
async def register(request: Request, body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    is_admin_reg = (body.role == "admin")

    if is_admin_reg:
        valid_keys = settings.valid_admin_keys_list
        if not valid_keys and settings.secret_key.strip():
            valid_keys = [settings.secret_key[:8]]
        if not body.admin_key or body.admin_key.strip() not in valid_keys:
            raise HTTPException(status_code=403, detail="Valid admin key required")

        user = User(
            email=email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        admin_sid = body.student_id.strip() if (body.student_id and body.student_id.strip()) else f"ADMIN-{user.id[:6].upper()}"
        admin_prof = StudentProfile(
            user_id=user.id,
            student_id=admin_sid,
            phone=body.phone or "",
            course="Administration",
            branch=body.branch or "Academic Staff",
        )
        db.add(admin_prof)
        await db.commit()
        await db.refresh(user)
    else:
        # Student registration — enforce role is strictly student
        sid = body.student_id or f"STU-{email.split('@')[0][:6].upper()}"
        existing_sid = await db.execute(select(StudentProfile).where(StudentProfile.student_id == sid))
        if existing_sid.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Student ID already registered")

        user = User(
            email=email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
            role="student",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        profile = StudentProfile(
            user_id=user.id,
            student_id=sid,
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

    user_resp = await _build_user_response(user, db)
    return AuthResponse(access_token=token, user=user_resp, otp_required=False)


@router.post("/register-admin", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
async def register_admin(
    request: Request,
    body: RegisterAdminRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register an administrator account with any custom email address format."""
    email = body.email.lower().strip()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    valid_keys = settings.valid_admin_keys_list
    if not valid_keys and settings.secret_key.strip():
        valid_keys = [settings.secret_key[:8]]

    if not body.admin_key or body.admin_key.strip() not in valid_keys:
        raise HTTPException(status_code=403, detail="Valid admin key required")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    admin_sid = body.student_id.strip() if (body.student_id and body.student_id.strip()) else f"ADMIN-{user.id[:6].upper()}"
    admin_prof = StudentProfile(
        user_id=user.id,
        student_id=admin_sid,
        phone=body.phone or "",
        course="Administration",
        branch="Academic Staff",
    )
    db.add(admin_prof)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600 * 24)

    user_resp = await _build_user_response(user, db)
    return AuthResponse(access_token=token, user=user_resp, otp_required=False)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("15/minute")
async def login(request: Request, body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower().strip()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Direct password authentication (OTP permanently removed)
    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600 * 24)

    user_resp = await _build_user_response(user, db)
    return AuthResponse(access_token=token, user=user_resp, otp_required=False)


@router.post("/verify-otp", response_model=AuthResponse)
@limiter.limit("15/minute")
async def verify_otp(
    request: Request,
    body: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Direct fallback returning session for backward compatibility."""
    email = body.email.strip().lower()
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": user.id, "role": user.role})
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600 * 24)

    user_resp = await _build_user_response(user, db)
    return AuthResponse(access_token=token, user=user_resp, otp_required=False)


@router.post("/resend-otp")
@limiter.limit("5/minute")
async def resend_otp(
    request: Request,
    body: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    return {"message": "OTP authentication is permanently disabled. Please log in directly with your password."}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_user_response(current_user, db)


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
