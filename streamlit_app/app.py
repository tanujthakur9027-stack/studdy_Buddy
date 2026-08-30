"""
StudyBuddy — Streamlit App (self-contained, no Render needed)
=============================================================
This file does two things:
  1. Launches the FastAPI backend (uvicorn) as a subprocess on localhost:8000
     the first time a Streamlit worker starts. All subsequent reruns reuse it.
  2. Renders the full 9-tab study UI, talking to the backend over loopback.

Deploy to Streamlit Cloud:
  - Repo root entry point : streamlit_app/app.py
  - Secrets (App Settings → Secrets):
        GROQ_API_KEY = "gsk_..."
  - That's it. No Render, no CORS, no environment variables to wire up.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import random
import logging
from pathlib import Path

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
# Repo root is two levels up from streamlit_app/app.py
_HERE       = Path(__file__).parent          # …/streamlit_app/
_REPO_ROOT  = _HERE.parent                   # …/Studdy_Buddy/
_BACKEND    = _REPO_ROOT / "backend"         # …/backend/
_DATA       = _REPO_ROOT / "data"            # …/data/  (created at runtime)

BACKEND_URL = "http://localhost:8000"

# ── Timeouts ──────────────────────────────────────────────────────────────────
TIMEOUT_SHORT = 60
TIMEOUT_LONG  = 180


# ─────────────────────────────────────────────────────────────────────────────
# Sub-process launcher — starts uvicorn once per Streamlit worker lifecycle
# ─────────────────────────────────────────────────────────────────────────────
def _start_backend() -> None:
    """
    Launch the FastAPI backend as a background subprocess (non-blocking).
    Guarded by st.session_state so it only happens once per worker, not on
    every Streamlit rerun.
    """
    if st.session_state.get("_backend_started"):
        return  # already running

    # Create data directories (SQLite, ChromaDB, uploads all live here)
    _DATA.mkdir(parents=True, exist_ok=True)
    (_DATA / "chroma_db").mkdir(exist_ok=True)
    (_DATA / "uploads").mkdir(exist_ok=True)
    (_DATA / "faiss_indexes").mkdir(exist_ok=True)

    # Pull GROQ_API_KEY from Streamlit secrets (set in App Settings → Secrets)
    groq_key = ""
    try:
        groq_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass
    # Also honour a plain env var (useful for local dev)
    groq_key = groq_key or os.environ.get("GROQ_API_KEY", "")

    env = {
        **os.environ,
        # LLM
        "GROQ_API_KEY":        groq_key,
        "GROQ_MODEL":          os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
        # Override any OpenAI key from secrets too
        "OPENAI_API_KEY":      os.environ.get("OPENAI_API_KEY",
                                    st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""),
        # Storage — all paths relative to backend/ cwd, pointing to ../data/
        "DATABASE_URL":        f"sqlite+aiosqlite:///{_DATA}/studybuddy.db",
        "CHROMA_PERSIST_DIR":  str(_DATA / "chroma_db"),
        "UPLOAD_DIR":          str(_DATA / "uploads"),
        "FAISS_INDEX_DIR":     str(_DATA / "faiss_indexes"),
        # Upload limit
        "MAX_FILE_SIZE_MB":    "200",
        # CORS — allow everything (loopback calls, no browser security boundary)
        "CORS_ORIGINS":        "*",
        # Rate limiting — more generous inside the single-process bundle
        "RATE_LIMIT_PER_MINUTE": "60",
        # Python path so backend imports resolve correctly
        "PYTHONPATH":          str(_BACKEND),
    }

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--workers", "1",
            "--log-level", "warning",
        ],
        cwd=str(_BACKEND),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    st.session_state["_backend_proc"]    = proc
    st.session_state["_backend_started"] = True


def _wait_for_backend(timeout: int = 60) -> bool:
    """Poll /health until backend is ready. Returns True on success."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _ensure_backend() -> bool:
    """
    Start backend if not yet running, then wait for it to be healthy.
    Shows a spinner while waiting. Returns True if backend is ready.
    """
    _start_backend()

    # If it was already running, do a quick health check
    if st.session_state.get("_backend_healthy"):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            # Backend died — allow restart on next rerun
            st.session_state.pop("_backend_healthy", None)
            st.session_state.pop("_backend_started", None)
            st.session_state.pop("_backend_proc", None)
            return False

    with st.spinner("⏳ Starting backend… (first load takes ~20 s to warm up the embedding model)"):
        ready = _wait_for_backend(timeout=90)

    if ready:
        st.session_state["_backend_healthy"] = True
    else:
        st.error(
            "❌ Backend failed to start within 90 seconds. "
            "Check that all dependencies are installed and GROQ_API_KEY is set."
        )
    return ready


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎓</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS — Vercel-style SaaS dark theme ─────────────────────────────────
st.markdown("""
<style>
/* ── Reset & base ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── App shell ─────────────────────────────────────────────────────────────── */
.stApp { background: #09090b; }
.block-container {
  max-width: 980px !important;
  padding: 2rem 2rem 4rem !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #09090b !important;
  border-right: 1px solid #27272a !important;
}
[data-testid="stSidebar"] > div { padding: 1.5rem 1rem; }

/* ── Tab bar — clean pill style ────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid #27272a !important;
  gap: 0 !important;
  padding: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  color: #71717a !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 10px 16px !important;
  margin-bottom: -1px !important;
  transition: color .15s, border-color .15s !important;
  white-space: nowrap !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #fafafa !important;
  border-bottom-color: #6366f1 !important;
  background: transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: #d4d4d8 !important;
  background: transparent !important;
}

/* ── Cards / containers ────────────────────────────────────────────────────── */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
  border-radius: 12px;
}
div[data-testid="stForm"] {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 12px;
  padding: 1.5rem !important;
}

/* ── Expander ──────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: #18181b !important;
  border: 1px solid #27272a !important;
  border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #d4d4d8 !important;
}
.streamlit-expanderHeader { font-weight: 600; }

/* ── Buttons ───────────────────────────────────────────────────────────────── */
[data-testid="baseButton-primary"] {
  background: #6366f1 !important;
  border: none !important;
  border-radius: 8px !important;
  color: #fff !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 8px 20px !important;
  transition: background .15s, opacity .15s !important;
}
[data-testid="baseButton-primary"]:hover { background: #4f46e5 !important; }
[data-testid="baseButton-secondary"] {
  background: #27272a !important;
  border: 1px solid #3f3f46 !important;
  border-radius: 8px !important;
  color: #d4d4d8 !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
}
[data-testid="baseButton-secondary"]:hover {
  background: #3f3f46 !important;
  border-color: #52525b !important;
}

/* ── Inputs ────────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] {
  background: #18181b !important;
  border: 1px solid #3f3f46 !important;
  border-radius: 8px !important;
  color: #fafafa !important;
  font-size: 14px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99,102,241,.2) !important;
}

/* ── Chat ──────────────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
  background: #18181b !important;
  border: 1px solid #27272a !important;
  border-radius: 12px !important;
  padding: 1rem 1.25rem !important;
  margin-bottom: .75rem !important;
}

/* ── Metrics ───────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 10px;
  padding: .75rem 1rem;
}
[data-testid="stMetricLabel"] { color: #71717a !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #fafafa !important; font-size: 22px !important; font-weight: 700 !important; }

/* ── Divider ───────────────────────────────────────────────────────────────── */
hr { border-color: #27272a !important; margin: 1.5rem 0 !important; }

/* ── Source chips ──────────────────────────────────────────────────────────── */
.src-chip {
  display: inline-flex; align-items: center; gap: 4px;
  background: #27272a; border: 1px solid #3f3f46;
  border-radius: 6px; padding: 3px 10px;
  font-size: 11px; color: #a1a1aa; margin: 2px;
  font-family: 'Inter', monospace;
}

/* ── Section headings ──────────────────────────────────────────────────────── */
.sb-heading {
  font-size: 22px !important;
  font-weight: 700 !important;
  color: #fafafa !important;
  margin-bottom: .25rem !important;
  letter-spacing: -.3px;
}
.sb-sub {
  font-size: 13px !important;
  color: #71717a !important;
  margin-bottom: 1.5rem !important;
}

/* ── Sidebar logo area ─────────────────────────────────────────────────────── */
.sb-logo {
  display: flex; align-items: center; gap: 10px;
  padding: .5rem 0 1rem 0; margin-bottom: .5rem;
}
.sb-logo-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.sb-logo-text { font-size: 16px; font-weight: 700; color: #fafafa; }
.sb-logo-badge {
  font-size: 10px; font-weight: 600; color: #a78bfa;
  background: rgba(167,139,250,.12); border: 1px solid rgba(167,139,250,.3);
  border-radius: 4px; padding: 1px 6px; margin-left: 2px;
}

/* ── Status badge ──────────────────────────────────────────────────────────── */
.status-ok   { color: #22c55e; font-size: 12px; font-weight: 600; }
.status-warn { color: #f59e0b; font-size: 12px; font-weight: 600; }

/* ── Upload drop zone ──────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background: #18181b !important;
  border: 1.5px dashed #3f3f46 !important;
  border-radius: 12px !important;
  padding: .75rem !important;
  transition: border-color .2s !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: #6366f1 !important;
}

/* ── Progress bar ──────────────────────────────────────────────────────────── */
[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
  border-radius: 99px !important;
}

/* ── Spinner ───────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: #6366f1 !important; }

/* ── Selectbox ─────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div {
  background: #18181b !important;
  border: 1px solid #3f3f46 !important;
  border-radius: 8px !important;
}

/* ── Alert boxes ───────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  border-left-width: 3px !important;
}

/* ── Slider ────────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] [data-baseweb="slider-track"] {
  background: #3f3f46 !important;
}

/* ── Dataframe ─────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Radio buttons ─────────────────────────────────────────────────────────── */
[data-testid="stRadio"] label { font-size: 13px !important; color: #d4d4d8 !important; }

/* ── Sidebar nav label ─────────────────────────────────────────────────────── */
.sb-nav-label {
  font-size: 10px; font-weight: 600; letter-spacing: .08em;
  color: #52525b; text-transform: uppercase; padding: .5rem .25rem .25rem;
}

/* ── Doc card ──────────────────────────────────────────────────────────────── */
.doc-card {
  background: #18181b; border: 1px solid #27272a; border-radius: 10px;
  padding: .875rem 1rem; margin-bottom: .5rem;
  transition: border-color .15s;
}
.doc-card:hover { border-color: #3f3f46; }
.doc-name  { font-size: 14px; font-weight: 600; color: #fafafa; }
.doc-meta  { font-size: 12px; color: #71717a; margin-top: 2px; }
.doc-desc  { font-size: 12px; color: #a1a1aa; margin-top: 4px; line-height: 1.5; }

/* ── Grade badge ───────────────────────────────────────────────────────────── */
.grade-s { color: #a78bfa; font-size: 48px; font-weight: 800; }
.grade-a { color: #22c55e; font-size: 48px; font-weight: 800; }
.grade-b { color: #3b82f6; font-size: 48px; font-weight: 800; }
.grade-c { color: #f59e0b; font-size: 48px; font-weight: 800; }
.grade-d { color: #ef4444; font-size: 48px; font-weight: 800; }

/* ── Flip card ─────────────────────────────────────────────────────────────── */
.flip-card {
  background: #18181b; border: 1px solid #27272a; border-radius: 14px;
  padding: 2rem 1.5rem; min-height: 160px; text-align: center;
}
.flip-q  { font-size: 18px; font-weight: 600; color: #d4d4d8; margin-bottom: 1rem; }
.flip-a  { font-size: 16px; color: #a1a1aa; }
.flip-hint { font-size: 12px; color: #52525b; margin-top: .75rem; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method: str, path: str, timeout: int = TIMEOUT_LONG, **kwargs):
    url = f"{BACKEND_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
        if resp.status_code == 200:
            return resp.json(), None
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return None, f"HTTP {resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, "Backend not reachable. Try refreshing the page."
    except requests.exceptions.Timeout:
        return None, "Request timed out — the LLM is taking too long. Try again."
    except Exception as exc:
        return None, str(exc)


def _get(path: str, timeout: int = TIMEOUT_SHORT, **kwargs):
    return _api("GET",  path, timeout=timeout, **kwargs)


def _post(path: str, timeout: int = TIMEOUT_LONG, **kwargs):
    return _api("POST", path, timeout=timeout, **kwargs)


# ── Session-state helper ──────────────────────────────────────────────────────
def _ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def _load_documents():
    if "documents_loaded" not in st.session_state:
        data, err = _get("/api/documents", timeout=15)
        if err:
            st.session_state["documents"] = []
        else:
            st.session_state["documents"] = data or []
        st.session_state["documents_loaded"] = True


def _active_doc_id() -> str | None:
    doc = st.session_state.get("active_doc")
    return doc["doc_id"] if doc else None


def _invalidate_docs():
    for k in ("documents_loaded", "documents", "active_doc"):
        st.session_state.pop(k, None)


def sidebar():
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown("""
<div class="sb-logo">
  <div class="sb-logo-icon">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
         xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3L2 9l10 6 10-6-10-6z" stroke="white" stroke-width="1.8"
            stroke-linejoin="round"/>
      <path d="M2 17l10 6 10-6" stroke="white" stroke-width="1.8"
            stroke-linejoin="round"/>
      <path d="M2 13l10 6 10-6" stroke="white" stroke-width="1.8"
            stroke-linejoin="round"/>
    </svg>
  </div>
  <span class="sb-logo-text">StudyBuddy</span>
  <span class="sb-logo-badge">AI</span>
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="sb-nav-label">System</div>', unsafe_allow_html=True)

        # ── Backend status ─────────────────────────────────────────────────
        with st.expander("Backend Status", expanded=False):
            if st.button("Check health", key="health_btn"):
                data, err = _get("/health", timeout=10)
                if err:
                    st.error(err, icon=None)
                else:
                    ok = data.get("status") == "ok"
                    cls = "status-ok" if ok else "status-warn"
                    lbl = "Operational" if ok else "Degraded"
                    st.markdown(f'<span class="{cls}">&#9679; {lbl}</span>',
                                unsafe_allow_html=True)
                    st.markdown(f"""
<div style="font-size:12px;color:#71717a;line-height:1.8;margin-top:.5rem">
  Provider &nbsp;<span style="color:#a1a1aa">{data.get('provider','?')}</span><br>
  Model &nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#a1a1aa">{data.get('model','?')}</span><br>
  Docs &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#a1a1aa">{data.get('indexed_documents',0)}</span><br>
  Vectors &nbsp;<span style="color:#a1a1aa">{data.get('faiss_vectors',0)}</span>
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="sb-nav-label" style="margin-top:.75rem">Context</div>',
                    unsafe_allow_html=True)

        # ── Document selector ──────────────────────────────────────────────
        _load_documents()
        docs: list[dict] = st.session_state.get("documents", [])
        if not docs:
            st.markdown("""
<div style="font-size:12px;color:#52525b;padding:.5rem .25rem;line-height:1.6">
  No documents indexed yet.<br>Upload one in the <b style="color:#71717a">Upload</b> tab.
</div>""", unsafe_allow_html=True)
        else:
            names = [d["filename"] for d in docs]
            idx   = st.selectbox(
                "Active document",
                range(len(names)),
                format_func=lambda i: names[i],
                key="active_doc_idx",
                label_visibility="collapsed",
            )
            st.session_state["active_doc"] = docs[idx]
            active = docs[idx]
            st.markdown(f"""
<div style="font-size:11px;color:#52525b;line-height:1.7;padding:.25rem .25rem 0">
  {active.get('chunks','?')} chunks &nbsp;·&nbsp;
  {active.get('pages','?')} pages &nbsp;·&nbsp;
  {active.get('parser_used','?')}
</div>""", unsafe_allow_html=True)

        # ── Footer ─────────────────────────────────────────────────────────
        st.markdown("""
<div style="position:fixed;bottom:1.25rem;font-size:11px;color:#3f3f46;line-height:1.6">
  Streamlit Cloud &nbsp;·&nbsp; FastAPI subprocess<br>
  <span style="color:#27272a">localhost:8000</span>
</div>""", unsafe_allow_html=True)


# ── Heading helper ────────────────────────────────────────────────────────────
def _heading(title: str, sub: str) -> None:
    st.markdown(f'<p class="sb-heading">{title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sb-sub">{sub}</p>',     unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Upload
# ─────────────────────────────────────────────────────────────────────────────
def tab_upload():
    _heading("Upload Documents",
             "Upload your syllabus, notes, or any study material. Up to 200 MB per file.")

    uploaded = st.file_uploader(
        "Choose file(s)",
        type=["pdf","txt","md","doc","docx","ppt","pptx","xls","xlsx",
              "png","jpg","jpeg","webp","bin"],
        accept_multiple_files=True,
        help="PDF · TXT · MD · DOCX · PPT · PPTX · XLSX · PNG · JPG · WEBP — max 200 MB",
    )

    if uploaded and st.button("Upload & Index", type="primary"):
        for f in uploaded:
            with st.spinner(f"Indexing {f.name} …"):
                data, err = _api(
                    "POST", "/api/upload", timeout=300,
                    files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")},
                )
            if err:
                st.error(f"{f.name}: {err}")
            else:
                st.success(
                    f"{data['filename']} — "
                    f"{data['chunks']} chunks · {data['pages']} pages · "
                    f"{data['parser_used']}"
                )
                if data.get("description"):
                    st.info(data['description'])
        _invalidate_docs()
        st.rerun()

    st.divider()
    st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;'
                'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">'
                'Indexed Documents</p>', unsafe_allow_html=True)
    _load_documents()
    docs: list[dict] = st.session_state.get("documents", [])

    if not docs:
        st.markdown("""
<div style="background:#18181b;border:1px dashed #27272a;border-radius:10px;
     padding:1.5rem;text-align:center;color:#52525b;font-size:13px">
  No documents yet. Upload one above.
</div>""", unsafe_allow_html=True)
        return

    for doc in docs:
        col1, col2 = st.columns([6, 1])
        with col1:
            with st.expander(doc['filename'], expanded=False):
                if doc.get("description"):
                    st.markdown(f'<p style="font-size:13px;color:#a1a1aa">{doc["description"]}</p>',
                                unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Chunks",  doc.get("chunks", "?"))
                c2.metric("Pages",   doc.get("pages",  "?"))
                c3.metric("Tokens",  doc.get("total_tokens", "?"))
                c4.metric("Parser",  doc.get("parser_used", "?"))
        with col2:
            if st.button("Delete", key=f"del_{doc['doc_id']}"):
                _, err = _api("DELETE", f"/api/documents/{doc['doc_id']}", timeout=15)
                if err:
                    st.error(err)
                else:
                    st.success(f"Deleted")
                    _invalidate_docs()
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: ELI10 Explain
# ─────────────────────────────────────────────────────────────────────────────
def tab_explain():
    _heading("ELI10 — Explain Like I'm 10",
             "Simplified, analogy-driven explanations of any concept from your document.")

    topic = st.text_input("Topic or concept",
                          placeholder="e.g. Photosynthesis, Newton's Laws, Supply & Demand")
    level = st.selectbox("Depth", ["eli5", "beginner", "intermediate"],
                         index=1,
                         format_func=lambda x: {
                             "eli5":         "Very Simple (ELI5)",
                             "beginner":     "Beginner",
                             "intermediate": "Intermediate",
                         }[x])

    if st.button("Generate Explanation", type="primary") and topic.strip():
        with st.spinner("Generating explanation …"):
            data, err = _post("/api/explain", json={
                "topic":  topic.strip(),
                "doc_id": _active_doc_id(),
                "level":  level,
            })
        if err:
            st.error(err)
        else:
            st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:12px;padding:1.5rem;margin:.75rem 0">
  <p style="font-size:13px;font-weight:600;color:#6366f1;margin-bottom:.5rem;
     text-transform:uppercase;letter-spacing:.06em">Explanation</p>
  <p style="font-size:15px;color:#d4d4d8;line-height:1.7">{data["explanation"]}</p>
</div>""", unsafe_allow_html=True)
            if data.get("analogy"):
                st.markdown(f"""
<div style="background:#1c1917;border:1px solid #27272a;border-left:3px solid #f59e0b;
     border-radius:10px;padding:1rem 1.25rem;margin:.5rem 0">
  <p style="font-size:12px;font-weight:600;color:#f59e0b;margin-bottom:.35rem">Analogy</p>
  <p style="font-size:14px;color:#d4d4d8">{data['analogy']}</p>
</div>""", unsafe_allow_html=True)
            if data.get("key_points"):
                pts_html = "".join(
                    f'<li style="color:#d4d4d8;font-size:14px;margin-bottom:.4rem">{p}</li>'
                    for p in data["key_points"]
                )
                st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;padding:1rem 1.25rem;margin:.5rem 0">
  <p style="font-size:12px;font-weight:600;color:#22c55e;margin-bottom:.5rem;
     text-transform:uppercase;letter-spacing:.06em">Key Points</p>
  <ul style="margin:0;padding-left:1.25rem">{pts_html}</ul>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Ask AI (RAG Q&A)
# ─────────────────────────────────────────────────────────────────────────────
def tab_ask():
    _heading("Ask AI — RAG Q&A",
             "Ask anything about your document. Answers include source citations.")

    _ss("ask_history", [])

    mode = st.radio("Answer mode", ["standard", "eli5"], horizontal=True,
                    format_func=lambda x: "📚 Standard" if x == "standard" else "🧒 ELI5")

    for msg in st.session_state["ask_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(
                            f'<span class="src-chip">'
                            f'{src["filename"]} &nbsp;p.{src["page"]}'
                            f'</span> <span style="font-size:12px;color:#71717a">'
                            f'{src.get("snippet","")[:100]}…</span>',
                            unsafe_allow_html=True,
                        )
            if msg.get("follow_ups"):
                st.markdown('<p style="font-size:12px;color:#52525b;margin:.5rem 0 .25rem">Suggested follow-ups</p>',
                            unsafe_allow_html=True)
                for fq in msg["follow_ups"]:
                    if st.button(fq, key=f"fq_{hash(fq)}"):
                        st.session_state["_ask_prefill"] = fq
                        st.rerun()

    question = st.chat_input("Ask a question …")
    if st.session_state.get("_ask_prefill"):
        question = st.session_state.pop("_ask_prefill")

    if question:
        st.session_state["ask_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking …"):
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["ask_history"][:-1]
                ]
                data, err = _post("/api/ask", json={
                    "question": question,
                    "doc_id":   _active_doc_id(),
                    "mode":     mode,
                    "k":        5,
                    "conversation_history": history[-6:],
                })
            if err:
                st.error(err)
                st.session_state["ask_history"].pop()
            else:
                answer     = data["answer"]
                sources    = data.get("sources", [])
                follow_ups = data.get("follow_up_questions", [])
                st.markdown(answer)
                if sources:
                        with st.expander("Sources", expanded=False):
                            for src in sources:
                                st.markdown(
                                    f'<span class="src-chip">'
                                    f'{src["filename"]} &nbsp;p.{src["page"]}'
                                    f'</span> <span style="font-size:12px;color:#71717a">'
                                    f'{src.get("snippet","")[:100]}…</span>',
                                    unsafe_allow_html=True,
                                )
                    if follow_ups:
                        st.markdown('<p style="font-size:12px;color:#52525b;margin:.5rem 0 .25rem">Suggested follow-ups</p>',
                                    unsafe_allow_html=True)
                        cols = st.columns(min(len(follow_ups), 3))
                        for i, fq in enumerate(follow_ups[:3]):
                            with cols[i]:
                                if st.button(fq, key=f"afq_{i}_{hash(fq)}"):
                                    st.session_state["_ask_prefill"] = fq
                                    st.rerun()
                st.session_state["ask_history"].append({
                    "role":       "assistant",
                    "content":    answer,
                    "sources":    sources,
                    "follow_ups": follow_ups,
                })

    if st.session_state["ask_history"] and st.button("🗑️ Clear conversation"):
        st.session_state["ask_history"] = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Quiz
