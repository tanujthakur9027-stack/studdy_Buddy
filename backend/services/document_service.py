"""
Document ingestion service
==========================
Responsibilities
- Parse PDF files with pdfplumber (primary) and PyPDF2 (fallback).
- Parse plain-text files directly.
- Chunk text with LangChain's RecursiveCharacterTextSplitter.
- Maintain TWO vector stores per document:
    1. ChromaDB  – persisted to disk, survives restarts, used for cross-session search.
    2. FAISS     – in-process memory, zero-latency for the current session, per-doc index.
- Expose a unified `retrieve_context()` that merges and deduplicates results from both.
"""
from __future__ import annotations

import io
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
import pdfplumber
import PyPDF2
from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.vectorstores import FAISS
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings
from utils.text_utils import clean_text, count_tokens

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Singleton embeddings (HuggingFace local — no API key required) ────────────
_embeddings: Optional[HuggingFaceEmbeddings] = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        # Model is pre-downloaded at Docker build time (see Dockerfile).
        # On first local run it downloads ~22 MB and caches in ~/.cache/huggingface
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings


# ── In-process FAISS registry  ────────────────────────────────────────────────
# Maps doc_id → FAISS index for that document (in-memory, per process).
# ⚠️  IN-MEMORY ONLY — requires --workers 1 (see render.yaml / Dockerfile CMD)
_faiss_registry: dict[str, FAISS] = {}
# Global FAISS index that merges ALL documents for cross-doc queries.
_faiss_global: Optional[FAISS] = None


def _get_faiss_for_doc(doc_id: str) -> Optional[FAISS]:
    return _faiss_registry.get(doc_id)


def _get_faiss_global() -> Optional[FAISS]:
    return _faiss_global


