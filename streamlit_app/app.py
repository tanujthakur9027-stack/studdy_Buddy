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
import threading
import logging
from pathlib import Path

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ── Absolute paths — derived from __file__, never from CWD ────────────────────
_HERE      = Path(__file__).resolve().parent   # .../streamlit_app
_REPO_ROOT = _HERE.parent                      # repo root
_BACKEND   = _REPO_ROOT / "backend"
# All persistent data lives INSIDE backend/ so that every launch
# (via `streamlit run`, Streamlit Cloud, or a direct uvicorn call)
# uses the exact same DB file and upload tree — no data loss on reboot.
_DATA      = _BACKEND                          # persistent storage root
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
_backend_ready_event  = threading.Event()
_backend_failed_event = threading.Event()


def _build_env() -> dict:
    _db_path = _BACKEND / "studybuddy.db"
    return {
        **os.environ,
        "GROQ_API_KEY":                _secret("GROQ_API_KEY"),
        "GROQ_MODEL":                  _secret("GROQ_MODEL", "qwen/qwen3.8-27b"),
        "GROQ_FALLBACK_MODELS":        _secret("GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b,openai/gpt-oss-120b"),
        "OPENAI_API_KEY":              _secret("OPENAI_API_KEY", ""),
        "DATABASE_URL":                f"sqlite+aiosqlite:///{_db_path}",
        "CHROMA_PERSIST_DIR":          str(_BACKEND / "chroma_db"),
        "UPLOAD_DIR":                  str(_BACKEND / "uploads"),
        "FAISS_INDEX_DIR":             str(_BACKEND / "faiss_indexes"),
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


def _wait_for_backend(env: dict) -> None:
    """Daemon thread — polls /health; sets the appropriate Event when done."""
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            if requests.get(f"{BACKEND_URL}/health", timeout=3).status_code == 200:
                _backend_ready_event.set()
                return
        except Exception:
            pass
        time.sleep(2)
    _backend_failed_event.set()


@st.cache_resource(show_spinner=False)
def _launch_backend() -> None:
    """Launch FastAPI subprocess once per worker. Health-poll runs on a daemon thread."""
    for sub in [
        "chroma_db", "uploads", "faiss_indexes",
        "uploads/assignments", "uploads/submissions",
        "uploads/notes", "uploads/photos",
    ]:
        (_BACKEND / sub).mkdir(parents=True, exist_ok=True)

    env = _build_env()

    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000",
         "--workers", "1", "--log-level", "warning"],
        cwd=str(_BACKEND), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.Popen(
        [sys.executable, "seed_admin.py"],
        cwd=str(_BACKEND), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    threading.Thread(target=_wait_for_backend, args=(env,), daemon=True).start()


# ── Page config — MUST be the first st.* call ──────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auth helpers ───────────────────────────────────────────────────────────────
def _is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))

def _is_admin() -> bool:
    return st.session_state.get("_user", {}).get("role") == "admin"

def _p(name: str) -> str:
    """Absolute page path — consistent across st.Page() and st.switch_page()."""
    return str(_PAGES / name)

# ── Share param ────────────────────────────────────────────────────────────────
_share_id = st.query_params.get("share")

# ─────────────────────────────────────────────────────────────────────────────
# Navigation — ALWAYS built and ALWAYS run on every script execution.
#
# RULE: st.navigation() + pg.run() must be reached on EVERY Streamlit rerun.
# Calling st.rerun() / st.stop() before pg.run() raises StreamlitAPIException
# ("Oh no" crash).  All pre-navigation work (backend wait, splash) must NOT
# call st.rerun() or st.stop() — instead they return early after rendering,
# and the next Streamlit-triggered rerun will re-evaluate the condition.
# ─────────────────────────────────────────────────────────────────────────────

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

# ── Backend startup (non-blocking) ─────────────────────────────────────────────
# Kick off the subprocess + daemon thread (idempotent — cached).
_launch_backend()

