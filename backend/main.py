"""
StudyBuddy FastAPI Application
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import get_settings
from database import init_db
from routers import ask, doubt, explain, quiz, revision, upload
from routers.chat import router as chat_router
from routers.cheatsheet import router as cheatsheet_router
from routers.documents import router as documents_router
from routers.progress import router as progress_router
from routers.share import router as share_router
from utils.log_config import setup_logging

# ── Logging ───────────────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Sentry (optional — only active when SENTRY_DSN is set) ───────────────────
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
        # Never log API keys or bearer tokens
        send_default_pii=False,
    )
    logger.info("Sentry initialised", extra={"dsn_prefix": settings.sentry_dsn[:30]})
else:
    logger.info("Sentry disabled — set SENTRY_DSN to enable error tracking")

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    for directory in [settings.upload_dir, settings.chroma_persist_dir, settings.faiss_index_dir]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    await init_db()
    logger.info(
        "startup",
        extra={
            "provider": settings.llm_provider,
            "model": settings.openai_model if settings.llm_provider == "openai" else settings.groq_model,
            "db": settings.database_url.split("///")[-1],
            "sentry": bool(settings.sentry_dsn),
        },
    )
    yield
    logger.info("shutdown")


app = FastAPI(
    title="StudyBuddy API",
    description=(
        "AI-powered study assistant — document ingestion (PDF/DOCX/PPT/XLSX/Images), "
        "FAISS in-memory + ChromaDB vector stores, ELI5/standard Q&A, "
        "quiz generation (DB-persisted sessions), revision planning, and RAG-based doubt solving."
    ),
    version="4.0.0",
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
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


# ── Request timing + request-id middleware ────────────────────────────────────
@app.middleware("http")
async def request_instrumentation(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    response = await call_next(request)
    latency_ms = int((time.monotonic() - t0) * 1000)

    # Security + observability headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{latency_ms}ms"

    # Skip logging for health checks to reduce noise
    if request.url.path not in ("/health", "/"):
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "request_id": request_id,
            },
        )
        if latency_ms > 5000:
            logger.warning(
                "slow_request",
                extra={"path": request.url.path, "latency_ms": latency_ms},
            )

    return response


# ── /api/* routers ────────────────────────────────────────────────────────────
app.include_router(upload.router,      prefix="/api")
app.include_router(ask.router,         prefix="/api")
app.include_router(quiz.router,        prefix="/api")
app.include_router(revision.router,    prefix="/api")
app.include_router(explain.router,     prefix="/api")
app.include_router(doubt.router,       prefix="/api")
app.include_router(documents_router,   prefix="/api")
app.include_router(chat_router,        prefix="/api")
app.include_router(share_router,       prefix="/api")
app.include_router(progress_router,    prefix="/api")
app.include_router(cheatsheet_router,  prefix="/api")

# ── Legacy / unversioned routers (backwards compatibility) ────────────────────
app.include_router(quiz.router)
app.include_router(revision.router)
app.include_router(explain.router)
app.include_router(doubt.router)


# ── System endpoints ──────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    """Extended health check — includes DB ping and vector store status."""
    from database import AsyncSessionLocal
    from services.document_service import list_indexed_docs

    # DB ping
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    indexed = list_indexed_docs()
    provider = settings.llm_provider
    active_model = (
        settings.openai_model if provider == "openai"
        else settings.groq_model if provider == "groq"
        else "none"
    )

    return JSONResponse({
        "status": "ok" if db_ok else "degraded",
        "provider": provider,
        "model": active_model,
        "database": "ok" if db_ok else "error",
        "sentry": "enabled" if settings.sentry_dsn else "disabled",
        "indexed_documents": len(indexed),
        "faiss_vectors": sum(d["vectors"] for d in indexed),
        "rate_limit": f"{settings.rate_limit_per_minute}/minute",
    })


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "StudyBuddy API v4 — visit /docs for Swagger UI",
        "provider": settings.llm_provider,
        "endpoints": {
            "upload":         "POST /api/upload",
            "ask":            "POST /api/ask",
            "ask_stream":     "POST /api/ask/stream",
            "quiz":           "POST /api/generate-quiz",
            "quiz_submit":    "POST /api/quiz/submit",
            "quiz_history":   "GET  /api/quiz/history",
            "planner":        "POST /api/generate-plan",
            "explain":        "POST /api/explain",
            "explain_stream": "POST /api/explain/stream",
            "doubt_stream":   "POST /api/doubt/stream",
            "cheatsheet":     "POST /api/cheatsheet",
            "documents":      "GET  /api/documents",
            "saved_answers":  "GET  /api/saved-answers",
            "chats":          "GET  /api/chats",
            "share_create":   "POST /api/share",
            "share_resolve":  "GET  /api/share/{id}",
            "progress":       "GET  /api/progress/summary",
            "health":         "GET  /health",
            "docs":           "GET  /docs",
        },
    }
