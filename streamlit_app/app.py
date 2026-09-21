"""
StudyBuddy AI — Streamlit multipage entry point
================================================
Deploy on Streamlit Cloud:
  Entry point : streamlit_app/app.py
  Secrets     : GROQ_API_KEY, SECRET_KEY, ADMIN_SEED_EMAIL, ADMIN_SEED_PASSWORD
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

# ── Absolute paths — derived from __file__, never from CWD ────────────────────
_HERE      = Path(__file__).resolve().parent   # .../streamlit_app
_REPO_ROOT = _HERE.parent                      # repo root
_BACKEND   = _REPO_ROOT / "backend"
_DATA      = _REPO_ROOT / "data"
_PAGES     = _HERE / "pages"                   # .../streamlit_app/pages

BACKEND_URL = "http://localhost:8000"


# ── Secret helper ──────────────────────────────────────────────────────────────
def _secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, os.environ.get(key, default))  # type: ignore[attr-defined]
    except Exception:
        return os.environ.get(key, default)


# ─────────────────────────────────────────────────────────────────────────────
# Backend subprocess — ONE launch per worker via @st.cache_resource
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _launch_backend() -> bool:
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
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000",
         "--workers", "1", "--log-level", "warning"],
        cwd=str(_BACKEND), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.Popen(
        [sys.executable, "seed_admin.py"],
        cwd=str(_BACKEND),
        env={**env, "DATABASE_URL": f"sqlite+aiosqlite:///{_DATA}/studybuddy.db"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            if requests.get(f"{BACKEND_URL}/health", timeout=3).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Start backend ──────────────────────────────────────────────────────────────
with st.spinner("⏳ Starting StudyBuddy AI… (first load ~20 s)"):
    backend_ready = _launch_backend()

if not backend_ready:
    st.error("❌ Backend failed to start. Check that all dependencies are installed.")
    st.stop()

# ── Auth helpers ───────────────────────────────────────────────────────────────
def _is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))

def _is_admin() -> bool:
    return st.session_state.get("_user", {}).get("role") == "admin"

# ── Share param ────────────────────────────────────────────────────────────────
_share_id = st.query_params.get("share")

# ── Splash screen ──────────────────────────────────────────────────────────────
if not st.session_state.get("_splash_done"):
    st.markdown("""
<style>
@keyframes sbFadeIn { from{opacity:0;transform:scale(.93)} to{opacity:1;transform:scale(1)} }
@media (prefers-reduced-motion:reduce){ .sb-splash,.sb-splash *{animation:none!important} }
.sb-splash{position:fixed;inset:0;z-index:9999;
  background:linear-gradient(135deg,#09090b 0%,#0f0f23 50%,#09090b 100%);
  display:flex;align-items:center;justify-content:center;flex-direction:column;
  animation:sbFadeIn .6s ease forwards}
.sb-splash-logo{width:72px;height:72px;border-radius:20px;
  background:linear-gradient(135deg,#6366f1,#8b5cf6);
  display:flex;align-items:center;justify-content:center;margin-bottom:1.5rem;
  animation:sbFadeIn .8s ease .2s both}
.sb-splash-title{font-size:2rem;font-weight:800;color:#fafafa;letter-spacing:-.04em;
  font-family:-apple-system,'Segoe UI',system-ui,sans-serif;animation:sbFadeIn .8s ease .4s both}
.sb-splash-sub{font-size:.95rem;color:#71717a;margin-top:.5rem;
  font-family:-apple-system,'Segoe UI',system-ui,sans-serif;animation:sbFadeIn .8s ease .6s both}
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
</div>""", unsafe_allow_html=True)
    time.sleep(1.8)
    st.session_state["_splash_done"] = True
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Page routing
#
# KEY RULE: st.Page() and st.switch_page() must use IDENTICAL path strings.
# We use ABSOLUTE paths from _PAGES (Path(__file__).resolve().parent / "pages").
# These never depend on CWD, so they work identically on Streamlit Cloud and
# locally regardless of which directory you run `streamlit run` from.
#
# Every page file imports _PAGE_MAP from app state and uses _sp("name.py") to
# get the same absolute path string for st.switch_page().
# ─────────────────────────────────────────────────────────────────────────────

def _p(name: str) -> str:
    """Absolute path string for a page — consistent across st.Page() and st.switch_page()."""
    return str(_PAGES / name)

# Expose the resolver to all page files via session_state
st.session_state["_pages_dir"] = str(_PAGES)

if not _is_logged_in() and not _share_id:
    pg = st.navigation(
        [st.Page(_p("login.py"), title="Login", icon="🔑")],
        position="hidden",
    )
else:
    pages_common = [
        st.Page(_p("dashboard.py"), title="Dashboard",      icon="🏠"),
        st.Page(_p("learning.py"),  title="AI Study Tools", icon="🧠"),
        st.Page(_p("classes.py"),   title="Classes",        icon="🏛️"),
        st.Page(_p("profile.py"),   title="Profile",        icon="👤"),
    ]
    pages_admin = (
        [st.Page(_p("admin.py"), title="Admin Panel", icon="⚙️")]
        if _is_admin() else []
    )
    pg = st.navigation(pages_common + pages_admin)

pg.run()
