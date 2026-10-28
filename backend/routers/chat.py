"""
/api/chats — Persistent chat session management for the Doubt Solver.

Endpoints:
  GET    /api/chats                          — list all sessions (newest first)
  POST   /api/chats                          — create a new session
  DELETE /api/chats/{session_id}             — delete a session + all its messages
  GET    /api/chats/{session_id}/messages    — fetch all messages in a session
  POST   /api/chats/{session_id}/messages    — append a message to a session
  PATCH  /api/chats/{session_id}/title       — rename a session
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies.auth import get_current_user_flex
from models.db_models import ChatSession, ChatMessage, User

router = APIRouter()
log = logging.getLogger(__name__)


# ── Pydantic schemas (router-local, no need to pollute models/schemas.py) ─────

class SessionOut(BaseModel):
    id: str
    title: str
    doc_id: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    title: str = "New Chat"
    doc_id: str | None = None


class MessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources_json: str    # raw JSON string; frontend parses it
    mode: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    role: str                        # "user" | "assistant"
    content: str
    sources_json: str = "[]"
    mode: str = "standard"


class TitleUpdate(BaseModel):
    title: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_out(s: ChatSession, count: int) -> SessionOut:
    return SessionOut(
        id=s.id,
        title=s.title,
        doc_id=s.doc_id,
        created_at=s.created_at,
        updated_at=s.updated_at,
        message_count=count,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/chats", response_model=list[SessionOut], tags=["Chat History"])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Return all chat sessions for the authenticated user, newest first, with message counts."""
    q = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .order_by(ChatSession.updated_at.desc())
    )
    if current_user is not None:
        q = q.where(ChatSession.user_id == current_user.id)
    result = await db.execute(q)
    sessions = result.scalars().all()
    return [_session_out(s, len(s.messages)) for s in sessions]


@router.post("/chats", response_model=SessionOut, status_code=201, tags=["Chat History"])
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Create a new (empty) chat session bound to the authenticated user."""
    session = ChatSession(
        title=body.title,
        doc_id=body.doc_id,
        user_id=current_user.id if current_user else None,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_out(session, 0)


@router.delete("/chats/{session_id}", status_code=204, tags=["Chat History"])
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Delete a chat session and all its messages (CASCADE, owner only)."""
    q = select(ChatSession).where(ChatSession.id == session_id)
    if current_user is not None:
        q = q.where(ChatSession.user_id == current_user.id)
    result = await db.execute(q)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()


@router.get(
    "/chats/{session_id}/messages",
    response_model=list[MessageOut],
    tags=["Chat History"],
)
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Return all messages in a session (owner only), in chronological order."""
    # Verify ownership
    sq = select(ChatSession).where(ChatSession.id == session_id)
    if current_user is not None:
        sq = sq.where(ChatSession.user_id == current_user.id)
    s_res = await db.execute(sq)
    if not s_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Chat session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()


@router.post(
    "/chats/{session_id}/messages",
    response_model=MessageOut,
    status_code=201,
    tags=["Chat History"],
)
async def append_message(
    session_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Append a message to a session and bump session.updated_at (owner only)."""
    # Verify session exists and belongs to caller
    sq = select(ChatSession).where(ChatSession.id == session_id)
    if current_user is not None:
        sq = sq.where(ChatSession.user_id == current_user.id)
    s_res = await db.execute(sq)
    session = s_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    msg = ChatMessage(
        session_id=session_id,
        role=body.role,
        content=body.content,
        sources_json=body.sources_json,
        mode=body.mode,
    )
    db.add(msg)

    # Touch updated_at on the parent session so the sidebar re-sorts
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(updated_at=_now())
    )

    await db.commit()
    await db.refresh(msg)
    return msg


@router.patch(
    "/chats/{session_id}/title",
    response_model=SessionOut,
    tags=["Chat History"],
)
async def rename_session(
    session_id: str,
    body: TitleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_flex),
):
    """Rename a chat session (owner only)."""
    sq = select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.id == session_id)
    if current_user is not None:
        sq = sq.where(ChatSession.user_id == current_user.id)
    result = await db.execute(sq)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session.title = body.title.strip() or "New Chat"
    await db.commit()
    await db.refresh(session)
    return _session_out(session, len(session.messages))
