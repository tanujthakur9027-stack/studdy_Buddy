"""
/api/progress — Study progress summary aggregated from quiz results (per user).

Endpoints:
  GET /api/progress/summary   — overall stats + last-10 quiz score history
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import get_current_user_flex
from models.db_models import QuizResult, FlashcardSession, Flashcard, FeynmanResult, User

router = APIRouter()
log = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuizScorePoint(BaseModel):
    date: str           # ISO date string
    percentage: float
    grade: str
    topic: str
    score: int
    total: int


class TopicStat(BaseModel):
    topic: str
    avg_pct: float
    attempts: int


class DailyActivity(BaseModel):
    date: str           # YYYY-MM-DD
    count: int          # number of study events that day


class FlashcardStats(BaseModel):
    total_sessions: int
    total_cards: int


class FeynmanHistoryPoint(BaseModel):
    date: str           # ISO date string
    score: int
    concept: str
    grade: str


class ProgressSummary(BaseModel):
    total_quizzes: int
    avg_score_pct: float
    best_score_pct: float
    current_streak_days: int
    total_questions_answered: int
    score_history: list[QuizScorePoint]         # last 10, newest first
    weak_topics: list[TopicStat]                # bottom-3 avg score
    strong_topics: list[TopicStat]              # top-3 avg score
    daily_activity: list[DailyActivity]         # last 90 days
    flashcard_stats: FlashcardStats
    feynman_history: list[FeynmanHistoryPoint]  # last 10, newest first


# ── Helper: compute study streak ─────────────────────────────────────────────

def _compute_streak(dates: list[datetime]) -> int:
    """Count consecutive distinct calendar days ending today (or yesterday)."""
    if not dates:
        return 0
    today = datetime.now(timezone.utc).date()
    unique_days = sorted({d.date() for d in dates}, reverse=True)
    streak = 0
    # Allow streak to start from today OR yesterday (so studying yesterday still counts)
    expected = today
    for day in unique_days:
        if day == expected:
            streak += 1
            expected = day - timedelta(days=1)
        elif streak == 0 and day == today - timedelta(days=1):
            # First activity was yesterday, not today — still a valid streak
            streak += 1
            expected = day - timedelta(days=1)
        else:
            break
    return streak


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/progress/summary", response_model=ProgressSummary, tags=["Progress"])
async def get_progress_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Aggregate the current user's quiz results into a progress dashboard summary."""
    uid = current_user.id if current_user else None

    q_results = select(QuizResult).order_by(QuizResult.completed_at.desc())
    q_fc_sessions = select(FlashcardSession)
    q_fc_cards = select(func.count()).select_from(Flashcard).join(
        FlashcardSession, Flashcard.session_id == FlashcardSession.id
    )
    if uid:
        q_results = q_results.where(QuizResult.user_id == uid)
        q_fc_sessions = q_fc_sessions.where(FlashcardSession.user_id == uid)
        q_fc_cards = q_fc_cards.where(FlashcardSession.user_id == uid)

    result = await db.execute(q_results)
    all_results = result.scalars().all()

    # --- Flashcard stats ---
    fc_sessions_result = await db.execute(q_fc_sessions)
    fc_session_rows = fc_sessions_result.scalars().all()
    fc_total_sessions = len(fc_session_rows)
    fc_cards_result = await db.execute(q_fc_cards)
    fc_total_cards = fc_cards_result.scalar() or 0
    flashcard_stats = FlashcardStats(
        total_sessions=fc_total_sessions,
        total_cards=fc_total_cards,
    )

    # --- Feynman history (last 10 for display; all for streak) ---
    q_feynman_all = select(FeynmanResult).order_by(FeynmanResult.created_at.desc())
    if uid:
        q_feynman_all = q_feynman_all.where(FeynmanResult.user_id == uid)
    feynman_all_result = await db.execute(q_feynman_all)
    all_feynman_rows = feynman_all_result.scalars().all()
    feynman_rows = all_feynman_rows[:10]
    feynman_history = [
        FeynmanHistoryPoint(
            date=r.created_at.isoformat(),
            score=r.score,
            concept=r.concept,
            grade=r.grade,
        )
        for r in feynman_rows
    ]

    # --- Daily activity (last 90 days: quiz + feynman + flashcard events) ---
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    # SQLite stores datetimes as naive strings; make cutoff naive for comparison
    cutoff_naive = cutoff.replace(tzinfo=None)
    activity_map: dict[str, int] = {}
    for r in all_results:
        ts = r.completed_at
        # Normalise: strip tzinfo if present so comparison is always naive vs naive
        ts_naive = ts.replace(tzinfo=None) if ts.tzinfo is not None else ts
        if ts_naive >= cutoff_naive:
            day = ts_naive.date().isoformat()
            activity_map[day] = activity_map.get(day, 0) + 1
    for r in all_feynman_rows:
        ts = r.created_at
        ts_naive = ts.replace(tzinfo=None) if ts.tzinfo is not None else ts
        if ts_naive >= cutoff_naive:
            day = ts_naive.date().isoformat()
            activity_map[day] = activity_map.get(day, 0) + 1
    for r in fc_session_rows:
        ts = r.created_at
        ts_naive = ts.replace(tzinfo=None) if ts.tzinfo is not None else ts
        if ts_naive >= cutoff_naive:
            day = ts_naive.date().isoformat()
            activity_map[day] = activity_map.get(day, 0) + 1
    daily_activity = [
        DailyActivity(date=d, count=c)
        for d, c in sorted(activity_map.items())
    ]

    # Combine quiz + feynman + flashcard dates for streak; make naive ones UTC-aware
    def _to_aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    streak_dates = (
        [_to_aware(r.completed_at) for r in all_results]
        + [_to_aware(r.created_at) for r in all_feynman_rows]
        + [_to_aware(r.created_at) for r in fc_session_rows]
    )
    streak = _compute_streak(streak_dates)

    if not all_results:
        return ProgressSummary(
            total_quizzes=0, avg_score_pct=0, best_score_pct=0,
            current_streak_days=streak, total_questions_answered=0,
            score_history=[], weak_topics=[], strong_topics=[],
            daily_activity=daily_activity,
            flashcard_stats=flashcard_stats,
            feynman_history=feynman_history,
        )

    # --- Core stats ---
    percentages = [r.percentage for r in all_results]
    avg_pct     = round(sum(percentages) / len(percentages), 1)
    best_pct    = round(max(percentages), 1)
    total_q     = sum(r.total for r in all_results)

    # --- Score history (last 10) ---
    history = [
        QuizScorePoint(
            date=r.completed_at.isoformat(),
            percentage=r.percentage,
            grade=r.grade,
            topic=r.topic or "General",
            score=r.score,
            total=r.total,
        )
        for r in all_results[:10]
    ]

    # --- Per-topic aggregation ---
    topic_map: dict[str, list[float]] = {}
    for r in all_results:
        key = r.topic or "General"
        topic_map.setdefault(key, []).append(r.percentage)

    topic_stats = [
        TopicStat(
            topic=t,
            avg_pct=round(sum(pcts) / len(pcts), 1),
            attempts=len(pcts),
        )
        for t, pcts in topic_map.items()
    ]
    topic_stats.sort(key=lambda x: x.avg_pct)

    weak_topics   = topic_stats[:3]
    strong_topics = list(reversed(topic_stats[-3:]))

    return ProgressSummary(
        total_quizzes=len(all_results),
        avg_score_pct=avg_pct,
        best_score_pct=best_pct,
        current_streak_days=streak,
        total_questions_answered=total_q,
        score_history=history,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        daily_activity=daily_activity,
        flashcard_stats=flashcard_stats,
        feynman_history=feynman_history,
    )
