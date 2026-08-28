"""
Quiz router
===========
POST /quiz/generate      — legacy path kept for backwards compatibility
POST /api/generate-quiz  — new canonical path (mounted with /api prefix in main.py)
POST /quiz/submit        — score answers, produce per-question breakdown + weak topics

Key improvements over the original:
- Accepts parsed notes context (doc_id) OR free-text topic or BOTH.
- Each question carries topic_tag and hint fields.
- Strict 4-option MCQ prompt with difficulty distribution enforcement.
- Submission returns per-question details, strong/weak topic split, letter grade.
- Weak-topic analysis is done in the same LLM call as scoring (no second round-trip).
"""
from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from models.schemas import (
    QuizAnswerDetail,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizQuestion,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from services.document_service import retrieve_context
from services.llm_service import chat
from utils.text_utils import strip_json_fences

logger = logging.getLogger(__name__)
router = APIRouter()

# In-process quiz store — maps quiz_id → list of QuizQuestion
# Replace with Redis / DB for multi-worker / production deployments.
_quiz_store: dict[str, list[QuizQuestion]] = {}

# ── Prompt helpers ────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are an expert educator and assessment designer. "
    "Create rigorous, unambiguous multiple-choice questions. "
    "Every question must have EXACTLY 4 distinct options and ONE correct answer. "
    "Distractors must be plausible but clearly wrong to a knowledgeable student."
)


def _difficulty_distribution(difficulty: str, n: int) -> str:
    if difficulty == "easy":
        return f"All {n} questions should be straightforward recall (difficulty: easy)."
    if difficulty == "medium":
        return f"All {n} questions should test application and understanding (difficulty: medium)."
    if difficulty == "hard":
        return f"All {n} questions should require analysis, synthesis, or evaluation (difficulty: hard)."
    # Mixed
    easy_n  = max(1, round(n * 0.30))
    med_n   = max(1, round(n * 0.50))
    hard_n  = n - easy_n - med_n
    return (
        f"Create {easy_n} easy recall questions, "
        f"{med_n} medium application questions, and "
        f"{hard_n} hard analysis questions. "
        "Mark each with its actual difficulty."
    )


def _grade(pct: float) -> str:
    if pct >= 90: return "S"
    if pct >= 75: return "A"
    if pct >= 60: return "B"
    if pct >= 45: return "C"
    return "D"


# ── Generate endpoint ─────────────────────────────────────────────────────────

async def _generate_quiz_core(req: QuizGenerateRequest) -> QuizGenerateResponse:
    """Shared implementation used by both route aliases."""
    subject = req.topic or "the uploaded study material"
    n = req.num_questions

    # Build RAG context block
    context_block = ""
    if req.doc_id:
        query = req.topic or "key concepts, definitions, and important facts"
        docs = retrieve_context(query, doc_id=req.doc_id, k=10)
        if docs:
            context_snippets = "\n---\n".join(d.page_content for d in docs)
            context_block = f"\n\nBase your questions on the following study material:\n{context_snippets}"

    diff_instruction = _difficulty_distribution(req.difficulty, n)

    user_prompt = f"""Create exactly {n} multiple-choice questions about: {subject}

{diff_instruction}{context_block}

Rules:
- Each question must have EXACTLY 4 options labelled internally as index 0, 1, 2, 3.
- correct_index is the 0-based index of the ONE correct option.
- explanation: 1-2 sentences explaining WHY the correct answer is right.
- topic_tag: a short 2-5 word label for the sub-topic this question tests (e.g. "Cell Division", "Ohm's Law").
- hint: a one-sentence nudge that helps without giving away the answer (shown to students who time out).
- difficulty: "easy", "medium", or "hard".

Respond ONLY with valid JSON (no markdown fences, no extra keys):
{{
  "topic": "<overall topic label>",
  "questions": [
    {{
      "question": "<full question text, 10-25 words>",
      "options": ["<option 0>", "<option 1>", "<option 2>", "<option 3>"],
      "correct_index": <0|1|2|3>,
      "explanation": "<1-2 sentence rationale>",
      "difficulty": "<easy|medium|hard>",
      "topic_tag": "<sub-topic label>",
      "hint": "<one-sentence nudge>"
    }}
  ]
}}"""

    try:
        raw = await chat(
            system=_SYSTEM,
            user=user_prompt,
            temperature=0.75,
            max_tokens=4096,   # Qwen3 needs room to think + output JSON
        )
        raw = strip_json_fences(raw)
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Quiz generation: LLM returned non-JSON — raw=%r — %s", raw[:300], exc)
        raise HTTPException(
            status_code=500,
            detail="Quiz generation failed: LLM returned malformed JSON. Please retry.",
        ) from exc
    except Exception as exc:
        logger.exception("Quiz generation unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Quiz generation error: {exc}") from exc

    raw_questions = data.get("questions", [])
    if not raw_questions:
        raise HTTPException(status_code=500, detail="LLM returned zero questions.")

    quiz_id = str(uuid.uuid4())
    questions: list[QuizQuestion] = []
    for q in raw_questions:
        opts = q.get("options", [])
        if len(opts) != 4:
            # Pad or truncate to exactly 4
            opts = (opts + ["—", "—", "—", "—"])[:4]
        questions.append(QuizQuestion(
            id=str(uuid.uuid4()),
            question=q.get("question", "").strip(),
            options=opts,
            correct_index=int(q.get("correct_index", 0)) % 4,
            explanation=q.get("explanation", "").strip(),
            difficulty=q.get("difficulty", "medium"),
            topic_tag=q.get("topic_tag", subject),
            hint=q.get("hint", ""),
        ))

    _quiz_store[quiz_id] = questions
    logger.info(
        "Quiz %s created: %d questions, difficulty=%s, topic=%s",
        quiz_id, len(questions), req.difficulty, subject,
    )

    return QuizGenerateResponse(
        quiz_id=quiz_id,
        questions=questions,
        topic=data.get("topic", subject),
        timer_seconds=req.timer_seconds,
        difficulty=req.difficulty,
    )