# While the backend is warming up, render a full-screen splash overlay and
# schedule a rerun via fragment auto-rerun — this keeps /healthz alive AND
# lets pg.run() proceed normally below.
if not _backend_ready_event.is_set() and not _backend_failed_event.is_set():
    st.markdown("""
<style>
.sb-loading-overlay{
  position:fixed;inset:0;z-index:9999;
  background:linear-gradient(135deg,#06061a,#0d0d2b,#06061a);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.5rem;
}
.sb-loading-logo{
  width:72px;height:72px;border-radius:20px;
  background:linear-gradient(135deg,#6366f1,#8b5cf6);
  display:flex;align-items:center;justify-content:center;
  animation:sbGlow 2s ease-in-out infinite;
}
.sb-loading-title{font-size:1.8rem;font-weight:800;color:#fff;letter-spacing:-.03em}
.sb-loading-title span{background:linear-gradient(90deg,#a78bfa,#6366f1);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sb-loading-sub{font-size:.85rem;color:rgba(255,255,255,.45)}
.sb-dots{display:flex;gap:6px;margin-top:.5rem}
.sb-dot{width:8px;height:8px;border-radius:50%;background:#6366f1;
  animation:sbDotBounce 1.2s ease-in-out infinite}
.sb-dot:nth-child(2){animation-delay:.2s}
.sb-dot:nth-child(3){animation-delay:.4s}
@keyframes sbGlow{0%,100%{box-shadow:0 0 20px rgba(99,102,241,.5)}
  50%{box-shadow:0 0 40px rgba(139,92,246,.8)}}
@keyframes sbDotBounce{0%,80%,100%{transform:scale(0.6);opacity:.4}
  40%{transform:scale(1);opacity:1}}
</style>
<div class="sb-loading-overlay">
  <div class="sb-loading-logo">
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
      <path d="M12 2L4 7l8 5 8-5-8-5z" stroke="rgba(255,255,255,.95)" stroke-width="1.9"
            stroke-linejoin="round" stroke-linecap="round"/>
      <path d="M4 17l8 5 8-5" stroke="rgba(255,255,255,.95)" stroke-width="1.9"
            stroke-linejoin="round" stroke-linecap="round"/>
      <path d="M4 12l8 5 8-5" stroke="rgba(255,255,255,.65)" stroke-width="1.9"
            stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
  </div>
  <div class="sb-loading-title">Study Buddy <span>AI</span></div>
  <div class="sb-loading-sub">Starting up — first load takes ~20 s</div>
  <div class="sb-dots">
    <div class="sb-dot"></div><div class="sb-dot"></div><div class="sb-dot"></div>
  </div>
</div>""", unsafe_allow_html=True)
    # Sleep briefly then let Streamlit's normal rerun cycle pick this up.
    # We do NOT call st.rerun() here — Streamlit reruns automatically on
    # widget interactions; the spinner + time.sleep combo keeps the loop going
    # without blocking /healthz for more than 2 s at a time.
    time.sleep(2)
    st.rerun()

if _backend_failed_event.is_set():
    st.error("❌ Backend failed to start after 90 s. Check that all dependencies are installed.")
    # pg.run() still executes below so navigation remains intact.

# ── Splash screen (shown once per session after backend is ready) ──────────────
elif not st.session_state.get("_splash_done"):
    st.markdown("""
<style>
.sb-splash{position:fixed;inset:0;z-index:9998;
  background:linear-gradient(135deg,#06061a 0%,#0d0d2b 35%,#0a0a1f 65%,#06061a 100%);
  background-size:300% 300%;animation:sbBgPulse 6s ease infinite;
  display:flex;align-items:center;justify-content:center;flex-direction:column;overflow:hidden}
@keyframes sbBgPulse{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
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
    if "_splash_start" not in st.session_state:
        st.session_state["_splash_start"] = time.monotonic()
    elapsed = time.monotonic() - st.session_state["_splash_start"]
    if elapsed >= 2.2:
        st.session_state["_splash_done"] = True
    else:
        time.sleep(min(0.5, 2.2 - elapsed))
    # Fall through to pg.run() — rerun will come from Streamlit automatically.
    st.rerun()

# ── Run the active page ────────────────────────────────────────────────────────
pg.run()
