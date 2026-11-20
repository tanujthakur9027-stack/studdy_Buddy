"""
routers/admin_students.py — Admin: student management.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
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
    role: Optional[str] = None


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


@router.get("/export/excel")
async def export_students_excel(
    search: str = "",
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download a styled Excel spreadsheet (.xlsx) of all registered students."""
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
    q = q.order_by(User.created_at.desc())
    result = await db.execute(q)
    rows = result.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students Roster"

    headers = [
        "Student ID", "Full Name", "Email Address", "Phone",
        "Course", "Branch", "Semester", "Section",
        "Academic Year", "Date of Birth", "Account Status", "Registered Date"
    ]
    ws.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    ws.row_dimensions[1].height = 26

    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    for row_idx, (user, prof) in enumerate(rows, start=2):
        row_data = [
            prof.student_id if prof and prof.student_id else f"STU-{user.id[:6].upper()}",
            user.full_name or "",
            user.email,
            prof.phone if prof and prof.phone else "",
            prof.course if prof and prof.course else "",
            prof.branch if prof and prof.branch else "",
            prof.semester if prof and prof.semester else "",
            prof.section if prof and prof.section else "",
            prof.academic_year if prof and prof.academic_year else "",
            prof.dob if prof and prof.dob else "",
            "Active" if user.is_active else "Inactive",
            user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
        ]
        ws.append(row_data)
        fill = alt_fill if row_idx % 2 == 0 else white_fill
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.fill = fill
            cell.alignment = Alignment(vertical="center")

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"studybuddy_students_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/csv")
async def export_students_csv(
    search: str = "",
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download a CSV file of all registered students."""
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
    q = q.order_by(User.created_at.desc())
    result = await db.execute(q)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Student ID", "Full Name", "Email Address", "Phone",
        "Course", "Branch", "Semester", "Section",
        "Academic Year", "Date of Birth", "Status", "Registered At"
    ])
    for user, prof in rows:
        writer.writerow([
            prof.student_id if prof and prof.student_id else f"STU-{user.id[:6].upper()}",
            user.full_name or "",
            user.email,
            prof.phone if prof and prof.phone else "",
            prof.course if prof and prof.course else "",
            prof.branch if prof and prof.branch else "",
            prof.semester if prof and prof.semester else "",
            prof.section if prof and prof.section else "",
            prof.academic_year if prof and prof.academic_year else "",
            prof.dob if prof and prof.dob else "",
            "Active" if user.is_active else "Inactive",
            str(user.created_at),
        ])

    buf.seek(0)
    filename = f"studybuddy_students_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def _resolve_student(db: AsyncSession, identifier: str) -> tuple[Optional[User], Optional[StudentProfile]]:
    result = await db.execute(
        select(User, StudentProfile)
        .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
        .where(
            (User.id == identifier) | (StudentProfile.student_id == identifier),
            User.role == "student",
        )
    )
    row = result.first()
    if not row:
        return None, None
    return row[0], row[1]


@router.get("/{student_id}", response_model=StudentProfileOut)
async def get_student(
    student_id: str,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user, profile = await _resolve_student(db, student_id)
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
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
    user, _ = await _resolve_student(db, student_id)
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
    user, profile = await _resolve_student(db, student_id)
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    if not profile:
        profile = StudentProfile(user_id=user.id, student_id=f"STU-{user.id[:6].upper()}")
        db.add(profile)

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None and body.email.strip():
        user.email = body.email.strip().lower()
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None and body.role in ("admin", "student"):
        user.role = body.role

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
    user, _ = await _resolve_student(db, student_id)
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
    user, profile = await _resolve_student(db, student_id)
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    if body.class_id:
        class_result = await db.execute(select(Class).where(Class.id == body.class_id))
        if not class_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Class not found")

    if not profile:
        profile = StudentProfile(user_id=user.id, student_id=f"STU-{user.id[:6].upper()}")
        db.add(profile)

    profile.class_id = body.class_id
    await db.commit()
    return {"message": "Class assignment updated", "class_id": body.class_id}
