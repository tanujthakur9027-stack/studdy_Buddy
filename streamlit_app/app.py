"""
StudyBuddy AI — Streamlit multipage entry point
================================================
• Uses @st.cache_resource so the backend subprocess is launched ONCE per Streamlit
  worker process, not once per browser session (fixes the race condition in the old
  st.session_state-based launcher).
• st.navigation / st.Page routing (requires streamlit >= 1.40).
• Token is restored from a cookie on every page load via streamlit-cookies-manager.
• ?share=<id> query param skips auth for public share links.

Deploy on Streamlit Cloud:
  Entry point : streamlit_app/app.py
  Secrets     : GROQ_API_KEY, SECRET_KEY, ADMIN_SEED_EMAIL, ADMIN_SEED_PASSWORD
                COOKIE_SECRET (random 32-char string)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import logging
from pathlib import Path

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE      = Path(__file__).parent
_REPO_ROOT = _HERE.parent
_BACKEND   = _REPO_ROOT / "backend"
_DATA      = _REPO_ROOT / "data"

BACKEND_URL = "http://localhost:8000"


# ── Secret helper ──────────────────────────────────────────────────────────────
def _secret(key: str, default: str = "") -> str:
    """Read from st.secrets first, then os.environ."""
    try:
        return st.secrets.get(key, os.environ.get(key, default))  # type: ignore[attr-defined]
    except Exception:
        return os.environ.get(key, default)


# ─────────────────────────────────────────────────────────────────────────────
# Backend subprocess — ONE launch per worker via @st.cache_resource
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _launch_backend() -> bool:
    """
    Launch uvicorn in a background subprocess and wait until /health responds.
    Called once per Streamlit worker process (not per browser tab).
    Returns True if the backend became healthy within the timeout.
    """
    for sub in [
        "chroma_db", "uploads", "faiss_indexes",
        "uploads/assignments", "uploads/submissions",
        "uploads/notes", "uploads/photos",
    ]:
        (_DATA / sub).mkdir(parents=True, exist_ok=True)

    env = {
        **os.environ,
        "GROQ_API_KEY":                _secret("GROQ_API_KEY"),
        "GROQ_MODEL":                  _secret("GROQ_MODEL", "groq/compound-mini"),
        "OPENAI_API_KEY":              _secret("OPENAI_API_KEY", ""),
        "DATABASE_URL":                f"sqlite+aiosqlite:///{_DATA}/studybuddy.db",
        "CHROMA_PERSIST_DIR":          str(_DATA / "chroma_db"),
        "UPLOAD_DIR":                  str(_DATA / "uploads"),
        "FAISS_INDEX_DIR":             str(_DATA / "faiss_indexes"),
        "MAX_FILE_SIZE_MB":            "200",
        "CORS_ORIGINS":                "*",
        "RATE_LIMIT_PER_MINUTE":       "60",
        "SECRET_KEY":                  _secret("SECRET_KEY", "dev-secret-change-in-prod"),
        "ACCESS_TOKEN_EXPIRE_MINUTES": "1440",
        "ADMIN_SEED_EMAIL":            _secret("ADMIN_SEED_EMAIL", "admin@studybuddy.com"),
        "ADMIN_SEED_PASSWORD":         _secret("ADMIN_SEED_PASSWORD", "Admin@StudyBuddy2024"),
        "SMTP_HOST":                   _secret("SMTP_HOST", ""),
        "SMTP_PORT":                   _secret("SMTP_PORT", "587"),
        "SMTP_USER":                   _secret("SMTP_USER", ""),
        "SMTP_PASS":                   _secret("SMTP_PASS", ""),
        "SMTP_FROM":                   _secret("SMTP_FROM", "noreply@studybuddy.com"),
        "APP_BASE_URL":                _secret("APP_BASE_URL", "https://studybuddy.streamlit.app"),
        "ASSIGNMENT_FILE_MAX_MB":      "50",
        "NOTE_FILE_MAX_MB":            "50",
        "PROFILE_PHOTO_MAX_MB":        "5",
        "PERIOD_DURATION_MINUTES":     "45",
        "LUNCH_DURATION_MINUTES":      "45",
        "PYTHONPATH":                  str(_BACKEND),
    }

    subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1", "--port", "8000",
            "--workers", "1", "--log-level", "warning",
        ],
        cwd=str(_BACKEND),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Seed admin (idempotent) in the background
    subprocess.Popen(
        [sys.executable, "seed_admin.py"],
        cwd=str(_BACKEND),
        env={
            **env,
            "DATABASE_URL": f"sqlite+aiosqlite:///{_DATA}/studybuddy.db",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 90 s for the backend to become healthy
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ── Page config (must be called before anything else writes to UI) ─────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Ensure backend is up (blocks with a spinner on cold start)
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("⏳ Starting StudyBuddy AI… (first load ~20 s)"):
    backend_ready = _launch_backend()

if not backend_ready:
    st.error("❌ Backend failed to start. Check that all dependencies are installed.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Token lives in st.session_state (per-browser-tab, persists across reruns).
# streamlit-cookies-manager is NOT used — it relies on @st.cache which was
# removed in Streamlit 1.36+ and raises AttributeError on modern versions.
# ─────────────────────────────────────────────────────────────────────────────
# Nothing to restore on cold load — user must log in again after a page refresh.
# Session state is preserved across st.rerun() within the same tab session.


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))


def _is_admin() -> bool:
    return st.session_state.get("_user", {}).get("role") == "admin"


# ─────────────────────────────────────────────────────────────────────────────
# ?share=<id> public route — skip auth
# ─────────────────────────────────────────────────────────────────────────────
_params = st.query_params
_share_id = _params.get("share")


# ─────────────────────────────────────────────────────────────────────────────
# Splash screen — shown once per browser session until backend is ready
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.get("_splash_done"):
    st.markdown("""
