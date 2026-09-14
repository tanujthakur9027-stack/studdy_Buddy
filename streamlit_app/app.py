"""
StudyBuddy — Streamlit App (self-contained, no Render needed)
=============================================================
Launches the FastAPI backend (uvicorn) as a subprocess on localhost:8000
the first time a Streamlit worker starts.

Deploy to Streamlit Cloud:
  - Entry point : streamlit_app/app.py
  - Secrets     : GROQ_API_KEY, SECRET_KEY, ADMIN_SEED_EMAIL, ADMIN_SEED_PASSWORD
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
_HERE      = Path(__file__).parent
_REPO_ROOT = _HERE.parent
_BACKEND   = _REPO_ROOT / "backend"
_DATA      = _REPO_ROOT / "data"

BACKEND_URL   = "http://localhost:8000"
TIMEOUT_SHORT = 60
TIMEOUT_LONG  = 180


# ─────────────────────────────────────────────────────────────────────────────
# Backend subprocess launcher
# ─────────────────────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    """Read from st.secrets first, then os.environ."""
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)


def _start_backend() -> None:
    if st.session_state.get("_backend_started"):
        return

    for sub in ["chroma_db", "uploads", "faiss_indexes",
                "uploads/assignments", "uploads/submissions",
                "uploads/notes", "uploads/photos"]:
        (_DATA / sub).mkdir(parents=True, exist_ok=True)

    env = {
        **os.environ,
        "GROQ_API_KEY":            _get_secret("GROQ_API_KEY"),
        "GROQ_MODEL":              _get_secret("GROQ_MODEL", "groq/compound-mini"),
        "OPENAI_API_KEY":          _get_secret("OPENAI_API_KEY", ""),
        "DATABASE_URL":            f"sqlite+aiosqlite:///{_DATA}/studybuddy.db",
        "CHROMA_PERSIST_DIR":      str(_DATA / "chroma_db"),
        "UPLOAD_DIR":              str(_DATA / "uploads"),
        "FAISS_INDEX_DIR":         str(_DATA / "faiss_indexes"),
        "MAX_FILE_SIZE_MB":        "200",
        "CORS_ORIGINS":            "*",
        "RATE_LIMIT_PER_MINUTE":   "60",
        # Auth
        "SECRET_KEY":              _get_secret("SECRET_KEY", "dev-secret-change-in-prod"),
        "ACCESS_TOKEN_EXPIRE_MINUTES": "1440",
        "ADMIN_SEED_EMAIL":        _get_secret("ADMIN_SEED_EMAIL", "admin@studybuddy.com"),
        "ADMIN_SEED_PASSWORD":     _get_secret("ADMIN_SEED_PASSWORD", "Admin@StudyBuddy2024"),
        # Email (optional)
        "SMTP_HOST":               _get_secret("SMTP_HOST", ""),
        "SMTP_PORT":               _get_secret("SMTP_PORT", "587"),
        "SMTP_USER":               _get_secret("SMTP_USER", ""),
        "SMTP_PASS":               _get_secret("SMTP_PASS", ""),
        "SMTP_FROM":               _get_secret("SMTP_FROM", "noreply@studybuddy.com"),
        "APP_BASE_URL":            _get_secret("APP_BASE_URL", "https://studybuddy.streamlit.app"),
        # File limits
        "ASSIGNMENT_FILE_MAX_MB":  "50",
        "NOTE_FILE_MAX_MB":        "50",
        "PROFILE_PHOTO_MAX_MB":    "5",
        # Timetable
        "PERIOD_DURATION_MINUTES": "45",
        "LUNCH_DURATION_MINUTES":  "45",
        "PYTHONPATH":              str(_BACKEND),
    }

    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000",
         "--workers", "1", "--log-level", "warning"],
        cwd=str(_BACKEND), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    st.session_state["_backend_started"] = True


def _wait_for_backend(timeout: int = 90) -> bool:
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
    _start_backend()
    if st.session_state.get("_backend_healthy"):
        try:
            requests.get(f"{BACKEND_URL}/health", timeout=3)
            return True
        except Exception:
            for k in ("_backend_healthy", "_backend_started"):
                st.session_state.pop(k, None)
            return False
    with st.spinner("⏳ Starting backend… first load takes ~20 s"):
        ready = _wait_for_backend()
    if ready:
        st.session_state["_backend_healthy"] = True
        # Auto-seed admin on first boot
        _seed_admin_once()
    else:
        st.error("❌ Backend failed to start. Check that dependencies are installed.")
    return ready


def _seed_admin_once():
    """Call seed_admin endpoint (idempotent — safe to call every startup)."""
    if st.session_state.get("_admin_seeded"):
        return
    try:
        admin_email = _get_secret("ADMIN_SEED_EMAIL", "admin@studybuddy.com")
        admin_pass  = _get_secret("ADMIN_SEED_PASSWORD", "Admin@StudyBuddy2024")
        # Try login first — if it works, admin already exists
        r = requests.post(f"{BACKEND_URL}/api/auth/login",
                          json={"email": admin_email, "password": admin_pass}, timeout=10)
        if r.status_code == 200:
            st.session_state["_admin_seeded"] = True
            return
        # Otherwise register as admin via seed script logic
        # We just try the login — if 401, try the seed endpoint isn't exposed
        # The backend seeds admin automatically via seed_admin.py
        # On Streamlit Cloud we run it as a subprocess
        subprocess.run(
            [sys.executable, "seed_admin.py"],
            cwd=str(_BACKEND),
            env={**os.environ,
                 "DATABASE_URL": f"sqlite+aiosqlite:///{_DATA}/studybuddy.db",
                 "SECRET_KEY": _get_secret("SECRET_KEY", "dev-secret"),
                 "ADMIN_SEED_EMAIL": admin_email,
                 "ADMIN_SEED_PASSWORD": admin_pass,
                 "PYTHONPATH": str(_BACKEND)},
            timeout=30, capture_output=True,
        )
        st.session_state["_admin_seeded"] = True
    except Exception:
        st.session_state["_admin_seeded"] = True  # don't retry


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif !important; }
.stApp { background: #09090b; }
.block-container { max-width: 980px !important; padding: 2rem 2rem 4rem !important; }
[data-testid="stSidebar"] { background: #09090b !important; border-right: 1px solid #27272a !important; }
[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #27272a !important; gap: 0 !important; padding: 0 !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { background: transparent !important; border: none !important; border-bottom: 2px solid transparent !important; border-radius: 0 !important; color: #71717a !important; font-size: 13px !important; font-weight: 500 !important; padding: 10px 14px !important; margin-bottom: -1px !important; white-space: nowrap !important; }
[data-testid="stTabs"] [aria-selected="true"] { color: #fafafa !important; border-bottom-color: #6366f1 !important; }
div[data-testid="stForm"] { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 1.5rem !important; }
[data-testid="stExpander"] { background: #18181b !important; border: 1px solid #27272a !important; border-radius: 10px !important; }
[data-testid="baseButton-primary"] { background: #6366f1 !important; border: none !important; border-radius: 8px !important; color: #fff !important; font-size: 13px !important; font-weight: 600 !important; }
[data-testid="baseButton-primary"]:hover { background: #4f46e5 !important; }
[data-testid="baseButton-secondary"] { background: #27272a !important; border: 1px solid #3f3f46 !important; border-radius: 8px !important; color: #d4d4d8 !important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { background: #18181b !important; border: 1px solid #3f3f46 !important; border-radius: 8px !important; color: #fafafa !important; }
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 2px rgba(99,102,241,.2) !important; }
[data-testid="stChatMessage"] { background: #18181b !important; border: 1px solid #27272a !important; border-radius: 12px !important; padding: 1rem 1.25rem !important; margin-bottom: .75rem !important; }
[data-testid="stMetric"] { background: #18181b; border: 1px solid #27272a; border-radius: 10px; padding: .75rem 1rem; }
[data-testid="stMetricLabel"] { color: #71717a !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #fafafa !important; font-size: 22px !important; font-weight: 700 !important; }
hr { border-color: #27272a !important; margin: 1.5rem 0 !important; }
[data-testid="stFileUploader"] { background: #18181b !important; border: 1.5px dashed #3f3f46 !important; border-radius: 12px !important; }
[data-baseweb="select"] > div { background: #18181b !important; border: 1px solid #3f3f46 !important; border-radius: 8px !important; }
.sb-heading { font-size: 22px !important; font-weight: 700 !important; color: #fafafa !important; margin-bottom: .25rem !important; letter-spacing: -.3px; }
.sb-sub { font-size: 13px !important; color: #71717a !important; margin-bottom: 1.5rem !important; }
.src-chip { display:inline-flex;align-items:center;gap:4px;background:#27272a;border:1px solid #3f3f46;border-radius:6px;padding:3px 10px;font-size:11px;color:#a1a1aa;margin:2px; }
.grade-s{color:#a78bfa;font-size:48px;font-weight:800}.grade-a{color:#22c55e;font-size:48px;font-weight:800}.grade-b{color:#3b82f6;font-size:48px;font-weight:800}.grade-c{color:#f59e0b;font-size:48px;font-weight:800}.grade-d{color:#ef4444;font-size:48px;font-weight:800}
.flip-card{background:#18181b;border:1px solid #27272a;border-radius:14px;padding:2rem 1.5rem;min-height:160px;text-align:center}
.flip-q{font-size:18px;font-weight:600;color:#d4d4d8;margin-bottom:1rem}.flip-a{font-size:16px;color:#a1a1aa}.flip-hint{font-size:12px;color:#52525b;margin-top:.75rem}
.sb-nav-label{font-size:10px;font-weight:600;letter-spacing:.08em;color:#52525b;text-transform:uppercase;padding:.5rem .25rem .25rem}
.card{background:#18181b;border:1px solid #27272a;border-radius:10px;padding:1rem 1.25rem;margin-bottom:.5rem}
.badge-green{background:#14532d;color:#4ade80;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px}
.badge-yellow{background:#422006;color:#fbbf24;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px}
.badge-blue{background:#1e3a5f;color:#60a5fa;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px}
.badge-red{background:#450a0a;color:#f87171;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px}
.badge-purple{background:#2e1065;color:#c4b5fd;font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px}
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method: str, path: str, timeout: int = TIMEOUT_LONG, **kwargs):
    url = f"{BACKEND_URL}{path}"
    # Inject auth token if logged in
    headers = kwargs.pop("headers", {})
    token = st.session_state.get("_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, url, timeout=timeout, headers=headers, **kwargs)
        if resp.status_code in (200, 201):
            try:
                return resp.json(), None
            except Exception:
                return resp.text, None
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return None, f"HTTP {resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, "Backend not reachable. Try refreshing."
    except requests.exceptions.Timeout:
        return None, "Request timed out. Try again."
    except Exception as exc:
        return None, str(exc)


def _get(path, timeout=TIMEOUT_SHORT, **kw):  return _api("GET",    path, timeout, **kw)
def _post(path, timeout=TIMEOUT_LONG, **kw):  return _api("POST",   path, timeout, **kw)
def _patch(path, timeout=TIMEOUT_SHORT, **kw):return _api("PATCH",  path, timeout, **kw)
def _delete(path, timeout=TIMEOUT_SHORT, **kw):return _api("DELETE", path, timeout, **kw)

def _ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

def _heading(title: str, sub: str):
    st.markdown(f'<p class="sb-heading">{title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sb-sub">{sub}</p>', unsafe_allow_html=True)

def _badge(text, color="blue"):
    return f'<span class="badge-{color}">{text}</span>'

def _card(content: str):
    st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Auth state helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))

def _current_user() -> dict:
    return st.session_state.get("_user", {})

def _is_admin() -> bool:
    return _current_user().get("role") == "admin"


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def _load_documents():
    if "documents_loaded" not in st.session_state:
        data, err = _get("/api/documents", timeout=15)
        st.session_state["documents"] = data or [] if not err else []
        st.session_state["documents_loaded"] = True

def _active_doc_id():
    doc = st.session_state.get("active_doc")
    return doc["doc_id"] if doc else None

def _invalidate_docs():
    for k in ("documents_loaded", "documents", "active_doc"):
        st.session_state.pop(k, None)


def sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
<div style="display:flex;align-items:center;gap:10px;padding:.75rem 0 1.25rem">
  <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
       display:flex;align-items:center;justify-content:center;flex-shrink:0">
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10 2L2 7l8 5 8-5-8-5z" stroke="rgba(255,255,255,0.95)" stroke-width="1.6" stroke-linejoin="round"/>
      <path d="M2 13l8 5 8-5" stroke="rgba(255,255,255,0.95)" stroke-width="1.6" stroke-linejoin="round"/>
      <path d="M2 10l8 5 8-5" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linejoin="round"/>
    </svg>
  </div>
  <span style="font-size:16px;font-weight:700;color:#fafafa">StudyBuddy</span>
  <span style="font-size:10px;font-weight:600;color:#a78bfa;background:rgba(167,139,250,.12);
       border:1px solid rgba(167,139,250,.3);border-radius:4px;padding:1px 6px">AI</span>
</div>""", unsafe_allow_html=True)

        # User info
        if _is_logged_in():
            user = _current_user()
            role_color = "#f59e0b" if _is_admin() else "#6366f1"
            role_label = "Admin" if _is_admin() else "Student"
            st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:8px;padding:.6rem .875rem;margin-bottom:.75rem">
  <p style="margin:0;font-size:13px;font-weight:600;color:#fafafa">{user.get('full_name','User')}</p>
  <p style="margin:2px 0 0;font-size:11px;color:#71717a">{user.get('email','')}</p>
  <span style="font-size:10px;font-weight:600;color:{role_color};background:{role_color}22;
       border-radius:4px;padding:1px 6px;margin-top:4px;display:inline-block">{role_label}</span>
