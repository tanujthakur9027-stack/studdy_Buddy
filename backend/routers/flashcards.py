"""
/api/flashcards — Generate and persist flashcard decks from indexed documents.

Endpoints:
  POST /api/flashcards/generate            — generate + persist a new deck
  GET  /api/flashcards?doc_id={id}         — list sessions for a document
  GET  /api/flashcards/{session_id}        — fetch an existing deck
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.db_models import FlashcardSession, Flashcard
from services.document_service import retrieve_context
from services.llm_service import chat
from utils.text_utils import truncate_to_tokens, strip_json_fences

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
log = logging.getLogger(__name__)

_SYSTEM = """\
You are a flashcard generator. Create a set of study flashcards from the provided material.

Return ONLY valid JSON (no markdown fences) — a list of objects:
[
  {
    "front": "<question or term — short, under 20 words>",
    "back": "<answer or definition — 1–3 sentences>",
    "topic_tag": "<sub-topic label>"
  }
]

Rules:
- Generate 12–20 cards covering the most important concepts.
- Vary the card types: definitions, "what is", "how does", "why does", cause-and-effect.
- Keep each front concise enough to read at a glance.
- Each back should fully answer the front in plain language."""


class FlashcardGenerateRequest(BaseModel):
    doc_id: str
    topic: str = ""
    num_cards: int = 15


class FlashcardOut(BaseModel):
    id: str
    front: str
    back: str
    topic_tag: str

    model_config = {"from_attributes": True}


class FlashcardSessionOut(BaseModel):
    id: str
    doc_id: str
    topic: str
    card_count: int
    created_at: str

    model_config = {"from_attributes": True}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/flashcards/generate", tags=["Flashcards"])
@limiter.limit("10/minute")
async def generate_flashcards(
    request: Request,
    req: FlashcardGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a flashcard deck from the document and persist it."""
    query = req.topic.strip() if req.topic.strip() else "key concepts definitions terms"
    docs = retrieve_context(query, doc_id=req.doc_id, k=12)

    if not docs:
        raise HTTPException(status_code=404, detail="No content found for this document.")

    raw_context = "\n\n---\n\n".join(d.page_content for d in docs)
    context = truncate_to_tokens(raw_context, max_tokens=4000)

    focus = f' Focus on: "{req.topic}".' if req.topic.strip() else ""
    user_prompt = (
        f"Generate {req.num_cards} flashcards from the following material.{focus}\n\n"
        f"=== MATERIAL ===\n{context}\n=== END ==="
    )

    try:
        raw = await chat(system=_SYSTEM, user=user_prompt, temperature=0.4, max_tokens=2000)
        cleaned = strip_json_fences(raw)
        cards_data = json.loads(cleaned)
        if not isinstance(cards_data, list):
            raise ValueError("Expected a JSON list")
    except (json.JSONDecodeError, ValueError) as e:
        log.error("flashcards JSON parse failed: %r", raw[:300] if "raw" in dir() else "")
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    # Persist session + cards
    session = FlashcardSession(
        id=str(uuid.uuid4()),
        doc_id=req.doc_id,
        topic=req.topic.strip() or "General",
    )
    db.add(session)

    cards = []
    for c in cards_data:
        card = Flashcard(
            id=str(uuid.uuid4()),
            session_id=session.id,
            front=c.get("front", ""),
            back=c.get("back", ""),
            topic_tag=c.get("topic_tag", ""),
        )
        db.add(card)
        cards.append(card)

    await db.commit()
    await db.refresh(session)

    return {
        "session_id": session.id,
        "doc_id": session.doc_id,
        "topic": session.topic,
        "cards": [
            {"id": card.id, "front": card.front, "back": card.back, "topic_tag": card.topic_tag}
            for card in cards
        ],
    }


@router.get("/flashcards", tags=["Flashcards"])
async def list_flashcard_sessions(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all flashcard sessions for a document."""
    result = await db.execute(
        select(FlashcardSession)
        .where(FlashcardSession.doc_id == doc_id)
        .order_by(FlashcardSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "doc_id": s.doc_id,
            "topic": s.topic,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/flashcards/{session_id}", tags=["Flashcards"])
async def get_flashcard_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch a flashcard deck by session id."""
    result = await db.execute(
        select(FlashcardSession)
        .options(selectinload(FlashcardSession.cards))
        .where(FlashcardSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Flashcard session not found")

    return {
        "session_id": session.id,
        "doc_id": session.doc_id,
        "topic": session.topic,
        "created_at": session.created_at.isoformat(),
        "cards": [
            {"id": c.id, "front": c.front, "back": c.back, "topic_tag": c.topic_tag}
            for c in session.cards
        ],
    }
