"""
pages/dashboard.py — Student/Admin Dashboard
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, current_user, is_admin, _p
from core.api_client import api_get

inject_global_css()
require_login()
page_enter()

user = current_user()
name = user.get("full_name", "Student").split()[0]

def _greeting():
    h = datetime.datetime.now().hour
    if h < 12:  return "Good morning",   "☀️"
    if h < 17:  return "Good afternoon", "👋"
    if h < 21:  return "Good evening",   "🌆"
    return "Good night", "🌙"

greeting_text, greeting_emoji = _greeting()

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
if is_admin():
    count_data, _         = api_get("/api/admin/students/count", timeout=10)
    assignments_data, _   = api_get("/api/admin/assignments",    timeout=10)
    announcements_data, _ = api_get("/api/admin/announcements",  timeout=10)

    total_students  = (count_data or {}).get("total", 0)
    active_students = (count_data or {}).get("active", 0)
    total_asgn      = len(assignments_data or [])
    published       = sum(1 for a in (assignments_data or []) if a.get("is_published"))

    # Hero
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#1e1b4b,#312e81,#2e1065);
     border-radius:20px;padding:2rem 2.5rem;margin-bottom:1.5rem;
     border:1px solid rgba(99,102,241,.35)">
  <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(99,102,241,.2);
       border:1px solid rgba(99,102,241,.4);border-radius:99px;padding:4px 12px;
       font-size:11px;font-weight:600;color:#a5b4fc;margin-bottom:.75rem">
    ⚙️ Admin Panel
  </div>
  <div style="font-size:1.75rem;font-weight:800;color:#fafafa;margin-bottom:.4rem">
    Welcome back, <span style="color:#a78bfa">{name}</span>
  </div>
  <div style="font-size:.9rem;color:rgba(255,255,255,.6)">
    Manage your institution — students, assignments, timetables and announcements.
  </div>
</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, color, label, val, sub in [
        (c1, "#6366f1", "Total Students",  total_students,  "enrolled"),
        (c2, "#22c55e", "Active Students", active_students, "this semester"),
        (c3, "#f59e0b", "Assignments",     total_asgn,      "created"),
        (c4, "#3b82f6", "Published",       published,       "visible to students"),
    ]:
        with col:
            st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:14px;
     padding:1.1rem 1.25rem;border-top:3px solid {color};margin-bottom:.5rem">
  <div style="font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;
       letter-spacing:.06em;margin-bottom:.4rem">{label}</div>
  <div style="font-size:2rem;font-weight:800;color:{color};line-height:1">{val}</div>
  <div style="font-size:11px;color:#52525b;margin-top:.3rem">{sub}</div>
</div>""", unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p style="font-size:12px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Recent Announcements</p>', unsafe_allow_html=True)
        for ann in (announcements_data or [])[:5]:
            card(f'<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{ann["title"]}</p>'
                 f'<p style="margin:4px 0 0;font-size:12px;color:#71717a">{ann["content"][:100]}…</p>')
    with col2:
        st.markdown('<p style="font-size:12px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Recent Assignments</p>', unsafe_allow_html=True)
        for a in (assignments_data or [])[:5]:
            b = badge("Published", "green") if a.get("is_published") else badge("Draft", "yellow")
            card(f'<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a["title"]} {b}</p>'
                 f'<p style="margin:4px 0 0;font-size:12px;color:#71717a">Due: {a.get("due_date","?")} · Max: {a.get("max_marks","?")} marks</p>')

# ─────────────────────────────────────────────────────────────────────────────
# STUDENT DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
else:
    assignments_data, _ = api_get("/api/assignments",                 timeout=10)
    notif_data, _       = api_get("/api/notifications/unread-count",  timeout=10)
    timetable_data, _   = api_get("/api/timetable/today",             timeout=10)
    marks_data, _       = api_get("/api/marks/summary",               timeout=10)
    progress_data, _    = api_get("/api/progress/summary",            timeout=15)

    pending = [a for a in (assignments_data or []) if (a.get("submission_status") or "pending") == "pending"]
    unread  = (notif_data   or {}).get("count", 0)
    streak  = (progress_data or {}).get("current_streak_days", 0)
    grade   = (marks_data   or {}).get("overall_grade") or "—"

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 45%,#2e1065 100%);
     border-radius:20px;padding:2rem 2.5rem;margin-bottom:1.5rem;
     border:1px solid rgba(99,102,241,.35);position:relative;overflow:hidden">
  <div style="position:absolute;top:0;right:0;bottom:0;width:45%;
       background:radial-gradient(ellipse at 80% 50%,rgba(139,92,246,.25),transparent 70%);
       pointer-events:none"></div>
  <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(99,102,241,.2);
       border:1px solid rgba(99,102,241,.4);border-radius:99px;padding:4px 14px;
       font-size:11px;font-weight:600;color:#a5b4fc;letter-spacing:.04em;margin-bottom:.875rem">
    ✦ Powered by RAG × LLM
  </div>
  <div style="font-size:1.8rem;font-weight:800;color:#fafafa;margin-bottom:.4rem;letter-spacing:-.02em;line-height:1.2">
    {greeting_text}, <span style="color:#a78bfa">{name}!</span> {greeting_emoji}
  </div>
  <div style="font-size:.9rem;color:rgba(255,255,255,.6);margin-bottom:1.25rem;line-height:1.6">
    Ready to study smarter? Upload your notes or paste text to unlock AI-powered<br>
    explanations, quizzes, and revision plans.
  </div>
