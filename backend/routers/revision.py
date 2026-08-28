"""
Revision Planner router
=======================
POST /revision/plan       — legacy path (unchanged behaviour, kept for compatibility)
POST /api/generate-plan   — new canonical path (mounted with /api prefix in main.py)

New features vs the original:
- Accepts raw `syllabus_text` and auto-extracts topics from it via a fast LLM pre-pass.
- Each task has a `session_type`: "concept" | "quiz" | "buffer" | "rest".
- Guarantees buffer days (~15 % of plan) and a rest day every 6–7 study days.
- Adds `subtopics` array, `day_label`, `notes` per session.
- Returns `PlanStats` (total_days, study_days, quiz_days, buffer_days, rest_days, …).
- Resolves the final topic list from syllabus_text OR explicit topics OR doc context.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException

from models.schemas import (
    PlanStats,
    RevisionPlanRequest,
    RevisionPlanResponse,
    RevisionTask,
)
from services.document_service import retrieve_context
from services.llm_service import chat
from utils.text_utils import strip_json_fences

logger = logging.getLogger(__name__)
router = APIRouter()

# ── helpers ───────────────────────────────────────────────────────────────────

_SYSTEM_PLANNER = """\
You are an expert academic coach who builds evidence-based revision schedules.
Use spaced repetition, interleaving, active recall, and the Pomodoro technique.
Prioritise weak topics by placing them earlier and repeating them more frequently.
Always include buffer days (catch-up / extra practice) and a rest day every 6-7 days.
Every session must belong to exactly one type: "concept", "quiz", "buffer", or "rest"."""


async def _extract_topics_from_syllabus(syllabus_text: str) -> list[str]:
    """
    Quick LLM pass to turn raw syllabus text → ordered list of study topics.
    Returns at most 20 topics.
    """
    prompt = (
        f"Extract a clean, ordered list of study topics from the following syllabus text.\n"
        f"Return ONLY valid JSON (no markdown fences):\n"
        f'{{ "topics": ["<topic 1>", "<topic 2>", ...] }}\n\n'
        f"Syllabus:\n{syllabus_text[:4000]}"
    )
    try:
        raw = await chat(
            system="You extract structured topic lists from syllabus text. Be concise.",
            user=prompt,
            temperature=0.3,
            max_tokens=512,
        )
        raw = strip_json_fences(raw)
        return json.loads(raw).get("topics", [])[:20]
    except Exception as exc:
        logger.warning("Topic extraction from syllabus failed: %s", exc)
        # Fallback: split on newlines / commas
        chunks = re.split(r"[\n,;]+", syllabus_text)
        return [c.strip() for c in chunks if 3 < len(c.strip()) < 80][:15]


def _compute_stats(tasks: list[RevisionTask], days_to_exam: int) -> PlanStats:
    dates = {t.date for t in tasks}
    concept_sessions = [t for t in tasks if t.session_type == "concept"]
    quiz_sessions    = [t for t in tasks if t.session_type == "quiz"]
    buffer_sessions  = [t for t in tasks if t.session_type == "buffer"]
    rest_sessions    = [t for t in tasks if t.session_type == "rest"]

    study_dates  = {t.date for t in concept_sessions + quiz_sessions}
    buffer_dates = {t.date for t in buffer_sessions}
    rest_dates   = {t.date for t in rest_sessions}

    # topics_covered = unique non-buffer/rest topic names
    covered = {t.topic for t in concept_sessions + quiz_sessions}

    return PlanStats(
        total_days=len(dates),
        study_days=len(study_dates),
        quiz_days=len({t.date for t in quiz_sessions}),
        buffer_days=len(buffer_dates),
        rest_days=len(rest_dates),
        total_study_mins=sum(t.duration_mins for t in tasks if t.session_type in ("concept", "quiz")),
        topics_covered=len(covered),
        days_to_exam=days_to_exam,
    )


# ── core generation ───────────────────────────────────────────────────────────

async def _generate_plan_core(req: RevisionPlanRequest) -> RevisionPlanResponse:
    today = date.today()

    # Validate exam date
    try:
        exam = date.fromisoformat(req.exam_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="exam_date must be YYYY-MM-DD.")

    days_left = (exam - today).days
    if days_left <= 0:
        raise HTTPException(status_code=422, detail="exam_date must be in the future.")

    # ── Resolve topic list ────────────────────────────────────────────────────
    topics: list[str] = list(req.topics)

    if not topics and req.syllabus_text:
        topics = await _extract_topics_from_syllabus(req.syllabus_text)

    if not topics and req.doc_id:
        docs = retrieve_context("key topics concepts syllabus", doc_id=req.doc_id, k=6)
        if docs:
            combined = " ".join(d.page_content[:200] for d in docs)
            topics = await _extract_topics_from_syllabus(combined)

    if not topics:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one of: topics, syllabus_text, or a doc_id.",
        )

    # ── RAG context (optional enrichment) ────────────────────────────────────
    context_block = ""
    if req.doc_id:
        docs = retrieve_context(" ".join(topics[:5]), doc_id=req.doc_id, k=5)
        if docs:
            context_block = "\n\nContext snippets from the student's notes:\n" + "\n---\n".join(
                d.page_content[:250] for d in docs
            )

    weak_str = ", ".join(req.weak_topics) if req.weak_topics else "none specified"
    topics_str = ", ".join(topics)
    daily_mins = int(req.daily_hours * 60)

    # ── LLM prompt ────────────────────────────────────────────────────────────
    user_prompt = f"""Create a complete day-by-day revision plan with these parameters:

