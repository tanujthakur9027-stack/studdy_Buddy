"""
/api/upload — ingest a document into the vector stores.

Supported formats: PDF, TXT, MD, DOC, DOCX, PPT, PPTX, XLSX, PNG, JPG, JPEG, WEBP, BIN.
- Validates content-type AND file extension for defence-in-depth.
- Returns extended IngestionStats including an auto-generated description.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models.db_models import Document
from models.schemas import UploadResponse
from services.document_service import process_and_index, save_upload

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Accept all MIME types the browser may send for supported formats
ALLOWED_MIME: set[str] = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # PowerPoint
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Excel
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Images
    "image/png",
    "image/jpeg",
    "image/webp",
    # Generic binary (some browsers send this for any file)
    "application/octet-stream",
}

ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".txt", ".md", ".doc", ".docx", ".bin",
    ".ppt", ".pptx",
    ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".webp",
}


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a document for ingestion",
    description=(
        "Upload a **PDF** or **TXT** file (DOCX also accepted). "
        "The file is parsed, chunked, and indexed into both a persistent ChromaDB store "
        "and an in-process FAISS index. "
        "Returns a `doc_id` you can pass to `/api/ask` to restrict answers to this document."
    ),
    tags=["Documents"],
)
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):  # noqa: B008
    # ── Validate MIME type ────────────────────────────────────────────────────
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported MIME type '{content_type}'. "
                f"Accepted: {', '.join(sorted(ALLOWED_MIME))}."
            ),
        )

    # ── Validate extension ────────────────────────────────────────────────────
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file extension '{ext}'. "
                f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
        )

    # ── Read & size-check ─────────────────────────────────────────────────────
    file_bytes = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_file_size_mb} MB size limit.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    # ── Save to disk ──────────────────────────────────────────────────────────
    try:
        filepath, doc_id = await save_upload(file_bytes, filename)
    except Exception as exc:
        logger.exception("Failed to save upload")
        raise HTTPException(status_code=500, detail=f"Could not save file: {exc}") from exc

    # ── Parse + Index ─────────────────────────────────────────────────────────
    try:
        stats = await process_and_index(file_bytes, filepath, doc_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Ingestion pipeline failed for %s", filename)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    # ── Persist metadata to DB ────────────────────────────────────────────────
    doc_row = Document(
        doc_id=stats.doc_id,
        filename=stats.filename,
        description=stats.description,
        pages=stats.pages,
        chunks=stats.chunks,
        total_chars=stats.total_chars,
        total_tokens=stats.total_tokens,
        parser_used=stats.parser_used,
    )
    db.add(doc_row)
    await db.commit()

    logger.info(
        "Ingested '%s' → doc_id=%s  pages=%d  chunks=%d  tokens=%d  parser=%s",
        filename, doc_id, stats.pages, stats.chunks, stats.total_tokens, stats.parser_used,
    )

    return UploadResponse(
        doc_id=stats.doc_id,
        filename=stats.filename,
        chunks=stats.chunks,
        pages=stats.pages,
        total_chars=stats.total_chars,
        total_tokens=stats.total_tokens,
        parser_used=stats.parser_used,
        description=stats.description,
    )
