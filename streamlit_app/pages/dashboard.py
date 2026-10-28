"""
pages/dashboard.py — Main Dashboard (Student & Admin Parity with localhost Next.js)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, current_user, is_admin, _p
from core.api_client import api_get, api_post, api_patch
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Universal Identity Header
render_identity_header()

user = current_user()
full_name = user.get("full_name", "Student")
first_name = full_name.split()[0] if full_name else "Student"

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
    # Load administrative metrics
    count_data, _       = api_get("/api/admin/students/count", timeout=10)
    classes_data, _     = api_get("/api/admin/classes", timeout=10)
    assignments_data, _ = api_get("/api/admin/assignments", timeout=10)
    submissions_data, _ = api_get("/api/admin/submissions?page_size=10", timeout=10)
    inquiries_data, _   = api_get("/api/notifications/admin/contacts", timeout=10)
    health_data, _      = api_get("/health", timeout=10)

    total_students  = (count_data or {}).get("total", 0)
    active_students = (count_data or {}).get("active", 0)
    total_classes   = len(classes_data or [])
    assignments     = assignments_data or []
    total_asgn      = len(assignments)
    published_asgn  = sum(1 for a in assignments if a.get("is_published"))
    submissions     = submissions_data or []
    pending_subs    = sum(1 for s in submissions if s.get("status") != "evaluated")
    inquiries       = inquiries_data or []
    unread_inq      = sum(1 for i in inquiries if not i.get("is_read"))
    health          = health_data or {}

    # Hero Banner
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#1e293b 100%);
     border-radius:20px;padding:2rem 2.2rem;margin-bottom:1.5rem;
     border:1px solid rgba(59,130,246,0.3);box-shadow:0 12px 35px -10px rgba(0,0,0,0.6)">
  <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(245,158,11,0.15);
       border:1px solid rgba(245,158,11,0.3);border-radius:99px;padding:3px 12px;
       font-size:11px;font-weight:700;color:#fbbf24;margin-bottom:.75rem">
    🛡️ OPERATIONS &amp; COMMS
  </div>
  <div style="font-size:1.8rem;font-weight:900;color:#ffffff;margin-bottom:.3rem;letter-spacing:-0.03em">
    Administrator Command Hub
  </div>
  <div style="font-size:.9rem;color:#9ca3af">
    Full institutional oversight: students, classes, evaluations, broadcasts, and student inquiries.
  </div>
</div>""", unsafe_allow_html=True)

    # System Diagnostics Bar
    api_status = health.get("status", "ok").upper()
    db_name = health.get("database", "sqlite")
    provider = health.get("provider", "groq")
    model = health.get("model", "qwen3")
    smtp_status = "Active" if health.get("smtp") == "configured" else "Simulation Mode"

    st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-radius:14px;
     padding:0.75rem 1.25rem;margin-bottom:1.5rem;display:flex;align-items:center;justify-content:space-between;
     flex-wrap:wrap;gap:12px;font-size:12px;color:#9ca3af">
  <div style="display:flex;align-items:center;gap:8px">
    <span style="display:inline-block;width:8px;height:8px;border-radius:99px;background:#10b981;box-shadow:0 0 10px #10b981"></span>
    <span>API: <strong style="color:#ffffff">{api_status}</strong></span>
  </div>
  <div>💾 DB: <strong style="color:#ffffff">{db_name}</strong></div>
  <div>✨ AI: <strong style="color:#60a5fa">{provider} ({model})</strong></div>
  <div>✉️ SMTP: <strong style="color:#fbbf24">{smtp_status}</strong></div>
  <div>⚡ Rate Limit: <strong style="color:#ffffff">{health.get('rate_limit', '60/min')}</strong></div>