</div>""", unsafe_allow_html=True)

            if st.button("🚪 Logout", key="sidebar_logout"):
                _post("/api/auth/logout")
                for k in ["_token", "_user", "_admin_seeded"]:
                    st.session_state.pop(k, None)
                st.rerun()

        # Document context (for AI tools)
        st.markdown('<div class="sb-nav-label" style="margin-top:.5rem">AI Context</div>', unsafe_allow_html=True)
        _load_documents()
        docs = st.session_state.get("documents", [])
        if not docs:
            st.markdown('<div style="font-size:12px;color:#52525b;padding:.5rem .25rem">No documents. Upload in the AI Tools tab.</div>', unsafe_allow_html=True)
        else:
            names = [d["filename"] for d in docs]
            idx = st.selectbox("Active document", range(len(names)),
                               format_func=lambda i: names[i],
                               key="active_doc_idx", label_visibility="collapsed")
            st.session_state["active_doc"] = docs[idx]

        # Backend health
        st.markdown('<div class="sb-nav-label" style="margin-top:.75rem">System</div>', unsafe_allow_html=True)
        with st.expander("Backend Status", expanded=False):
            if st.button("Check health", key="health_btn"):
                data, err = _get("/health", timeout=10)
                if err:
                    st.error(err)
                else:
                    ok = data.get("status") == "ok"
                    st.markdown(
                        f'<span style="color:{"#22c55e" if ok else "#f59e0b"};font-size:12px;font-weight:600">'
                        f'{"● Operational" if ok else "⚠ Degraded"}</span>',
                        unsafe_allow_html=True)
                    st.caption(f"Provider: {data.get('provider','?')} · Model: {data.get('model','?')}")

        st.markdown("""
<div style="position:fixed;bottom:1.25rem;font-size:11px;color:#3f3f46">
  Streamlit Cloud · FastAPI subprocess
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Login / Register
# ─────────────────────────────────────────────────────────────────────────────
def tab_auth():
    if _is_logged_in():
        user = _current_user()
        st.success(f"✅ Logged in as **{user.get('full_name')}** ({user.get('role')})")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;color:#a1a1aa">Email</p>
  <p style="margin:4px 0 0;font-size:15px;color:#fafafa;font-weight:600">{user.get('email')}</p>
</div>""", unsafe_allow_html=True)
        with col2:
            if st.button("Logout", type="primary"):
                _post("/api/auth/logout")
                for k in ["_token", "_user"]:
                    st.session_state.pop(k, None)
                st.rerun()
        return

    _heading("Welcome to StudyBuddy", "Login to access your dashboard, or register a new student account.")

    login_tab, reg_tab = st.tabs(["🔑 Login", "📝 Register Student"])

    with login_tab:
        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submit   = st.form_submit_button("Login", type="primary")
        if submit:
            if not email or not password:
                st.error("Email and password are required.")
            else:
                data, err = _post("/api/auth/login",
                                  json={"email": email.strip(), "password": password})
                if err:
                    st.error(f"Login failed: {err}")
                else:
                    st.session_state["_token"] = data["access_token"]
                    st.session_state["_user"]  = data["user"]
                    st.success(f"Welcome back, {data['user']['full_name']}!")
                    st.rerun()

        st.markdown("""
<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;padding:1rem 1.25rem;margin-top:1rem">
  <p style="margin:0;font-size:12px;font-weight:600;color:#f59e0b">Admin / Demo Login</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">
    Email: <span style="color:#d4d4d8">admin@studybuddy.com</span><br>
    Password: <span style="color:#d4d4d8">Admin@StudyBuddy2024</span>
  </p>
</div>""", unsafe_allow_html=True)

    with reg_tab:
        with st.form("register_form"):
            st.markdown("**Personal Information**")
            c1, c2 = st.columns(2)
            full_name   = c1.text_input("Full Name *")
            student_id  = c2.text_input("Student ID / Roll Number *")
            email       = st.text_input("Email *")
            c3, c4 = st.columns(2)
            password    = c3.text_input("Password * (min 8 chars)", type="password")
            phone       = c4.text_input("Phone Number")
            st.markdown("**Academic Details**")
            c5, c6 = st.columns(2)
            course      = c5.text_input("Course / Degree", placeholder="B.Tech")
            branch      = c6.text_input("Branch / Stream", placeholder="CSE")
            c7, c8, c9 = st.columns(3)
            semester    = c7.text_input("Semester", placeholder="3rd")
            section     = c8.text_input("Section", placeholder="A")
            academic_yr = c9.text_input("Academic Year", placeholder="2024-25")
            dob         = st.text_input("Date of Birth (optional)", placeholder="YYYY-MM-DD")
            submit      = st.form_submit_button("Create Account", type="primary")

        if submit:
            if not all([full_name, student_id, email, password]):
                st.error("Full Name, Student ID, Email and Password are required.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                data, err = _post("/api/auth/register", json={
                    "full_name": full_name.strip(),
                    "student_id": student_id.strip(),
                    "email": email.strip().lower(),
                    "password": password,
                    "phone": phone.strip(),
                    "course": course.strip(),
                    "branch": branch.strip(),
                    "semester": semester.strip(),
                    "section": section.strip(),
                    "academic_year": academic_yr.strip(),
                    "dob": dob.strip() or None,
                })
                if err:
                    st.error(f"Registration failed: {err}")
                else:
                    st.session_state["_token"] = data["access_token"]
                    st.session_state["_user"]  = data["user"]
                    st.success(f"Account created! Welcome, {data['user']['full_name']}!")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def tab_dashboard():
    if not _is_logged_in():
        st.warning("Please login first → go to the **Login** tab.")
        return

    user = _current_user()
    _heading(f"Dashboard", f"Welcome back, {user.get('full_name', 'User')} 👋")

    if _is_admin():
        # Admin stats
        count_data, _ = _get("/api/admin/students/count", timeout=10)
        assignments_data, _ = _get("/api/admin/assignments", timeout=10)
        announcements_data, _ = _get("/api/admin/announcements", timeout=10)

        total_students = count_data.get("total", 0) if count_data else 0
        active_students = count_data.get("active", 0) if count_data else 0
        total_assignments = len(assignments_data) if assignments_data else 0
        published = sum(1 for a in (assignments_data or []) if a.get("is_published"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Students", total_students)
        c2.metric("Active Students", active_students)
        c3.metric("Total Assignments", total_assignments)
        c4.metric("Published", published)

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Recent Announcements</p>', unsafe_allow_html=True)
            for ann in (announcements_data or [])[:5]:
                st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{ann['title']}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">{ann['content'][:100]}...</p>
</div>""", unsafe_allow_html=True)
        with col2:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Recent Assignments</p>', unsafe_allow_html=True)
            for a in (assignments_data or [])[:5]:
                badge = "green" if a.get("is_published") else "yellow"
                label = "Published" if a.get("is_published") else "Draft"
                st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a['title']} {_badge(label, badge)}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">Due: {a.get('due_date','?')} · Max: {a.get('max_marks','?')} marks</p>
