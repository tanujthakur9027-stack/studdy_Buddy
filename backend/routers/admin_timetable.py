"""
routers/admin_timetable.py — Admin: timetable CRUD and publish.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin
from models.db_models import Timetable, TimetableSlot, StudentProfile
from services.notification_service import create_bulk_notifications
from services.timetable_service import (
    compute_slot_times, compute_lunch_times,
    check_teacher_conflict, check_room_conflict,
)

router = APIRouter(prefix="/admin/timetables", tags=["Admin - Timetable"])


class TimetableCreate(BaseModel):
    class_id: str
    section_id: Optional[str] = None
    name: str = "Timetable"
    start_time: str = "09:00"
    periods_per_day: int = 8
    lunch_after_period: int = 4


class TimetableOut(BaseModel):
    id: str
    class_id: str
    section_id: Optional[str]
    name: str
    start_time: str
    periods_per_day: int
    lunch_after_period: int
    is_published: bool
    created_at: str


class SlotCreate(BaseModel):
    day_of_week: int        # 0=Mon..5=Sat
    period_number: int      # 1-based
    subject_id: Optional[str] = None
    teacher_id: Optional[str] = None
    room: str = ""


class SlotOut(BaseModel):
    id: str
    day_of_week: int
    period_number: int
    subject_id: Optional[str]
    teacher_id: Optional[str]
    room: str
    start_time: str
    end_time: str


@router.get("", response_model=list[TimetableOut])
async def list_timetables(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Timetable).order_by(Timetable.created_at.desc()))
    return [_tt_out(t) for t in result.scalars()]


@router.post("", response_model=TimetableOut, status_code=201)
async def create_timetable(body: TimetableCreate, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    tt = Timetable(
        class_id=body.class_id, section_id=body.section_id,
        name=body.name, start_time=body.start_time,
        periods_per_day=body.periods_per_day,
        lunch_after_period=body.lunch_after_period,
        created_by=admin.id,
    )
    db.add(tt)
    await db.commit()
    await db.refresh(tt)
    return _tt_out(tt)


@router.patch("/{tt_id}", response_model=TimetableOut)
async def update_timetable(
    tt_id: str, body: TimetableCreate,
    admin=Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Timetable).where(Timetable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")
    tt.name = body.name
    tt.start_time = body.start_time
    tt.periods_per_day = body.periods_per_day
    tt.lunch_after_period = body.lunch_after_period
    await db.commit()
    return _tt_out(tt)


@router.delete("/{tt_id}")
async def delete_timetable(tt_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Timetable).where(Timetable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")
    await db.delete(tt)
    await db.commit()
    return {"message": "Timetable deleted"}


@router.post("/{tt_id}/publish")
async def publish_timetable(tt_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Timetable).where(Timetable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")

    tt.is_published = True
    await db.flush()

    q = select(StudentProfile.user_id).where(StudentProfile.class_id == tt.class_id)
    student_ids_result = await db.execute(q)
    student_ids = [row[0] for row in student_ids_result.all()]

    if student_ids:
        await create_bulk_notifications(
            db, student_ids,
            title="Timetable Published",
            message=f"The timetable '{tt.name}' has been published.",
            notif_type="timetable",
            reference_id=tt.id,
        )

    await db.commit()
    return {"message": f"Timetable published. Notified {len(student_ids)} students."}


# ── Slot management ───────────────────────────────────────────────────────────

@router.get("/{tt_id}/slots", response_model=list[SlotOut])
async def list_slots(tt_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    tt_result = await db.execute(select(Timetable).where(Timetable.id == tt_id))
    tt = tt_result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")

    result = await db.execute(
        select(TimetableSlot).where(TimetableSlot.timetable_id == tt_id)
        .order_by(TimetableSlot.day_of_week, TimetableSlot.period_number)
    )
    return [_slot_out(s, tt.start_time, tt.lunch_after_period) for s in result.scalars()]


@router.post("/{tt_id}/slots", response_model=SlotOut, status_code=201)
async def create_slot(
    tt_id: str, body: SlotCreate,
    admin=Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    tt_result = await db.execute(select(Timetable).where(Timetable.id == tt_id))
    tt = tt_result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")

    # Conflict detection
    if body.teacher_id:
        conflict = await check_teacher_conflict(
            db, body.teacher_id, tt_id, body.day_of_week, body.period_number
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Teacher conflict: already assigned at this time")

    if body.room:
        room_conflict = await check_room_conflict(
            db, body.room, tt_id, body.day_of_week, body.period_number
        )
        if room_conflict:
            raise HTTPException(status_code=409, detail="Room conflict: already in use at this time")

    slot = TimetableSlot(
        timetable_id=tt_id,
        day_of_week=body.day_of_week,
        period_number=body.period_number,
        subject_id=body.subject_id,
        teacher_id=body.teacher_id,
        room=body.room,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return _slot_out(slot, tt.start_time, tt.lunch_after_period)


@router.patch("/{tt_id}/slots/{slot_id}", response_model=SlotOut)
async def update_slot(
    tt_id: str, slot_id: str, body: SlotCreate,
    admin=Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    tt_result = await db.execute(select(Timetable).where(Timetable.id == tt_id))
    tt = tt_result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")

    result = await db.execute(select(TimetableSlot).where(TimetableSlot.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if body.teacher_id:
        conflict = await check_teacher_conflict(
            db, body.teacher_id, tt_id, body.day_of_week, body.period_number, exclude_slot_id=slot_id
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Teacher conflict")

    slot.day_of_week = body.day_of_week
    slot.period_number = body.period_number
    slot.subject_id = body.subject_id
    slot.teacher_id = body.teacher_id
    slot.room = body.room
    await db.commit()
    return _slot_out(slot, tt.start_time, tt.lunch_after_period)


@router.delete("/{tt_id}/slots/{slot_id}")
async def delete_slot(
    tt_id: str, slot_id: str,
    admin=Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TimetableSlot).where(TimetableSlot.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    await db.delete(slot)
    await db.commit()
    return {"message": "Slot deleted"}


def _tt_out(t: Timetable) -> TimetableOut:
    return TimetableOut(
        id=t.id, class_id=t.class_id, section_id=t.section_id,
        name=t.name, start_time=t.start_time, periods_per_day=t.periods_per_day,
        lunch_after_period=t.lunch_after_period, is_published=t.is_published,
        created_at=str(t.created_at),
    )


def _slot_out(s: TimetableSlot, start_time: str, lunch_after: int) -> SlotOut:
    st, et = compute_slot_times(start_time, s.period_number, lunch_after)
    return SlotOut(
        id=s.id, day_of_week=s.day_of_week, period_number=s.period_number,
        subject_id=s.subject_id, teacher_id=s.teacher_id, room=s.room,
        start_time=st, end_time=et,
    )
