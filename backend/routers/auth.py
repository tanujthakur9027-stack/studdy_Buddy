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

limiter = Limiter(key_func=get_remote_address)

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
        if email_sent:
            return f"{prefix}Security code sent! (Dev Auto-fill also enabled below; please check inbox and spam folder)."
        return f"{prefix}Security code generated below for instant access (Development Mode)."
    if email_sent:
        return f"{prefix}Security verification code dispatched! Please check your email inbox and Spam/Junk folder."
    current_settings = get_settings()
    if not current_settings.smtp_host:
        return f"{prefix}Notice: Real email sending is active, but SMTP_HOST is not configured in backend/.env. Security code provided below."
    return f"{prefix}Email dispatch issue detected. Backup security code provided below for instant verification."


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
        valid_keys = [settings.admin_seed_password, "admin2024", "Admin@StudyBuddy2024"]
        if settings.secret_key:
            valid_keys.append(settings.secret_key[:8])
        if body.admin_key and body.admin_key.strip() not in valid_keys:
            raise HTTPException(status_code=403, detail="Invalid Administrator Setup Key.")

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
        # Student registration
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

    current_settings = get_settings()
    if current_settings.otp_auth_enabled:
        code = f"{secrets.randbelow(900000) + 100000}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=current_settings.otp_expire_minutes)
        new_otp = AuthOTP(email=user.email, otp_code=code, purpose="login", expires_at=expires, is_used=False)
        db.add(new_otp)
        await db.commit()

        acc_type = "Administrator" if is_admin_reg else "Student"
        email_html = f"""
        <p>Hello <b>{user.full_name}</b>,</p>
        <p>Welcome to StudyBuddy! Your {acc_type} account verification code (OTP) is:</p>
        <div style="font-size:32px;font-weight:900;letter-spacing:8px;color:#818cf8;background:#1e1b4b;padding:14px 20px;border-radius:10px;text-align:center;margin:16px 0;display:inline-block;">{code}</div>
        <p style="font-size:13px;color:#9ca3af;">This code is valid for {current_settings.otp_expire_minutes} minutes.</p>
        """
        email_sent = await send_email(to=user.email, subject=f"[StudyBuddy] Verify Your {acc_type} Account", body=email_html)
        print(f"\n=======================================================\n🔑 [STUDYBUDDY OTP] Registration code for {user.email}: >>> {code} <<<\n=======================================================\n", flush=True)

        is_sim = bool(current_settings.otp_simulation_mode or not email_sent)
        return AuthResponse(
            access_token=None,
            user=None,
            otp_required=True,
            email=user.email,
            message=_get_otp_dispatch_message(email_sent, f"{acc_type} account created.", sim_active=is_sim),
            simulation_otp=code if is_sim else None,
        )

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

    valid_keys = [settings.admin_seed_password, "admin2024", "Admin@StudyBuddy2024"]
    if settings.secret_key:
        valid_keys.append(settings.secret_key[:8])

    if body.admin_key and body.admin_key.strip() not in valid_keys:
        raise HTTPException(
            status_code=403,
            detail="Invalid Administrator Setup Key. Default is 'Admin@StudyBuddy2024'.",
        )

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

    current_settings = get_settings()
    if current_settings.otp_auth_enabled:
        code = f"{secrets.randbelow(900000) + 100000}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=current_settings.otp_expire_minutes)
        new_otp = AuthOTP(email=user.email, otp_code=code, purpose="login", expires_at=expires, is_used=False)
        db.add(new_otp)
        await db.commit()

        email_html = f"""
        <p>Hello <b>{user.full_name}</b>,</p>
        <p>Welcome to StudyBuddy as an Administrator! Your verification code (OTP) is:</p>
        <div style="font-size:32px;font-weight:900;letter-spacing:8px;color:#818cf8;background:#1e1b4b;padding:14px 20px;border-radius:10px;text-align:center;margin:16px 0;display:inline-block;">{code}</div>
        <p style="font-size:13px;color:#9ca3af;">This code is valid for {current_settings.otp_expire_minutes} minutes.</p>
        """
        email_sent = await send_email(to=user.email, subject="[StudyBuddy] Admin Verification Code", body=email_html)
        print(f"\n=======================================================\n🔑 [STUDYBUDDY OTP] Admin Registration code for {user.email}: >>> {code} <<<\n=======================================================\n", flush=True)

        is_sim = bool(current_settings.otp_simulation_mode or not email_sent)
        return AuthResponse(
            access_token=None,
            user=None,
            otp_required=True,
            email=user.email,
            message=_get_otp_dispatch_message(email_sent, "Administrator account created.", sim_active=is_sim),
            simulation_otp=code if is_sim else None,
        )

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

    # If an OTP code was provided directly in login payload
    if body.otp_code:
        now_utc = datetime.now(timezone.utc)
        otp_res = await db.execute(
            select(AuthOTP)
            .where(
                AuthOTP.email == user.email,
                AuthOTP.is_used == False,
                AuthOTP.expires_at > now_utc,
            )
            .order_by(AuthOTP.created_at.desc())
        )
        otp_rec = otp_res.scalar_one_or_none()
        if not otp_rec or otp_rec.otp_code != body.otp_code.strip():
            raise HTTPException(status_code=400, detail="Invalid or expired OTP code")
        otp_rec.is_used = True
        await db.commit()

        token = create_access_token({"sub": user.id, "role": user.role})
        response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600 * 24)
        user_resp = await _build_user_response(user, db)
        return AuthResponse(access_token=token, user=user_resp, otp_required=False)

    current_settings = get_settings()
    # 2-Step OTP Authentication Flow
    if current_settings.otp_auth_enabled:
        await db.execute(
            update(AuthOTP)
            .where(AuthOTP.email == user.email, AuthOTP.is_used == False)
            .values(is_used=True)
        )
        code = f"{secrets.randbelow(900000) + 100000}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=current_settings.otp_expire_minutes)
        new_otp = AuthOTP(email=user.email, otp_code=code, purpose="login", expires_at=expires, is_used=False)
        db.add(new_otp)
        await db.commit()

        email_html = f"""
        <p>Hello <b>{user.full_name}</b>,</p>
        <p>Your one-time security verification code (OTP) for StudyBuddy is:</p>
        <div style="font-size:32px;font-weight:900;letter-spacing:8px;color:#818cf8;background:#1e1b4b;padding:14px 20px;border-radius:10px;text-align:center;margin:16px 0;display:inline-block;">{code}</div>
        <p style="font-size:13px;color:#9ca3af;">This code is valid for {current_settings.otp_expire_minutes} minutes. Please do not share this code with anyone.</p>
        """
        email_sent = await send_email(to=user.email, subject="[StudyBuddy] Your Login Verification Code", body=email_html)
        print(f"\n=======================================================\n🔑 [STUDYBUDDY OTP] Login code for {user.email}: >>> {code} <<<\n=======================================================\n", flush=True)

        is_sim = bool(current_settings.otp_simulation_mode or not email_sent)
        return AuthResponse(
            access_token=None,
            user=None,
            otp_required=True,
            email=user.email,
            message=_get_otp_dispatch_message(email_sent, sim_active=is_sim),
            simulation_otp=code if is_sim else None,
        )

    # Direct login if OTP auth is turned off
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
    email = body.email.strip().lower()
    code = body.otp_code.strip()

    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    now_utc = datetime.now(timezone.utc)
    otp_result = await db.execute(
        select(AuthOTP)
        .where(
            AuthOTP.email == email,
            AuthOTP.is_used == False,
            AuthOTP.expires_at > now_utc,
        )
        .order_by(AuthOTP.created_at.desc())
    )
    otp_row = otp_result.scalar_one_or_none()
    if not otp_row or otp_row.otp_code != code:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP verification code.")

    otp_row.is_used = True
    await db.commit()

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
    email = body.email.strip().lower()
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    await db.execute(
        update(AuthOTP)
        .where(AuthOTP.email == email, AuthOTP.is_used == False)
        .values(is_used=True)
    )

    current_settings = get_settings()
    code = f"{secrets.randbelow(900000) + 100000}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=current_settings.otp_expire_minutes)
    new_otp = AuthOTP(email=email, otp_code=code, purpose="login", expires_at=expires, is_used=False)
    db.add(new_otp)
    await db.commit()

    email_html = f"""
    <p>Hello <b>{user.full_name}</b>,</p>
    <p>Your new StudyBuddy one-time security code is:</p>
    <div style="font-size:32px;font-weight:900;letter-spacing:8px;color:#818cf8;background:#1e1b4b;padding:14px 20px;border-radius:10px;text-align:center;margin:16px 0;display:inline-block;">{code}</div>
    <p style="font-size:13px;color:#9ca3af;">Valid for {current_settings.otp_expire_minutes} minutes.</p>
    """
    email_sent = await send_email(to=email, subject="[StudyBuddy] Resent OTP Verification Code", body=email_html)
    print(f"\n=======================================================\n🔑 [STUDYBUDDY OTP] Resent code for {user.email}: >>> {code} <<<\n=======================================================\n", flush=True)

    is_sim = bool(current_settings.otp_simulation_mode or not email_sent)
    return {
        "message": _get_otp_dispatch_message(email_sent, "Fresh code:", sim_active=is_sim),
        "simulation_otp": code if is_sim else None,
    }


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