</div>""", unsafe_allow_html=True)
    else:
        # Student dashboard
        assignments_data, _ = _get("/api/assignments", timeout=10)
        notif_data, _ = _get("/api/notifications/unread-count", timeout=10)
        timetable_data, _ = _get("/api/timetable/today", timeout=10)
        marks_data, _ = _get("/api/marks/summary", timeout=10)

        pending = [a for a in (assignments_data or []) if a.get("submission_status") == "pending"]
        unread  = notif_data.get("count", 0) if notif_data else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Assignments", len(assignments_data) if assignments_data else 0)
        c2.metric("Pending", len(pending))
        c3.metric("Notifications 🔔", unread)
        c4.metric("Overall %", f"{marks_data.get('overall_percentage', 0):.0f}%" if marks_data else "—")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Today\'s Schedule</p>', unsafe_allow_html=True)
            if timetable_data and timetable_data.get("periods"):
                for p in timetable_data["periods"]:
                    st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">P{p['period_number']} — {p.get('subject','Free')}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">{p.get('start_time','?')} – {p.get('end_time','?')} {('· ' + p['room']) if p.get('room') else ''}</p>
</div>""", unsafe_allow_html=True)
            else:
                st.info("No timetable published yet.")
        with col2:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Pending Assignments</p>', unsafe_allow_html=True)
            if pending:
                for a in pending[:5]:
                    st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a['title']}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">Due: {a.get('due_date','?')} {a.get('due_time','')}</p>
</div>""", unsafe_allow_html=True)
            else:
                st.success("🎉 No pending assignments!")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Assignments (Student view + submission)
# ─────────────────────────────────────────────────────────────────────────────
def tab_assignments():
    if not _is_logged_in():
        st.warning("Please login first.")
        return

    _heading("Assignments", "View and submit your assignments.")

    data, err = _get("/api/assignments", timeout=15)
    if err:
        st.error(err); return
    assignments = data or []

    filter_status = st.selectbox("Filter", ["All", "Pending", "Submitted", "Evaluated"],
                                 label_visibility="collapsed")

    filtered = assignments
    if filter_status == "Pending":
        filtered = [a for a in assignments if a.get("submission_status") == "pending"]
    elif filter_status == "Submitted":
        filtered = [a for a in assignments if a.get("submission_status") == "submitted"]
    elif filter_status == "Evaluated":
        filtered = [a for a in assignments if a.get("submission_status") == "evaluated"]

    if not filtered:
        st.info("No assignments found.")
        return

    for a in filtered:
        status = a.get("submission_status", "pending")
        badge_color = {"pending": "yellow", "submitted": "blue", "evaluated": "green"}.get(status, "yellow")
        with st.expander(f"📋 {a['title']}  {_badge(status.title(), badge_color)}", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("Max Marks", a.get("max_marks", "?"))
            c2.metric("Due Date", a.get("due_date", "?"))
            c3.metric("Due Time", a.get("due_time", "?"))

            if a.get("description"):
                st.markdown(f'<p style="font-size:14px;color:#d4d4d8;margin:.5rem 0">{a["description"]}</p>', unsafe_allow_html=True)
            if a.get("instructions"):
                st.markdown(f'<p style="font-size:13px;color:#a1a1aa"><b>Instructions:</b> {a["instructions"]}</p>', unsafe_allow_html=True)
            if a.get("file_url"):
                st.markdown(f'[📎 Download Assignment File]({BACKEND_URL}{a["file_url"]})')

            # Show existing submission
            if a.get("my_submission"):
                sub = a["my_submission"]
                st.markdown("---")
                st.markdown(f'<p style="font-size:13px;font-weight:600;color:#22c55e">✅ Submitted on {sub.get("submitted_at","?")[:10]}</p>', unsafe_allow_html=True)
                if sub.get("is_evaluated"):
                    st.markdown(f'<p style="font-size:15px;font-weight:700;color:#fafafa">Marks: {sub.get("marks_obtained","?")} / {a.get("max_marks","?")}</p>', unsafe_allow_html=True)
                    if sub.get("feedback"):
                        st.info(f"💬 Teacher feedback: {sub['feedback']}")
            elif status == "pending":
                st.markdown("---")
                st.markdown('<p style="font-size:13px;font-weight:600;color:#f59e0b">📤 Submit Your Work</p>', unsafe_allow_html=True)
                with st.form(f"submit_{a['id']}"):
                    notes = st.text_area("Notes / Comments (optional)", height=80)
                    file  = st.file_uploader("Attach file (optional)",
                                              type=["pdf","docx","doc","pptx","zip","png","jpg"])
                    sub_btn = st.form_submit_button("Submit Assignment", type="primary")
                if sub_btn:
                    files = {"file": (file.name, file.getvalue(), file.type)} if file else None
                    data2, err2 = _api("POST", f"/api/assignments/{a['id']}/submit",
                                       data={"notes": notes} if notes else {},
                                       files=files if files else None)
                    if err2:
                        st.error(err2)
                    else:
                        st.success("Submitted successfully!")
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Marks (Student view)
# ─────────────────────────────────────────────────────────────────────────────
def tab_marks():
    if not _is_logged_in():
        st.warning("Please login first.")
        return

    _heading("My Marks", "View your published marks and grades by subject.")

    summary, err = _get("/api/marks/summary", timeout=15)
    if err:
        st.error(err); return
    if not summary:
        st.info("No marks published yet.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall", f"{summary.get('overall_obtained', 0)} / {summary.get('overall_max', 0)}")
    c2.metric("Percentage", f"{summary.get('overall_percentage', 0):.1f}%")
    c3.metric("Grade", summary.get("overall_grade", "—"))

    st.divider()
    for subj in summary.get("subjects", []):
        with st.expander(f"📚 {subj.get('subject_name', 'Unknown')}  —  {subj.get('percentage', 0):.0f}%  {_badge(subj.get('grade','?'), 'purple')}", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Obtained", subj.get("total_obtained", 0))
            c2.metric("Maximum", subj.get("total_max", 0))
            c3.metric("Percentage", f"{subj.get('percentage', 0):.1f}%")
            c4.metric("Grade", subj.get("grade", "—"))

            marks_data, _ = _get(f"/api/marks/subject/{subj['subject_id']}", timeout=10)
            if marks_data and marks_data.get("categories"):
                st.markdown('<p style="font-size:12px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin:.75rem 0 .5rem">Assessment Breakdown</p>', unsafe_allow_html=True)
                for cat in marks_data["categories"]:
                    pct = cat.get("percentage", 0)
                    bar_color = "#22c55e" if pct >= 75 else "#f59e0b" if pct >= 50 else "#ef4444"
                    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;margin:.35rem 0"><span style="font-size:13px;color:#d4d4d8">{cat.get("category_name","?")}</span><span style="font-size:13px;font-weight:600;color:{bar_color}">{cat.get("obtained_marks","?")} / {cat.get("max_marks","?")} ({pct:.0f}%)</span></div>', unsafe_allow_html=True)
                    st.progress(min(pct / 100, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Timetable (Student view)
# ─────────────────────────────────────────────────────────────────────────────
def tab_timetable():
    if not _is_logged_in():
        st.warning("Please login first.")
        return

    _heading("Class Timetable", "Your weekly class schedule with subjects and timings.")

    data, err = _get("/api/timetable", timeout=15)
    if err:
        st.error(err); return
    if not data or not data.get("schedule"):
        st.info("No timetable published for your class yet.")
        if not data or data.get("message"):
            st.caption(data.get("message", "") if data else "Ask your teacher to assign you to a class first.")
        return

    schedule = data["schedule"]
    lunch_start = data.get("lunch_start", "")
    lunch_end   = data.get("lunch_end", "")

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    day_names = [d["day"] for d in schedule if d.get("periods")]
    selected_day = st.selectbox("Select Day", day_names, key="tt_day")

    day_data = next((d for d in schedule if d["day"] == selected_day), None)
    if not day_data:
        st.info("No classes on this day."); return

    periods = day_data.get("periods", [])
    lunch_after = data.get("lunch_after_period", 4)

    st.markdown(f'<p style="font-size:13px;color:#71717a;margin-bottom:1rem">📅 {selected_day} · {data.get("name","Timetable")}</p>', unsafe_allow_html=True)

    for p in periods:
        if p["period_number"] == lunch_after + 1 and lunch_start:
            st.markdown(f"""
