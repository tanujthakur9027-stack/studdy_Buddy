"""
services/storage_service.py — Abstracted file storage.

Supports:
1. Cloud Object Storage: S3 / Cloudflare R2 / MinIO when configured via environment/secrets.
2. Local Filesystem: Clean fallback with persistent absolute paths.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from config import get_settings

logger = logging.getLogger(__name__)
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

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".zip", ".jpg", ".jpeg", ".png", ".webp", ".gif",
}


def _get_upload_dir(folder: str) -> Path:
    # Always resolve absolute path inside backend/uploads or configured dir
    base = Path(settings.upload_dir)
    if not base.is_absolute():
        base = (Path(__file__).resolve().parent.parent / base).resolve()
    path = base / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_s3_client():
    """Build boto3 S3 client for Cloudflare R2, AWS S3, or MinIO."""
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        logger.warning("boto3 is not installed; S3 storage unavailable")
        return None

    client_kwargs = {
        "service_name": "s3",
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
        "region_name": settings.s3_region_name or "auto",
        "config": Config(s3={"addressing_style": "virtual" if not settings.s3_endpoint_url else "path"}),
    }
    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url

    return boto3.client(**client_kwargs)


def _upload_to_s3_sync(client, content: bytes, key: str, content_type: str) -> str:
    """Synchronous upload task for execution in asyncio.to_thread."""
    extra_args = {"ContentType": content_type}
    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=content,
        **extra_args,
    )
    if settings.s3_public_url:
        base = settings.s3_public_url.rstrip("/")
        return f"{base}/{key}"
    if settings.s3_endpoint_url:
        return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket_name}/{key}"
    return f"https://{settings.s3_bucket_name}.s3.amazonaws.com/{key}"


def _delete_from_s3_sync(client, key: str) -> None:
    try:
        client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
    except Exception as exc:
        logger.warning("S3 delete failed for key %s: %s", key, exc)


async def save_file(
    file: UploadFile,
    folder: str,
    max_mb: Optional[int] = None,
    allowed_types: Optional[set] = None,
) -> str:
    """
    Save an uploaded file.
    If S3/R2 is configured, uploads directly to Cloud Object Storage.
    Otherwise, saves to persistent local storage and returns relative URL /uploads/{folder}/{unique_name}.
    Raises ValueError on validation failure.
    """
    if allowed_types and file.content_type not in allowed_types:
        raise ValueError(f"File type '{file.content_type}' is not allowed")

    content = await file.read()

    if max_mb and len(content) > max_mb * 1024 * 1024:
        raise ValueError(f"File size exceeds {max_mb} MB limit")

    ext = Path(file.filename or "file").suffix.lower() or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"

    # 1. Attempt Cloud Object Storage (S3 / R2)
    if settings.is_s3_configured:
        s3 = _get_s3_client()
        if s3:
            key = f"{folder}/{unique_name}"
            content_type = file.content_type or "application/octet-stream"
            try:
                url = await asyncio.to_thread(_upload_to_s3_sync, s3, content, key, content_type)
                logger.info("Uploaded file to S3: %s", url)
                return url
            except Exception as exc:
                logger.error("S3 upload failed, falling back to local: %s", exc)

    # 2. Local filesystem storage
    dest = _get_upload_dir(folder) / unique_name
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    return f"/uploads/{folder}/{unique_name}"


def delete_file(url: str) -> bool:
    """Delete a file given its URL path (cloud or local). Returns True if deleted/handled, False otherwise."""
    if not url:
        return False

    # S3 deletion
    if url.startswith("http://") or url.startswith("https://"):
        if settings.is_s3_configured:
            s3 = _get_s3_client()
            if s3:
                # Extract key from url
                parts = url.split(f"{settings.s3_bucket_name}/")
                key = parts[-1] if len(parts) > 1 else url.split("/")[-2] + "/" + url.split("/")[-1]
                _delete_from_s3_sync(s3, key)
                return True
        return False

    # Local filesystem deletion
    base = Path(settings.upload_dir).resolve()

    # Properly strip leading / or uploads/ prefix if present
    cleaned = url.strip().replace("\\", "/").lstrip("/")
    if cleaned.startswith("uploads/"):
        cleaned = cleaned[len("uploads/"):]

    target_path = (base / cleaned).resolve()

    # Path traversal guard: must be strictly within upload directory
    try:
        is_safe = target_path.is_relative_to(base)
    except AttributeError:
        try:
            target_path.relative_to(base)
            is_safe = True
        except ValueError:
            is_safe = False

    if not is_safe:
        logger.warning(
            "path_traversal_attempt_blocked",
            extra={"attempted_path": url, "resolved": str(target_path)},
        )
        return False

    if target_path.is_file():
        target_path.unlink(missing_ok=True)
        return True

    return False
