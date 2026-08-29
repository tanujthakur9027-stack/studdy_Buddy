"""
/api/ask — RAG-powered question answering with a Standard vs ELI5 mode toggle.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import AskRequest, AskResponse, SourceChunk
from services.document_service import retrieve_context
from services.llm_service import chat_with_history
from utils.text_utils import truncate_to_tokens, strip_json_fences

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM_STANDARD = """\
You are StudyBuddy, a knowledgeable and patient AI tutor.
Answer the student's question using ONLY the provided context from their notes where possible.
If the context is insufficient, use your general knowledge but explicitly say so.

Formatting rules:
- Use Markdown: **bold** key terms, bullet lists, numbered steps where appropriate.
- Code snippets go in fenced code blocks.
- Target length: 200–400 words (longer only if the question genuinely requires it).
- End with a brief encouragement line."""

_SYSTEM_ELI5 = """\
You are StudyBuddy, a brilliantly clear teacher who explains things to a 10-year-old child.
Use the provided context from the student's notes as your source material.
If the context doesn't cover the question, use your general knowledge but say so simply.

Strict rules:
- Use the SIMPLEST words possible — if a 10-year-old wouldn't know a word, replace it.
- Short sentences (max 20 words each).
- Explain every technical term with an everyday analogy (e.g. "like a library for information").
- Use at most 1–2 short bullet lists if helpful.
- NO jargon, NO complex formulas — describe maths conceptually.
- Target length: 150–250 words.
- End with one fun fact or encouragement."""

_RESPONSE_SCHEMA = """\

Respond ONLY with valid JSON (no markdown fences) matching exactly:
{
  "answer": "<your markdown answer here>",
  "follow_up_questions": ["<question 1>", "<question 2>", "<question 3>"]
}"""


def _build_context_block(context_text: str) -> str:
    if not context_text.strip():
        return ""
    return (
        "\n\n=== CONTEXT FROM STUDENT'S NOTES ===\n"
        + context_text
        + "\n=== END CONTEXT ===\n"
    )


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about uploaded notes",
    description=(
        "Retrieves relevant context from indexed documents via FAISS + ChromaDB and "
        "answers the question using an LLM. "
        "Set `mode='eli5'` for a simplified, child-friendly explanation; "
        "`mode='standard'` (default) for a thorough academic answer."
    ),
    tags=["Ask"],
)
@limiter.limit("20/minute")
async def ask_question(request: Request, req: AskRequest) -> AskResponse:
    # ── 1. Retrieve context chunks ────────────────────────────────────────────
    context_docs = retrieve_context(
        query=req.question,
        doc_id=req.doc_id,
        k=req.k,
    )

    # Build context string, capped at ~3 000 tokens to stay well within limits
    raw_context = "\n\n---\n\n".join(doc.page_content for doc in context_docs)
    context_text = truncate_to_tokens(raw_context, max_tokens=3000)

    # Build rich source attribution
    sources: list[SourceChunk] = []
    for doc in context_docs:
        m = doc.metadata
        sources.append(SourceChunk(
            filename=m.get("filename", "unknown"),
            page=int(m.get("page", 0)),
            chunk_index=int(m.get("chunk_index", 0)),
            snippet=doc.page_content[:200].replace("\n", " "),
        ))

    # ── 2. Choose system prompt ───────────────────────────────────────────────
    system = _SYSTEM_ELI5 if req.mode == "eli5" else _SYSTEM_STANDARD

    # ── 3. Build message history ──────────────────────────────────────────────
    history: list[dict] = []
    if req.conversation_history:
        for turn in req.conversation_history[-6:]:
            history.append({"role": turn.role, "content": turn.content})

    # Inject context + question as the latest user message
    context_block = _build_context_block(context_text)
    user_message = (
        f"{context_block}"
        f"Student's question: {req.question}"
        f"{_RESPONSE_SCHEMA}"
    )
    history.append({"role": "user", "content": user_message})

    # ── 4. LLM call ───────────────────────────────────────────────────────────
    try:
        raw = await chat_with_history(
            system=system,
            history=history,
            temperature=0.55 if req.mode == "standard" else 0.70,
            max_tokens=1200,
        )
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    # ── 5. Parse response ─────────────────────────────────────────────────────
    cleaned = strip_json_fences(raw)
    try:
        data = json.loads(cleaned)
        answer = data.get("answer") or cleaned
        follow_ups = data.get("follow_up_questions") or []
    except json.JSONDecodeError:
        # Model ignored the JSON instruction — return raw text gracefully
        logger.warning("/api/ask: LLM returned non-JSON, using raw text as answer")
        answer = cleaned
        follow_ups = []

    if not answer:
        raise HTTPException(status_code=500, detail="LLM returned an empty answer.")

    return AskResponse(
        answer=answer,
        mode_used=req.mode,
        sources=sources,
        follow_up_questions=follow_ups[:3],
        context_chunks_used=len(context_docs),
    )