<div style="background:#422006;border:1px solid #92400e;border-radius:10px;padding:.75rem 1rem;margin:.5rem 0;text-align:center">
  <span style="color:#fbbf24;font-weight:600;font-size:14px">🍽️ Lunch Break · {lunch_start} – {lunch_end}</span>
</div>""", unsafe_allow_html=True)

        subj = p.get("subject") or "Free Period"
        color = "#6366f1" if p.get("subject") else "#3f3f46"
        st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-left:3px solid {color};
     border-radius:10px;padding:.875rem 1.25rem;margin:.4rem 0;display:flex;justify-content:space-between;align-items:center">
  <div>
    <span style="font-size:11px;color:#52525b;font-weight:600">Period {p['period_number']}</span>
    <p style="margin:2px 0 0;font-size:15px;font-weight:600;color:#fafafa">{subj}</p>
    {f'<p style="margin:2px 0 0;font-size:12px;color:#71717a">🏫 {p["room"]}</p>' if p.get('room') else ''}
  </div>
  <span style="font-size:13px;color:#71717a">{p.get('start_time','?')} – {p.get('end_time','?')}</span>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Notifications
# ─────────────────────────────────────────────────────────────────────────────
def tab_notifications():
    if not _is_logged_in():
        st.warning("Please login first.")
        return

    _heading("Notifications", "Your alerts and updates from Study Buddy.")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("✓ Mark all read"):
            _, err = _patch("/api/notifications/read-all")
            if err:
                st.error(err)
            else:
                st.success("All marked as read!")
                st.rerun()

    data, err = _get("/api/notifications?page_size=50", timeout=15)
    if err:
        st.error(err); return
    notifications = data or []

    if not notifications:
        st.info("No notifications yet.")
        return

    TYPE_ICON = {"assignment": "📋", "marks": "📊", "timetable": "📅",
                 "announcement": "📢", "submission": "✅", "note": "📁", "general": "🔔"}

    for n in notifications:
        is_read = n.get("is_read", False)
        bg = "#18181b" if is_read else "#1e1b4b"
        border = "#27272a" if is_read else "#6366f1"
        icon = TYPE_ICON.get(n.get("notif_type", "general"), "🔔")
        created = n.get("created_at", "")[:16].replace("T", " ")

        col1, col2 = st.columns([10, 1])
        with col1:
            st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;padding:.875rem 1.25rem;margin:.4rem 0">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{icon} {n.get('title','')}</p>
    <span style="font-size:11px;color:#52525b;white-space:nowrap;margin-left:8px">{created}</span>
  </div>
  <p style="margin:4px 0 0;font-size:13px;color:#a1a1aa">{n.get('message','')}</p>
</div>""", unsafe_allow_html=True)
        with col2:
            if not is_read:
                if st.button("✓", key=f"notif_{n['id']}"):
                    _patch(f"/api/notifications/{n['id']}/read")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Notes (Student sharing)
# ─────────────────────────────────────────────────────────────────────────────
def tab_notes():
    if not _is_logged_in():
        st.warning("Please login first.")
        return

    _heading("Notes & Resources", "Share and discover study notes with classmates.")

    upload_tab, browse_tab = st.tabs(["📤 Upload Note", "📚 Browse Notes"])

    with upload_tab:
        with st.form("upload_note_form"):
            title       = st.text_input("Title *")
            description = st.text_area("Description", height=80)
            c1, c2     = st.columns(2)
            subject     = c1.text_input("Subject")
            semester    = c2.text_input("Semester")
            c3, c4     = st.columns(2)
            course      = c3.text_input("Course")
            visibility  = c4.selectbox("Visibility", ["connections", "class", "public"])
            tags        = st.text_input("Tags (comma-separated)", placeholder="maths, calculus, notes")
            file        = st.file_uploader("File *", type=["pdf","docx","doc","pptx","ppt","png","jpg","jpeg","txt"])
            submit      = st.form_submit_button("Upload Note", type="primary")

        if submit:
            if not title or not file:
                st.error("Title and file are required.")
            else:
                files_data = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
                form_data  = {"title": title, "description": description, "subject": subject,
                               "semester": semester, "course": course, "visibility": visibility, "tags": tags}
                _, err = _api("POST", "/api/notes", timeout=60,
                              data=form_data, files=files_data)
                if err:
                    st.error(err)
                else:
                    st.success("Note uploaded successfully!")
                    st.rerun()

    with browse_tab:
        search = st.text_input("Search notes", placeholder="Search by title, subject or tags…")
        data, err = _get(f"/api/notes?search={search}" if search else "/api/notes", timeout=15)
        if err:
            st.error(err); return
        notes = data or []

        if not notes:
            st.info("No notes found. Be the first to share!")
            return

        for n in notes:
            with st.expander(f"📄 {n.get('title','')}  —  {n.get('subject','')}  {_badge(n.get('visibility','?'), 'blue')}", expanded=False):
                c1, c2, c3 = st.columns(3)
                c1.metric("Semester", n.get("semester") or "—")
                c2.metric("Course", n.get("course") or "—")
                c3.metric("Shared by", n.get("uploader_name", "?"))
                if n.get("description"):
                    st.caption(n["description"])
                if n.get("tags"):
                    st.markdown(f'<p style="font-size:12px;color:#71717a">🏷️ {n["tags"]}</p>', unsafe_allow_html=True)

                col1, col2 = st.columns([3, 1])
                with col2:
                    st.markdown(f'<a href="{BACKEND_URL}/api/notes/{n["id"]}/download" target="_blank" style="display:inline-block;background:#6366f1;color:#fff;padding:6px 14px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none">⬇️ Download</a>', unsafe_allow_html=True)
                    user = _current_user()
                    if n.get("uploaded_by") == user.get("id"):
                        if st.button("🗑️ Delete", key=f"del_note_{n['id']}"):
                            _, err = _delete(f"/api/notes/{n['id']}")
                            if err:
                                st.error(err)
                            else:
                                st.success("Deleted"); st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Connections
# ─────────────────────────────────────────────────────────────────────────────
def tab_connections():
    if not _is_logged_in():
        st.warning("Please login first.")
        return

    _heading("Connections", "Connect with classmates to share notes and collaborate.")

    conn_tab, search_tab, req_tab = st.tabs(["👥 My Connections", "🔍 Find Students", "📨 Requests"])

    with conn_tab:
        data, err = _get("/api/connections", timeout=15)
        if err:
            st.error(err)
        else:
            connections = data or []
            if not connections:
                st.info("No connections yet. Search for classmates to connect!")
            for c in connections:
                peer = c.get("user", {})
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{peer.get('full_name','?')}</p>
  <p style="margin:3px 0 0;font-size:12px;color:#71717a">{peer.get('course','')} {peer.get('branch','')} · Sem {peer.get('semester','?')}</p>
</div>""", unsafe_allow_html=True)
                with col2:
                    if st.button("Remove", key=f"remove_{c['id']}"):
                        _, err = _delete(f"/api/connections/{c['id']}")
                        if err:
                            st.error(err)
                        else:
                            st.success("Removed"); st.rerun()

    with search_tab:
        search = st.text_input("Search by name, student ID, course or semester",
                               placeholder="e.g. Rahul, CS2024, CSE, 3rd")
        if search:
            data, err = _get(f"/api/connections/search?q={search}", timeout=15)
            if err:
                st.error(err)
            else:
                results = data or []
                if not results:
                    st.info("No students found.")
                for s in results:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{s.get('full_name','?')}</p>
  <p style="margin:3px 0 0;font-size:12px;color:#71717a">{s.get('course','')} · {s.get('branch','')} · Sem {s.get('semester','?')} · {s.get('section','?')}</p>
</div>""", unsafe_allow_html=True)
                    with col2:
                        conn_status = s.get("connection_status", "none")
                        if conn_status == "none":
                            if st.button("Connect", key=f"conn_{s['user_id']}"):
                                _, err = _post("/api/connections/request",
                                               json={"to_user_id": s["user_id"]})
                                if err:
                                    st.error(err)
                                else:
                                    st.success("Request sent!"); st.rerun()
                        elif conn_status == "pending":
                            st.markdown('<span style="color:#f59e0b;font-size:12px">⏳ Pending</span>', unsafe_allow_html=True)
                        elif conn_status == "connected":
                            st.markdown('<span style="color:#22c55e;font-size:12px">✅ Connected</span>', unsafe_allow_html=True)

    with req_tab:
        data, err = _get("/api/connections/requests/incoming", timeout=15)
        if err:
            st.error(err)
        else:
            requests_list = data or []
            if not requests_list:
                st.info("No pending connection requests.")
            for r in requests_list:
                sender = r.get("from_user", {})
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{sender.get('full_name','?')}</p>
  <p style="margin:3px 0 0;font-size:12px;color:#71717a">Wants to connect</p>