</div>""", unsafe_allow_html=True)

    # Get Started button (native Streamlit — actually clickable)
    if st.button("🚀 Get Started →", type="primary"):
        st.switch_page(_p("learning.py"))

    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

    # ── Stat cards ────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    for col, color, label, val, sub in [
        (c1, "#f59e0b", "Pending",       str(len(pending)), "assignments due"),
        (c2, "#22c55e", "Grade",         grade,             "overall average"),
        (c3, "#a78bfa", "Streak 🔥",     f"{streak}d",      "days in a row"),
        (c4, "#6366f1", "Notifications", str(unread),       "unread alerts"),
    ]:
        with col:
            st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:14px;
     padding:1.1rem 1.25rem;border-top:3px solid {color};margin-bottom:.75rem">
  <div style="font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;
       letter-spacing:.06em;margin-bottom:.4rem">{label}</div>
  <div style="font-size:2rem;font-weight:800;color:{color};line-height:1">{val}</div>
  <div style="font-size:11px;color:#52525b;margin-top:.3rem">{sub}</div>
</div>""", unsafe_allow_html=True)

    # ── Explore Features label ────────────────────────────────────────────────
    st.markdown('<p style="font-size:12px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.06em;margin:.25rem 0 1rem">Explore Features</p>', unsafe_allow_html=True)

    # ── Feature cards (2 rows × 3) ────────────────────────────────────────────
    # Each card: (bg_gradient, border_color, hover_shadow_color, icon, title, desc, page)
    FEATURES = [
        ("#1e1b4b,#312e81", "#4338ca", "rgba(99,102,241,.45)",   "📤", "Study Material", "Upload docs or paste notes to index",          "learning.py"),
        ("#451a03,#78350f", "#b45309", "rgba(245,158,11,.4)",    "💡", "ELI10",          "Get simplified explanations for any topic",     "learning.py"),
        ("#2e1065,#4c1d95", "#7c3aed", "rgba(139,92,246,.45)",   "⚡", "AI Quiz",         "Test knowledge with adaptive quizzes",          "learning.py"),
        ("#052e16,#14532d", "#166534", "rgba(34,197,94,.35)",    "📅", "Revision Plan",  "Build a smart study schedule",                 "learning.py"),
        ("#4c0519,#881337", "#be123c", "rgba(244,63,94,.4)",     "💬", "Ask AI",          "Chat with your documents via RAG",             "learning.py"),
        ("#083344,#164e63", "#0e7490", "rgba(6,182,212,.35)",    "🃏", "Flashcards",      "AI-generated spaced repetition cards",         "learning.py"),
    ]

    row1 = st.columns(3)
    row2 = st.columns(3)
    cols = row1 + row2

    for i, (col, (bg, border, shadow, icon, title, desc, page)) in enumerate(zip(cols, FEATURES)):
        delay = 0.08 + i * 0.07
        with col:
            st.markdown(f"""
<div style="background:linear-gradient(135deg,{bg});border:1px solid {border};
     border-radius:16px;padding:1.25rem 1.4rem;margin-bottom:.25rem;
     animation:fadeUp .5s {delay:.2f}s both;cursor:pointer;
     transition:transform .2s,box-shadow .2s">
  <div style="width:40px;height:40px;border-radius:10px;background:rgba(255,255,255,.1);
       display:flex;align-items:center;justify-content:center;
       font-size:1.25rem;margin-bottom:.75rem">{icon}</div>
  <div style="font-size:.95rem;font-weight:700;color:#fafafa;margin-bottom:.2rem">{title}</div>
  <div style="font-size:.8rem;color:rgba(255,255,255,.5);line-height:1.4">{desc}</div>
</div>""", unsafe_allow_html=True)
            if st.button(f"Open", key=f"feat_{i}", use_container_width=True):
                st.switch_page(_p(page))

    # ── Schedule + Assignments ────────────────────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p style="font-size:12px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Today\'s Schedule</p>', unsafe_allow_html=True)
        periods = (timetable_data or {}).get("periods", [])
        if periods:
            for p in periods[:6]:
                card(f'<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">P{p["period_number"]} — {p.get("subject","Free")}</p>'
                     f'<p style="margin:4px 0 0;font-size:12px;color:#71717a">{p.get("start_time","?")} – {p.get("end_time","?")}{(" · " + p["room"]) if p.get("room") else ""}</p>')
        else:
            st.info("No timetable published yet.")

    with col2:
        st.markdown('<p style="font-size:12px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Pending Assignments</p>', unsafe_allow_html=True)
        if pending:
            for a in pending[:5]:
                card(f'<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a["title"]}</p>'
                     f'<p style="margin:4px 0 0;font-size:12px;color:#71717a">Due: {a.get("due_date","?")} {a.get("due_time","")}</p>')
        else:
            st.success("🎉 No pending assignments!")
