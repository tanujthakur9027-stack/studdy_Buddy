"""
StudyBuddy FastAPI Application
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import get_settings
from database import init_db
from routers import ask, doubt, explain, quiz, revision, upload
from routers.documents import router as documents_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    for directory in [settings.upload_dir, settings.chroma_persist_dir, settings.faiss_index_dir]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    await init_db()
    logger.info(
        "StudyBuddy API started — provider: %s, model: %s, db: %s",
        settings.llm_provider,
        settings.openai_model if settings.llm_provider == "openai" else settings.groq_model,
        settings.database_url.split("///")[-1],
    )
    yield
    logger.info("StudyBuddy API shutting down")


app = FastAPI(
    title="StudyBuddy API",
    description=(
        "AI-powered study assistant — document ingestion (PDF/DOCX/PPT/XLSX/Images), "
        "FAISS in-memory + ChromaDB vector stores, ELI5/standard Q&A, "
        "quiz generation (DB-persisted sessions), revision planning, and RAG-based doubt solving."
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate limiter state + handler ──────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── /api/* routers ────────────────────────────────────────────────────────────
app.include_router(upload.router,      prefix="/api")
app.include_router(ask.router,         prefix="/api")
app.include_router(quiz.router,        prefix="/api")
app.include_router(revision.router,    prefix="/api")
app.include_router(explain.router,     prefix="/api")
app.include_router(doubt.router,       prefix="/api")
app.include_router(documents_router,   prefix="/api")

# ── Legacy / unversioned routers (backwards compatibility) ────────────────────
app.include_router(quiz.router)
app.include_router(revision.router)
app.include_router(explain.router)
app.include_router(doubt.router)


# ── System endpoints ──────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    from services.document_service import list_indexed_docs
    indexed = list_indexed_docs()
    provider = settings.llm_provider
    active_model = (
        settings.openai_model if provider == "openai"
        else settings.groq_model if provider == "groq"
        else "none"
    )
    return JSONResponse({
        "status": "ok",
        "provider": provider,
        "model": active_model,
        "indexed_documents": len(indexed),
        "faiss_vectors": sum(d["vectors"] for d in indexed),
        "rate_limit": f"{settings.rate_limit_per_minute}/minute",
    })


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "StudyBuddy API v3 — visit /docs for Swagger UI",
        "provider": settings.llm_provider,
        "endpoints": {
            "upload":         "POST /api/upload",
            "ask":            "POST /api/ask",
            "quiz":           "POST /api/generate-quiz",
            "quiz_submit":    "POST /api/quiz/submit",
            "quiz_history":   "GET  /api/quiz/history",
            "planner":        "POST /api/generate-plan",
            "explain":        "POST /api/explain",
            "doubt":          "POST /api/doubt/solve",
            "documents":      "GET  /api/documents",
            "saved_answers":  "GET  /api/saved-answers",
            "docs":           "GET  /docs",
        },
    }
