"""
pages/assignments.py — Student Assignments View (matching Next.js /assignments)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, is_admin, _p
from core.api_client import api_get, api_request, BACKEND_URL
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Render top identity header banner
render_identity_header()

if is_admin():
    st.info("👆 You are logged in as **Admin**. Use the **⚙️ Admin Hub** to manage assignments.")
    st.stop()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    📋 Assignments
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Track upcoming course tasks, view deadlines, and submit your homework attachments.
  </p>
</div>""", unsafe_allow_html=True)

data, err = api_get("/api/assignments", timeout=15)
if err:
    st.error(f"Failed to load assignments: {err}")
    st.stop()

assignments = data or []

# Calculate quick metrics
total_count = len(assignments)
pending_count = sum(1 for a in assignments if (a.get("submission_status") or "pending") == "pending")
submitted_count = sum(1 for a in assignments if a.get("submission_status") == "submitted")
evaluated_count = sum(1 for a in assignments if a.get("submission_status") == "evaluated")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total", total_count)
m2.metric("Pending", pending_count)
m3.metric("Submitted", submitted_count)
m4.metric("Evaluated", evaluated_count)

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

filter_status = st.selectbox(
    "Filter Assignments",
    ["All", "Pending", "Submitted", "Evaluated"],
    index=0,
)

filtered = assignments
if filter_status == "Pending":
    filtered = [a for a in assignments if (a.get("submission_status") or "pending") == "pending"]
elif filter_status == "Submitted":
    filtered = [a for a in assignments if a.get("submission_status") == "submitted"]
elif filter_status == "Evaluated":
    filtered = [a for a in assignments if a.get("submission_status") == "evaluated"]

if not filtered:
    st.info(f"No {filter_status.lower() if filter_status != 'All' else ''} assignments found.")
else:
    for a in filtered:
        status = a.get("submission_status") or "pending"
        badge_color = {"pending": "yellow", "submitted": "blue", "evaluated": "green"}.get(status, "yellow")

        with st.expander(f"📋 {a.get('title', 'Assignment')}  —  Due: {a.get('due_date', '?')}", expanded=(status == "pending")):
            st.markdown(f"Status: {badge(status.title(), badge_color)}", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Max Marks", a.get("max_marks", "?"))
            c2.metric("Due Date", a.get("due_date", "?"))
            c3.metric("Due Time", a.get("due_time", "?"))

            if a.get("description"):
                st.markdown(
                    f'<p style="font-size:14px;color:#d1d5db;background:rgba(31,41,55,0.4);padding:10px 14px;border-radius:10px;margin:.75rem 0">{a["description"]}</p>',
                    unsafe_allow_html=True,
                )

            if a.get("file_url"):
                st.markdown(f'[📎 Download Assignment Handout / File]({BACKEND_URL}{a["file_url"]})')

            col_plan, _ = st.columns([2, 5])
            with col_plan:
                if st.button(f"📅 AI Study Plan for this Task", key=f"plan_{a['id']}"):
                    st.session_state["_planner_prefill_date"] = a.get("due_date", "")
                    st.switch_page(_p("learning.py"))

            if a.get("my_submission"):
                sub = a["my_submission"]
                st.markdown("---")
                st.markdown(f'<p style="font-size:13px;font-weight:600;color:#10b981">✅ Submitted on {sub.get("submitted_at","?")[:10]}</p>', unsafe_allow_html=True)
                if sub.get("is_evaluated"):
                    st.markdown(f'<p style="font-size:15px;font-weight:700;color:#ffffff">Marks Obtained: {sub.get("marks_obtained","?")} / {a.get("max_marks","?")}</p>', unsafe_allow_html=True)
                    if sub.get("feedback"):
                        st.info(f"Instructor Feedback: {sub['feedback']}")
            elif status == "pending":
                st.markdown("---")
                st.markdown('<p style="font-size:13px;font-weight:700;color:#f59e0b">📤 Submit Your Work</p>', unsafe_allow_html=True)
                with st.form(f"submit_{a['id']}"):
                    notes_text = st.text_area("Submission Notes / Comments (optional)", height=80, key=f"n_{a['id']}")
                    file = st.file_uploader(
                        "Attach file (PDF, DOCX, PNG, GIF, ZIP...)",
                        type=["pdf", "docx", "doc", "pptx", "zip", "png", "jpg", "jpeg", "gif", "webp"],
                        key=f"f_{a['id']}",
                    )
                    sub_btn = st.form_submit_button("Submit Assignment →", type="primary")

                if sub_btn:
                    files = {"file": (file.name, file.getvalue(), file.type)} if file else None
                    _, err2 = api_request(
                        "POST",
                        f"/api/assignments/{a['id']}/submit",
                        data={"notes": notes_text} if notes_text else {},
                        files=files,
                    )
                    if err2:
                        st.error(err2)
                    else:
                        st.success("Assignment submitted successfully!")
                        st.rerun()
