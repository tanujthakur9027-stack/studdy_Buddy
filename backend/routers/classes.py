"""
routers/classes.py — Class-Based Management System.

Features:
  - CRUD for School Classes (name + section, e.g. "10-A")
  - Multi-admin assignment per class (Super Admin only)
  - Student enrollment (single & CSV bulk upload) with class-unique roll numbers
  - Student transfer and removal preserving enrollment history
  - Class-targeted messaging / broadcast notifications with student narrowing
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from database import get_db
from dependencies.auth import (
    check_class_access,
    get_current_user,
    require_admin,
    require_super_admin,
)
from models.db_models import (
    ClassAdmin,
    ClassEnrollment,
    SchoolClass,
    StudentProfile,
    User,
    Notification,
)
from services.auth_service import hash_password
from services.email_service import send_email
from services.notification_service import create_bulk_notifications

router = APIRouter(prefix="/classes", tags=["Classes"])
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClassCreate(BaseModel):
    name: str                           # e.g. "10"
    section: str = "A"                  # e.g. "A"
    academic_year: str = "2024-2025"    # e.g. "2024-2025"


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    is_active: Optional[bool] = None


class ClassAdminOut(BaseModel):
    id: str
    admin_user_id: str
    email: str
    full_name: str
    created_at: str


class ClassOut(BaseModel):
    id: str
    name: str
    section: str
    academic_year: str
    display_name: str
    created_by: str
    created_at: str
    is_active: bool
    student_count: int = 0
    admins: list[ClassAdminOut] = []


class AssignAdminRequest(BaseModel):
    admin_user_id: Optional[str] = None
    email: Optional[str] = None


class AddStudentRequest(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    roll_number: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UpdateStudentRequest(BaseModel):
    roll_number: Optional[str] = None
    target_class_id: Optional[str] = None  # Transfer to another class


class StudentEnrollmentOut(BaseModel):
    id: str
    class_id: str
    student_id: str   # User.id
    roll_number: str
    full_name: str
    email: str
    joined_at: str
    is_active: bool


class ClassBroadcastRequest(BaseModel):
    title: str
    message: str
    target_student_ids: Optional[list[str]] = None  # Narrow to specific student IDs
    send_email: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _build_class_out(cls: SchoolClass, db: AsyncSession) -> ClassOut:
    # Count active students
    cnt_res = await db.execute(
        select(func.count(ClassEnrollment.id)).where(
            ClassEnrollment.class_id == cls.id,
            ClassEnrollment.is_active == True,  # noqa: E712
        )
    )
    cnt = cnt_res.scalar() or 0

    # Get class admins
    adm_res = await db.execute(
        select(ClassAdmin, User)
        .join(User, User.id == ClassAdmin.admin_user_id)
        .where(ClassAdmin.class_id == cls.id)
    )
    admin_outs = [
        ClassAdminOut(
            id=ca.id,
            admin_user_id=u.id,
            email=u.email,
            full_name=u.full_name or "",
            created_at=str(ca.created_at),
        )
        for ca, u in adm_res.all()
    ]

    return ClassOut(
        id=cls.id,
        name=cls.name,
        section=cls.section,
        academic_year=cls.academic_year,
        display_name=cls.display_name,
        created_by=cls.created_by,
        created_at=str(cls.created_at),
        is_active=cls.is_active,
        student_count=cnt,
        admins=admin_outs,
    )


# ── Class Management ──────────────────────────────────────────────────────────

@router.post("", response_model=ClassOut, status_code=201)
async def create_class(
    body: ClassCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new School Class (e.g. 10-A)."""
    clean_name = body.name.strip()
    clean_sec = body.section.strip().upper()
    clean_year = body.academic_year.strip()

    if not clean_name or not clean_sec:
        raise HTTPException(status_code=400, detail="Class name and section are required")

    # Check unique constraint (name, section, academic_year)
    existing = await db.execute(
        select(SchoolClass).where(
            SchoolClass.name == clean_name,
            SchoolClass.section == clean_sec,
            SchoolClass.academic_year == clean_year,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Class '{clean_name}-{clean_sec}' for academic year '{clean_year}' already exists",
        )

    new_cls = SchoolClass(
        name=clean_name,
        section=clean_sec,
        academic_year=clean_year,
        created_by=current_user.id,
    )
    db.add(new_cls)
    await db.flush()

    # Automatically assign the creator as a ClassAdmin if not super admin
    if not current_user.is_super_admin_user:
        ca = ClassAdmin(class_id=new_cls.id, admin_user_id=current_user.id)
        db.add(ca)

    await db.commit()
    await db.refresh(new_cls)
    return await _build_class_out(new_cls, db)


@router.get("", response_model=list[ClassOut])
async def list_classes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List classes accessible to the current user.
    - Super Admin: all classes
    - Class Admin: only classes they are assigned to
    - Student: their active enrolled class
    """
    if current_user.role == "admin":
        if current_user.is_super_admin_user:
            res = await db.execute(
                select(SchoolClass)
                .order_by(SchoolClass.is_active.desc(), SchoolClass.name, SchoolClass.section)
            )
            classes = res.scalars().all()
        else:
            res = await db.execute(
                select(SchoolClass)
                .join(ClassAdmin, ClassAdmin.class_id == SchoolClass.id)
                .where(ClassAdmin.admin_user_id == current_user.id)
                .order_by(SchoolClass.is_active.desc(), SchoolClass.name, SchoolClass.section)
            )
            classes = res.scalars().all()
    elif current_user.role == "student":
        res = await db.execute(
            select(SchoolClass)
            .join(ClassEnrollment, ClassEnrollment.class_id == SchoolClass.id)
            .where(
                ClassEnrollment.student_id == current_user.id,
                ClassEnrollment.is_active == True,  # noqa: E712
            )
        )
        classes = res.scalars().all()
    else:
        classes = []

    out = []
    for c in classes:
        out.append(await _build_class_out(c, db))
    return out


@router.get("/{id}", response_model=ClassOut)
async def get_class_details(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific class (permission checked)."""
    cls = await check_class_access(id, current_user, db, require_write=False)
    return await _build_class_out(cls, db)


@router.put("/{id}", response_model=ClassOut)
async def update_class(
    id: str,
    body: ClassUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update class metadata (Class Admin or Super Admin)."""
    cls = await check_class_access(id, current_user, db, require_write=True)

    if body.name is not None:
        cls.name = body.name.strip()
    if body.section is not None:
        cls.section = body.section.strip().upper()
    if body.academic_year is not None:
        cls.academic_year = body.academic_year.strip()
    if body.is_active is not None:
        cls.is_active = body.is_active

    await db.commit()
    await db.refresh(cls)
    return await _build_class_out(cls, db)


@router.delete("/{id}")
async def delete_class(
    id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Archive / soft delete a class (sets is_active=False)."""
    cls = await check_class_access(id, current_user, db, require_write=True)
    cls.is_active = False
    await db.commit()
    return {"message": f"Class '{cls.display_name}' has been archived", "id": id}


# ── Class Admins Assignment (Super Admin Only) ───────────────────────────────

@router.post("/{id}/admins", response_model=ClassOut)
async def assign_class_admin(
    id: str,
    body: AssignAdminRequest,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign an admin user to manage a specific class (Super Admin only)."""
    cls_res = await db.execute(select(SchoolClass).where(SchoolClass.id == id))
    cls = cls_res.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    target_user: Optional[User] = None
    if body.admin_user_id:
        u_res = await db.execute(select(User).where(User.id == body.admin_user_id))
        target_user = u_res.scalar_one_or_none()
    elif body.email:
        u_res = await db.execute(select(User).where(User.email == body.email.strip().lower()))
        target_user = u_res.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    if target_user.role != "admin":
        raise HTTPException(status_code=400, detail="Target user does not have 'admin' role")

    # Check if already assigned
    existing = await db.execute(
        select(ClassAdmin).where(
            ClassAdmin.class_id == id,
            ClassAdmin.admin_user_id == target_user.id,
        )
    )
    if not existing.scalar_one_or_none():
        ca = ClassAdmin(class_id=id, admin_user_id=target_user.id)
        db.add(ca)
        await db.commit()

    return await _build_class_out(cls, db)


@router.delete("/{id}/admins/{admin_user_id}")
async def remove_class_admin(
    id: str,
    admin_user_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove an admin user from a class's assigned admins (Super Admin only)."""
    res = await db.execute(
        select(ClassAdmin).where(
            ClassAdmin.class_id == id,
            ClassAdmin.admin_user_id == admin_user_id,
        )
    )
    ca = res.scalar_one_or_none()
    if not ca:
        raise HTTPException(status_code=404, detail="Admin assignment not found for this class")

    await db.delete(ca)
    await db.commit()
    return {"message": "Admin unassigned from class", "class_id": id, "admin_user_id": admin_user_id}


# ── Student Enrollment Management ─────────────────────────────────────────────

@router.get("/{id}/students", response_model=list[StudentEnrollmentOut])
async def list_class_students(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all students enrolled in the class (permission checked)."""
    await check_class_access(id, current_user, db, require_write=False)

    q = (
        select(ClassEnrollment, User)
        .join(User, User.id == ClassEnrollment.student_id)
        .where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.is_active == True,  # noqa: E712
        )
        .order_by(ClassEnrollment.roll_number, User.full_name)
    )
    res = await db.execute(q)

    out = []
    for enr, u in res.all():
        out.append(
            StudentEnrollmentOut(
                id=enr.id,
                class_id=enr.class_id,
                student_id=u.id,
                roll_number=enr.roll_number,
                full_name=u.full_name or "",
                email=u.email,
                joined_at=str(enr.joined_at),
                is_active=enr.is_active,
            )
        )
    return out


@router.post("/{id}/students", response_model=StudentEnrollmentOut, status_code=201)
async def add_student_to_class(
    id: str,
    body: AddStudentRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a student to this class:
    - If user exists (by email or user_id): enroll them into this class.
    - If user does not exist and password+full_name provided: create user + profile + enroll.
    - Roll number is validated for uniqueness within this class.
    """
    cls = await check_class_access(id, current_user, db, require_write=True)

    student_user: Optional[User] = None
    email_clean = body.email.strip().lower() if body.email else None

    if body.user_id:
        res = await db.execute(select(User).where(User.id == body.user_id))
        student_user = res.scalar_one_or_none()
    elif email_clean:
        res = await db.execute(select(User).where(User.email == email_clean))
        student_user = res.scalar_one_or_none()

    # If student user doesn't exist, create account
    if not student_user:
        if not email_clean or not body.password or not body.full_name:
            raise HTTPException(
                status_code=400,
                detail="Student does not exist. Provide email, full_name, and password to create account.",
            )
        student_user = User(
            email=email_clean,
            full_name=body.full_name.strip(),
            password_hash=hash_password(body.password),
            role="student",
        )
        db.add(student_user)
        await db.flush()

        prof = StudentProfile(
            user_id=student_user.id,
            student_id=body.roll_number or f"STU-{student_user.id[:8]}",
            class_id=cls.id,
            section=cls.section,
            academic_year=cls.academic_year,
        )
        db.add(prof)
        await db.flush()

    # Determine roll number
    roll = (body.roll_number or "").strip()
    if not roll:
        # Check existing profile
        p_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_user.id))
        prof = p_res.scalar_one_or_none()
        roll = prof.student_id if (prof and prof.student_id) else f"ROLL-{student_user.id[:6]}"

    # Validate roll number unique within this class
    res_roll = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.roll_number == roll,
            ClassEnrollment.is_active == True,  # noqa: E712
            ClassEnrollment.student_id != student_user.id,
        )
    )
    if res_roll.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Roll number '{roll}' is already assigned in class '{cls.display_name}'",
        )

    # Deactivate any previous active enrollments for this student (one active class at a time)
    await db.execute(
        update(ClassEnrollment)
        .where(ClassEnrollment.student_id == student_user.id, ClassEnrollment.is_active == True)
        .values(is_active=False)
    )

    # Check if enrollment record already exists for this (class_id, student_id)
    enr_res = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.student_id == student_user.id,
        )
    )
    enr = enr_res.scalar_one_or_none()
    if enr:
        enr.roll_number = roll
        enr.is_active = True
    else:
        enr = ClassEnrollment(
            class_id=id,
            student_id=student_user.id,
            roll_number=roll,
            is_active=True,
        )
        db.add(enr)

    # Sync StudentProfile
    p_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_user.id))
    profile = p_res.scalar_one_or_none()
    if profile:
        profile.class_id = id
        profile.section = cls.section
        profile.academic_year = cls.academic_year
        profile.student_id = roll
    else:
        profile = StudentProfile(
            user_id=student_user.id,
            student_id=roll,
            class_id=id,
            section=cls.section,
            academic_year=cls.academic_year,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(enr)

    return StudentEnrollmentOut(
        id=enr.id,
        class_id=enr.class_id,
        student_id=student_user.id,
        roll_number=enr.roll_number,
        full_name=student_user.full_name or "",
        email=student_user.email,
        joined_at=str(enr.joined_at),
        is_active=enr.is_active,
    )


@router.post("/{id}/students/bulk")
async def bulk_upload_students(
    id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import students from a CSV file:
    CSV headers: name, email, roll_number (optional: password)
    Returns a per-row success/error report and validates duplicates.
    """
    cls = await check_class_access(id, current_user, db, require_write=True)

    contents = await file.read()
    try:
        text_data = contents.decode("utf-8-sig")
    except Exception:
        text_data = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_data))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Invalid CSV format: no headers found")

    # Normalize header names (lowercase, stripped)
    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    name_col = headers.get("name") or headers.get("full_name") or headers.get("student_name")
    email_col = headers.get("email") or headers.get("student_email")
    roll_col = headers.get("roll_number") or headers.get("roll") or headers.get("student_id")
    pass_col = headers.get("password") or headers.get("pass")

    if not email_col or not name_col:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least 'name' and 'email' columns (optional: 'roll_number', 'password')",
        )

    results = []
    success_count = 0
    fail_count = 0

    seen_rolls = set()
    # Pre-fetch existing rolls in this class
    existing_rolls_res = await db.execute(
        select(ClassEnrollment.roll_number).where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.is_active == True,  # noqa: E712
        )
    )
    for r in existing_rolls_res.scalars().all():
        seen_rolls.add(r.strip().lower())

    for idx, row in enumerate(reader, start=2):
        name = (row.get(name_col) or "").strip()
        email = (row.get(email_col) or "").strip().lower()
        roll = (row.get(roll_col) or "").strip() if roll_col else ""
        raw_pass = (row.get(pass_col) or "Student@123").strip() if pass_col else "Student@123"

        if not email or "@" not in email:
            results.append({"row": idx, "email": email, "status": "error", "error": "Invalid email address"})
            fail_count += 1
            continue
        if not name:
            results.append({"row": idx, "email": email, "status": "error", "error": "Name is missing"})
            fail_count += 1
            continue

        if not roll:
            roll = f"ROLL-{email.split('@')[0]}"

        roll_key = roll.lower()
        if roll_key in seen_rolls:
            results.append({
                "row": idx, "email": email, "status": "error",
                "error": f"Duplicate roll number '{roll}' inside class '{cls.display_name}'",
            })
            fail_count += 1
            continue

        try:
            # Check or create user
            u_res = await db.execute(select(User).where(User.email == email))
            u = u_res.scalar_one_or_none()
            if not u:
                u = User(
                    email=email,
                    full_name=name,
                    password_hash=hash_password(raw_pass),
                    role="student",
                )
                db.add(u)
                await db.flush()

            # Deactivate previous enrollments
            await db.execute(
                update(ClassEnrollment)
                .where(ClassEnrollment.student_id == u.id, ClassEnrollment.is_active == True)
                .values(is_active=False)
            )

            # Check existing enrollment record for this class
            enr_res = await db.execute(
                select(ClassEnrollment).where(
                    ClassEnrollment.class_id == id,
                    ClassEnrollment.student_id == u.id,
                )
            )
            enr = enr_res.scalar_one_or_none()
            if enr:
                enr.roll_number = roll
                enr.is_active = True
            else:
                enr = ClassEnrollment(
                    class_id=id,
                    student_id=u.id,
                    roll_number=roll,
                    is_active=True,
                )
                db.add(enr)

            # Update StudentProfile
            p_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == u.id))
            prof = p_res.scalar_one_or_none()
            if prof:
                prof.class_id = id
                prof.section = cls.section
                prof.academic_year = cls.academic_year
                prof.student_id = roll
            else:
                prof = StudentProfile(
                    user_id=u.id,
                    student_id=roll,
                    class_id=id,
                    section=cls.section,
                    academic_year=cls.academic_year,
                )
                db.add(prof)

            seen_rolls.add(roll_key)
            success_count += 1
            results.append({"row": idx, "email": email, "roll": roll, "status": "success"})
        except Exception as exc:
            results.append({"row": idx, "email": email, "status": "error", "error": str(exc)})
            fail_count += 1

    await db.commit()
    return {
        "class_id": id,
        "class_name": cls.display_name,
        "total_rows": success_count + fail_count,
        "succeeded": success_count,
        "failed": fail_count,
        "results": results,
    }


@router.put("/{id}/students/{student_id}", response_model=StudentEnrollmentOut)
async def update_class_student(
    id: str,
    student_id: str,
    body: UpdateStudentRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update roll number or transfer student to another class.
    Transfer deactivates old enrollment and activates new enrollment, preserving history.
    """
    await check_class_access(id, current_user, db, require_write=True)

    # Find current active enrollment
    res = await db.execute(
        select(ClassEnrollment, User)
        .join(User, User.id == ClassEnrollment.student_id)
        .where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.is_active == True,  # noqa: E712
        )
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Student enrollment not found in this class")
    enr, stu_user = row

    if body.roll_number:
        clean_roll = body.roll_number.strip()
        # Verify uniqueness in target class
        target_cid = body.target_class_id or id
        dup_res = await db.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == target_cid,
                ClassEnrollment.roll_number == clean_roll,
                ClassEnrollment.student_id != student_id,
                ClassEnrollment.is_active == True,  # noqa: E712
            )
        )
        if dup_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Roll number '{clean_roll}' is already in use")
        enr.roll_number = clean_roll

    # Handle Transfer
    if body.target_class_id and body.target_class_id != id:
        # Check target class access
        target_cls = await check_class_access(body.target_class_id, current_user, db, require_write=True)

        # Deactivate old enrollment
        enr.is_active = False

        # Create or activate enrollment in target class
        new_enr_res = await db.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == target_cls.id,
                ClassEnrollment.student_id == student_id,
            )
        )
        new_enr = new_enr_res.scalar_one_or_none()
        if new_enr:
            new_enr.is_active = True
            new_enr.roll_number = enr.roll_number
            enr = new_enr
        else:
            enr = ClassEnrollment(
                class_id=target_cls.id,
                student_id=student_id,
                roll_number=enr.roll_number,
                is_active=True,
            )
            db.add(enr)

        # Update StudentProfile
        p_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
        prof = p_res.scalar_one_or_none()
        if prof:
            prof.class_id = target_cls.id
            prof.section = target_cls.section
            prof.academic_year = target_cls.academic_year

    await db.commit()
    await db.refresh(enr)

    return StudentEnrollmentOut(
        id=enr.id,
        class_id=enr.class_id,
        student_id=stu_user.id,
        roll_number=enr.roll_number,
        full_name=stu_user.full_name or "",
        email=stu_user.email,
        joined_at=str(enr.joined_at),
        is_active=enr.is_active,
    )