</div>""", unsafe_allow_html=True)
                with col2:
                    if st.button("✅ Accept", key=f"acc_{r['id']}"):
                        _, err = _patch(f"/api/connections/request/{r['id']}",
                                        json={"action": "accept"})
                        if err:
                            st.error(err)
                        else:
                            st.success("Accepted!"); st.rerun()
                with col3:
                    if st.button("❌ Reject", key=f"rej_{r['id']}"):
                        _, err = _patch(f"/api/connections/request/{r['id']}",
                                        json={"action": "reject"})
                        if err:
                            st.error(err)
                        else:
                            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Admin Panel
# ─────────────────────────────────────────────────────────────────────────────
def tab_admin():
    if not _is_logged_in():
        st.warning("Please login first.")
        return
    if not _is_admin():
        st.error("🔒 Admin access required.")
        return

    _heading("Admin Panel", "Manage students, classes, assignments, marks and timetable.")

    (students_tab, classes_tab, assignments_tab,
     submissions_tab, marks_tab, timetable_tab, announcements_tab) = st.tabs([
        "👨‍🎓 Students", "🏛️ Classes", "📋 Assignments",
        "✅ Submissions", "📊 Marks", "📅 Timetable", "📢 Announcements"
    ])

    # ── Students ──────────────────────────────────────────────────────────────
    with students_tab:
        st.markdown("### Registered Students")
        search = st.text_input("Search by name, email or student ID", key="admin_student_search")
        data, err = _get(f"/api/admin/students?search={search}" if search else "/api/admin/students", timeout=15)
        if err:
            st.error(err)
        else:
            students = data or []
            st.caption(f"{len(students)} student(s)")
            for s in students:
                with st.expander(f"{'🟢' if s.get('is_active') else '🔴'} {s.get('full_name','?')} — {s.get('student_id','?')}", expanded=False):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Email", s.get("email", "?"))
                    c2.metric("Course", s.get("course", "—") or "—")
                    c3.metric("Semester", s.get("semester", "—") or "—")
                    c4.metric("Section", s.get("section", "—") or "—")
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        btn_label = "Deactivate" if s.get("is_active") else "Activate"
                        btn_color = "secondary"
                        if st.button(btn_label, key=f"toggle_{s['id']}"):
                            _, err = _patch(f"/api/admin/students/{s['id']}/status",
                                            json={"is_active": not s.get("is_active")})
                            if err:
                                st.error(err)
                            else:
                                st.rerun()

    # ── Classes ───────────────────────────────────────────────────────────────
    with classes_tab:
        st.markdown("### Classes, Sections & Subjects")
        classes_data, _ = _get("/api/admin/classes", timeout=10)
        sections_data, _ = _get("/api/admin/sections", timeout=10)
        subjects_data, _ = _get("/api/admin/subjects", timeout=10)
        classes   = classes_data or []
        sections  = sections_data or []
        subjects  = subjects_data or []

        col1, col2, col3 = st.columns(3)
        with col1:
            with st.form("new_class"):
                st.markdown("**New Class**")
                cls_name   = st.text_input("Class Name", placeholder="B.Tech CSE Year 2")
                cls_course = st.text_input("Course", placeholder="B.Tech")
                if st.form_submit_button("Create Class", type="primary"):
                    if cls_name:
                        _, err = _post("/api/admin/classes", json={"name": cls_name, "course": cls_course})
                        if err: st.error(err)
                        else: st.success("Created!"); st.rerun()
        with col2:
            with st.form("new_section"):
                st.markdown("**New Section**")
                sec_cls  = st.selectbox("Class", options=[c["id"] for c in classes],
                                        format_func=lambda i: next((c["name"] for c in classes if c["id"]==i), i),
                                        key="sec_cls_sel")
                sec_name = st.text_input("Section Name", placeholder="A")
                if st.form_submit_button("Create Section", type="primary"):
                    if sec_name and sec_cls:
                        _, err = _post("/api/admin/sections", json={"name": sec_name, "class_id": sec_cls})
                        if err: st.error(err)
                        else: st.success("Created!"); st.rerun()
        with col3:
            with st.form("new_subject"):
                st.markdown("**New Subject**")
                sub_cls  = st.selectbox("Class", options=[c["id"] for c in classes],
                                        format_func=lambda i: next((c["name"] for c in classes if c["id"]==i), i),
                                        key="sub_cls_sel")
                sub_name = st.text_input("Subject Name", placeholder="Data Structures")
                sub_code = st.text_input("Code (optional)", placeholder="CS301")
                if st.form_submit_button("Create Subject", type="primary"):
                    if sub_name and sub_cls:
                        _, err = _post("/api/admin/subjects", json={"name": sub_name, "code": sub_code, "class_id": sub_cls})
                        if err: st.error(err)
                        else: st.success("Created!"); st.rerun()

        st.divider()
        for cls in classes:
            cls_sections = [s for s in sections if s["class_id"] == cls["id"]]
            cls_subjects  = [s for s in subjects  if s["class_id"] == cls["id"]]
            with st.expander(f"📁 {cls['name']} · {len(cls_sections)} sections · {len(cls_subjects)} subjects"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Sections**")
                    for sec in cls_sections:
                        col1, col2 = st.columns([3, 1])
                        col1.markdown(f"<span style='color:#d4d4d8'>{sec['name']}</span>", unsafe_allow_html=True)
                        if col2.button("Delete", key=f"delsec_{sec['id']}"):
                            _delete(f"/api/admin/sections/{sec['id']}"); st.rerun()
                with c2:
                    st.markdown("**Subjects**")
                    for sub in cls_subjects:
                        col1, col2 = st.columns([3, 1])
                        col1.markdown(f"<span style='color:#d4d4d8'>{sub['name']}</span><span style='color:#52525b;font-size:11px'> {sub.get('code','')}</span>", unsafe_allow_html=True)
                        if col2.button("Delete", key=f"delsub_{sub['id']}"):
                            _delete(f"/api/admin/subjects/{sub['id']}"); st.rerun()

    # ── Assignments ───────────────────────────────────────────────────────────
    with assignments_tab:
        st.markdown("### Manage Assignments")
        classes_data, _ = _get("/api/admin/classes", timeout=10)
        subjects_data, _ = _get("/api/admin/subjects", timeout=10)
        classes  = classes_data or []
        subjects = subjects_data or []

        with st.expander("➕ Create New Assignment", expanded=False):
            with st.form("create_assignment"):
                title    = st.text_input("Title *")
                c1, c2  = st.columns(2)
                cls_id  = c1.selectbox("Class *", [c["id"] for c in classes],
                                       format_func=lambda i: next((c["name"] for c in classes if c["id"]==i), i))
                sub_id  = c2.selectbox("Subject *", [s["id"] for s in subjects],
                                       format_func=lambda i: next((s["name"] for s in subjects if s["id"]==i), i))
                desc     = st.text_area("Description", height=80)
                instr    = st.text_area("Instructions", height=80)
                c3, c4, c5 = st.columns(3)
                due_date = c3.date_input("Due Date")
                due_time = c4.text_input("Due Time", value="23:59")
                max_marks = c5.number_input("Max Marks", value=100, min_value=1)
                file     = st.file_uploader("Attach file (optional)", type=["pdf","docx","pptx","zip"])
                submit   = st.form_submit_button("Create Assignment", type="primary")
            if submit and title and cls_id and sub_id:
                files_data = {"file": (file.name, file.getvalue(), file.type)} if file else None
                form_data  = {"title": title, "class_id": cls_id, "subject_id": sub_id,
                               "description": desc, "instructions": instr,
                               "due_date": str(due_date), "due_time": due_time,
                               "max_marks": str(max_marks)}
                _, err = _api("POST", "/api/admin/assignments", timeout=30,
                              data=form_data, files=files_data)
                if err: st.error(err)
                else: st.success("Assignment created!"); st.rerun()

        data, err = _get("/api/admin/assignments", timeout=15)
        if err: st.error(err)
        else:
            for a in (data or []):
                badge = "green" if a.get("is_published") else "yellow"
                label = "Published" if a.get("is_published") else "Draft"
                col1, col2, col3 = st.columns([5, 1, 1])
                with col1:
                    st.markdown(f"""
<div class="card">
  <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a['title']} {_badge(label,badge)}</p>
  <p style="margin:3px 0 0;font-size:12px;color:#71717a">Due: {a.get('due_date','?')} · Max: {a.get('max_marks','?')}</p>
