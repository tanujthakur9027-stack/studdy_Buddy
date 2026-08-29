"""
/api/cheatsheet — AI-generated one-page cheat sheet from an indexed document.

Streams a structured Markdown cheat sheet token-by-token via SSE, then sends
a final [DONE] event. The frontend renders it as a printable card.

Endpoint:
  POST /api/cheatsheet  (streams SSE)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.document_service import retrieve_context
from services.llm_service import stream_chat
from utils.text_utils import truncate_to_tokens

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
log = logging.getLogger(__name__)

_CHEATSHEET_SYSTEM = """\
You are an expert study assistant creating a concise, well-structured cheat sheet.
Your output must be in Markdown and follow this exact structure (use these exact headings):

## 📌 Key Definitions
(Bullet list of 5-8 key terms with 1-sentence definitions)

## 🔢 Formulas & Rules
(Bullet list of important formulas, equations, or rules — use inline code for formulas)

## 💡 Core Concepts
(Numbered list of 4-6 core ideas, each 1-2 sentences)

## ⚡ Quick Facts
(Bullet list of 5-8 memorable facts or mnemonics)

## 📝 Exam Tips
(3-5 actionable tips for exams based on this content)

Keep each item short — this is a reference card, not an essay. Use bold for emphasis."""


class CheatsheetRequest(BaseModel):
    doc_id: str
    topic: str = ""       # optional focus topic; if empty uses full document


@router.post("/cheatsheet", tags=["Learning"])
@limiter.limit("10/minute")
async def generate_cheatsheet(request: Request, req: CheatsheetRequest) -> StreamingResponse:
    """Stream an AI cheat sheet for the given document as SSE tokens."""
    # Retrieve the most relevant context chunks
    query = req.topic if req.topic.strip() else "key concepts definitions formulas summary"
    docs = retrieve_context(query, doc_id=req.doc_id, k=12)

    if not docs:
        async def _empty():
            yield "data: [ERROR] No content found for this document. Please re-upload it.\n\n"
        return StreamingResponse(_empty(), media_type="text/event-stream")

    raw_context = "\n\n---\n\n".join(d.page_content for d in docs)
    context = truncate_to_tokens(raw_context, max_tokens=4000)

    focus = f' Focus specifically on: "{req.topic}".' if req.topic.strip() else ""
    user_prompt = (
        f"Create a one-page cheat sheet from the following study material.{focus}\n\n"
        f"=== STUDY MATERIAL ===\n{context}\n=== END ==="
    )

    async def event_stream():
        try:
            async for token in stream_chat(
                system=_CHEATSHEET_SYSTEM,
                user=user_prompt,
                temperature=0.45,
                max_tokens=1400,
            ):
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except Exception as exc:
            log.exception("Cheatsheet stream error")
            yield f"data: [ERROR] {exc}\n\n"
            return
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