# ── ChromaDB (persisted) ─────────────────────────────────────────────────────
def get_chroma(collection: str = "studybuddy") -> Chroma:
    return Chroma(
        collection_name=collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


# ── PDF parsing ───────────────────────────────────────────────────────────────

def _extract_pdf_pdfplumber(file_bytes: bytes) -> list[tuple[int, str]]:
    """
    Primary PDF extractor using pdfplumber.
    Returns list of (page_number, text) tuples (1-indexed).
    Raises on complete failure.
    """
    pages: list[tuple[int, str]] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            # Also pull text from any tables on the page
            tables = page.extract_tables() or []
            table_text = ""
            for table in tables:
                for row in table:
                    row_cells = [str(c or "").strip() for c in row]
                    table_text += "  |  ".join(row_cells) + "\n"
            combined = raw + ("\n" + table_text if table_text.strip() else "")
            pages.append((i, clean_text(combined)))
    return pages


def _extract_pdf_pypdf2(file_bytes: bytes) -> list[tuple[int, str]]:
    """
    Fallback PDF extractor using PyPDF2.
    Returns list of (page_number, text) tuples (1-indexed).
    """
    pages: list[tuple[int, str]] = []
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    for i, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        pages.append((i, clean_text(raw)))
    return pages


def extract_pdf_pages(file_bytes: bytes, filename: str) -> tuple[list[tuple[int, str]], str]:
    """
    Try pdfplumber first; fall back to PyPDF2 if pdfplumber produces empty output
    or raises. Returns (pages, parser_name) so the caller gets both in one pass.
    """
    try:
        pages = _extract_pdf_pdfplumber(file_bytes)
        total_chars = sum(len(t) for _, t in pages)
        if total_chars > 50:
            logger.info("[%s] pdfplumber extracted %d pages, %d chars", filename, len(pages), total_chars)
            return pages, "pdfplumber"
        logger.warning("[%s] pdfplumber gave sparse output (%d chars) — trying PyPDF2", filename, total_chars)
    except Exception as exc:
        logger.warning("[%s] pdfplumber failed (%s) — falling back to PyPDF2", filename, exc)

    pages = _extract_pdf_pypdf2(file_bytes)
    total_chars = sum(len(t) for _, t in pages)
    logger.info("[%s] PyPDF2 extracted %d pages, %d chars", filename, len(pages), total_chars)
    return pages, "PyPDF2"


def _strip_md_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from markdown content."""
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)


def extract_txt(file_bytes: bytes, is_markdown: bool = False) -> list[tuple[int, str]]:
    """Parse plain-text or markdown. Splits on double-newlines to form logical 'pages'."""
    raw = file_bytes.decode("utf-8", errors="replace")
    if is_markdown:
        raw = _strip_md_frontmatter(raw)
    segments = [s.strip() for s in re.split(r"\n{2,}", raw) if s.strip()]
    # Group segments into pseudo-pages of ~1 500 chars each
    pages: list[tuple[int, str]] = []
    page_num = 1
    current: list[str] = []
    current_len = 0
    for seg in segments:
        current.append(seg)
        current_len += len(seg)
        if current_len >= 1500:
            pages.append((page_num, clean_text("\n\n".join(current))))
            page_num += 1
            current, current_len = [], 0
    if current:
        pages.append((page_num, clean_text("\n\n".join(current))))
    return pages


# ── Chunking ──────────────────────────────────────────────────────────────────

def make_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    )


def pages_to_documents(
    pages: list[tuple[int, str]],
    doc_id: str,
    filename: str,
) -> list[Document]:
    """Convert (page_num, text) pairs to LangChain Documents."""
    docs: list[Document] = []
    for page_num, text in pages:
        if not text.strip():
            continue
        docs.append(Document(
            page_content=text,
            metadata={
                "doc_id": doc_id,
                "filename": filename,
                "page": page_num,
                "source": f"{filename}#page{page_num}",
            },
        ))
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = make_splitter()
    chunks = splitter.split_documents(docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["token_count"] = count_tokens(chunk.page_content)
    return chunks


# ── Ingestion pipeline ────────────────────────────────────────────────────────

async def save_upload(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """Persist raw file to disk. Returns (filepath, doc_id)."""
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    ext = Path(filename).suffix
    filepath = upload_path / f"{doc_id}{ext}"
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_bytes)
    return str(filepath), doc_id


class IngestionStats:
    """Carries per-document ingestion metrics back to the caller."""
    def __init__(
        self,
        doc_id: str,
        filename: str,
        pages: int,
        chunks: int,
        total_chars: int,
        total_tokens: int,
        parser_used: str,
    ):
        self.doc_id = doc_id
        self.filename = filename
        self.pages = pages
        self.chunks = chunks
        self.total_chars = total_chars
        self.total_tokens = total_tokens
        self.parser_used = parser_used


async def process_and_index(
    file_bytes: bytes,
    filepath: str,
    doc_id: str,
    filename: str,
) -> IngestionStats:
    """
    Full ingestion pipeline:
    1. Extract text (PDF: pdfplumber → PyPDF2 fallback; TXT: direct; DOCX: Docx2txtLoader).
    2. Convert to LangChain Documents, chunk, tag metadata.
    3. Index into ChromaDB (persistent) AND FAISS (in-memory, per-doc + global).
    Returns IngestionStats for the response body.
    """
    global _faiss_global

    ext = Path(filename).suffix.lower()
    parser_used = "direct"

    # ── 1. Extract ────────────────────────────────────────────────────────────
    if ext == ".pdf":
        # extract_pdf_pages returns (pages, parser_name) in one pass — no double extraction
        pages, parser_used = extract_pdf_pages(file_bytes, filename)
    elif ext in (".txt", ".md"):
        pages = extract_txt(file_bytes, is_markdown=(ext == ".md"))
        parser_used = "plaintext" if ext == ".txt" else "markdown"
    elif ext in (".docx", ".doc"):
        # Docx2txtLoader needs a path on disk — file already saved
        loader = Docx2txtLoader(filepath)
        loaded = loader.load()
        pages = [(i + 1, clean_text(doc.page_content)) for i, doc in enumerate(loaded)]
        parser_used = "python-docx"
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    if not pages or all(not t.strip() for _, t in pages):
        raise ValueError("No extractable text found in the uploaded file.")

    # ── 2. Build Document objects & chunk ─────────────────────────────────────
    raw_docs = pages_to_documents(pages, doc_id, filename)
    chunks = chunk_documents(raw_docs)

    total_chars = sum(len(c.page_content) for c in chunks)
    total_tokens = sum(c.metadata.get("token_count", 0) for c in chunks)

    # ── 3a. ChromaDB (disk-persisted) ─────────────────────────────────────────
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    chroma = get_chroma()
    chroma.add_documents(chunks)

    # ── 3b. FAISS per-document in-memory index ────────────────────────────────
    embeddings = get_embeddings()
    doc_faiss = FAISS.from_documents(chunks, embeddings)
    _faiss_registry[doc_id] = doc_faiss
    logger.info("[%s] FAISS per-doc index built (%d chunks)", filename, len(chunks))

    # ── 3c. Merge into global FAISS index ─────────────────────────────────────
    if _faiss_global is None:
        _faiss_global = FAISS.from_documents(chunks, embeddings)
    else:
        _faiss_global.merge_from(doc_faiss)
    logger.info("Global FAISS index now contains %d vectors", _faiss_global.index.ntotal)

    return IngestionStats(
        doc_id=doc_id,
        filename=filename,
        pages=len(pages),
        chunks=len(chunks),
        total_chars=total_chars,
        total_tokens=total_tokens,
        parser_used=parser_used,
    )


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_context(
    query: str,
    doc_id: Optional[str] = None,
    k: int = 5,
) -> list[Document]:
    """
    Retrieve the top-k most relevant chunks for *query*.

    Strategy (in order of preference):
    1. If doc_id is given AND a per-doc FAISS index exists → use it (fastest, most precise).
    2. If doc_id is given but FAISS index is absent → fall back to global FAISS with metadata filter.
    3. If no doc_id → query global FAISS index.
    4. Final safety net → ChromaDB with optional metadata filter.

    Results from multiple sources are merged and deduplicated by content hash.
    """
    results: list[Document] = []

    # ── FAISS path ────────────────────────────────────────────────────────────
    if doc_id:
        per_doc = _get_faiss_for_doc(doc_id)
        if per_doc is not None:
            try:
                results = per_doc.similarity_search(query, k=k)
                logger.debug("FAISS per-doc hit: %d results for doc %s", len(results), doc_id)
            except Exception as exc:
                logger.warning("FAISS per-doc search failed: %s", exc)

    if not results:
        global_idx = _get_faiss_global()
        if global_idx is not None:
            try:
                candidates = global_idx.similarity_search(query, k=k * 3)
                if doc_id:
                    candidates = [d for d in candidates if d.metadata.get("doc_id") == doc_id]
                results = candidates[:k]
                logger.debug("FAISS global hit: %d results", len(results))
            except Exception as exc:
                logger.warning("FAISS global search failed: %s", exc)

    # ── ChromaDB safety net ───────────────────────────────────────────────────
    if not results:
        try:
            chroma = get_chroma()
            filter_dict = {"doc_id": doc_id} if doc_id else None
            results = chroma.similarity_search(query, k=k, filter=filter_dict)
            logger.debug("ChromaDB fallback: %d results", len(results))
        except Exception as exc:
            logger.error("ChromaDB search also failed: %s", exc)

    # ── Deduplicate by content ────────────────────────────────────────────────
    seen: set[int] = set()
    unique: list[Document] = []
    for doc in results:
        h = hash(doc.page_content)
        if h not in seen:
            seen.add(h)
            unique.append(doc)

    return unique[:k]


def list_indexed_docs() -> list[dict]:
    """Return metadata for all currently indexed documents (from FAISS registry)."""
    result = []
    for doc_id, idx in _faiss_registry.items():
        try:
            vectors = idx.index.ntotal
        except Exception:
            vectors = 0
        result.append({"doc_id": doc_id, "vectors": vectors})
    return result
