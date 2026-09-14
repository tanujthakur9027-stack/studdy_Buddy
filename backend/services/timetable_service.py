"""
services/timetable_service.py — Timetable period-time computation and conflict detection.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.db_models import TimetableSlot

settings = get_settings()

PERIOD_MINS = settings.period_duration_minutes   # default 45
LUNCH_MINS = settings.lunch_duration_minutes      # default 45


def compute_slot_times(
    start_time_str: str,
    period_number: int,
    lunch_after_period: int,
) -> tuple[str, str]:
    """
    Compute start and end time strings (HH:MM) for a given period number.

    Args:
        start_time_str: School start time e.g. "09:00"
        period_number: 1-based period number
        lunch_after_period: Lunch break inserted after this period number

    Returns:
        (start_str, end_str) in "HH:MM" format
    """
    h, m = map(int, start_time_str.split(":"))
    base = datetime(2000, 1, 1, h, m)

    offset_minutes = (period_number - 1) * PERIOD_MINS
    # Add lunch break duration if this period is after the lunch break
    if period_number > lunch_after_period:
        offset_minutes += LUNCH_MINS

    start = base + timedelta(minutes=offset_minutes)
    end = start + timedelta(minutes=PERIOD_MINS)

    return start.strftime("%H:%M"), end.strftime("%H:%M")


def compute_lunch_times(
    start_time_str: str,
    lunch_after_period: int,
) -> tuple[str, str]:
    """Return (start, end) of the lunch break."""
    h, m = map(int, start_time_str.split(":"))
    base = datetime(2000, 1, 1, h, m)
    lunch_start = base + timedelta(minutes=lunch_after_period * PERIOD_MINS)
    lunch_end = lunch_start + timedelta(minutes=LUNCH_MINS)
    return lunch_start.strftime("%H:%M"), lunch_end.strftime("%H:%M")


async def check_teacher_conflict(
    db: AsyncSession,
    teacher_id: str,
    timetable_id: str,
    day_of_week: int,
    period_number: int,
    exclude_slot_id: str | None = None,
) -> bool:
    """
    Returns True if the teacher is already assigned to another slot
    at the same day/period in any timetable.
    """
    q = select(TimetableSlot).where(
        and_(
            TimetableSlot.teacher_id == teacher_id,
            TimetableSlot.day_of_week == day_of_week,
            TimetableSlot.period_number == period_number,
            TimetableSlot.timetable_id != timetable_id,
        )
    )
    if exclude_slot_id:
        q = q.where(TimetableSlot.id != exclude_slot_id)
    result = await db.execute(q)
    return result.scalar_one_or_none() is not None


async def check_room_conflict(
    db: AsyncSession,
    room: str,
    timetable_id: str,
    day_of_week: int,
    period_number: int,
    exclude_slot_id: str | None = None,
) -> bool:
    """
    Returns True if the room is already in use at the same day/period
    in a different timetable.
    """
    if not room:
        return False
    q = select(TimetableSlot).where(
        and_(
            TimetableSlot.room == room,
            TimetableSlot.day_of_week == day_of_week,
            TimetableSlot.period_number == period_number,
            TimetableSlot.timetable_id != timetable_id,
        )
    )
    if exclude_slot_id:
        q = q.where(TimetableSlot.id != exclude_slot_id)
    result = await db.execute(q)
    return result.scalar_one_or_none() is not None
