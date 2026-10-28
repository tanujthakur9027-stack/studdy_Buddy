"""
pages/classes.py — Academic Management Hub
Provides tabs for Assignments, Marks, Timetable, Notifications, Notes, and Connections,
matching the Next.js academic sections.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, is_admin, _p
from core.api_client import api_get, api_post, api_patch, api_delete, api_request, BACKEND_URL
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Universal Identity Header
render_identity_header()

if is_admin():
    st.info("👆 You are logged in as **Admin**. Use the **⚙️ Admin Hub** from the navigation menu.")
    st.stop()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    🏛️ Classes &amp; Academic Center
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Manage your schedule, coursework, grades, shared notes, and peer study network.
  </p>
</div>""", unsafe_allow_html=True)

# Quick Nav pills
col_pills = st.columns(6)
with col_pills[0]:
    if st.button("📋 Assignments", key="pill_asgn", use_container_width=True):
        st.switch_page(_p("assignments.py"))
with col_pills[1]:
    if st.button("📊 Marks", key="pill_marks", use_container_width=True):
        st.switch_page(_p("marks.py"))
with col_pills[2]:
    if st.button("📅 Timetable", key="pill_tt", use_container_width=True):
        st.switch_page(_p("timetable.py"))
with col_pills[3]:
    if st.button("🔔 Alerts", key="pill_notif", use_container_width=True):
        st.switch_page(_p("notifications.py"))
with col_pills[4]:
    if st.button("📁 Notes", key="pill_notes", use_container_width=True):
        st.switch_page(_p("notes.py"))
with col_pills[5]:
    if st.button("👥 Peers", key="pill_conn", use_container_width=True):
        st.switch_page(_p("connections.py"))

st.divider()

(tab_asgn, tab_marks, tab_tt, tab_notif, tab_notes, tab_conn) = st.tabs([
    "📋 Assignments", "📊 Marks", "📅 Timetable",
    "🔔 Notifications", "📁 Notes", "👥 Connections",
])