@router.delete("/{id}/students/{student_id}")
async def remove_student_from_class(
    id: str,
    student_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove student from class (soft deactivation preserving academic history)."""
    await check_class_access(id, current_user, db, require_write=True)

    res = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.is_active == True,  # noqa: E712
        )
    )
    enr = res.scalar_one_or_none()
    if not enr:
        raise HTTPException(status_code=404, detail="Student enrollment not found in this class")

    enr.is_active = False

    # Clear profile class_id if it pointed to this class
    p_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    prof = p_res.scalar_one_or_none()
    if prof and prof.class_id == id:
        prof.class_id = None

    await db.commit()
    return {"message": "Student removed from class", "class_id": id, "student_id": student_id}


# ── Class-Targeted Broadcast & Messaging ──────────────────────────────────────

async def _send_bulk_emails_task(recipients: list[str], subject: str, message_body: str) -> None:
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#1f2937">
      <h2 style="color:#2563eb;margin-top:0">{subject}</h2>
      <p style="white-space:pre-wrap;line-height:1.6">{message_body}</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0" />
      <p style="font-size:12px;color:#9ca3af">This is an automated notification from StudyBuddy.</p>
    </div>
    """
    for email in recipients:
        try:
            await send_email(to=email, subject=f"[StudyBuddy] {subject}", body=html)
        except Exception as exc:
            logger.warning("bulk_email_dispatch_failed", extra={"recipient": email, "error": str(exc)})


@router.post("/{id}/broadcast", status_code=201)
async def broadcast_to_class(
    id: str,
    body: ClassBroadcastRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Send announcement or message to the whole class or selected students in it.
    - Verified class admin access required.
    - Resolves recipients strictly from active enrollments in that class.
    - Optional target_student_ids narrowing.
    - Returns within ~100ms with queued status and recipient count.
    """
    cls = await check_class_access(id, current_user, db, require_write=True)

    q = (
        select(User)
        .join(ClassEnrollment, ClassEnrollment.student_id == User.id)
        .where(
            ClassEnrollment.class_id == id,
            ClassEnrollment.is_active == True,  # noqa: E712
            User.is_active == True,              # noqa: E712
        )
    )

    if body.target_student_ids:
        q = q.where(User.id.in_(body.target_student_ids))

    res = await db.execute(q)
    recipients = res.scalars().all()

    if not recipients:
        raise HTTPException(status_code=404, detail="No active students found in this class matching criteria")

    user_ids = [u.id for u in recipients]
    emails = [u.email for u in recipients if u.email]

    # Bulk in-app notifications
    await create_bulk_notifications(
        db=db,
        user_ids=user_ids,
        title=f"[{cls.display_name}] {body.title}",
        message=body.message,
        notif_type="announcement",
        reference_id=cls.id,
    )
    await db.commit()

    if body.send_email and emails and settings.smtp_host:
        background_tasks.add_task(
            _send_bulk_emails_task,
            emails,
            f"[{cls.display_name}] {body.title}",
            body.message,
        )

    return {
        "queued": True,
        "class_id": id,
        "class_name": cls.display_name,
        "recipient_count": len(user_ids),
        "email_queued": bool(body.send_email and settings.smtp_host),
    }
