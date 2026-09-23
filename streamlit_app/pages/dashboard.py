"""
pages/dashboard.py — Student/Admin Dashboard

Student view: hero banner with greeting, animated stat cards,
feature cards grid, today's schedule, pending assignments.
Admin view: stat cards, recent announcements/assignments.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
import streamlit as st

from core.styles import inject_global_css, heading, badge, card
from core.animations import page_enter, count_up_metric
from core.auth_state import require_login, current_user, is_admin, _p
from core.api_client import api_get

inject_global_css()
require_login()
page_enter()

user = current_user()
name = user.get("full_name", "Student").split()[0]  # first name only

# ── Greeting helper ────────────────────────────────────────────────────────────
def _greeting() -> tuple[str, str]:
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning", "☀️"
    if hour < 17:
        return _greeting_afternoon()
    if hour < 21:
        return "Good evening", "🌆"
    return "Good night", "🌙"

def _greeting_afternoon() -> tuple[str, str]:
    return "Good afternoon", "👋"


greeting_text, greeting_emoji = _greeting()


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
if is_admin():
    count_data, _        = api_get("/api/admin/students/count", timeout=10)
    assignments_data, _  = api_get("/api/admin/assignments",    timeout=10)
    announcements_data, _= api_get("/api/admin/announcements",  timeout=10)

    total_students  = (count_data or {}).get("total", 0)
    active_students = (count_data or {}).get("active", 0)
    total_asgn      = len(assignments_data or [])
    published       = sum(1 for a in (assignments_data or []) if a.get("is_published"))

    # Admin hero
    st.markdown(f"""
<div class="hero-banner" style="animation:fadeUp .5s both">
  <div class="hero-label">⚙️ Admin Panel</div>
  <div class="hero-title">Welcome back, <span>{name}</span></div>
  <div class="hero-sub">Manage your institution — students, assignments, timetables and announcements.</div>
</div>""", unsafe_allow_html=True)

    # Stat cards
    c1, c2, c3, c4 = st.columns(4)
    cards_data = [
        (c1, "card-fade-1", "#6366f1", "Total Students",  total_students,  "enrolled"),
        (c2, "card-fade-2", "#22c55e", "Active Students",  active_students, "this semester"),
        (c3, "card-fade-3", "#f59e0b", "Assignments",      total_asgn,      "created"),
        (c4, "card-fade-4", "#3b82f6", "Published",        published,       "visible to students"),
    ]
    for col, fade, color, label, value, sub in cards_data:
        with col:
            st.markdown(f"""
<div class="{fade}">
  <div class="stat-card" style="--accent-color:{color}">
    <div class="stat-label">{label}</div>
    <div class="stat-value" style="color:{color}">{value}</div>
    <div class="stat-sub">{sub}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Recent Announcements</p>', unsafe_allow_html=True)
        for ann in (announcements_data or [])[:5]:
            card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{ann['title']}</p>
<p style="margin:4px 0 0;font-size:12px;color:#71717a">{ann['content'][:100]}…</p>""")
    with col2:
        st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Recent Assignments</p>', unsafe_allow_html=True)
        for a in (assignments_data or [])[:5]:
            b = badge("Published", "green") if a.get("is_published") else badge("Draft", "yellow")
            card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a['title']} {b}</p>
<p style="margin:4px 0 0;font-size:12px;color:#71717a">Due: {a.get('due_date','?')} · Max: {a.get('max_marks','?')} marks</p>""")

