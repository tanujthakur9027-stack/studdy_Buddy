"""
dependencies/auth.py — FastAPI authentication dependencies.

get_current_user      → requires valid JWT; raises 401 if missing/invalid.
get_optional_user     → returns User or None; never raises.
get_current_user_flex → respects AUTH_REQUIRED flag:
                        if True  → behaves like get_current_user
                        if False → returns None (anonymous); AI endpoints
                                   continue to work without a token so that
                                   the legacy Next.js frontend keeps working.
require_admin         → gate for admin-only endpoints.
require_student       → gate for student or admin.
"""
from __future__ import annotations
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.db_models import User, SchoolClass, ClassAdmin, ClassEnrollment
from services.auth_service import decode_token
from config import get_settings
from typing import Optional

security = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    try:
        return await get_current_user(credentials, access_token, db)
    except HTTPException:
        return None


async def get_current_user_flex(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Flexible auth dependency.

    • AUTH_REQUIRED=true  → identical to get_current_user (raises 401 if no token).
    • AUTH_REQUIRED=false → returns None for anonymous requests; routers must handle
      None user_id gracefully (no per-user filtering, data is globally visible).
      This preserves backwards-compatibility with the legacy Next.js frontend.
    """
    if settings.auth_required:
        return await get_current_user(credentials, access_token, db)
    return await get_optional_user(credentials, access_token, db)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("student", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")
    return current_user


async def require_super_admin(current_user: User = Depends(require_admin)) -> User:
    if not current_user.is_super_admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Administrator access required",
        )
    return current_user


async def check_class_access(
    class_id: str,
    user: User,
    db: AsyncSession,
    require_write: bool = False,
) -> SchoolClass:
    """
    Core class permission check.
    - super admin: access to every class (read & write)
    - class admin: access only if listed in ClassAdmin for that class, otherwise 403
    - student: read-only access to their own enrolled class only; write attempts raise 403
    """
    res = await db.execute(select(SchoolClass).where(SchoolClass.id == class_id))
    school_class = res.scalar_one_or_none()
    if not school_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    if user.role == "admin":
        if user.is_super_admin_user:
            return school_class

        # Check if user is an assigned class admin
        res_admin = await db.execute(
            select(ClassAdmin).where(
                ClassAdmin.class_id == class_id,
                ClassAdmin.admin_user_id == user.id,
            )
        )
        if not res_admin.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not assigned to manage this class",
            )
        return school_class

    elif user.role == "student":
        if require_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students have read-only access to class resources",
            )
        # Check active enrollment
        res_enr = await db.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == class_id,
                ClassEnrollment.student_id == user.id,
                ClassEnrollment.is_active == True,
            )
        )
        if not res_enr.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not enrolled in this class",
            )
        return school_class

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_class_access(require_write: bool = False):
    """Factory dependency to enforce class access from path parameter `class_id` or `id`."""
    async def _dependency(
        class_id: Optional[str] = None,
        id: Optional[str] = None,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> SchoolClass:
        cid = class_id or id
        if not cid:
            raise HTTPException(status_code=400, detail="class_id is required")
        return await check_class_access(cid, user, db, require_write=require_write)
    return _dependency