<style>
@keyframes fadeIn  { from{opacity:0;transform:scale(.92)} to{opacity:1;transform:scale(1)} }
@keyframes fadeOut { from{opacity:1} to{opacity:0;pointer-events:none} }
@media (prefers-reduced-motion: reduce) {
  .sb-splash, .sb-splash * { animation: none !important; }
}
.sb-splash {
  position:fixed; inset:0; z-index:9999;
  background: linear-gradient(135deg, #09090b 0%, #0f0f23 50%, #09090b 100%);
  display:flex; align-items:center; justify-content:center; flex-direction:column;
  animation: fadeIn .6s ease forwards;
}
.sb-splash-logo {
  width:72px; height:72px; border-radius:20px;
  background: linear-gradient(135deg,#6366f1,#8b5cf6);
  display:flex; align-items:center; justify-content:center;
  margin-bottom:1.5rem;
  animation: fadeIn .8s ease .2s both;
}
.sb-splash-title {
  font-size:2rem; font-weight:800; color:#fafafa; letter-spacing:-.04em;
  font-family: -apple-system,'Segoe UI',system-ui,sans-serif;
  animation: fadeIn .8s ease .4s both;
}
.sb-splash-sub {
  font-size:.95rem; color:#71717a; margin-top:.5rem;
  font-family: -apple-system,'Segoe UI',system-ui,sans-serif;
  animation: fadeIn .8s ease .6s both;
}
.sb-splash-dot {
  width:8px; height:8px; border-radius:50%;
  background:#6366f1; margin:.top:1.5rem;
  animation: fadeIn .8s ease .8s both;
}
</style>
<div class="sb-splash">
  <div class="sb-splash-logo">
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none">
      <path d="M12 3L4 8l8 5 8-5-8-5z" stroke="rgba(255,255,255,.95)" stroke-width="1.8" stroke-linejoin="round"/>
      <path d="M4 16l8 5 8-5" stroke="rgba(255,255,255,.95)" stroke-width="1.8" stroke-linejoin="round"/>
      <path d="M4 12l8 5 8-5" stroke="rgba(255,255,255,.7)" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="sb-splash-title">Study Buddy AI</div>
  <div class="sb-splash-sub">Your intelligent learning companion</div>
</div>
""", unsafe_allow_html=True)
    time.sleep(1.8)
    st.session_state["_splash_done"] = True
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Page routing via st.navigation (requires streamlit >= 1.40)
# ─────────────────────────────────────────────────────────────────────────────
from streamlit.navigation.page import StreamlitPage  # noqa: E402  (after set_page_config)

# Import page render functions
sys.path.insert(0, str(_HERE))

from pages.login      import render as _login_page       # noqa: E402
from pages.dashboard  import render as _dashboard_page   # noqa: E402
from pages.learning   import render as _learning_page    # noqa: E402
from pages.classes    import render as _classes_page     # noqa: E402
from pages.profile    import render as _profile_page     # noqa: E402
from pages.admin      import render as _admin_page       # noqa: E402


if not _is_logged_in() and not _share_id:
    # ── Unauthenticated: only show Login page, nothing else ───────────────────
    pg = st.navigation([st.Page(_login_page, title="Login", icon="🔑")], position="hidden")
    pg.run()
else:
    # ── Authenticated: full nav ───────────────────────────────────────────────
    pages_common = [
        st.Page(_dashboard_page, title="Dashboard",      icon="🏠"),
        st.Page(_learning_page,  title="AI Study Tools", icon="🧠"),
        st.Page(_classes_page,   title="Classes",        icon="🏛️"),
        st.Page(_profile_page,   title="Profile",        icon="👤"),
    ]
    pages_admin = [
        st.Page(_admin_page, title="Admin Panel", icon="⚙️"),
    ] if _is_admin() else []

    pg = st.navigation(pages_common + pages_admin)
    pg.run()
