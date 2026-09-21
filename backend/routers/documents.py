"""
documents.py — Manage a user's uploaded document metadata.

All endpoints filter by the authenticated user's ID so that:
- Users only see their own documents.
- AUTH_REQUIRED=false → anonymous mode, no user filter (legacy behaviour).

GET  /api/documents            — list caller's indexed documents
DELETE /api/documents/{doc_id} — remove a document (owner only)
GET  /api/saved-answers        — list caller's bookmarked Q&A pairs
POST /api/saved-answers        — save a new bookmark
DELETE /api/saved-answers/{id} — remove a bookmark
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import get_current_user_flex
from models.db_models import Document, SavedAnswer, User

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents", tags=["Documents"])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Return the caller's indexed documents ordered by upload time (newest first)."""
    q = select(Document).order_by(Document.uploaded_at.desc())
    if current_user is not None:
        q = q.where(Document.user_id == current_user.id)
    result = await db.execute(q)
    docs = result.scalars().all()
    return [
        {
            "doc_id": d.doc_id,
            "filename": d.filename,
            "description": d.description,
            "pages": d.pages,
            "chunks": d.chunks,
            "total_chars": d.total_chars,
            "total_tokens": d.total_tokens,
            "parser_used": d.parser_used,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Remove document metadata from the DB (owner only)."""
    q = select(Document).where(Document.doc_id == doc_id)
    if current_user is not None:
        q = q.where(Document.user_id == current_user.id)
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    await db.delete(doc)
    await db.commit()
    return {"deleted": doc_id}


# ── Saved Answers ─────────────────────────────────────────────────────────────

class SaveAnswerRequest(BaseModel):
    question: str
    answer: str


@router.get("/saved-answers", tags=["Saved Answers"])
async def list_saved_answers(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Return the caller's bookmarked Q&A pairs ordered by save time (newest first)."""
    q = select(SavedAnswer).order_by(SavedAnswer.saved_at.desc())
    if current_user is not None:
        q = q.where(SavedAnswer.user_id == current_user.id)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "saved_at": r.saved_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/saved-answers", status_code=201, tags=["Saved Answers"])
async def save_answer(
    req: SaveAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Bookmark a question + answer pair."""
    uid = current_user.id if current_user else None
    q = select(SavedAnswer).where(SavedAnswer.question == req.question)
    if uid:
        q = q.where(SavedAnswer.user_id == uid)
    existing = await db.execute(q)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This answer is already bookmarked.")

    row = SavedAnswer(question=req.question, answer=req.answer, user_id=uid)
    db.add(row)
    await db.commit()
    return {"id": row.id, "saved_at": row.saved_at.isoformat()}


@router.delete("/saved-answers/{answer_id}", tags=["Saved Answers"])
async def delete_saved_answer(
    answer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Remove a bookmarked answer (owner only)."""
    q = select(SavedAnswer).where(SavedAnswer.id == answer_id)
    if current_user is not None:
        q = q.where(SavedAnswer.user_id == current_user.id)
    result = await db.execute(q)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Saved answer not found.")
    await db.delete(row)
    await db.commit()
    return {"deleted": answer_id}
