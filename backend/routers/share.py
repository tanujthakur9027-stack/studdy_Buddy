"""
/api/share — Short-link sharing for quizzes and documents.

Endpoints:
  POST /api/share          — create a share link (returns a short id)
  GET  /api/share/{id}     — resolve a share link (public, no auth required)
  DELETE /api/share/{id}   — deactivate a share link
"""
from __future__ import annotations

import json
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.db_models import SharedResource

router = APIRouter()

_CHARS = string.ascii_letters + string.digits


def _short_id(length: int = 10) -> str:
    """Generate a URL-safe random id (e.g. 'aB3xY9kLmN')."""
    return "".join(random.choices(_CHARS, k=length))


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ShareCreate(BaseModel):
    resource_type: str          # "quiz" | "document"
    payload: dict               # the full quiz/document data to embed
    title: str = ""
    expires_days: int = 30      # 0 = never expires


class ShareOut(BaseModel):
    id: str
    resource_type: str
    title: str
    created_at: datetime
    expires_at: datetime | None
    share_url: str              # convenience field built server-side

    model_config = {"from_attributes": True}


class ShareResolved(BaseModel):
    id: str
    resource_type: str
    title: str
    payload: dict
    created_at: datetime
    expires_at: datetime | None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/share", response_model=ShareOut, status_code=201, tags=["Share"])
async def create_share(body: ShareCreate, db: AsyncSession = Depends(get_db)):
    """Create a share link containing the given payload JSON."""
    # Collision-safe short id
    for _ in range(5):
        sid = _short_id()
        existing = await db.get(SharedResource, sid)
        if not existing:
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique share id")

    expires_at = None
    if body.expires_days > 0:
        expires_at = _now() + timedelta(days=body.expires_days)

    resource = SharedResource(
        id=sid,
        resource_type=body.resource_type,
        payload_json=json.dumps(body.payload),
        title=body.title,
        expires_at=expires_at,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return ShareOut(
        id=resource.id,
        resource_type=resource.resource_type,
        title=resource.title,
        created_at=resource.created_at,
        expires_at=resource.expires_at,
        share_url=f"/share/{resource.id}",
    )


@router.get("/share/{share_id}", response_model=ShareResolved, tags=["Share"])
async def resolve_share(share_id: str, db: AsyncSession = Depends(get_db)):
    """Resolve a share link — returns the embedded payload."""
    resource = await db.get(SharedResource, share_id)
    if not resource or not resource.is_active:
        raise HTTPException(status_code=404, detail="Share link not found or has been deactivated")

    if resource.expires_at and resource.expires_at < _now():
        raise HTTPException(status_code=410, detail="Share link has expired")

    return ShareResolved(
        id=resource.id,
        resource_type=resource.resource_type,
        title=resource.title,
        payload=json.loads(resource.payload_json),
        created_at=resource.created_at,
        expires_at=resource.expires_at,
    )


@router.delete("/share/{share_id}", status_code=204, tags=["Share"])
async def deactivate_share(share_id: str, db: AsyncSession = Depends(get_db)):
    """Soft-delete a share link (marks it inactive)."""
    resource = await db.get(SharedResource, share_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Share link not found")
    resource.is_active = False
    await db.commit()
