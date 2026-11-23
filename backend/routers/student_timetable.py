"""
routers/student_timetable.py — Student: view published timetable with computed times.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import get_current_user
from models.db_models import Timetable, TimetableSlot, StudentProfile, Subject, User, ClassEnrollment
from services.timetable_service import compute_slot_times, compute_lunch_times

router = APIRouter(prefix="/timetable", tags=["Student - Timetable"])

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@router.get("")
async def get_timetable(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=current_user.id, student_id=f"STU-{current_user.id[:6].upper()}")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    # Get student's class (prioritizing active ClassEnrollment)
    enr_res = await db.execute(
        select(ClassEnrollment.class_id).where(
            ClassEnrollment.student_id == current_user.id,
            ClassEnrollment.is_active == True,  # noqa: E712
        )
    )
    class_id = enr_res.scalar_one_or_none()
    if not class_id:
        class_id = profile.class_id if profile else None

    if not class_id:
        return {"timetable": None, "message": "No class assigned"}

    tt_result = await db.execute(
        select(Timetable).where(
            Timetable.class_id == class_id,
            Timetable.is_published == True,  # noqa: E712
        ).order_by(Timetable.updated_at.desc())
    )
    tt = tt_result.scalars().first()
    if not tt:
        return {"timetable": None, "message": "No timetable published yet"}

    slots_result = await db.execute(
        select(TimetableSlot)
        .where(TimetableSlot.timetable_id == tt.id)
        .order_by(TimetableSlot.day_of_week, TimetableSlot.period_number)
    )
    slots = slots_result.scalars().all()

    # Pre-fetch subjects and teachers in batch to eliminate N+1 database queries
    subject_ids = {s.subject_id for s in slots if s.subject_id}
    teacher_ids = {s.teacher_id for s in slots if s.teacher_id}

    subjects_map: dict[str, str] = {}
    if subject_ids:
        subj_res = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        subjects_map = {s.id: s.name for s in subj_res.scalars().all()}

    teachers_map: dict[str, str] = {}
    if teacher_ids:
        teach_res = await db.execute(select(User).where(User.id.in_(teacher_ids)))
        teachers_map = {u.id: u.full_name for u in teach_res.scalars().all()}

    # Build grid
    lunch_start, lunch_end = compute_lunch_times(tt.start_time, tt.lunch_after_period)
    schedule = []
    for day_idx, day_name in enumerate(DAYS):
        day_slots = [s for s in slots if s.day_of_week == day_idx]
        periods = []
        for s in day_slots:
            st, et = compute_slot_times(tt.start_time, s.period_number, tt.lunch_after_period)
            subj_name = subjects_map.get(s.subject_id, "") if s.subject_id else ""
            teacher_name = teachers_map.get(s.teacher_id, "") if s.teacher_id else ""

            periods.append({
                "period_number": s.period_number,
                "subject": subj_name,
                "teacher": teacher_name,
                "room": s.room,
                "start_time": st,
                "end_time": et,
            })
        schedule.append({"day": day_name, "day_index": day_idx, "periods": periods})

    return {
        "timetable_id": tt.id,
        "name": tt.name,
        "start_time": tt.start_time,
        "periods_per_day": tt.periods_per_day,
        "lunch_after_period": tt.lunch_after_period,
        "lunch_start": lunch_start,
        "lunch_end": lunch_end,
        "schedule": schedule,
    }


@router.get("/today")
async def get_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today_idx = datetime.now(timezone.utc).weekday()  # 0=Mon..6=Sun
    if today_idx > 5:
        return {"day": DAYS[0] if today_idx == 6 else "Sunday", "periods": [], "is_weekend": True}

    full = await get_timetable(current_user, db)
    if not full.get("schedule"):
        return {"day": DAYS[today_idx], "periods": [], "is_weekend": False}

    day_data = next(
        (d for d in full["schedule"] if d["day_index"] == today_idx), None
    )
    return {
        "day": DAYS[today_idx],
        "periods": day_data["periods"] if day_data else [],
        "is_weekend": False,
        "lunch_start": full.get("lunch_start"),
        "lunch_end": full.get("lunch_end"),
    }