</div>""", unsafe_allow_html=True)

    # 6 Metric Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Students", total_students, f"{active_students} active")
    m2.metric("Classes", total_classes, "active cohorts")
    m3.metric("Assignments", total_asgn, f"{published_asgn} published")
    m4.metric("Submissions", len(submissions), f"{pending_subs} pending review")
    m5.metric("Inquiries", len(inquiries), f"{unread_inq} unread")
    m6.metric("Indexed Docs", health.get("indexed_documents", 0), f"{health.get('faiss_vectors', 0)} vectors")

    st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)

    tab_overview, tab_inq_list, tab_broadcast = st.tabs([
        "📋 Overview & Shortcuts", f"📬 Student Inquiries ({unread_inq})", "✉️ Broadcast Notification & Email"
    ])

    with tab_overview:
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">Recent Submissions To Review</p>', unsafe_allow_html=True)
            if not submissions:
                st.info("No submissions recorded.")
            else:
                for s in submissions[:5]:
                    status = s.get("status", "submitted")
                    b_color = "green" if status == "evaluated" else "yellow"
                    card(f'<div style="display:flex;justify-content:space-between;align-items:center">'
                         f'<div><p style="margin:0;font-size:14px;font-weight:700;color:#ffffff">{s.get("student_name","Student")}</p>'
                         f'<p style="margin:2px 0 0;font-size:12px;color:#9ca3af">Submission ID: {s.get("id","")[:8]}</p></div>'
                         f'{badge(status.title(), b_color)}</div>')

        with c_right:
            st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">Administrative Quick Actions</p>', unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("👥 Manage Students", key="btn_adm_stu", use_container_width=True):
                    st.switch_page(_p("admin.py"))
                if st.button("🏛️ Manage Classes", key="btn_adm_cls", use_container_width=True):
                    st.switch_page(_p("admin.py"))
                if st.button("📅 Set Timetable", key="btn_adm_tt", use_container_width=True):
                    st.switch_page(_p("admin.py"))
            with col_b2:
                if st.button("📋 Assignments", key="btn_adm_asgn", use_container_width=True):
                    st.switch_page(_p("admin.py"))
                if st.button("📊 Grade Marks", key="btn_adm_mrk", use_container_width=True):
                    st.switch_page(_p("admin.py"))
                if st.button("📢 Announcements", key="btn_adm_ann", use_container_width=True):
                    st.switch_page(_p("admin.py"))

    with tab_inq_list:
        if not inquiries:
            st.info("No student contact inquiries received yet.")
        else:
            for inq in inquiries:
                is_read = inq.get("is_read", False)
                bg = "rgba(17,24,39,0.9)" if is_read else "rgba(30,27,75,0.6)"
                border = "rgba(31,41,55,0.9)" if is_read else "rgba(99,102,241,0.5)"
                col_iq, col_act = st.columns([10, 2])
                with col_iq:
                    stu_info = f"{inq.get('sender_name','Student')} ({inq.get('sender_email','')})"
                    created = inq.get("created_at", "")[:16].replace("T", " ")
                    st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:14px;padding:1rem 1.25rem;margin:0.4rem 0">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
    <strong style="color:#ffffff;font-size:14px">{inq.get('title','')}</strong>
    <span style="font-size:11px;color:#6b7280">{created}</span>
  </div>
  <p style="font-size:12px;color:#818cf8;margin:2px 0 6px">From: {stu_info}</p>
  <p style="font-size:13px;color:#d1d5db;margin:0;line-height:1.5">{inq.get('message','')}</p>
</div>""", unsafe_allow_html=True)
                with col_act:
                    if not is_read:
                        if st.button("Mark Reviewed", key=f"rev_{inq['id']}", use_container_width=True):
                            api_patch(f"/api/notifications/{inq['id']}/read")
                            st.rerun()

    with tab_broadcast:
        with st.form("dash_broadcast_form"):
            st.markdown("**Dispatch Broadcast to Campus / Cohort**")
            b_target = st.selectbox("Target Audience", ["All Students", "Specific Class", "Single Student"])
            b_target_id = st.text_input("Target ID (Class ID or Student User ID, if not All)")
            b_title = st.text_input("Notification Title *", placeholder="e.g. Midterm Examination Schedule Released")
            b_message = st.text_area("Message Content *", placeholder="Provide full details...", height=100)
            b_email = st.checkbox("Also dispatch email via SMTP relay", value=False)
            b_submit = st.form_submit_button("Broadcast Now →", type="primary")

        if b_submit:
            if not b_title.strip() or not b_message.strip():
                st.error("Please provide both a title and message.")
            else:
                target_code = "all"
                if b_target == "Specific Class": target_code = "class"
                elif b_target == "Single Student": target_code = "student"
                res, err = api_post("/api/notifications/broadcast", json={
                    "title": b_title.strip(),
                    "message": b_message.strip(),
                    "target": target_code,
                    "target_id": b_target_id.strip() if b_target_id.strip() else None,
                    "send_email": b_email,
                })
                if err:
                    st.error(err)
                else:
                    st.success(f"Dispatched! In-app notifications created: {res.get('in_app_count', 0)}")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STUDENT DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
