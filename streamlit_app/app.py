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
# ── Backend readiness state (shared across threads) ───────────────────────────
_backend_ready_event = threading.Event()
_backend_failed_event = threading.Event()


def _build_env() -> dict:
    # All paths are absolute and rooted in _BACKEND (= repo_root/backend/).
    # This is the same directory the standalone uvicorn launch uses, so the
    # DB file, uploads, and vector stores are always in one place and survive
    # every reboot / Streamlit rerun without data loss.
    _db_path = _BACKEND / "studybuddy.db"
    return {
        **os.environ,
        "GROQ_API_KEY":                _secret("GROQ_API_KEY"),
        "GROQ_MODEL":                  _secret("GROQ_MODEL", "qwen/qwen3.8-27b"),
        "GROQ_FALLBACK_MODELS":        _secret("GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b,openai/gpt-oss-120b"),
        "OPENAI_API_KEY":              _secret("OPENAI_API_KEY", ""),
        # Absolute path — same file regardless of who launches the process
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
    """Run in a daemon thread — polls backend /health without blocking main thread."""
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
    """
    Launch the FastAPI subprocess ONCE per Streamlit worker process.
    The health-poll runs on a daemon thread so the Streamlit main thread
    (which must keep responding to /healthz) is never blocked.
    """
    # Pre-create the backend storage tree so uvicorn never fails on first run
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
    # seed_admin.py is idempotent (INSERT OR IGNORE) — safe to run every startup
    subprocess.Popen(
        [sys.executable, "seed_admin.py"],
        cwd=str(_BACKEND), env=env,   # reuse same env — same DB path
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    t = threading.Thread(target=_wait_for_backend, args=(env,), daemon=True)
    t.start()


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Start backend (non-blocking launch; poll in small Streamlit-friendly steps) ─
_launch_backend()  # spawns subprocess + daemon poll thread (cached — runs once)

# Wait for readiness without holding the main thread for more than 2 s at a time.
# Streamlit re-runs the script every ~2 s via st.rerun(), keeping /healthz alive.
if not _backend_ready_event.is_set() and not _backend_failed_event.is_set():
    with st.spinner("⏳ Starting StudyBuddy AI… (first load ~30 s)"):
        # Yield back to Streamlit after 2 s so /healthz remains responsive.
        time.sleep(2)
    st.rerun()

if _backend_failed_event.is_set():
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
@media (prefers-reduced-motion:reduce){.sb-splash,
  .sb-splash *{animation:none!important;transition:none!important}}

@keyframes sbBgPulse {
  0%,100%{background-position:0% 50%}
  50%{background-position:100% 50%}
}
@keyframes sbLogoIn {
  0%{opacity:0;transform:scale(.5) translateY(30px)}
  60%{transform:scale(1.08) translateY(-4px)}
  100%{opacity:1;transform:scale(1) translateY(0)}
}
@keyframes sbLogoGlow {
  0%,100%{box-shadow:0 0 30px rgba(99,102,241,.5),0 0 60px rgba(139,92,246,.25)}
  50%{box-shadow:0 0 50px rgba(99,102,241,.8),0 0 90px rgba(139,92,246,.45)}
}
@keyframes sbTitleIn {
  0%{opacity:0;transform:translateY(20px)}
  100%{opacity:1;transform:translateY(0)}
}
@keyframes sbUnderline {
  0%{width:0}100%{width:60px}
}
@keyframes sbSubIn {
  0%{opacity:0;transform:translateY(12px)}
  100%{opacity:1;transform:translateY(0)}
}
@keyframes sbStarFloat {
  0%,100%{transform:translateY(0) rotate(0deg);opacity:.7}
  33%{transform:translateY(-12px) rotate(8deg);opacity:1}
  66%{transform:translateY(4px) rotate(-4deg);opacity:.5}
}
@keyframes sbParticle {
  0%{transform:translateY(0) translateX(0);opacity:0}
  10%{opacity:.6}
  90%{opacity:.3}
  100%{transform:translateY(-120px) translateX(var(--dx));opacity:0}
}
@keyframes sbFadeOut {
  0%{opacity:1}100%{opacity:0;pointer-events:none}
}

.sb-splash {
  position:fixed;inset:0;z-index:9999;
  background:linear-gradient(135deg,#06061a 0%,#0d0d2b 35%,#0a0a1f 65%,#06061a 100%);
  background-size:300% 300%;
  animation:sbBgPulse 6s ease infinite;
  display:flex;align-items:center;justify-content:center;flex-direction:column;
  overflow:hidden;
}
.sb-splash.hiding{animation:sbFadeOut .5s ease forwards}

/* floating particles */
.sb-particle {
  position:absolute;width:4px;height:4px;border-radius:50%;
  background:rgba(139,92,246,.7);
  animation:sbParticle var(--dur,3s) var(--delay,0s) ease-in infinite;
}

/* logo icon */
.sb-splash-logo {
  width:80px;height:80px;border-radius:22px;
  background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 60%,#a78bfa 100%);
  display:flex;align-items:center;justify-content:center;
  margin-bottom:1.75rem;
  animation:sbLogoIn .8s cubic-bezier(.34,1.56,.64,1) .1s both,
            sbLogoGlow 3s ease-in-out 1s infinite;
}

/* title */
.sb-splash-title {
  font-size:2.1rem;font-weight:800;letter-spacing:-.04em;
  font-family:-apple-system,'Segoe UI',system-ui,sans-serif;
  color:#fff;
  animation:sbTitleIn .7s cubic-bezier(.16,1,.3,1) .5s both;
}
.sb-splash-title span {
  background:linear-gradient(90deg,#a78bfa,#6366f1);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}

/* animated underline */
.sb-splash-line {
  height:3px;
  background:linear-gradient(90deg,#6366f1,#a78bfa);
  border-radius:2px;margin:.4rem auto .9rem;
  animation:sbUnderline .6s cubic-bezier(.16,1,.3,1) .9s both;
}

/* subtitle */
.sb-splash-sub {
  font-size:.9rem;color:rgba(255,255,255,.5);
  font-family:-apple-system,'Segoe UI',system-ui,sans-serif;
  animation:sbSubIn .6s ease 1s both;
  letter-spacing:.02em;
}
.sb-star {
  display:inline-block;color:#fbbf24;font-size:.8rem;
  animation:sbStarFloat 2.5s ease-in-out infinite;
}
.sb-star:last-child{animation-delay:.8s}
</style>

<div class="sb-splash" id="sbSplash">

  <!-- particles -->
  <div class="sb-particle" style="left:12%;bottom:10%;--dur:3.5s;--delay:0s;--dx:20px"></div>
  <div class="sb-particle" style="left:25%;bottom:15%;--dur:4s;--delay:.5s;--dx:-15px;width:3px;height:3px;background:rgba(99,102,241,.5)"></div>
  <div class="sb-particle" style="left:40%;bottom:8%;--dur:3s;--delay:1s;--dx:25px;width:5px;height:5px;background:rgba(167,139,250,.6)"></div>
  <div class="sb-particle" style="left:60%;bottom:12%;--dur:4.5s;--delay:.3s;--dx:-20px"></div>
  <div class="sb-particle" style="left:75%;bottom:18%;--dur:3.8s;--delay:.7s;--dx:10px;width:3px;height:3px"></div>
  <div class="sb-particle" style="left:88%;bottom:9%;--dur:3.2s;--delay:1.2s;--dx:-25px;background:rgba(99,102,241,.6)"></div>
  <div class="sb-particle" style="left:50%;bottom:5%;--dur:2.8s;--delay:.2s;--dx:15px;width:6px;height:6px;background:rgba(139,92,246,.4)"></div>
  <div class="sb-particle" style="left:33%;bottom:20%;--dur:5s;--delay:.9s;--dx:-10px;width:2px;height:2px"></div>
  <div class="sb-particle" style="left:70%;bottom:6%;--dur:3.6s;--delay:1.5s;--dx:18px;background:rgba(167,139,250,.5)"></div>

  <!-- logo -->
  <div class="sb-splash-logo">
    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
      <path d="M12 2L4 7l8 5 8-5-8-5z" stroke="rgba(255,255,255,.95)" stroke-width="1.9" stroke-linejoin="round" stroke-linecap="round"/>
      <path d="M4 17l8 5 8-5" stroke="rgba(255,255,255,.95)" stroke-width="1.9" stroke-linejoin="round" stroke-linecap="round"/>
      <path d="M4 12l8 5 8-5" stroke="rgba(255,255,255,.65)" stroke-width="1.9" stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
  </div>

  <!-- title -->
  <div class="sb-splash-title">Study Buddy <span>AI</span></div>

  <!-- animated underline -->
  <div class="sb-splash-line"></div>

  <!-- subtitle -->
  <div class="sb-splash-sub">
    <span class="sb-star">✦</span>&nbsp; Your personal AI learning companion &nbsp;<span class="sb-star">✦</span>
  </div>

</div>""", unsafe_allow_html=True)
    # Record when the splash started (first render only).
    if "_splash_start" not in st.session_state:
        st.session_state["_splash_start"] = time.monotonic()
    # Re-run after 2.2 s without blocking the main thread so /healthz stays alive.
    elapsed = time.monotonic() - st.session_state["_splash_start"]
    if elapsed < 2.2:
        time.sleep(min(0.5, 2.2 - elapsed))  # yield in short 0.5 s increments
        st.rerun()
    else:
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
# Page files import _p() from core.auth_state which derives the same absolute
# path from its own __file__ location — no session_state dependency.
#
# Navigation is rebuilt on every run: unauthenticated → only login.py;
# authenticated → dashboard, learning, classes, profile (+ admin if admin).
# After login/logout, pages use st.rerun() so app.py rebuilds nav correctly.
# ─────────────────────────────────────────────────────────────────────────────

def _p(name: str) -> str:
    """Absolute path string for a page — consistent across st.Page() and st.switch_page()."""
    return str(_PAGES / name)

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
