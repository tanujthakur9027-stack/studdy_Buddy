"""
StudyBuddy AI — Streamlit multipage entry point
================================================
Deploy on Streamlit Cloud:
  Entry point : streamlit_app/app.py
  Secrets     : GROQ_API_KEY, SECRET_KEY (required)
                GEMINI_API_KEY, ADMIN_SEED_EMAIL, ADMIN_SEED_PASSWORD (optional)

Architecture (no cold start):
  FastAPI runs in a background thread inside the SAME Python process as
  Streamlit via uvicorn.Server.  No subprocess, no polling loop.
  The server is ready in ~2 s — before Streamlit renders the first frame.
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import logging
import tempfile
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

# ── Absolute paths ─────────────────────────────────────────────────────────────
_HERE      = Path(__file__).resolve().parent   # .../streamlit_app
_REPO_ROOT = _HERE.parent                      # repo root
_BACKEND   = _REPO_ROOT / "backend"
_PAGES     = _HERE / "pages"

# ── Put backend/ on sys.path so `import main`, `import config`, etc. work ──────
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

BACKEND_URL = "http://localhost:8000"


# ── Secret injection — must happen BEFORE backend modules are imported ─────────
def _inject_secrets() -> None:
    """
    Push Streamlit secrets (or env vars) into os.environ so that
    pydantic-settings / config.py picks them up when it loads.
    Called exactly once, before any backend import.
    """
    _db_path = _BACKEND / "studybuddy.db"

    # Directories
    for sub in [
        "chroma_db", "uploads", "faiss_indexes",
        "uploads/assignments", "uploads/submissions",
        "uploads/notes", "uploads/photos",
    ]:
        (_BACKEND / sub).mkdir(parents=True, exist_ok=True)

    def _s(key: str, default: str = "") -> str:
        try:
            return st.secrets.get(key, os.environ.get(key, default))  # type: ignore[attr-defined]
        except Exception:
            return os.environ.get(key, default)

    overrides = {
        "GROQ_API_KEY":                _s("GROQ_API_KEY"),
        "GROQ_MODEL":                  _s("GROQ_MODEL", "qwen/qwen3-27b"),
        "GROQ_FALLBACK_MODELS":        _s("GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b,openai/gpt-oss-120b"),
        "GEMINI_API_KEY":              _s("GEMINI_API_KEY", ""),
        "GEMINI_MODEL":                _s("GEMINI_MODEL", "gemini-2.5-flash"),
        "DATABASE_URL":                f"sqlite+aiosqlite:///{_db_path}",
        "CHROMA_PERSIST_DIR":          str(_BACKEND / "chroma_db"),
        "UPLOAD_DIR":                  str(_BACKEND / "uploads"),
        "FAISS_INDEX_DIR":             str(_BACKEND / "faiss_indexes"),
        "MAX_FILE_SIZE_MB":            "200",
        "CORS_ORIGINS":                "*",
        "RATE_LIMIT_PER_MINUTE":       "60",
        "SECRET_KEY":                  _s("SECRET_KEY", "dev-secret-change-in-prod"),
        "ACCESS_TOKEN_EXPIRE_MINUTES": "1440",
        "ADMIN_SEED_EMAIL":            _s("ADMIN_SEED_EMAIL", "admin@studybuddy.com"),
        "ADMIN_SEED_PASSWORD":         _s("ADMIN_SEED_PASSWORD", "Admin@StudyBuddy2024"),
        "SMTP_HOST":                   _s("SMTP_HOST", ""),
        "SMTP_PORT":                   _s("SMTP_PORT", "587"),
        "SMTP_USER":                   _s("SMTP_USER", ""),
        "SMTP_PASS":                   _s("SMTP_PASS", ""),
        "SMTP_FROM":                   _s("SMTP_FROM", "noreply@studybuddy.com"),
        "APP_BASE_URL":                _s("APP_BASE_URL", "https://studybuddy.streamlit.app"),
        "ASSIGNMENT_FILE_MAX_MB":      "50",
        "NOTE_FILE_MAX_MB":            "50",
        "PROFILE_PHOTO_MAX_MB":        "5",
        "PERIOD_DURATION_MINUTES":     "45",
        "LUNCH_DURATION_MINUTES":      "45",
    }
    for k, v in overrides.items():
        if v:  # don't overwrite with empty strings
            os.environ[k] = v


# ── In-process FastAPI server via uvicorn.Server ───────────────────────────────
@st.cache_resource(show_spinner=False)
def _start_backend() -> str:
    """
    Import and start the FastAPI app in a background thread.
    Returns "ok" immediately — the server is ready within ~2 s.
    Uses @st.cache_resource so this runs ONCE per Streamlit worker process.
    """
    _inject_secrets()

    import uvicorn  # noqa: PLC0415

    # Import the FastAPI app object — pydantic-settings reads env vars NOW
    # (os.environ already has our secrets from _inject_secrets above)
    from main import app as fastapi_app  # noqa: PLC0415

    config = uvicorn.Config(
        app=fastapi_app,
        host="127.0.0.1",
        port=8000,
        workers=1,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    def _run() -> None:
        # Each thread needs its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # Seed admin account after a short delay to let DB init finish
    def _seed() -> None:
        import time, importlib  # noqa: PLC0415
        time.sleep(4)           # wait for init_db() to complete
        try:
            import asyncio as _asyncio  # noqa: PLC0415
            seed_mod = importlib.import_module("seed_admin")
            _asyncio.run(seed_mod.seed())
        except Exception as exc:
            logger.warning("seed_admin failed: %s", exc)

    threading.Thread(target=_seed, daemon=True).start()

    return "ok"


# ── Page config — MUST be the very first st.* call ────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Start backend in-process (non-blocking, returns immediately) ───────────────
_start_backend()

# ── Auth helpers ───────────────────────────────────────────────────────────────
def _is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))

def _is_admin() -> bool:
    return st.session_state.get("_user", {}).get("role") == "admin"

def _p(name: str) -> str:
    return str(_PAGES / name)


# ── Share param ────────────────────────────────────────────────────────────────
_share_id = st.query_params.get("share")

# ── Navigation ─────────────────────────────────────────────────────────────────
if not _is_logged_in() and not _share_id:
    pg = st.navigation(
        [st.Page(_p("login.py"), title="Login", icon="🔑")],
        position="hidden",
    )
elif _is_admin():
    pg = st.navigation([
        st.Page(_p("dashboard.py"), title="Dashboard",      icon="🏠"),
        st.Page(_p("learning.py"),  title="AI Study Tools", icon="🧠"),
        st.Page(_p("profile.py"),   title="Profile",        icon="👤"),
        st.Page(_p("admin.py"),     title="Admin Panel",    icon="⚙️"),
    ])
else:
    pg = st.navigation([
        st.Page(_p("dashboard.py"), title="Dashboard",      icon="🏠"),
        st.Page(_p("learning.py"),  title="AI Study Tools", icon="🧠"),
        st.Page(_p("classes.py"),   title="Classes",        icon="🏛️"),
        st.Page(_p("profile.py"),   title="Profile",        icon="👤"),
    ])

# ── Splash screen — shown once per session, pure CSS (no rerun needed) ─────────
if not st.session_state.get("_splash_done"):
    st.session_state["_splash_done"] = True
    st.markdown("""