else:
    assignments_data, _ = api_get("/api/assignments",                timeout=10)
    notif_data, _       = api_get("/api/notifications/unread-count",  timeout=10)
    timetable_data, _   = api_get("/api/timetable/today",             timeout=10)
    marks_data, _       = api_get("/api/marks/summary",               timeout=10)
    progress_data, _    = api_get("/api/progress/summary",            timeout=15)
    announcements_data, _ = api_get("/api/announcements",            timeout=10)

    assignments = assignments_data or []
    pending = [a for a in assignments if (a.get("submission_status") or "pending") == "pending"]
    unread  = (notif_data   or {}).get("count", 0)
    streak  = (progress_data or {}).get("current_streak_days", 0)
    quizzes = (progress_data or {}).get("total_quizzes", 0)
    grade   = (marks_data   or {}).get("overall_grade") or "—"
    today_periods = (timetable_data or {}).get("periods", [])
    announcements = announcements_data or []

    # Hero Banner
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#1e293b 100%);
     border-radius:22px;padding:2.2rem 2.5rem;margin-bottom:1.5rem;
     border:1px solid rgba(59,130,246,0.25);position:relative;overflow:hidden;
     box-shadow:0 12px 35px -10px rgba(0,0,0,0.6)">
  <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(59,130,246,0.15);
       border:1px solid rgba(59,130,246,0.35);border-radius:99px;padding:4px 14px;
       font-size:11px;font-weight:700;color:#93c5fd;letter-spacing:0.04em;margin-bottom:0.9rem">
    ✦ POWERED BY HYBRID RAG × LLM
  </div>
  <div style="font-size:1.85rem;font-weight:900;color:#ffffff;margin-bottom:.4rem;letter-spacing:-0.03em;line-height:1.2">
    {greeting_text}, <span style="background:linear-gradient(90deg,#93c5fd,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent">{first_name}!</span> {greeting_emoji}
  </div>
  <div style="font-size:.92rem;color:#9ca3af;margin-bottom:1.25rem;line-height:1.6">
    Ready to master your courses? Upload study materials, take adaptive AI quizzes, and review deadlines.
  </div>