</div>""", unsafe_allow_html=True)
                with col2:
                    if not a.get("is_published"):
                        if st.button("Publish", key=f"pub_{a['id']}"):
                            _, err = _post(f"/api/admin/assignments/{a['id']}/publish")
                            if err: st.error(err)
                            else: st.success("Published!"); st.rerun()
                with col3:
                    if st.button("Delete", key=f"del_a_{a['id']}"):
                        _delete(f"/api/admin/assignments/{a['id']}"); st.rerun()

    # ── Submissions ───────────────────────────────────────────────────────────
    with submissions_tab:
        st.markdown("### Assignment Submissions")
        assignments_data, _ = _get("/api/admin/assignments", timeout=10)
        assignment_list = assignments_data or []
        sel_asgn = st.selectbox("Select Assignment",
                                 ["All"] + [a["id"] for a in assignment_list],
                                 format_func=lambda i: "All Assignments" if i == "All" else
                                             next((a["title"] for a in assignment_list if a["id"]==i), i))

        params = f"?assignment_id={sel_asgn}" if sel_asgn != "All" else ""
        data, err = _get(f"/api/admin/submissions{params}", timeout=15)
        if err: st.error(err)
        else:
            subs = data or []
            st.caption(f"{len(subs)} submission(s)")
            for sub in subs:
                status_color = {"evaluated": "#22c55e", "submitted": "#6366f1", "late": "#f59e0b"}.get(sub.get("status",""), "#71717a")
                with st.expander(f"{'✅' if sub.get('is_evaluated') else '📤'} {sub.get('student_name','?')} — {sub.get('status','?').title()}", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Student", sub.get("student_name","?"))
                    c2.metric("Submitted", sub.get("submitted_at","?")[:10])
                    c3.metric("Marks", f"{sub.get('marks_obtained','—')}" if sub.get('is_evaluated') else "Not graded")

                    if sub.get("notes"):
                        st.caption(f"Notes: {sub['notes']}")
                    if sub.get("file_url"):
                        st.markdown(f'[📎 Download Submission]({BACKEND_URL}{sub["file_url"]})')
                    if sub.get("feedback"):
                        st.info(f"Feedback: {sub['feedback']}")

                    max_m = next((a["max_marks"] for a in assignment_list if a["id"]==sub.get("assignment_id")), 100)
                    with st.form(f"grade_{sub['id']}"):
                        g_marks   = st.number_input("Marks", min_value=0.0, max_value=float(max_m),
                                                     value=float(sub.get("marks_obtained") or 0), step=0.5)
                        g_feedback = st.text_area("Feedback", value=sub.get("feedback",""), height=60)
                        if st.form_submit_button("Save Grade", type="primary"):
                            _, err = _patch(f"/api/admin/submissions/{sub['id']}/grade",
                                            json={"marks_obtained": g_marks, "feedback": g_feedback})
                            if err: st.error(err)
                            else: st.success("Graded!"); st.rerun()

    # ── Marks ─────────────────────────────────────────────────────────────────
    with marks_tab:
        st.markdown("### Marks Management")
        subjects_data, _ = _get("/api/admin/subjects", timeout=10)
        subjects = subjects_data or []
        sel_sub = st.selectbox("Select Subject", [s["id"] for s in subjects],
                                format_func=lambda i: next((s["name"] for s in subjects if s["id"]==i), i),
                                key="marks_sub_sel")
        if sel_sub:
            cats_data, _ = _get(f"/api/admin/assessment-categories?subject_id={sel_sub}", timeout=10)
            cats = cats_data or []

            with st.expander("➕ Add Assessment Category"):
                with st.form("new_cat"):
                    c1, c2, c3 = st.columns(3)
                    cat_name    = c1.text_input("Name", placeholder="Mid-Term")
                    cat_max     = c2.number_input("Max Marks", value=50, min_value=1)
                    cat_weight  = c3.number_input("Weightage %", value=20, min_value=1, max_value=100)
                    if st.form_submit_button("Create", type="primary"):
                        _, err = _post("/api/admin/assessment-categories",
                                       json={"name": cat_name, "subject_id": sel_sub,
                                             "max_marks": cat_max, "weightage": cat_weight})
                        if err: st.error(err)
                        else: st.success("Created!"); st.rerun()

            if cats:
                sel_cat = st.selectbox("Select Category to Enter Marks",
                                        [c["id"] for c in cats],
                                        format_func=lambda i: next((f"{c['name']} (max:{c['max_marks']})" for c in cats if c["id"]==i), i))
                cat_obj = next((c for c in cats if c["id"] == sel_cat), None)

                students_data, _ = _get("/api/admin/students", timeout=10)
                students = students_data or []

                if students and cat_obj:
                    st.markdown(f'<p style="font-size:13px;color:#71717a">Entering marks for: <b style="color:#fafafa">{cat_obj["name"]}</b> (max: {cat_obj["max_marks"]})</p>', unsafe_allow_html=True)

                    report_data, _ = _get(f"/api/admin/marks/report?subject_id={sel_sub}", timeout=10)
                    report = report_data or []

                    with st.form("enter_marks_form"):
                        entries = []
                        for s in students:
                            existing = next((r for r in report if r.get("student_id")==s["id"]
                                             and r.get("category")==cat_obj["name"]), None)
                            col1, col2, col3 = st.columns([3, 2, 2])
                            col1.markdown(f'<p style="margin-top:.85rem;font-size:13px;color:#d4d4d8">{s["full_name"]}</p>', unsafe_allow_html=True)
                            marks_val = col2.number_input("", min_value=0.0, max_value=float(cat_obj["max_marks"]),
                                                          value=float(existing["obtained"]) if existing else 0.0,
                                                          step=0.5, key=f"m_{s['id']}")
                            remarks   = col3.text_input("", placeholder="Remarks", key=f"r_{s['id']}")
                            entries.append((s["id"], marks_val, remarks))

                        col1, col2 = st.columns(2)
                        save_btn    = col1.form_submit_button("💾 Save Marks", type="primary")
                        publish_btn = col2.form_submit_button("📢 Save & Publish")

                    if save_btn or publish_btn:
                        payload = [{"student_id": sid, "category_id": sel_cat,
                                    "obtained_marks": m, "remarks": r}
                                   for sid, m, r in entries]
                        _, err = _post("/api/admin/marks", json=payload)
                        if err:
                            st.error(err)
                        else:
                            if publish_btn:
                                _, err2 = _post("/api/admin/marks/publish",
                                                json={"category_id": sel_cat})
                                if err2: st.error(err2)
                                else: st.success("Marks saved & published! Students notified.")
                            else:
                                st.success("Marks saved.")
                            st.rerun()

    # ── Timetable ─────────────────────────────────────────────────────────────
    with timetable_tab:
        st.markdown("### Timetable Management")
        classes_data, _ = _get("/api/admin/classes", timeout=10)
        classes = classes_data or []

        with st.expander("➕ Create New Timetable"):
            with st.form("new_tt"):
                c1, c2 = st.columns(2)
                tt_cls  = c1.selectbox("Class *", [c["id"] for c in classes],
                                        format_func=lambda i: next((c["name"] for c in classes if c["id"]==i), i))
                tt_name = c2.text_input("Name", value="Timetable")
                c3, c4, c5 = st.columns(3)
                tt_start = c3.text_input("Start Time", value="09:00")
                tt_prd   = c4.number_input("Periods/Day", value=8, min_value=1, max_value=12)
                tt_lunch = c5.number_input("Lunch After Period", value=4, min_value=1)
                if st.form_submit_button("Create Timetable", type="primary"):
                    _, err = _post("/api/admin/timetables", json={
                        "class_id": tt_cls, "name": tt_name, "start_time": tt_start,
                        "periods_per_day": int(tt_prd), "lunch_after_period": int(tt_lunch)
                    })
                    if err: st.error(err)
                    else: st.success("Created!"); st.rerun()

        tt_data, err = _get("/api/admin/timetables", timeout=15)
        if err: st.error(err)
        else:
            subjects_data, _ = _get("/api/admin/subjects", timeout=10)
            subjects = subjects_data or []

            for tt in (tt_data or []):
                badge = "green" if tt.get("is_published") else "yellow"
                label = "Published" if tt.get("is_published") else "Draft"
                with st.expander(f"📅 {tt['name']} {_badge(label, badge)} — Start: {tt['start_time']} · {tt['periods_per_day']} periods"):
                    slots_data, _ = _get(f"/api/admin/timetables/{tt['id']}/slots", timeout=10)
                    slots = slots_data or []
                    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

                    # Quick slot adder
                    with st.form(f"add_slot_{tt['id']}"):
                        st.markdown("**Add / Update Slot**")
                        sc1, sc2, sc3, sc4 = st.columns(4)
                        s_day  = sc1.selectbox("Day", range(6), format_func=lambda i: DAYS[i],
                                               key=f"sd_{tt['id']}")
                        s_prd  = sc2.number_input("Period", min_value=1, max_value=tt["periods_per_day"],
                                                   key=f"sp_{tt['id']}")
                        s_sub  = sc3.selectbox("Subject", [""] + [s["id"] for s in subjects],
                                               format_func=lambda i: "Free" if not i else
                                               next((s["name"] for s in subjects if s["id"]==i), i),
                                               key=f"ss_{tt['id']}")
                        s_room = sc4.text_input("Room", key=f"sr_{tt['id']}")
                        if st.form_submit_button("Save Slot"):
                            existing_slot = next((s for s in slots
                                                  if s["day_of_week"]==s_day and s["period_number"]==s_prd), None)
                            payload = {"day_of_week": int(s_day), "period_number": int(s_prd),
                                       "subject_id": s_sub or None, "teacher_id": None, "room": s_room}
                            if existing_slot:
                                _, err = _patch(f"/api/admin/timetables/{tt['id']}/slots/{existing_slot['id']}",
                                                json=payload)
                            else:
                                _, err = _post(f"/api/admin/timetables/{tt['id']}/slots", json=payload)
                            if err: st.error(err)
                            else: st.success("Slot saved!"); st.rerun()

                    # Publish button
                    if not tt.get("is_published"):
                        if st.button(f"📢 Publish Timetable", key=f"pub_tt_{tt['id']}"):
                            _, err = _post(f"/api/admin/timetables/{tt['id']}/publish")
                            if err: st.error(err)
                            else: st.success("Published! Students notified."); st.rerun()

    # ── Announcements ─────────────────────────────────────────────────────────
    with announcements_tab:
        st.markdown("### Announcements")
        classes_data, _ = _get("/api/admin/classes", timeout=10)
        classes = classes_data or []

        with st.form("new_ann"):
            ann_title   = st.text_input("Title *")
            ann_content = st.text_area("Content *", height=120)
            ann_cls     = st.selectbox("Target",
                                       [""] + [c["id"] for c in classes],
                                       format_func=lambda i: "All Students (Broadcast)" if not i
                                       else next((c["name"] for c in classes if c["id"]==i), i))
            if st.form_submit_button("📢 Post Announcement", type="primary"):
                if ann_title and ann_content:
                    _, err = _post("/api/admin/announcements",
                                   json={"title": ann_title, "content": ann_content,
                                         "class_id": ann_cls or None, "section_id": None})
                    if err: st.error(err)
                    else: st.success("Posted! Students notified."); st.rerun()
                else:
                    st.error("Title and content are required.")

        data, err = _get("/api/admin/announcements", timeout=15)
        if err: st.error(err)
        else:
            for ann in (data or []):
                target = next((c["name"] for c in classes if c["id"]==ann.get("class_id")), "All Students")
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
<div class="card">
  <div style="display:flex;justify-content:space-between">
    <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{ann['title']}</p>
    <span style="font-size:11px;color:#52525b">{ann.get('created_at','')[:10]}</span>
  </div>
  <p style="margin:4px 0 0;font-size:13px;color:#a1a1aa">{ann['content'][:150]}{'...' if len(ann['content'])>150 else ''}</p>
  <p style="margin:4px 0 0;font-size:11px;color:#52525b">→ {target}</p>
</div>""", unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️", key=f"del_ann_{ann['id']}"):
                        _delete(f"/api/admin/announcements/{ann['id']}"); st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# AI Tools tabs (original 9 tabs — preserved exactly)