# ─────────────────────────────────────────────────────────────────────────────
# STUDENT DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
else:
    assignments_data, _ = api_get("/api/assignments",            timeout=10)
    notif_data, _       = api_get("/api/notifications/unread-count", timeout=10)
    timetable_data, _   = api_get("/api/timetable/today",        timeout=10)
    marks_data, _       = api_get("/api/marks/summary",          timeout=10)
    progress_data, _    = api_get("/api/progress/summary",       timeout=15)

    pending = [a for a in (assignments_data or []) if (a.get("submission_status") or "pending") == "pending"]
    unread  = (notif_data  or {}).get("count", 0)
    streak  = (progress_data or {}).get("current_streak_days", 0)
    grade   = (marks_data  or {}).get("overall_grade") or "—"

    # ── Hero banner ────────────────────────────────────────────────────────────
    st.markdown(f"""
<div class="hero-banner" style="animation:fadeUp .5s both">
  <div class="hero-label">✦ Powered by RAG × LLM</div>
  <div class="hero-title">{greeting_text}, <span>{name}!</span> {greeting_emoji}</div>
  <div class="hero-sub">
    Ready to study smarter? Upload your notes or paste text to unlock AI-powered
    explanations, quizzes, and revision plans.
  </div>
  <div style="display:inline-flex;gap:.75rem;flex-wrap:wrap;position:relative;z-index:1">
    <a href="#" onclick="return false;"
       style="display:inline-flex;align-items:center;gap:6px;
              background:linear-gradient(135deg,#6366f1,#8b5cf6);
              color:#fff;font-size:13px;font-weight:700;padding:9px 20px;
              border-radius:99px;text-decoration:none;
              box-shadow:0 4px 18px rgba(99,102,241,.5)">
      Get Started →
    </a>
  </div>
</div>""", unsafe_allow_html=True)

    # Streamlit button hidden inside hero — use native button below for navigation
    col_btn = st.columns([1, 3])[0]

    # ── Stat cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    stat_rows = [
        (c1, "card-fade-1", "#f59e0b", "Pending",      str(len(pending)), "assignments due"),
        (c2, "card-fade-2", "#22c55e", "Grade",         grade,             "overall average"),
        (c3, "card-fade-3", "#a78bfa", "Streak 🔥",     f"{streak}",       "days in a row"),
        (c4, "card-fade-4", "#6366f1", "Notifications", str(unread),       "unread alerts"),
    ]
    for col, fade, color, label, value, sub in stat_rows:
        with col:
            st.markdown(f"""
<div class="{fade}">
  <div class="stat-card" style="--accent-color:{color}">
    <div class="stat-label">{label}</div>
    <div class="stat-value" style="color:{color}">{value}</div>
    <div class="stat-sub">{sub}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin:.1rem 0 1rem">Explore Features</p>', unsafe_allow_html=True)

    # ── Feature cards grid ─────────────────────────────────────────────────────
    feat_row1 = st.columns(3)
    feat_row2 = st.columns(3)

    features = [
        # (col, fade-cls, card-color, icon, title, desc, page)
        (feat_row1[0], "feat-fade-1", "indigo",  "📤", "Study Material",
         "Upload docs or paste notes to index", "learning.py"),
        (feat_row1[1], "feat-fade-2", "amber",   "💡", "ELI10",
         "Get simplified explanations for any topic", "learning.py"),
        (feat_row1[2], "feat-fade-3", "violet",  "⚡", "AI Quiz",
         "Test knowledge with adaptive quizzes", "learning.py"),
        (feat_row2[0], "feat-fade-4", "emerald", "📅", "Revision Plan",
         "Build a smart study schedule", "learning.py"),
        (feat_row2[1], "feat-fade-5", "rose",    "💬", "Ask AI",
         "Chat with your documents via RAG", "learning.py"),
        (feat_row2[2], "feat-fade-6", "cyan",    "🃏", "Flashcards",
         "AI-generated spaced repetition cards", "learning.py"),
    ]

    for col, fade, color, icon, title, desc, page in features:
        with col:
            st.markdown(f"""
<div class="{fade}">
  <div class="feat-card feat-card-{color}">
    <div class="feat-icon">{icon}</div>
    <div class="feat-title">{title}</div>
    <div class="feat-desc">{desc}</div>
  </div>
</div>""", unsafe_allow_html=True)
            if st.button(f"Open {title}", key=f"feat_{title}", use_container_width=True):
                st.switch_page(_p(page))

    # ── Schedule + Assignments ─────────────────────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Today\'s Schedule</p>', unsafe_allow_html=True)
        periods = (timetable_data or {}).get("periods", [])
        if periods:
            for p in periods[:6]:
                card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">P{p['period_number']} — {p.get('subject','Free')}</p>
<p style="margin:4px 0 0;font-size:12px;color:#71717a">{p.get('start_time','?')} – {p.get('end_time','?')}{(' · ' + p['room']) if p.get('room') else ''}</p>""")
        else:
            st.info("No timetable published yet.")

    with col2:
        st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">Pending Assignments</p>', unsafe_allow_html=True)
        if pending:
            for a in pending[:5]:
                card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{a['title']}</p>
<p style="margin:4px 0 0;font-size:12px;color:#71717a">Due: {a.get('due_date','?')} {a.get('due_time','')}</p>""")
        else:
            st.success("🎉 No pending assignments!")
