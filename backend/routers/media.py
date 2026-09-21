"""
/api/media — Owner-only media upload & serve (GIF, PNG, JPG, WEBP).

POST /api/media/upload   — validate, save, return media metadata
GET  /api/media/{id}     — stream media bytes to owner only
"""
from __future__ import annotations

import io
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import aiofiles

from config import get_settings
from database import get_db
from dependencies.auth import get_current_user
from models.db_models import Media, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["Media"])
settings = get_settings()

ALLOWED_MIME = {
    "image/gif", "image/png", "image/jpeg", "image/webp",
    "image/jfif", "image/pjpeg",
}
ALLOWED_EXTS = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".jfif"}

MAX_MEDIA_MB = 5
MAX_FRAME_COUNT = 300
MAX_DIMENSION = 4096   # pixels per side


@router.post("/upload", status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a media file (GIF, PNG, JPG, WEBP).

    Validation:
    - MIME type and extension allow-list
    - Real content verified with Pillow (Image.open + verify magic bytes)
    - Size cap (MAX_MEDIA_MB)
    - GIF frame-count cap (MAX_FRAME_COUNT)
    - Pixel-dimension cap (MAX_DIMENSION)
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported media type: {content_type}")

    original_name = file.filename or "upload"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=415, detail=f"Unsupported extension: {ext}")

    file_bytes = await file.read()

    # Size limit
    max_bytes = MAX_MEDIA_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_MEDIA_MB} MB limit.")
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Empty file.")

    # Real content validation via Pillow
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(file_bytes))
        img.verify()           # raises on corrupt files
        img = PILImage.open(io.BytesIO(file_bytes))  # re-open after verify
        width, height = img.size
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid image: {exc}") from exc

    # Dimension cap
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=422,
            detail=f"Image too large ({width}×{height}). Max is {MAX_DIMENSION}px per side.",
        )

    # GIF-specific: magic bytes + frame count
    frame_count = 1
    if ext == ".gif" or content_type == "image/gif":
        if not (file_bytes[:6] in (b"GIF87a", b"GIF89a")):
            raise HTTPException(status_code=422, detail="File does not appear to be a valid GIF.")
        frame_count = getattr(img, "n_frames", 1)
        if frame_count > MAX_FRAME_COUNT:
            raise HTTPException(
                status_code=422,
                detail=f"GIF has {frame_count} frames; max allowed is {MAX_FRAME_COUNT}.",
            )

    # Save under uuid filename (never user-supplied name)
    media_dir = Path(settings.upload_dir) / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    filename_uuid = f"{uuid.uuid4()}{ext}"
    filepath = media_dir / filename_uuid
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_bytes)

    # Persist metadata
    row = Media(
        user_id=current_user.id,
        filename_uuid=filename_uuid,
        original_name=original_name,
        mime=content_type,
        size=len(file_bytes),
        width=width,
        height=height,
        frame_count=frame_count,
    )
    db.add(row)
    await db.commit()

    return {
        "id": row.id,
        "original_name": original_name,
        "mime": content_type,
        "size": len(file_bytes),
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "url": f"/api/media/{row.id}",
    }


@router.get("/{media_id}")
async def get_media(
    media_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream the media file to the authenticated owner."""
    result = await db.execute(
        select(Media).where(Media.id == media_id, Media.user_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Media not found.")

    filepath = Path(settings.upload_dir) / "media" / row.filename_uuid
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Media file missing from storage.")

    async with aiofiles.open(filepath, "rb") as f:
        content = await f.read()

    return Response(content=content, media_type=row.mime)