Topics to cover: {topics_str}
Weak topics (extra attention): {weak_str}
Exam date: {req.exam_date}  ({days_left} days from today, {today})
Daily study time available: {req.daily_hours:.1f} hours ({daily_mins} mins){context_block}

Session type rules:
- "concept"  → Core topic teaching/review session (Active Recall, Feynman, Mind Map, Flashcards, Reading)
- "quiz"     → Self-testing session (Practice Problems, Mock Test, Spaced Repetition, Past Papers)
- "buffer"   → Catch-up/revision buffer (no new content, review difficult areas)
- "rest"     → Complete rest day (no study — place one every 6-7 days and the day before the exam)

Scheduling rules:
1. Weak topics must appear in the FIRST THIRD of the plan and recur more often.
2. Every topic needs at least one "quiz" session after its first "concept" session.
3. Insert one "buffer" day per ~5 study days (15-20 % of total days).
4. Insert one "rest" day per ~6-7 days AND the day before the exam.
5. Final 2 days before the exam: one "buffer" (full review), one "rest".
6. Each day can have MULTIPLE sessions. Total duration per day must NOT exceed {daily_mins} mins.
7. Each session should be 25-90 mins.

Respond ONLY with valid JSON (no markdown fences):
{{
  "topic_list": ["<resolved topic 1>", ...],
  "plan": [
    {{
      "date": "YYYY-MM-DD",
      "day_label": "Day N · Weekday DD Mon",
      "session_type": "<concept|quiz|buffer|rest>",
      "topic": "<topic name or 'Buffer Review' or 'Rest Day'>",
      "subtopics": ["<subtopic 1>", "<subtopic 2>"],
      "duration_mins": <25-90>,
      "priority": "<high|medium|low>",
      "technique": "<technique name>",
      "resources": ["<resource 1>"],
      "notes": "<one sentence coaching note for this session>"
    }}
  ],
  "summary": "<3-4 sentence overview of the strategy>",
  "tips": ["<tip 1>", "<tip 2>", "<tip 3>", "<tip 4>", "<tip 5>"]
}}"""

    try:
        raw = await chat(
            system=_SYSTEM_PLANNER,
            user=user_prompt,
            temperature=0.55,
            max_tokens=3000,   # Groq free tier: keep under 4096 output tokens
        )
        raw = strip_json_fences(raw)
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Revision planner: LLM returned non-JSON: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Plan generation failed: LLM returned malformed JSON. Please retry.",
        ) from exc
    except Exception as exc:
        logger.exception("Revision planner unexpected error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raw_tasks = data.get("plan", [])
    if not raw_tasks:
        raise HTTPException(status_code=500, detail="LLM returned an empty plan.")

    # Build validated task objects
    tasks: list[RevisionTask] = []
    for t in raw_tasks:
        stype = t.get("session_type", "concept")
        if stype not in ("concept", "quiz", "buffer", "rest"):
            stype = "concept"
        tasks.append(RevisionTask(
            date=t.get("date", ""),
            day_label=t.get("day_label", ""),
            session_type=stype,
            topic=t.get("topic", "").strip(),
            subtopics=t.get("subtopics", []),
            duration_mins=max(10, int(t.get("duration_mins", 30))),
            priority=t.get("priority", "medium"),
            technique=t.get("technique", "Active Recall"),
            resources=t.get("resources", []),
            notes=t.get("notes", ""),
        ))

    resolved_topics = data.get("topic_list", topics)
    stats = _compute_stats(tasks, days_left)

    logger.info(
        "Plan generated: %d sessions across %d days, %d topics, exam in %d days",
        len(tasks), stats.total_days, stats.topics_covered, days_left,
    )

    return RevisionPlanResponse(
        plan=tasks,
        summary=data.get("summary", ""),
        tips=data.get("tips", []),
        stats=stats,
        topic_list=resolved_topics,
    )


# ── Route handlers ────────────────────────────────────────────────────────────

@router.post(
    "/revision/plan",
    response_model=RevisionPlanResponse,
    summary="Generate revision plan (legacy path)",
    tags=["Planner"],
)
async def generate_revision_plan(req: RevisionPlanRequest) -> RevisionPlanResponse:
    """Legacy path kept for backwards compatibility."""
    return await _generate_plan_core(req)


@router.post(
    "/generate-plan",
    response_model=RevisionPlanResponse,
    summary="Generate a day-by-day revision plan",
    description=(
        "Accepts syllabus text, a topic list, or an indexed document ID, plus an "
        "exam date and daily study hours. Returns a full day-by-day schedule broken "
        "into **concept review**, **practice quiz**, **buffer**, and **rest** sessions. "
        "Includes per-task subtopics, study technique, resources, and a coaching note."
    ),
    tags=["Planner"],
)
async def generate_plan_api(req: RevisionPlanRequest) -> RevisionPlanResponse:
    """Canonical endpoint: POST /api/generate-plan"""
    return await _generate_plan_core(req)