# ─────────────────────────────────────────────────────────────────────────────
def tab_quiz():
    _heading("Quiz", "Generate a timed multiple-choice quiz from your document.")

    _ss("quiz_data",     None)
    _ss("quiz_answers",  {})
    _ss("quiz_result",   None)
    _ss("quiz_start_ts", None)

    # Generate form
    if st.session_state["quiz_data"] is None and st.session_state["quiz_result"] is None:
        with st.form("quiz_form"):
            topic      = st.text_input("Topic (optional)", placeholder="Leave blank to use document")
            num_q      = st.slider("Questions", 3, 15, 5)
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"])
            submitted  = st.form_submit_button("🎯 Generate Quiz", type="primary")

        if submitted:
            with st.spinner("Generating questions …"):
                data, err = _post("/api/generate-quiz", json={
                    "doc_id":        _active_doc_id(),
                    "topic":         topic.strip() or None,
                    "num_questions": num_q,
                    "difficulty":    difficulty,
                })
            if err:
                st.error(err)
            else:
                st.session_state.update({
                    "quiz_data":     data,
                    "quiz_answers":  {},
                    "quiz_result":   None,
                    "quiz_start_ts": time.time(),
                })
                st.rerun()
        return

    # Show result
    if st.session_state["quiz_result"] is not None:
        res   = st.session_state["quiz_result"]
        grade = res.get("grade", "?")
        pct   = res.get("percentage", 0)
        icon  = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "😬"}.get(grade, "📊")

        st.markdown(f"## {icon} Grade: **{grade}** — {pct:.0f}%")
        c1, c2, c3 = st.columns(3)
        c1.metric("Score",  f"{res['score']} / {res['total']}")
        c2.metric("Time",   f"{res.get('time_taken',0):.0f}s")
        c3.metric("Grade",  grade)

        if res.get("weak_topics"):
            st.warning("📉 Weak topics: " + ", ".join(res["weak_topics"]))
        if res.get("strong_topics"):
            st.success("📈 Strong topics: " + ", ".join(res["strong_topics"]))
        if res.get("recommendations"):
            st.info("💡 " + " · ".join(res["recommendations"]))

        with st.expander("Detailed Review", expanded=True):
            for d in res.get("details", []):
                correct = d["is_correct"]
                color   = "#22c55e" if correct else "#ef4444"
                label   = "Correct" if correct else "Incorrect"
                st.markdown(
                    f'<p style="font-size:14px;font-weight:600;color:{color}'
                    f';margin-bottom:.25rem">[{label}] {d["question"]}</p>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Your answer: {d['user_index']} · Correct: {d['correct_index']}")
                if d.get("explanation"):
                    st.markdown(
                        f'<p style="font-size:13px;color:#a1a1aa;'
                        f'margin:.25rem 0 .75rem">{d["explanation"]}</p>',
                        unsafe_allow_html=True,
                    )
                st.divider()

        if st.button("New Quiz"):
            st.session_state.update({"quiz_data": None, "quiz_answers": {}, "quiz_result": None})
            st.rerun()
        return

    # Active quiz
    quiz      = st.session_state["quiz_data"]
    questions = quiz.get("questions", [])
    answers   = st.session_state["quiz_answers"]

    st.markdown(f"**Topic:** {quiz.get('topic','Mixed')} · **Difficulty:** {quiz.get('difficulty','?')}")
    st.progress(len(answers) / len(questions) if questions else 0,
                text=f"{len(answers)} / {len(questions)} answered")

    for i, q in enumerate(questions):
        with st.container(border=True):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            st.caption(f"🏷️ {q.get('topic_tag','')} · {q.get('difficulty','')}")
            opts   = q.get("options", [])
            chosen = st.radio("Choose:", range(len(opts)),
                              format_func=lambda j, opts=opts: opts[j],
                              key=f"q_{q['id']}", index=None)
            if chosen is not None:
                answers[q["id"]] = chosen
                st.session_state["quiz_answers"] = answers

    all_answered = len(answers) == len(questions)
    if st.button("✅ Submit Quiz", type="primary", disabled=not all_answered):
        elapsed = time.time() - (st.session_state["quiz_start_ts"] or time.time())
        with st.spinner("Grading …"):
            data, err = _post("/quiz/submit", json={
                "quiz_id":    quiz["quiz_id"],
                "answers":    answers,
                "time_taken": int(elapsed),
            })
        if err:
            st.error(err)
        else:
            st.session_state["quiz_result"] = data
            st.rerun()

    if st.button("Discard Quiz"):
        st.session_state.update({"quiz_data": None, "quiz_answers": {}})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Revision Planner
# ─────────────────────────────────────────────────────────────────────────────
def tab_planner():
    _heading("Revision Planner",
             "Personalised day-by-day study schedule generated from your exam date.")

    _ss("plan_data", None)

    if st.session_state["plan_data"] is None:
        with st.form("planner_form"):
            exam_date   = st.date_input("Exam date")
            daily_hours = st.slider("Daily study hours", 0.5, 8.0, 2.0, step=0.5)
            syllabus    = st.text_area("Syllabus / topics (optional)", height=100,
                                       placeholder="Chapter 1: Kinematics\nChapter 2: Dynamics…")
            submitted   = st.form_submit_button("Generate Plan", type="primary")

        if submitted:
            with st.spinner("Building revision plan …"):
                data, err = _post("/api/generate-plan", json={
                    "exam_date":     exam_date.isoformat(),
                    "daily_hours":   daily_hours,
                    "syllabus_text": syllabus.strip() or None,
                    "doc_id":        _active_doc_id(),
                })
            if err:
                st.error(err)
            else:
                st.session_state["plan_data"] = data
                st.rerun()
        return

    resp  = st.session_state["plan_data"]
    stats = resp.get("stats", {})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days to exam",  stats.get("days_to_exam", "?"))
    c2.metric("Study days",    stats.get("study_days",   "?"))
    c3.metric("Total hours",   f"{stats.get('total_study_mins',0)//60}h")
    c4.metric("Topics",        stats.get("topics_covered","?"))

    if resp.get("summary"):
        st.info(resp["summary"])
    if resp.get("tips"):
        with st.expander("Study Tips", expanded=False):
            for tip in resp["tips"]:
                st.markdown(f"- {tip}")

    st.divider()
    st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;'
                'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">'
                'Day-by-Day Schedule</p>', unsafe_allow_html=True)
    SESS_COLOR = {"concept": "#6366f1", "quiz": "#f59e0b", "buffer": "#3b82f6", "rest": "#52525b"}
    SESS_LABEL = {"concept": "Study", "quiz": "Quiz", "buffer": "Buffer", "rest": "Rest"}
    PRIO_COLOR = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}

    for task in resp.get("plan", []):
        stype   = task.get("session_type", "")
        sc      = SESS_COLOR.get(stype, "#71717a")
        sl      = SESS_LABEL.get(stype, stype.capitalize())
        pc      = PRIO_COLOR.get(task.get("priority",""), "#52525b")
        day_lbl = task.get('day_label', task.get('date',''))
        label   = (f'<span style="background:{sc}22;color:{sc};border:1px solid {sc}44;'
                   f'border-radius:4px;font-size:10px;font-weight:600;padding:1px 7px;'
                   f'margin-right:6px">{sl}</span>'
                   f'<b>{day_lbl}</b> &nbsp;'
                   f'<span style="color:#71717a">{task.get("topic","")}</span>')
        with st.expander(f"{sl} · {day_lbl} · {task.get('topic','')}", expanded=False):
            st.markdown(label, unsafe_allow_html=True)
            if task.get("subtopics"):
                st.markdown(
                    '<p style="font-size:12px;color:#a1a1aa;margin:.5rem 0 .25rem">Subtopics</p>'
                    + ", ".join(f'<span style="color:#d4d4d8">{s}</span>'
                                for s in task["subtopics"]),
                    unsafe_allow_html=True,
                )
            cols = st.columns(3)
            cols[0].metric("Duration", f"{task.get('duration_mins',0)} min")
            cols[1].metric("Technique", task.get('technique','—'))
            cols[2].metric("Priority",  task.get('priority','—'))
            if task.get("notes"):
                st.caption(task["notes"])

    if st.button("New Plan"):
        st.session_state["plan_data"] = None
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Flashcards
# ─────────────────────────────────────────────────────────────────────────────
def tab_flashcards():
    _heading("Flashcards", "AI-generated flip cards for spaced-repetition practice.")

    _ss("fc_cards",   None)
    _ss("fc_index",   0)
    _ss("fc_flipped", False)

    if st.session_state["fc_cards"] is None:
        with st.form("fc_form"):
            topic  = st.text_input("Topic (optional)")
            num    = st.slider("Number of cards", 3, 20, 8)
            submit = st.form_submit_button("Generate Cards", type="primary")

        if submit:
            with st.spinner("Generating flashcards …"):
                data, err = _post("/api/flashcards/generate", json={
                    "doc_id": _active_doc_id(),
                    "topic":  topic.strip() or None,
                    "count":  num,
                })
            if err:
                st.error(err)
            else:
                cards = data.get("cards", data.get("flashcards", []))
                if cards:
                    st.session_state.update({"fc_cards": cards, "fc_index": 0, "fc_flipped": False})
                    st.rerun()
                else:
                    st.warning("No cards returned.")
        return

    cards   = st.session_state["fc_cards"]
    idx     = st.session_state["fc_index"]
    flipped = st.session_state["fc_flipped"]
    card    = cards[idx]
    front   = card.get("front", card.get("question", ""))
    back    = card.get("back",  card.get("answer",   ""))

    st.progress((idx + 1) / len(cards), text=f"Card {idx+1} / {len(cards)}")
    st.markdown(f"""
<div class="flip-card">
  <p class="flip-q">{front}</p>
  {'<p class="flip-a">' + back + '</p>' if flipped
   else '<p class="flip-hint">Click Flip to reveal the answer</p>'}
</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Prev",    disabled=idx == 0):
        st.session_state.update({"fc_index": idx-1, "fc_flipped": False}); st.rerun()
    if c2.button("Flip"):
        st.session_state["fc_flipped"] = not flipped; st.rerun()
    if c3.button("Next",    disabled=idx >= len(cards)-1):
        st.session_state.update({"fc_index": idx+1, "fc_flipped": False}); st.rerun()
    if c4.button("Shuffle"):
        random.shuffle(cards)
        st.session_state.update({"fc_cards": cards, "fc_index": 0, "fc_flipped": False}); st.rerun()

    if st.button("New Deck"):
        st.session_state.update({"fc_cards": None, "fc_index": 0, "fc_flipped": False})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Feynman Mode
# ─────────────────────────────────────────────────────────────────────────────
def tab_feynman():
    _heading("Feynman Technique",
             "Explain a concept in your own words — the AI scores your understanding and surfaces gaps.")

    with st.form("feynman_form"):
        concept     = st.text_input("Concept to explain", placeholder="e.g. Photosynthesis")
        explanation = st.text_area("Your explanation", height=200,
                                   placeholder="Explain the concept as if teaching a 10-year-old …")
        submitted   = st.form_submit_button("Evaluate", type="primary")

    if submitted and concept.strip() and explanation.strip():
        with st.spinner("Evaluating your explanation …"):
            data, err = _post("/api/feynman/evaluate", json={
                "concept":     concept.strip(),
                "explanation": explanation.strip(),
                "doc_id":      _active_doc_id(),
            })
        if err:
            st.error(err)
            return

        score  = data.get("score", 0)
        grade  = data.get("grade", "?")
        gcls   = {"S":"grade-s","A":"grade-a","B":"grade-b","C":"grade-c","D":"grade-d"}.get(grade,"grade-b")
        gcolor = {"S":"#a78bfa","A":"#22c55e","B":"#3b82f6","C":"#f59e0b","D":"#ef4444"}.get(grade,"#6366f1")

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem">'
            f'<span class="{gcls}">{grade}</span>'
            f'<div><p style="font-size:24px;font-weight:700;color:#fafafa;margin:0">'
            f'{score}/100</p>'
            f'<p style="font-size:13px;color:#71717a;margin:0">Feynman Score</p></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.progress(score / 100)

        col1, col2 = st.columns(2)
        with col1:
            if data.get("strengths"):
                s_html = "".join(
                    f'<li style="color:#d4d4d8;font-size:13px;margin-bottom:.3rem">{s}</li>'
                    for s in data["strengths"]
                )
                st.markdown(
                    f'<div style="background:#18181b;border:1px solid #27272a;'
                    f'border-left:3px solid #22c55e;border-radius:10px;padding:1rem 1.25rem">'
                    f'<p style="font-size:11px;font-weight:600;color:#22c55e;'
                    f'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">Strengths</p>'
                    f'<ul style="margin:0;padding-left:1.1rem">{s_html}</ul></div>',
                    unsafe_allow_html=True,
                )
        with col2:
            if data.get("gaps"):
                g_html = "".join(
                    f'<li style="color:#d4d4d8;font-size:13px;margin-bottom:.3rem">{g}</li>'
                    for g in data["gaps"]
                )
                st.markdown(
                    f'<div style="background:#18181b;border:1px solid #27272a;'
                    f'border-left:3px solid #ef4444;border-radius:10px;padding:1rem 1.25rem">'
                    f'<p style="font-size:11px;font-weight:600;color:#ef4444;'
                    f'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">Gaps to Fill</p>'
                    f'<ul style="margin:0;padding-left:1.1rem">{g_html}</ul></div>',
                    unsafe_allow_html=True,
                )

        if data.get("coaching_tip"):
            st.markdown(
                f'<div style="background:#1c1917;border:1px solid #27272a;'
                f'border-left:3px solid #f59e0b;border-radius:10px;'
                f'padding:.875rem 1.25rem;margin-top:.75rem">'
                f'<p style="font-size:11px;font-weight:600;color:#f59e0b;'
                f'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.35rem">Coaching Tip</p>'
                f'<p style="font-size:14px;color:#d4d4d8">{data["coaching_tip"]}</p></div>',
                unsafe_allow_html=True,
            )

        if data.get("qa_pairs"):
            with st.expander("Q&A Pairs to study", expanded=False):
                for pair in data["qa_pairs"]:
                    st.markdown(
                        f'<p style="font-size:13px;font-weight:600;color:#d4d4d8">Q: {pair["question"]}</p>'
                        f'<p style="font-size:13px;color:#a1a1aa;margin-bottom:.75rem">A: {pair["answer"]}</p>',
                        unsafe_allow_html=True,
                    )
                    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Cheat Sheet
# ─────────────────────────────────────────────────────────────────────────────
def tab_cheatsheet():
    _heading("Cheat Sheet", "One-page key-concept summary of your document.")

    doc_id = _active_doc_id()
    if not doc_id:
        st.warning("⚠️ Upload and select a document first.")
        return

    topic = st.text_input("Focus topic (optional)", placeholder="e.g. Formulas, Key Definitions")

    if st.button("Generate Cheat Sheet", type="primary"):
        with st.spinner("Generating cheat sheet …"):
            data, err = _post("/api/cheatsheet", json={
                "doc_id": doc_id,
                "topic":  topic.strip() or None,
            })
        if err:
            st.error(err)
        else:
            content = data.get("content", data.get("cheatsheet", str(data)))
            st.markdown("---")
            st.markdown(content)
            st.download_button(
                "⬇️ Download (.md)",
                data=content,
                file_name="cheatsheet.md",
                mime="text/markdown",
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Progress Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def tab_progress():
    _heading("Progress Dashboard", "Your study analytics — quizzes, Feynman sessions, streaks.")

    with st.spinner("Loading progress …"):
        data, err = _get("/api/progress/summary", timeout=30)

    if err:
        st.error(err)
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Quizzes",       data.get("total_quizzes", 0))
    c2.metric("Avg Score",           f"{data.get('avg_score_pct', 0):.0f}%")
    c3.metric("Best Score",          f"{data.get('best_score_pct', 0):.0f}%")
    c4.metric("Streak (days)",       data.get("current_streak_days", 0))
    st.metric("Questions Answered",  data.get("total_questions_answered", 0))

    if data.get("score_history"):
        st.divider()
        st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;'
                    'text-transform:uppercase;letter-spacing:.06em">Score History</p>',
                    unsafe_allow_html=True)
        rows = [
            {"Date": h["date"], "Topic": h["topic"],
             "Score": f"{h['score']}/{h['total']}", "Grade": h["grade"]}
            for h in data["score_history"][-20:]
        ]
        st.dataframe(rows, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if data.get("weak_topics"):
            st.markdown('<p style="font-size:12px;font-weight:600;color:#ef4444;'
                        'text-transform:uppercase;letter-spacing:.06em;margin:.75rem 0 .5rem">'
                        'Weak Topics</p>', unsafe_allow_html=True)
            for t in data["weak_topics"]:
                st.progress(t["avg_pct"] / 100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")
    with col2:
        if data.get("strong_topics"):
            st.markdown('<p style="font-size:12px;font-weight:600;color:#22c55e;'
                        'text-transform:uppercase;letter-spacing:.06em;margin:.75rem 0 .5rem">'
                        'Strong Topics</p>', unsafe_allow_html=True)
            for t in data["strong_topics"]:
                st.progress(t["avg_pct"] / 100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")

    if data.get("feynman_history"):
        st.divider()
        st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;'
                    'text-transform:uppercase;letter-spacing:.06em">Feynman History</p>',
                    unsafe_allow_html=True)
        rows = [
            {"Date": h["date"], "Concept": h["concept"],
             "Score": h["score"], "Grade": h["grade"]}
            for h in data["feynman_history"][-10:]
        ]
        st.dataframe(rows, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Step 1: ensure backend is running (blocks until healthy or 90s) ───────
    if not _ensure_backend():
        st.stop()

    # ── Step 2: sidebar ───────────────────────────────────────────────────────
    sidebar()

    # ── Step 3: tabs ──────────────────────────────────────────────────────────
    tabs = st.tabs([
        "Upload",
        "ELI10",
        "Ask AI",
        "Quiz",
        "Planner",
        "Flashcards",
        "Feynman",
        "Cheat Sheet",
        "Progress",
    ])

    with tabs[0]: tab_upload()
    with tabs[1]: tab_explain()
    with tabs[2]: tab_ask()
    with tabs[3]: tab_quiz()
    with tabs[4]: tab_planner()
    with tabs[5]: tab_flashcards()
    with tabs[6]: tab_feynman()
    with tabs[7]: tab_cheatsheet()
    with tabs[8]: tab_progress()


if __name__ == "__main__":
    main()