# ─────────────────────────────────────────────────────────────────────────────
def tab_upload():
    _heading("Upload Documents", "Upload your syllabus, notes, or study material. Up to 200 MB.")
    uploaded = st.file_uploader("Choose file(s)",
        type=["pdf","txt","md","doc","docx","ppt","pptx","xls","xlsx","png","jpg","jpeg","webp","bin"],
        accept_multiple_files=True)
    if uploaded and st.button("Upload & Index", type="primary"):
        for f in uploaded:
            with st.spinner(f"Indexing {f.name} …"):
                data, err = _api("POST", "/api/upload", timeout=300,
                                 files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")})
            if err: st.error(f"{f.name}: {err}")
            else:
                st.success(f"{data['filename']} — {data['chunks']} chunks · {data['pages']} pages · {data['parser_used']}")
                if data.get("description"): st.info(data['description'])
        _invalidate_docs(); st.rerun()

    st.divider()
    st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Indexed Documents</p>', unsafe_allow_html=True)
    _load_documents()
    docs = st.session_state.get("documents", [])
    if not docs:
        st.markdown('<div style="background:#18181b;border:1px dashed #27272a;border-radius:10px;padding:1.5rem;text-align:center;color:#52525b;font-size:13px">No documents yet. Upload one above.</div>', unsafe_allow_html=True)
        return
    for doc in docs:
        col1, col2 = st.columns([6, 1])
        with col1:
            with st.expander(doc['filename'], expanded=False):
                if doc.get("description"): st.markdown(f'<p style="font-size:13px;color:#a1a1aa">{doc["description"]}</p>', unsafe_allow_html=True)
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Chunks", doc.get("chunks","?")); c2.metric("Pages", doc.get("pages","?"))
                c3.metric("Tokens", doc.get("total_tokens","?")); c4.metric("Parser", doc.get("parser_used","?"))
        with col2:
            if st.button("Delete", key=f"del_{doc['doc_id']}"):
                _, err = _api("DELETE", f"/api/documents/{doc['doc_id']}", timeout=15)
                if err: st.error(err)
                else: st.success("Deleted"); _invalidate_docs(); st.rerun()


def tab_explain():
    _heading("ELI10 — Explain Like I'm 10", "Simplified explanations of any concept.")
    topic = st.text_input("Topic or concept", placeholder="e.g. Photosynthesis, Newton's Laws")
    level = st.selectbox("Depth", ["eli5","beginner","intermediate"],
                         format_func=lambda x: {"eli5":"Very Simple (ELI5)","beginner":"Beginner","intermediate":"Intermediate"}[x])
    if st.button("Generate Explanation", type="primary") and topic.strip():
        with st.spinner("Generating …"):
            data, err = _post("/api/explain", json={"topic":topic.strip(),"doc_id":_active_doc_id(),"level":level})
        if err: st.error(err)
        else:
            st.markdown(f'<div style="background:#18181b;border:1px solid #27272a;border-radius:12px;padding:1.5rem"><p style="font-size:15px;color:#d4d4d8;line-height:1.7">{data["explanation"]}</p></div>', unsafe_allow_html=True)
            if data.get("analogy"): st.info(f"💡 Analogy: {data['analogy']}")
            if data.get("key_points"):
                for pt in data["key_points"]: st.markdown(f"- {pt}")


def tab_ask():
    _heading("Ask AI — RAG Q&A", "Ask anything about your document.")
    _ss("ask_history", [])
    mode = st.radio("Mode", ["standard","eli5"], horizontal=True,
                    format_func=lambda x: "📚 Standard" if x=="standard" else "🧒 ELI5")
    for msg in st.session_state["ask_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.markdown(f'<span class="src-chip">{src["filename"]} p.{src["page"]}</span>', unsafe_allow_html=True)
    question = st.chat_input("Ask a question …")
    if st.session_state.get("_ask_prefill"):
        question = st.session_state.pop("_ask_prefill")
    if question:
        st.session_state["ask_history"].append({"role":"user","content":question})
        with st.chat_message("user"): st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking …"):
                data, err = _post("/api/ask", json={"question":question,"doc_id":_active_doc_id(),"mode":mode,"k":5,
                                                    "conversation_history":[{"role":m["role"],"content":m["content"]} for m in st.session_state["ask_history"][:-1]][-6:]})
            if err: st.error(err); st.session_state["ask_history"].pop()
            else:
                st.markdown(data["answer"])
                if data.get("sources"):
                    with st.expander("Sources"):
                        for src in data["sources"]: st.markdown(f'<span class="src-chip">{src["filename"]} p.{src["page"]}</span>', unsafe_allow_html=True)
                st.session_state["ask_history"].append({"role":"assistant","content":data["answer"],"sources":data.get("sources",[])})
    if st.session_state["ask_history"] and st.button("🗑️ Clear"):
        st.session_state["ask_history"] = []; st.rerun()


def tab_quiz():
    _heading("Quiz", "Timed multiple-choice quiz from your document.")
    _ss("quiz_data", None); _ss("quiz_answers", {}); _ss("quiz_result", None); _ss("quiz_start_ts", None)
    if st.session_state["quiz_data"] is None and st.session_state["quiz_result"] is None:
        with st.form("quiz_form"):
            topic = st.text_input("Topic (optional)"); num_q = st.slider("Questions", 3, 15, 5)
            difficulty = st.selectbox("Difficulty", ["easy","medium","hard","mixed"])
            if st.form_submit_button("🎯 Generate Quiz", type="primary"):
                with st.spinner("Generating …"):
                    data, err = _post("/api/generate-quiz", json={"doc_id":_active_doc_id(),"topic":topic.strip() or None,"num_questions":num_q,"difficulty":difficulty})
                if err: st.error(err)
                else: st.session_state.update({"quiz_data":data,"quiz_answers":{},"quiz_result":None,"quiz_start_ts":time.time()}); st.rerun()
        return
    if st.session_state["quiz_result"] is not None:
        res = st.session_state["quiz_result"]
        st.markdown(f"## Grade: **{res.get('grade','?')}** — {res.get('percentage',0):.0f}%")
        c1,c2,c3 = st.columns(3); c1.metric("Score",f"{res['score']}/{res['total']}"); c2.metric("Time",f"{res.get('time_taken',0):.0f}s"); c3.metric("Grade",res.get("grade","?"))
        with st.expander("Review", expanded=True):
            for d in res.get("details",[]):
                st.markdown(f'<p style="color:{"#22c55e" if d["is_correct"] else "#ef4444"};font-size:14px;font-weight:600">{"✓" if d["is_correct"] else "✗"} {d["question"]}</p>', unsafe_allow_html=True)
                if d.get("explanation"): st.caption(d["explanation"])
                st.divider()
        if st.button("New Quiz"): st.session_state.update({"quiz_data":None,"quiz_answers":{},"quiz_result":None}); st.rerun()
        return
    quiz = st.session_state["quiz_data"]; questions = quiz.get("questions",[]); answers = st.session_state["quiz_answers"]
    st.progress(len(answers)/len(questions) if questions else 0, text=f"{len(answers)}/{len(questions)} answered")
    for i,q in enumerate(questions):
        with st.container(border=True):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            chosen = st.radio("", range(len(q.get("options",[]))), format_func=lambda j,opts=q.get("options",[]): opts[j], key=f"q_{q['id']}", index=None)
            if chosen is not None: answers[q["id"]] = chosen; st.session_state["quiz_answers"] = answers
    if st.button("✅ Submit Quiz", type="primary", disabled=len(answers)!=len(questions)):
        elapsed = time.time() - (st.session_state["quiz_start_ts"] or time.time())
        with st.spinner("Grading …"):
            data, err = _post("/quiz/submit", json={"quiz_id":quiz["quiz_id"],"answers":answers,"time_taken":int(elapsed)})
        if err: st.error(err)
        else: st.session_state["quiz_result"] = data; st.rerun()
    if st.button("Discard"): st.session_state.update({"quiz_data":None,"quiz_answers":{}}); st.rerun()


def tab_planner():
    _heading("Revision Planner", "Personalised study schedule from your exam date.")
    _ss("plan_data", None)
    if st.session_state["plan_data"] is None:
        with st.form("planner_form"):
            exam_date = st.date_input("Exam date"); daily_hours = st.slider("Daily study hours",0.5,8.0,2.0,step=0.5)
            syllabus = st.text_area("Syllabus / topics (optional)", height=100)
            if st.form_submit_button("Generate Plan", type="primary"):
                with st.spinner("Building plan …"):
                    data, err = _post("/api/generate-plan", json={"exam_date":exam_date.isoformat(),"daily_hours":daily_hours,"syllabus_text":syllabus.strip() or None,"doc_id":_active_doc_id()})
                if err: st.error(err)
                else: st.session_state["plan_data"] = data; st.rerun()
        return
    resp = st.session_state["plan_data"]; stats = resp.get("stats",{})
    c1,c2,c3,c4 = st.columns(4); c1.metric("Days",stats.get("days_to_exam","?")); c2.metric("Study days",stats.get("study_days","?")); c3.metric("Hours",f"{stats.get('total_study_mins',0)//60}h"); c4.metric("Topics",stats.get("topics_covered","?"))
    if resp.get("summary"): st.info(resp["summary"])
    for task in resp.get("plan",[]):
        with st.expander(f"{task.get('session_type','').title()} · {task.get('day_label',task.get('date',''))} · {task.get('topic','')}"):
            c1,c2,c3 = st.columns(3); c1.metric("Duration",f"{task.get('duration_mins',0)} min"); c2.metric("Technique",task.get('technique','—')); c3.metric("Priority",task.get('priority','—'))
            if task.get("notes"): st.caption(task["notes"])
    if st.button("New Plan"): st.session_state["plan_data"] = None; st.rerun()


def tab_flashcards():
    _heading("Flashcards", "AI-generated flip cards for spaced-repetition.")
    _ss("fc_cards",None); _ss("fc_index",0); _ss("fc_flipped",False)
    if st.session_state["fc_cards"] is None:
        with st.form("fc_form"):
            topic = st.text_input("Topic (optional)"); num = st.slider("Cards",3,20,8)
            if st.form_submit_button("Generate Cards", type="primary"):
                with st.spinner("Generating …"):
                    data, err = _post("/api/flashcards/generate", json={"doc_id":_active_doc_id(),"topic":topic.strip() or None,"count":num})
                if err: st.error(err)
                else:
                    cards = data.get("cards", data.get("flashcards",[]))
                    if cards: st.session_state.update({"fc_cards":cards,"fc_index":0,"fc_flipped":False}); st.rerun()
                    else: st.warning("No cards returned.")
        return
    cards = st.session_state["fc_cards"]; idx = st.session_state["fc_index"]; flipped = st.session_state["fc_flipped"]; card = cards[idx]
    st.progress((idx+1)/len(cards), text=f"Card {idx+1}/{len(cards)}")
    front_text = card.get("front", card.get("question", ""))
    if flipped:
        back_text = card.get("back", card.get("answer", ""))
        answer_html = f'<p class="flip-a">{back_text}</p>'
    else:
        answer_html = '<p class="flip-hint">Click Flip to reveal</p>'
    st.markdown(f'<div class="flip-card"><p class="flip-q">{front_text}</p>{answer_html}</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    if c1.button("Prev", disabled=idx==0): st.session_state.update({"fc_index":idx-1,"fc_flipped":False}); st.rerun()
    if c2.button("Flip"): st.session_state["fc_flipped"] = not flipped; st.rerun()
    if c3.button("Next", disabled=idx>=len(cards)-1): st.session_state.update({"fc_index":idx+1,"fc_flipped":False}); st.rerun()
    if c4.button("Shuffle"): random.shuffle(cards); st.session_state.update({"fc_cards":cards,"fc_index":0,"fc_flipped":False}); st.rerun()
    if st.button("New Deck"): st.session_state.update({"fc_cards":None,"fc_index":0,"fc_flipped":False}); st.rerun()


def tab_feynman():
    _heading("Feynman Technique", "Explain a concept — AI scores your understanding.")
    with st.form("feynman_form"):
        concept = st.text_input("Concept", placeholder="e.g. Photosynthesis")
        explanation = st.text_area("Your explanation", height=200)
        submitted = st.form_submit_button("Evaluate", type="primary")
    if submitted and concept.strip() and explanation.strip():
        with st.spinner("Evaluating …"):
            data, err = _post("/api/feynman/evaluate", json={"concept":concept.strip(),"explanation":explanation.strip(),"doc_id":_active_doc_id()})
        if err: st.error(err); return
        score = data.get("score",0); grade = data.get("grade","?")
        gcls = {"S":"grade-s","A":"grade-a","B":"grade-b","C":"grade-c","D":"grade-d"}.get(grade,"grade-b")
        st.markdown(f'<div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem"><span class="{gcls}">{grade}</span><div><p style="font-size:24px;font-weight:700;color:#fafafa;margin:0">{score}/100</p><p style="font-size:13px;color:#71717a;margin:0">Feynman Score</p></div></div>', unsafe_allow_html=True)
        st.progress(score/100)
        c1,c2 = st.columns(2)
        with c1:
            if data.get("strengths"): st.success("**Strengths**\n" + "\n".join(f"- {s}" for s in data["strengths"]))
        with c2:
            if data.get("gaps"): st.error("**Gaps to Fill**\n" + "\n".join(f"- {g}" for g in data["gaps"]))
        if data.get("coaching_tip"): st.info(f"💡 {data['coaching_tip']}")


def tab_cheatsheet():
    _heading("Cheat Sheet", "One-page key-concept summary.")
    doc_id = _active_doc_id()
    if not doc_id: st.warning("⚠️ Upload and select a document first."); return
    topic = st.text_input("Focus topic (optional)")
    if st.button("Generate Cheat Sheet", type="primary"):
        with st.spinner("Generating …"):
            try:
                resp = requests.post(f"{BACKEND_URL}/api/cheatsheet", json={"doc_id":doc_id,"topic":topic.strip()}, stream=True, timeout=TIMEOUT_LONG)
                if not resp.ok: st.error(f"HTTP {resp.status_code}"); return
                parts = []
                for line in resp.iter_lines(decode_unicode=True):
                    if not line.startswith("data: "): continue
                    payload = line[6:]
                    if payload == "[DONE]": break
                    if payload.startswith("[ERROR]"): st.error(payload[7:]); return
                    parts.append(payload.replace("\\n","\n"))
                content = "".join(parts)
            except Exception as e:
                st.error(str(e)); return
        if content:
            st.markdown(content)
            st.download_button("⬇️ Download (.md)", data=content, file_name="cheatsheet.md", mime="text/markdown")


def tab_progress():
    _heading("Progress Dashboard", "Your study analytics — quizzes, Feynman sessions, streaks.")
    with st.spinner("Loading …"):
        data, err = _get("/api/progress/summary", timeout=30)
    if err: st.error(err); return
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Quizzes", data.get("total_quizzes",0)); c2.metric("Avg Score",f"{data.get('avg_score_pct',0):.0f}%")
    c3.metric("Best Score",f"{data.get('best_score_pct',0):.0f}%"); c4.metric("Streak",data.get("current_streak_days",0))
    if data.get("score_history"):
        st.divider()
        st.dataframe([{"Date":h["date"],"Topic":h["topic"],"Score":f"{h['score']}/{h['total']}","Grade":h["grade"]} for h in data["score_history"][-20:]], use_container_width=True)
    c1,c2 = st.columns(2)
    with c1:
        if data.get("weak_topics"):
            st.markdown('<p style="font-size:12px;font-weight:600;color:#ef4444;text-transform:uppercase">Weak Topics</p>', unsafe_allow_html=True)
            for t in data["weak_topics"]: st.progress(t["avg_pct"]/100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")
    with c2:
        if data.get("strong_topics"):
            st.markdown('<p style="font-size:12px;font-weight:600;color:#22c55e;text-transform:uppercase">Strong Topics</p>', unsafe_allow_html=True)
            for t in data["strong_topics"]: st.progress(t["avg_pct"]/100, text=f"{t['topic']} ({t['avg_pct']:.0f}%)")


# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not _ensure_backend():
        st.stop()

    sidebar()

    tabs = st.tabs([
        "🔑 Login",
        "🏠 Dashboard",
        "📋 Assignments",
        "📊 Marks",
        "📅 Timetable",
        "🔔 Notifications",
        "📁 Notes",
        "👥 Connections",
        "🛡️ Admin",
        "─────",
        "📤 Upload",
        "💡 ELI10",
        "🤖 Ask AI",
        "🎯 Quiz",
        "📆 Planner",
        "🃏 Flashcards",
        "🧠 Feynman",
        "📝 Cheat Sheet",
        "📈 Progress",
    ])

    with tabs[0]:  tab_auth()
    with tabs[1]:  tab_dashboard()
    with tabs[2]:  tab_assignments()
    with tabs[3]:  tab_marks()
    with tabs[4]:  tab_timetable()
    with tabs[5]:  tab_notifications()
    with tabs[6]:  tab_notes()
    with tabs[7]:  tab_connections()
    with tabs[8]:  tab_admin()
    with tabs[9]:  st.markdown('<p style="color:#3f3f46;font-size:13px;margin-top:2rem;text-align:center">── AI Study Tools ──</p>', unsafe_allow_html=True)
    with tabs[10]: tab_upload()
    with tabs[11]: tab_explain()
    with tabs[12]: tab_ask()
    with tabs[13]: tab_quiz()
    with tabs[14]: tab_planner()
    with tabs[15]: tab_flashcards()
    with tabs[16]: tab_feynman()
    with tabs[17]: tab_cheatsheet()
    with tabs[18]: tab_progress()


if __name__ == "__main__":
    main()
