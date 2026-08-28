"""
StudyBuddy FastAPI Application
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from routers import ask, doubt, explain, quiz, revision, upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure required directories exist
    for directory in [settings.upload_dir, settings.chroma_persist_dir, settings.faiss_index_dir]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    logger.info(
        "StudyBuddy API started — provider: %s, model: %s",
        settings.llm_provider,
        settings.openai_model if settings.llm_provider == "openai" else settings.groq_model,
    )
    yield
    logger.info("StudyBuddy API shutting down")


app = FastAPI(
    title="StudyBuddy API",
    description=(
        "AI-powered study assistant — document ingestion (PDF/TXT via pdfplumber + PyPDF2), "
        "FAISS in-memory + ChromaDB vector stores, ELI5/standard Q&A, "
        "quiz generation, revision planning, and RAG-based doubt solving."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── /api/* routers ────────────────────────────────────────────────────────────
#   POST /api/upload          — parse PDF/TXT, build FAISS + ChromaDB indexes
#   POST /api/ask             — RAG Q&A with standard vs eli5 mode toggle
#   POST /api/generate-quiz   — canonical quiz generation endpoint
#   POST /api/generate-plan   — canonical revision planner endpoint
#   POST /api/explain         — ELI5 / simplified explanation (canonical)
#   POST /api/doubt/solve     — RAG conversational Q&A (canonical)
app.include_router(upload.router,   prefix="/api")
app.include_router(ask.router,      prefix="/api")
app.include_router(quiz.router,     prefix="/api")
app.include_router(revision.router, prefix="/api")
app.include_router(explain.router,  prefix="/api")
app.include_router(doubt.router,    prefix="/api")

# ── Legacy / unversioned routers (kept for backwards compatibility) ────────────
#   POST /quiz/generate   — kept for backwards compatibility
#   POST /revision/plan   — kept for backwards compatibility
#   POST /explain         — kept for backwards compatibility
#   POST /doubt/solve     — kept for backwards compatibility
app.include_router(quiz.router)
app.include_router(revision.router)
app.include_router(explain.router)
app.include_router(doubt.router)


# ── System endpoints ──────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    from services.document_service import list_indexed_docs
    indexed = list_indexed_docs()
    return JSONResponse({
        "status": "ok",
        "model": settings.openai_model,
        "indexed_documents": len(indexed),
        "faiss_vectors": sum(d["vectors"] for d in indexed),
    })


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "StudyBuddy API v2 — visit /docs for Swagger UI",
        "provider": settings.llm_provider,
        "endpoints": {
            "upload":     "POST /api/upload",
            "ask":        "POST /api/ask",
            "quiz":       "POST /api/generate-quiz",
            "planner":    "POST /api/generate-plan",
            "explain":    "POST /api/explain",
            "doubt":      "POST /api/doubt/solve",
            "docs":       "GET  /docs",
        },
    }