</div>""", unsafe_allow_html=True)

    col_btn_start, _ = st.columns([2.5, 7.5])
    with col_btn_start:
        if st.button("🚀 Explore AI Study Tools →", type="primary", use_container_width=True):
            st.switch_page(_p("learning.py"))

    st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)

    # 6 Metric Cards matching Next.js localhost 1:1
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Pending Tasks", len(pending), "assignments due")
    c2.metric("Overall Grade", grade, "academic avg")
    c3.metric("Today's Classes", len(today_periods), "lectures")
    c4.metric("Unread Alerts", unread, "notifications")
    c5.metric("Study Streak", f"{streak}d", "consecutive")
    c6.metric("Quizzes Taken", quizzes, "completed")

    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

    # 2-Column Academic Status Grid
    col_left, col_right = st.columns(2)

    with col_left:
        # Upcoming Assignments
        st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">📋 Upcoming Assignments</p>', unsafe_allow_html=True)
        if not assignments:
            st.info("No assignments posted yet.")
        else:
            for a in assignments[:4]:
                st_badge = badge(a.get("submission_status", "pending").title(), "green" if a.get("submission_status") else "yellow")
                card(f'<div style="display:flex;justify-content:space-between;align-items:center">'
                     f'<div><p style="margin:0;font-size:14px;font-weight:700;color:#ffffff">{a.get("title","")}</p>'
                     f'<p style="margin:2px 0 0;font-size:12px;color:#9ca3af">Due: {a.get("due_date","?")} {a.get("due_time","")}</p></div>'
                     f'{st_badge}</div>')
            if st.button("View All Assignments →", key="btn_go_asgn", use_container_width=True):
                st.switch_page(_p("assignments.py"))

        st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)

        # Campus Announcements
        st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">📢 Campus Announcements</p>', unsafe_allow_html=True)
        if not announcements:
            st.info("No announcements published.")
        else:
            for ann in announcements[:3]:
                created = ann.get("created_at", "")[:10]
                card(f'<p style="margin:0;font-size:14px;font-weight:700;color:#ffffff">{ann.get("title","")}</p>'
                     f'<p style="margin:4px 0 0;font-size:12px;color:#9ca3af">{ann.get("content","")[:110]}…</p>'
                     f'<span style="font-size:10px;color:#6b7280;display:block;margin-top:4px">{created}</span>')

    with col_right:
        # Today's Schedule
        st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">📅 Today\'s Lecture Schedule</p>', unsafe_allow_html=True)
        if not today_periods:
            st.info("No classes scheduled for today.")
        else:
            for p in today_periods[:5]:
                subj = p.get("subject") or "Free Period"
                card(f'<div style="display:flex;justify-content:space-between;align-items:center">'
                     f'<div><span style="font-size:11px;color:#6b7280;font-weight:700">Period {p.get("period_number","?")}</span>'
                     f'<p style="margin:2px 0 0;font-size:14px;font-weight:700;color:#ffffff">{subj}</p></div>'
                     f'<span style="font-size:12px;color:#60a5fa;font-family:monospace">{p.get("start_time","")} – {p.get("end_time","")}</span></div>')
            if st.button("Full Timetable →", key="btn_go_tt", use_container_width=True):
                st.switch_page(_p("timetable.py"))

        st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)

        # Quick Links
        st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">⚡ Quick Navigation</p>', unsafe_allow_html=True)
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            if st.button("📊 My Marks & GPA", key="btn_q_marks", use_container_width=True):
                st.switch_page(_p("marks.py"))
            if st.button("👥 Study Connections", key="btn_q_conn", use_container_width=True):
                st.switch_page(_p("connections.py"))
        with col_q2:
            if st.button("📁 Notes Repository", key="btn_q_notes", use_container_width=True):
                st.switch_page(_p("notes.py"))
            if st.button("👤 My Profile", key="btn_q_prof", use_container_width=True):
                st.switch_page(_p("profile.py"))

    # Feature Grid
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">🧠 Explore AI Study Tools</p>', unsafe_allow_html=True)

    f_col1, f_col2, f_col3 = st.columns(3)
    features_list = [
        ("📤", "Study Material", "Upload PDFs or paste notes to index via RAG", f_col1),
        ("💡", "ELI10 Explainer", "Simplify complex technical topics in plain terms", f_col2),
        ("⚡", "Adaptive Quiz", "Interactive quizzes generated from notes", f_col3),
        ("📅", "Revision Planner", "Smart spaced revision schedule", f_col1),
        ("💬", "Document Chat", "Ask questions directly to your uploaded textbooks", f_col2),
        ("🃏", "Flashcards", "Spaced repetition flashcards with hints", f_col3),
    ]

    for icon, title, desc, target_col in features_list:
        with target_col:
            st.markdown(f"""
<div style="background:rgba(17,24,39,0.85);border:1px solid rgba(31,41,55,0.9);border-radius:16px;padding:1.1rem 1.25rem;margin-bottom:0.6rem">
  <div style="font-size:1.4rem;margin-bottom:0.4rem">{icon}</div>
  <p style="font-size:14px;font-weight:700;color:#ffffff;margin:0 0 2px">{title}</p>
  <p style="font-size:12px;color:#9ca3af;margin:0;line-height:1.4">{desc}</p>
</div>""", unsafe_allow_html=True)
            if st.button("Launch", key=f"f_launch_{title}", use_container_width=True):
                st.switch_page(_p("learning.py"))
