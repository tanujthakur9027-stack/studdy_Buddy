"""
pages/dashboard.py — Student/Admin Dashboard

Student view: stat cards (assignments, grade, schedule, notifications),
upcoming assignments, today's timetable, quick-action buttons to Learning.
Admin view: student count, assignment stats, recent announcements.

All cards have staggered fade-up animation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, heading, badge, card
from core.animations import page_enter, count_up_metric
from core.auth_state import require_login, current_user, is_admin
from core.api_client import api_get

inject_global_css()
require_login()
page_enter()

user = current_user()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-fade" style="margin-bottom:1.5rem">
  <h2 style="font-size:26px;font-weight:800;color:#fafafa;margin:0">
    Dashboard
  </h2>
  <p style="color:#71717a;font-size:14px;margin:.25rem 0 0">
    Welcome back, <span style="color:#a78bfa;font-weight:600">{user.get('full_name','User')}</span> 👋
  </p>
</div>
""", unsafe_allow_html=True)


if is_admin():
    # ── Admin Dashboard ───────────────────────────────────────────────────────
    count_data, _ = api_get("/api/admin/students/count", timeout=10)
    assignments_data, _ = api_get("/api/admin/assignments", timeout=10)
    announcements_data, _ = api_get("/api/admin/announcements", timeout=10)

    total_students  = (count_data or {}).get("total", 0)
    active_students = (count_data or {}).get("active", 0)
    total_asgn = len(assignments_data or [])
    published  = sum(1 for a in (assignments_data or []) if a.get("is_published"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="card-fade-1">', unsafe_allow_html=True)
        count_up_metric("Total Students", total_students, color="#6366f1")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card-fade-2">', unsafe_allow_html=True)
        count_up_metric("Active Students", active_students, color="#22c55e")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card-fade-3">', unsafe_allow_html=True)
        count_up_metric("Assignments", total_asgn, color="#f59e0b")
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="card-fade-4">', unsafe_allow_html=True)
        count_up_metric("Published", published, color="#3b82f6")
        st.markdown('</div>', unsafe_allow_html=True)

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

else:
    # ── Student Dashboard ─────────────────────────────────────────────────────
    assignments_data, _ = api_get("/api/assignments", timeout=10)
    notif_data, _       = api_get("/api/notifications/unread-count", timeout=10)
    timetable_data, _   = api_get("/api/timetable/today", timeout=10)
    marks_data, _       = api_get("/api/marks/summary", timeout=10)
    progress_data, _    = api_get("/api/progress/summary", timeout=15)

    pending = [a for a in (assignments_data or []) if a.get("submission_status") == "pending"]
    unread  = (notif_data or {}).get("count", 0)
    streak  = (progress_data or {}).get("current_streak_days", 0)
    avg_pct = (progress_data or {}).get("avg_score_pct", 0)

    # Stat cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="card-fade-1">', unsafe_allow_html=True)
        count_up_metric("Pending Assignments", len(pending), color="#f59e0b")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card-fade-2">', unsafe_allow_html=True)
        grade = (marks_data or {}).get("overall_grade") or "—"
        st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;padding:.875rem 1rem;animation:countUp 0.5s 0.12s both">
  <p style="margin:0;font-size:12px;color:#71717a">Overall Grade</p>
  <p style="margin:4px 0 0;font-size:26px;font-weight:800;color:#22c55e">{grade}</p>
</div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card-fade-3">', unsafe_allow_html=True)
        count_up_metric("Study Streak 🔥", streak, suffix=" days", color="#f59e0b")
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="card-fade-4">', unsafe_allow_html=True)
        count_up_metric("🔔 Notifications", unread, color="#6366f1")
        st.markdown('</div>', unsafe_allow_html=True)

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

    # Quick actions
    st.divider()
    st.markdown('<p style="font-size:13px;font-weight:600;color:#a1a1aa;margin-bottom:.75rem">Quick Actions</p>', unsafe_allow_html=True)
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("🧠 AI Study Tools →", use_container_width=True, type="primary"):
            st.switch_page("pages/learning.py")
    with qa2:
        if st.button("📋 Assignments →", use_container_width=True):
            st.switch_page("pages/classes.py")
    with qa3:
        if st.button("📈 Progress →", use_container_width=True):
            st.switch_page("pages/learning.py")
