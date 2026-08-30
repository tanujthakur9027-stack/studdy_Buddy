"""
Explain router — ELI5 / simplified explanation endpoint.
"""
from __future__ import annotations

import json
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from models.schemas import ExplainRequest, ExplainResponse
from services.llm_service import chat, stream_chat
from services.document_service import retrieve_context
from utils.text_utils import strip_json_fences

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
log = logging.getLogger(__name__)

LEVEL_PROMPTS = {
    "eli5": (
        "You are a brilliant teacher explaining to a curious 6-year-old child. "
        "Use very simple words, short sentences, and vivid everyday analogies. "
        "Avoid jargon entirely."
    ),
    "beginner": (
        "You are a patient tutor explaining to a high-school student with no prior knowledge. "
        "Use clear language, relatable examples, and avoid heavy technical terms."
    ),
    "intermediate": (
        "You are a university professor explaining to an undergraduate student. "
        "Use precise terminology, but still provide clear examples and comparisons."
    ),
}


@router.post("/explain", response_model=ExplainResponse, tags=["Learning"])
@limiter.limit("20/minute")
async def explain_topic(request: Request, req: ExplainRequest):
    """Return a simplified explanation, analogy, and key points for a topic."""
    system = LEVEL_PROMPTS[req.level]

    # Optionally augment with RAG context
    context_block = ""
    if req.doc_id:
        docs = retrieve_context(req.topic, doc_id=req.doc_id, k=4)
        if docs:
            context_block = "\n\nRelevant context from the student's notes:\n" + "\n---\n".join(
                d.page_content for d in docs
            )

    user_prompt = f"""Explain the following topic: "{req.topic}"{context_block}

Respond ONLY with valid JSON matching this schema (no markdown fences):
{{
  "explanation": "<clear explanation in 150-250 words>",
  "analogy": "<one vivid everyday analogy>",
  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]
}}"""

    try:
        raw = await chat(system=system, user=user_prompt, temperature=0.65, max_tokens=4096)
        cleaned = strip_json_fences(raw)
        log.info("explain raw len=%d cleaned len=%d preview=%r", len(raw), len(cleaned), cleaned[:120])
        data = json.loads(cleaned)
        return ExplainResponse(
            explanation=data.get("explanation", ""),
            analogy=data.get("analogy", ""),
            key_points=data.get("key_points", []),
        )
    except json.JSONDecodeError as e:
        log.error("explain JSON fail: %r", raw[:300])
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Streaming endpoint ─────────────────────────────────────────────────────────

@router.post("/explain/stream", tags=["Learning"])
@limiter.limit("20/minute")
async def explain_topic_stream(request: Request, req: ExplainRequest) -> StreamingResponse:
    """Stream the explanation token-by-token via SSE."""
    system = LEVEL_PROMPTS[req.level]

    context_block = ""
    if req.doc_id:
        docs = retrieve_context(req.topic, doc_id=req.doc_id, k=4)
        if docs:
            context_block = "\n\nRelevant context from the student's notes:\n" + "\n---\n".join(
                d.page_content for d in docs
            )

    user_prompt = (
        f'Explain the following topic clearly: "{req.topic}"{context_block}\n\n'
        "Use Markdown. Include:\n"
        "1. A clear explanation (150-250 words)\n"
        "2. A vivid everyday analogy starting with 'Think of it like:'\n"
        "3. Key points as a bullet list starting with '**Key Points:**'"
    )

    async def event_stream():
        try:
            async for token in stream_chat(
                system=system,
                user=user_prompt,
                temperature=0.65,
                max_tokens=1000,
            ):
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"
            return
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
