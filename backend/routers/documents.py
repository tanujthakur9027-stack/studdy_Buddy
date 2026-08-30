"""
documents.py — Manage user's uploaded document metadata.

GET  /api/documents          — list all indexed documents (metadata from DB)
DELETE /api/documents/{doc_id} — remove a document's metadata from DB
GET  /api/saved-answers      — list bookmarked Q&A pairs
POST /api/saved-answers      — save a new bookmark
DELETE /api/saved-answers/{id} — remove a bookmark
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.db_models import Document, SavedAnswer

logger = logging.getLogger(__name__)
router = APIRouter()

_CACHE_10S  = {"Cache-Control": "public, max-age=10, stale-while-revalidate=30"}
_CACHE_30S  = {"Cache-Control": "public, max-age=30, stale-while-revalidate=60"}


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents", tags=["Documents"])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Return all indexed documents ordered by upload time (newest first)."""
    result = await db.execute(
        select(Document).order_by(Document.uploaded_at.desc())
    )
    docs = result.scalars().all()
    data = [
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
    return JSONResponse(content=data, headers=_CACHE_10S)


@router.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Remove document metadata from the DB (does NOT remove vectors from ChromaDB/FAISS)."""
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
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
async def list_saved_answers(db: AsyncSession = Depends(get_db)):
    """Return all bookmarked Q&A pairs ordered by save time (newest first)."""
    result = await db.execute(
        select(SavedAnswer).order_by(SavedAnswer.saved_at.desc())
    )
    rows = result.scalars().all()
    data = [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "saved_at": r.saved_at.isoformat(),
        }
        for r in rows
    ]
    return JSONResponse(content=data, headers=_CACHE_30S)


@router.post("/saved-answers", status_code=201, tags=["Saved Answers"])
async def save_answer(req: SaveAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Bookmark a question + answer pair."""
    # Avoid exact duplicates on the same question
    existing = await db.execute(
        select(SavedAnswer).where(SavedAnswer.question == req.question)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This answer is already bookmarked.")

    row = SavedAnswer(question=req.question, answer=req.answer)
    db.add(row)
    await db.commit()
    return {"id": row.id, "saved_at": row.saved_at.isoformat()}


@router.delete("/saved-answers/{answer_id}", tags=["Saved Answers"])
async def delete_saved_answer(answer_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a bookmarked answer."""
    result = await db.execute(select(SavedAnswer).where(SavedAnswer.id == answer_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Saved answer not found.")
    await db.delete(row)
    await db.commit()
    return {"deleted": answer_id}