@router.post(
    "/quiz/generate",
    response_model=QuizGenerateResponse,
    summary="Generate a quiz (legacy path)",
    tags=["Quiz"],
)
async def generate_quiz(req: QuizGenerateRequest) -> QuizGenerateResponse:
    """Generate 3-10 MCQs from a topic or document. Legacy path kept for compatibility."""
    return await _generate_quiz_core(req)


@router.post(
    "/generate-quiz",
    response_model=QuizGenerateResponse,
    summary="Generate a quiz (canonical /api path)",
    description=(
        "Generate 3–10 multiple-choice questions from a **topic** string, an "
        "indexed **document** (via doc_id), or both. "
        "Each question carries a `topic_tag`, `hint`, `difficulty`, and full `explanation`. "
        "Set `timer_seconds` to 15 or 30 — the value is echoed back so the frontend "
        "can configure its countdown timer."
    ),
    tags=["Quiz"],
)
async def generate_quiz_api(req: QuizGenerateRequest) -> QuizGenerateResponse:
    """Canonical endpoint: POST /api/generate-quiz"""
    return await _generate_quiz_core(req)


# ── Submit / score endpoint ───────────────────────────────────────────────────

@router.post(
    "/quiz/submit",
    response_model=QuizSubmitResponse,
    summary="Submit quiz answers and get detailed results",
    tags=["Quiz"],
)
async def submit_quiz(req: QuizSubmitRequest) -> QuizSubmitResponse:
    """
    Score a completed quiz. Returns:
    - per-question breakdown (correct/wrong, topic_tag, explanation)
    - weak and strong topic lists derived from answer pattern
    - letter grade (S/A/B/C/D)
    - LLM-generated personalised recommendations
    """
    questions = _quiz_store.get(req.quiz_id)
    if not questions:
        raise HTTPException(
            status_code=404,
            detail="Quiz session not found. Sessions are in-process only; please generate a new quiz.",
        )

    # ── Score ─────────────────────────────────────────────────────────────────
    details: list[QuizAnswerDetail] = []
    topic_results: dict[str, list[bool]] = defaultdict(list)

    for q in questions:
        user_idx = req.answers.get(q.id, -1)
        is_correct = user_idx == q.correct_index
        topic_results[q.topic_tag].append(is_correct)
        details.append(QuizAnswerDetail(
            question_id=q.id,
            question=q.question,
            user_index=user_idx,
            correct_index=q.correct_index,
            is_correct=is_correct,
            topic_tag=q.topic_tag,
            difficulty=q.difficulty,
            explanation=q.explanation,
        ))

    score   = sum(1 for d in details if d.is_correct)
    total   = len(details)
    pct     = round((score / total) * 100, 1) if total else 0.0
    grade   = _grade(pct)

    # ── Classify topics as weak / strong ──────────────────────────────────────
    weak_topics:   list[str] = []
    strong_topics: list[str] = []
    for tag, results in topic_results.items():
        accuracy = sum(results) / len(results)
        if accuracy < 0.5:
            weak_topics.append(tag)
        else:
            strong_topics.append(tag)

    # ── LLM personalised recommendations ─────────────────────────────────────
    recommendations: list[str] = []
    wrong_qs = [d.question for d in details if not d.is_correct]
    if wrong_qs:
        prompt = (
            "A student just completed a quiz and got these questions wrong:\n"
            + "\n".join(f"- {q}" for q in wrong_qs[:8])
            + f"\n\nWeak topics identified: {', '.join(weak_topics) or 'none'}"
            + f"\nScore: {score}/{total} ({pct}%)"
            "\n\nRespond ONLY with valid JSON (no markdown fences):\n"
            '{"recommendations": ["<specific study tip 1>", "<tip 2>", "<tip 3>", "<tip 4>"]}'
        )
        try:
            raw = await chat(
                system=(
                    "You are a caring, concise study coach. "
                    "Give actionable, specific revision tips (not generic advice). "
                    "Each tip should mention a technique or resource."
                ),
                user=prompt,
                temperature=0.5,
                max_tokens=512,
            )
            raw = strip_json_fences(raw)
            parsed = json.loads(raw)
            recommendations = parsed.get("recommendations", [])
        except Exception as exc:
            logger.warning("Recommendations LLM call failed: %s", exc)

    return QuizSubmitResponse(
        score=score,
        total=total,
        percentage=pct,
        time_taken=req.time_taken,
        details=details,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        recommendations=recommendations,
        grade=grade,
    )
