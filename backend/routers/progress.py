"""
/api/progress — Study progress summary aggregated from quiz results.

Endpoints:
  GET /api/progress/summary   — overall stats + last-10 quiz score history
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.db_models import QuizResult, FlashcardSession, Flashcard, FeynmanResult

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
    expected = today
    for day in unique_days:
        if day == expected or day == expected - timedelta(days=1) and streak == 0:
            streak += 1
            expected = day - timedelta(days=1)
        else:
            break
    return streak


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/progress/summary", response_model=ProgressSummary, tags=["Progress"])
async def get_progress_summary(db: AsyncSession = Depends(get_db)):
    """Aggregate quiz results into a progress dashboard summary."""
    result = await db.execute(
        select(QuizResult).order_by(QuizResult.completed_at.desc())
    )
    all_results = result.scalars().all()

    # --- Flashcard stats ---
    fc_count_result = await db.execute(select(func.count()).select_from(FlashcardSession))
    fc_total_sessions = fc_count_result.scalar() or 0
    fc_cards_result = await db.execute(select(func.count()).select_from(Flashcard))
    fc_total_cards = fc_cards_result.scalar() or 0
    flashcard_stats = FlashcardStats(
        total_sessions=fc_total_sessions,
        total_cards=fc_total_cards,
    )

    # --- Feynman history (last 10) ---
    feynman_result = await db.execute(
        select(FeynmanResult).order_by(FeynmanResult.created_at.desc()).limit(10)
    )
    feynman_rows = feynman_result.scalars().all()
    feynman_history = [
        FeynmanHistoryPoint(
            date=r.created_at.isoformat(),
            score=r.score,
            concept=r.concept,
            grade=r.grade,
        )
        for r in feynman_rows
    ]

    # --- Daily activity (last 90 days: quiz + feynman events) ---
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    activity_map: dict[str, int] = {}
    for r in all_results:
        if r.completed_at >= cutoff:
            day = r.completed_at.date().isoformat()
            activity_map[day] = activity_map.get(day, 0) + 1
    for r in feynman_rows:
        if r.created_at >= cutoff:
            day = r.created_at.date().isoformat()
            activity_map[day] = activity_map.get(day, 0) + 1
    daily_activity = [
        DailyActivity(date=d, count=c)
        for d, c in sorted(activity_map.items())
    ]

    if not all_results:
        return ProgressSummary(
            total_quizzes=0, avg_score_pct=0, best_score_pct=0,
            current_streak_days=0, total_questions_answered=0,
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
    streak      = _compute_streak([r.completed_at for r in all_results])

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
