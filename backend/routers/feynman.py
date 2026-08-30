"""
/api/feynman/evaluate — Feynman Technique evaluator.

The student types an explanation of a concept in their own words.
The LLM grades it, identifies gaps, generates Q&A pairs from the explanation,
and provides a coaching tip.

Endpoint:
  POST /api/feynman/evaluate
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.db_models import FeynmanResult
from models.schemas import FeynmanRequest, FeynmanResponse, QAPair
from services.document_service import retrieve_context
from services.llm_service import chat
from utils.text_utils import strip_json_fences

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
log = logging.getLogger(__name__)

_SYSTEM = """\
You are an expert tutor evaluating a student's understanding using the Feynman Technique.
The student has tried to explain a concept in their own words.
Your job is to:
1. Score their explanation on accuracy, completeness, and clarity (0–100).
2. Identify what they got right (strengths).
3. Identify specific knowledge gaps or misconceptions (gaps).
4. Generate 3–5 question-answer pairs that test the key ideas in their explanation.
5. Give one concise, actionable coaching tip.

Grading scale: S=90–100, A=75–89, B=60–74, C=40–59, D=0–39

Respond ONLY with valid JSON (no markdown fences) matching exactly:
{
  "score": <integer 0-100>,
  "grade": "<S|A|B|C|D>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "qa_pairs": [
    {"question": "<question>", "answer": "<concise answer>"}
  ],
  "coaching_tip": "<one actionable sentence>"
}"""


@router.post("/feynman/evaluate", response_model=FeynmanResponse, tags=["Feynman"])
@limiter.limit("10/minute")
async def evaluate_feynman(
    request: Request,
    req: FeynmanRequest,
    db: AsyncSession = Depends(get_db),
) -> FeynmanResponse:
    """Evaluate a student's Feynman-style explanation and return feedback + Q&A pairs."""
    # Optional: enrich with doc context so grading is grounded in actual material
    context_block = ""
    if req.doc_id:
        docs = retrieve_context(req.concept, doc_id=req.doc_id, k=5)
        if docs:
            context_block = "\n\nReference material from student's notes:\n" + "\n---\n".join(
                d.page_content for d in docs
            )

    user_prompt = (
        f'Concept being explained: "{req.concept}"\n\n'
        f"Student's explanation:\n{req.explanation}"
        f"{context_block}"
    )

    try:
        raw = await chat(
            system=_SYSTEM,
            user=user_prompt,
            temperature=0.4,
            max_tokens=900,
        )
        cleaned = strip_json_fences(raw)
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.error("feynman JSON parse failed: %r", raw[:300] if "raw" in dir() else "no raw")
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    score     = max(0, min(100, int(data.get("score", 0))))
    grade     = data.get("grade", "D")
    strengths = data.get("strengths", [])
    gaps      = data.get("gaps", [])
    qa_raw    = data.get("qa_pairs", [])
    tip       = data.get("coaching_tip", "Keep practising!")

    qa_pairs = [QAPair(question=q["question"], answer=q["answer"]) for q in qa_raw if "question" in q and "answer" in q]

    # Persist for progress tracking
    result = FeynmanResult(
        concept=req.concept[:255],
        explanation_length=len(req.explanation),
        score=score,
        grade=grade,
        gap_count=len(gaps),
        doc_id=req.doc_id,
    )
    db.add(result)
    await db.commit()

    return FeynmanResponse(
        score=score,
        grade=grade,
        strengths=strengths,
        gaps=gaps,
        qa_pairs=qa_pairs,
        coaching_tip=tip,
    )
