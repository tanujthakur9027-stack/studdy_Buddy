"""
/api/upload — ingest a PDF or TXT file into the vector stores.

Changes vs the original /upload route:
- Mounted at /api/upload (prefix added in main.py).
- Passes raw file_bytes directly to process_and_index (no disk read needed for parsing).
- Returns extended IngestionStats: pages, chars, tokens, parser_used.
- Validates content-type AND file extension for defence-in-depth.
- Rejects encrypted / zero-text PDFs with a clear 422 error.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import get_settings
from models.schemas import UploadResponse
from services.document_service import process_and_index, save_upload

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Accept both the MIME type the browser sends and common mis-labelled types
ALLOWED_MIME: set[str] = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Some browsers / OS upload PDFs as octet-stream
    "application/octet-stream",
}

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt", ".md", ".doc", ".docx"}


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
async def upload_document(file: UploadFile = File(...)):  # noqa: B008
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
        # Known user-facing errors (encrypted PDF, no text, bad extension)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Ingestion pipeline failed for %s", filename)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {exc}",
        ) from exc

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
    )