# ── Assignments ──
with tab_asgn:
    data, err = api_get("/api/assignments", timeout=15)
    if err:
        st.error(err)
    else:
        assignments = data or []
        filter_status = st.selectbox("Filter", ["All", "Pending", "Submitted", "Evaluated"], key="cls_asgn_filter")
        filtered = assignments
        if filter_status == "Pending":
            filtered = [a for a in assignments if (a.get("submission_status") or "pending") == "pending"]
        elif filter_status == "Submitted":
            filtered = [a for a in assignments if a.get("submission_status") == "submitted"]
        elif filter_status == "Evaluated":
            filtered = [a for a in assignments if a.get("submission_status") == "evaluated"]

        if not filtered:
            st.info("No assignments found.")
        else:
            for a in filtered:
                status = a.get("submission_status") or "pending"
                badge_color = {"pending": "yellow", "submitted": "blue", "evaluated": "green"}.get(status, "yellow")
                with st.expander(f"📋 {a['title']}  —  Due: {a.get('due_date','?')}", expanded=False):
                    st.markdown(badge(status.title(), badge_color), unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Max Marks", a.get("max_marks", "?"))
                    c2.metric("Due Date", a.get("due_date", "?"))
                    c3.metric("Due Time", a.get("due_time", "?"))

                    if a.get("description"):
                        st.markdown(f'<p style="font-size:14px;color:#d1d5db;margin:.5rem 0">{a["description"]}</p>', unsafe_allow_html=True)
                    if a.get("file_url"):
                        st.markdown(f'[📎 Download Assignment File]({BACKEND_URL}{a["file_url"]})')

                    if st.button(f"📅 AI Study Plan for this Task", key=f"cls_plan_{a['id']}"):
                        st.session_state["_planner_prefill_date"] = a.get("due_date", "")
                        st.switch_page(_p("learning.py"))

# ── Marks ──
with tab_marks:
    summary, err = api_get("/api/marks/summary", timeout=15)
    if err:
        st.error(err)
    elif not summary:
        st.info("No marks published yet.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall Obtained", f"{summary.get('overall_obtained',0)} / {summary.get('overall_max',0)}")
        c2.metric("Percentage", f"{summary.get('overall_percentage',0):.1f}%")
        c3.metric("Grade", summary.get("overall_grade", "—"))
        st.divider()
        for subj in summary.get("subjects", []):
            with st.expander(f"📚 {subj.get('subject_name','Unknown')}  —  {subj.get('percentage',0):.0f}% ({subj.get('grade','?')})", expanded=False):
                ca, cb, cc, cd = st.columns(4)
                ca.metric("Obtained", subj.get("total_obtained", 0))
                cb.metric("Maximum", subj.get("total_max", 0))
                cc.metric("Percentage", f"{subj.get('percentage',0):.1f}%")
                cd.metric("Grade", subj.get("grade", "—"))

# ── Timetable ──
with tab_tt:
    data, err = api_get("/api/timetable", timeout=15)
    if err:
        st.error(err)
    elif not data or not data.get("schedule"):
        st.info("No timetable published for your class yet.")
    else:
        schedule = data["schedule"]
        day_names = [d["day"] for d in schedule if d.get("periods")]
        selected_day = st.selectbox("Select Day", day_names, key="cls_tt_day")
        day_data = next((d for d in schedule if d["day"] == selected_day), None)
        if day_data:
            for p in day_data.get("periods", []):
                subj = p.get("subject") or "Free Period"
                color = "#3b82f6" if p.get("subject") else "#4b5563"
                st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-left:4px solid {color};border-radius:12px;padding:0.875rem 1.25rem;margin:0.4rem 0;display:flex;justify-content:space-between">
  <div>
    <span style="font-size:11px;color:#6b7280;font-weight:600">Period {p['period_number']}</span>
    <p style="margin:2px 0 0;font-size:15px;font-weight:700;color:#ffffff">{subj}</p>
    {f'<p style="margin:2px 0 0;font-size:12px;color:#9ca3af">🏫 {p["room"]}</p>' if p.get("room") else ""}
  </div>
  <span style="font-size:13px;color:#60a5fa;font-family:monospace">{p.get('start_time','?')} – {p.get('end_time','?')}</span>
</div>""", unsafe_allow_html=True)

# ── Notifications ──
with tab_notif:
    data, err = api_get("/api/notifications?page_size=20", timeout=15)
    if err:
        st.error(err)
    else:
        notifications = data or []
        if not notifications:
            st.info("No notifications.")
        for n in notifications[:10]:
            is_read = n.get("is_read", False)
            bg = "rgba(17,24,39,0.9)" if is_read else "rgba(30,27,75,0.6)"
            st.markdown(f"""
<div style="background:{bg};border:1px solid rgba(31,41,55,0.9);border-radius:12px;padding:0.75rem 1.2rem;margin:0.3rem 0">
  <p style="margin:0;font-size:13.5px;font-weight:700;color:#ffffff">{n.get('title','')}</p>
  <p style="margin:3px 0 0;font-size:12px;color:#9ca3af">{n.get('message','')}</p>
</div>""", unsafe_allow_html=True)

# ── Notes ──
with tab_notes:
    data, err = api_get("/api/notes", timeout=15)
    if err:
        st.error(err)
    else:
        notes = data or []
        if not notes:
            st.info("No shared notes available.")
        for n in notes[:8]:
            card(f'<p style="margin:0;font-size:14px;font-weight:700;color:#ffffff">{n.get("title","Untitled")} ({n.get("subject","General")})</p>'
                 f'<p style="margin:4px 0 0;font-size:12px;color:#9ca3af">Shared by: {n.get("uploader_name","Peer")}</p>')

# ── Connections ──
with tab_conn:
    data, err = api_get("/api/connections", timeout=15)
    if err:
        st.error(err)
    else:
        connections = data or []
        if not connections:
            st.info("No connections yet.")
        for c in connections:
            peer = c.get("user", {})
            card(f'<p style="margin:0;font-size:14px;font-weight:700;color:#ffffff">{peer.get("full_name","Peer")}</p>'
                 f'<p style="margin:4px 0 0;font-size:12px;color:#9ca3af">{peer.get("email","")} · {peer.get("course","")}</p>')