<style>
.sb-splash{
  position:fixed;inset:0;z-index:9998;pointer-events:none;
  background:linear-gradient(135deg,#06061a 0%,#0d0d2b 35%,#0a0a1f 65%,#06061a 100%);
  background-size:300% 300%;
  animation:sbBgPulse 6s ease infinite,sbFadeOut .4s ease 2.2s forwards;
  display:flex;align-items:center;justify-content:center;flex-direction:column;overflow:hidden}
@keyframes sbBgPulse{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes sbFadeOut{0%{opacity:1}100%{opacity:0;visibility:hidden}}
.sb-splash-logo{width:80px;height:80px;border-radius:22px;
  background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 60%,#a78bfa 100%);
  display:flex;align-items:center;justify-content:center;margin-bottom:1.75rem;
  animation:sbLogoIn .8s cubic-bezier(.34,1.56,.64,1) .1s both,sbLogoGlow 3s ease-in-out 1s infinite}
@keyframes sbLogoIn{0%{opacity:0;transform:scale(.5) translateY(30px)}
  60%{transform:scale(1.08) translateY(-4px)}100%{opacity:1;transform:scale(1) translateY(0)}}
@keyframes sbLogoGlow{0%,100%{box-shadow:0 0 30px rgba(99,102,241,.5)}
  50%{box-shadow:0 0 50px rgba(99,102,241,.8)}}
.sb-splash-title{font-size:2.1rem;font-weight:800;letter-spacing:-.04em;
  font-family:-apple-system,'Segoe UI',system-ui,sans-serif;color:#fff;
  animation:sbTitleIn .7s cubic-bezier(.16,1,.3,1) .5s both}
.sb-splash-title span{background:linear-gradient(90deg,#a78bfa,#6366f1);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sb-splash-line{height:3px;background:linear-gradient(90deg,#6366f1,#a78bfa);
  border-radius:2px;margin:.4rem auto .9rem;
  animation:sbUnderline .6s cubic-bezier(.16,1,.3,1) .9s both}
@keyframes sbTitleIn{0%{opacity:0;transform:translateY(20px)}100%{opacity:1;transform:translateY(0)}}
@keyframes sbUnderline{0%{width:0}100%{width:60px}}
.sb-splash-sub{font-size:.9rem;color:rgba(255,255,255,.5);
  font-family:-apple-system,'Segoe UI',system-ui,sans-serif;
  animation:sbSubIn .6s ease 1s both;letter-spacing:.02em}
@keyframes sbSubIn{0%{opacity:0;transform:translateY(12px)}100%{opacity:1;transform:translateY(0)}}
@media(prefers-reduced-motion:reduce){.sb-splash,.sb-splash *{animation:none!important}}
</style>
<div class="sb-splash">
  <div class="sb-splash-logo">
    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
      <path d="M12 2L4 7l8 5 8-5-8-5z" stroke="rgba(255,255,255,.95)" stroke-width="1.9"
            stroke-linejoin="round" stroke-linecap="round"/>
      <path d="M4 17l8 5 8-5" stroke="rgba(255,255,255,.95)" stroke-width="1.9"
            stroke-linejoin="round" stroke-linecap="round"/>
      <path d="M4 12l8 5 8-5" stroke="rgba(255,255,255,.65)" stroke-width="1.9"
            stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
  </div>
  <div class="sb-splash-title">Study Buddy <span>AI</span></div>
  <div class="sb-splash-line"></div>
  <div class="sb-splash-sub">✦&nbsp; Your personal AI learning companion &nbsp;✦</div>
</div>""", unsafe_allow_html=True)

# ── Run the active page ────────────────────────────────────────────────────────
pg.run()
