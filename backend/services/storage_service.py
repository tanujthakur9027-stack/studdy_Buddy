"""
services/storage_service.py — Abstracted file storage.

Backed by local filesystem in development.
Swap save_file / delete_file implementations for S3/GCS in production.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from config import get_settings

settings = get_settings()

# Allowed MIME types per upload category
ALLOWED_ASSIGNMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "application/x-zip-compressed",
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_NOTE_TYPES = ALLOWED_ASSIGNMENT_TYPES

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".zip", ".jpg", ".jpeg", ".png", ".webp",
}


def _get_upload_dir(folder: str) -> Path:
    path = Path(settings.upload_dir) / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_file(
    file: UploadFile,
    folder: str,
    max_mb: Optional[int] = None,
    allowed_types: Optional[set] = None,
) -> str:
    """
    Save an uploaded file to local storage.
    Returns the relative URL path: /uploads/{folder}/{unique_name}.
    Raises ValueError on validation failure.
    """
    if allowed_types and file.content_type not in allowed_types:
        raise ValueError(f"File type '{file.content_type}' is not allowed")

    content = await file.read()

    if max_mb and len(content) > max_mb * 1024 * 1024:
        raise ValueError(f"File size exceeds {max_mb} MB limit")

    ext = Path(file.filename or "file").suffix.lower() or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = _get_upload_dir(folder) / unique_name

    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    return f"/uploads/{folder}/{unique_name}"


def delete_file(url: str) -> None:
    """Delete a file given its relative URL path."""
    if not url:
        return
    # Convert /uploads/folder/file.ext to filesystem path
    relative = url.lstrip("/")
    path = Path(settings.upload_dir).parent / relative
    if path.exists():
        path.unlink(missing_ok=True)
