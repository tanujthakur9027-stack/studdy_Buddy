"""
pages/classes.py — Classes & Assignments

Student tabs:
  1. Assignments — list, filter, submit with file/GIF attachment
  2. Marks — grades by subject with progress bars
  3. Timetable — weekly schedule with lunch break
  4. Notifications — mark read, types with icons
  5. Notes — upload and browse class notes
  6. Connections — find + manage peer connections

Planner integration: "Plan for this assignment" button pre-fills the planner.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, is_admin, _p
from core.api_client import api_get, api_post, api_patch, api_delete, api_request, BACKEND_URL
from core.media_uploader import render_media_uploader


inject_global_css()
require_login()
page_enter()

# Admins have their own dedicated panel — redirect them away from this student page
if is_admin():
    st.info("👆 You are logged in as **Admin**. Use the **⚙️ Admin Panel** from the navigation menu.")
    st.stop()

st.markdown("""
<div style="margin-bottom:1.5rem;animation:fadeUp .4s both">
  <h1 style="font-size:1.6rem;font-weight:800;color:#fafafa;margin:0 0 .25rem;letter-spacing:-.03em">
    🏛️ Classes &amp; Assignments
  </h1>
  <p style="font-size:.875rem;color:#71717a;margin:0">Manage your schedule, assignments and classmates.</p>
</div>""", unsafe_allow_html=True)

def _sec(t): st.markdown(f'<p style="font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:.07em;margin:.25rem 0 .75rem">{t}</p>', unsafe_allow_html=True)
def _tab_head(t, s=""): st.markdown(f'<p style="font-size:1rem;font-weight:700;color:#fafafa;margin:0 0 .2rem">{t}</p>{"<p style=font-size:.8rem;color:#71717a;margin:0 0 1rem>"+s+"</p>" if s else ""}', unsafe_allow_html=True)

(tab_asgn, tab_marks, tab_tt, tab_notif, tab_notes, tab_conn) = st.tabs([
    "📋 Assignments", "📊 Marks", "📅 Timetable",
    "🔔 Notifications", "📁 Notes", "👥 Connections",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Assignments
# ─────────────────────────────────────────────────────────────────────────────
with tab_asgn:
    _tab_head("My Assignments", "View and submit your assignments.")
    data, err = api_get("/api/assignments", timeout=15)
    if err:
        st.error(err)
    else:
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
        else:
            for a in filtered:
                status = a.get("submission_status") or "pending"
                badge_color = {"pending": "yellow", "submitted": "blue", "evaluated": "green"}.get(status, "yellow")
                with st.expander(f"📋 {a['title']}", expanded=False):
                    # Badge rendered inside body — expander labels don't support HTML
                    st.markdown(badge(status.title(), badge_color), unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Max Marks", a.get("max_marks", "?"))
                    c2.metric("Due Date",  a.get("due_date", "?"))
                    c3.metric("Due Time",  a.get("due_time", "?"))

                    if a.get("description"):
                        st.markdown(f'<p style="font-size:14px;color:#d4d4d8;margin:.5rem 0">{a["description"]}</p>',
                                    unsafe_allow_html=True)
                    if a.get("file_url"):
                        st.markdown(f'[📎 Download Assignment File]({BACKEND_URL}{a["file_url"]})')

                    # Quick plan button
                    if st.button(f"📅 Plan for this assignment", key=f"plan_{a['id']}"):
                        st.session_state["_planner_prefill_date"] = a.get("due_date", "")
                        st.switch_page(_p("learning.py"))

                    if a.get("my_submission"):
                        sub = a["my_submission"]
                        st.markdown("---")
                        st.markdown(f'<p style="font-size:13px;font-weight:600;color:#22c55e">✅ Submitted on {sub.get("submitted_at","?")[:10]}</p>',
                                    unsafe_allow_html=True)
                        if sub.get("is_evaluated"):
                            st.markdown(f'<p style="font-size:15px;font-weight:700;color:#fafafa">Marks: {sub.get("marks_obtained","?")} / {a.get("max_marks","?")}</p>',
                                        unsafe_allow_html=True)
                            if sub.get("feedback"):
                                st.info(f"💬 {sub['feedback']}")
                    elif status == "pending":
                        st.markdown("---")
                        st.markdown('<p style="font-size:13px;font-weight:600;color:#f59e0b">📤 Submit Your Work</p>',
                                    unsafe_allow_html=True)
                        with st.form(f"submit_{a['id']}"):
                            notes_text = st.text_area("Notes / Comments (optional)", height=80, key=f"n_{a['id']}")
                            # GIF-capable file attachment
                            file = st.file_uploader("Attach file (optional — PDF, DOCX, PNG, GIF…)",
                                                     type=["pdf","docx","doc","pptx","zip","png","jpg","jpeg","gif","webp"],
                                                     key=f"f_{a['id']}")
                            sub_btn = st.form_submit_button("Submit Assignment", type="primary")
                        if sub_btn:
                            files = {"file": (file.name, file.getvalue(), file.type)} if file else None
                            _, err2 = api_request("POST", f"/api/assignments/{a['id']}/submit",
                                                   data={"notes": notes_text} if notes_text else {},
                                                   files=files)
                            if err2:
                                st.error(err2)
                            else:
                                st.success("Submitted successfully!")
                                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Marks
# ─────────────────────────────────────────────────────────────────────────────
with tab_marks:
    _tab_head("My Marks", "View published grades by subject.")
    summary, err = api_get("/api/marks/summary", timeout=15)
    if err:
        st.error(err)
    elif not summary:
        st.info("No marks published yet.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall", f"{summary.get('overall_obtained',0)} / {summary.get('overall_max',0)}")
        c2.metric("Percentage", f"{summary.get('overall_percentage',0):.1f}%")
        c3.metric("Grade", summary.get("overall_grade", "—"))
        st.divider()
        for subj in summary.get("subjects", []):
            with st.expander(f"📚 {subj.get('subject_name','Unknown')}  —  {subj.get('percentage',0):.0f}%  {badge(subj.get('grade','?'),'purple')}", expanded=False):
                ca, cb, cc, cd = st.columns(4)
                ca.metric("Obtained",    subj.get("total_obtained", 0))
                cb.metric("Maximum",     subj.get("total_max", 0))
                cc.metric("Percentage",  f"{subj.get('percentage',0):.1f}%")
                cd.metric("Grade",       subj.get("grade", "—"))
                marks_data, _ = api_get(f"/api/marks/subject/{subj['subject_id']}", timeout=10)
                if marks_data and marks_data.get("categories"):
                    st.markdown('<p style="font-size:12px;font-weight:600;color:#a1a1aa;margin:.75rem 0 .5rem">Breakdown</p>',
                                unsafe_allow_html=True)
                    for cat in marks_data["categories"]:
                        pct = cat.get("percentage", 0)
                        bar_color = "#22c55e" if pct >= 75 else "#f59e0b" if pct >= 50 else "#ef4444"
                        st.markdown(f'<div style="display:flex;justify-content:space-between;margin:.35rem 0"><span style="font-size:13px;color:#d4d4d8">{cat.get("category_name","?")}</span><span style="font-size:13px;font-weight:600;color:{bar_color}">{cat.get("obtained_marks","?")} / {cat.get("max_marks","?")} ({pct:.0f}%)</span></div>',
                                    unsafe_allow_html=True)
                        st.progress(min(pct / 100, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Timetable
# ─────────────────────────────────────────────────────────────────────────────
with tab_tt:
    _tab_head("Class Timetable", "Your weekly class schedule.")
    data, err = api_get("/api/timetable", timeout=15)
    if err:
        st.error(err)
    elif not data or not data.get("schedule"):
        st.info("No timetable published for your class yet.")
    else:
        schedule    = data["schedule"]
        lunch_start = data.get("lunch_start", "")
        lunch_end   = data.get("lunch_end", "")
        lunch_after = data.get("lunch_after_period", 4)
        day_names   = [d["day"] for d in schedule if d.get("periods")]
        selected_day = st.selectbox("Select Day", day_names, key="tt_day")
        day_data = next((d for d in schedule if d["day"] == selected_day), None)
        if day_data:
            for p in day_data.get("periods", []):
                if p["period_number"] == lunch_after + 1 and lunch_start:
                    st.markdown(f"""
<div style="background:#422006;border:1px solid #92400e;border-radius:10px;padding:.75rem 1rem;margin:.5rem 0;text-align:center">
  <span style="color:#fbbf24;font-weight:600;font-size:14px">🍽️ Lunch Break · {lunch_start} – {lunch_end}</span>
</div>""", unsafe_allow_html=True)
                subj  = p.get("subject") or "Free Period"
                color = "#6366f1" if p.get("subject") else "#3f3f46"
                st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-left:3px solid {color};
     border-radius:10px;padding:.875rem 1.25rem;margin:.4rem 0;display:flex;justify-content:space-between">
  <div>
    <span style="font-size:11px;color:#52525b;font-weight:600">Period {p['period_number']}</span>
    <p style="margin:2px 0 0;font-size:15px;font-weight:600;color:#fafafa">{subj}</p>
    {f'<p style="margin:2px 0 0;font-size:12px;color:#71717a">🏫 {p["room"]}</p>' if p.get("room") else ""}
  </div>
  <span style="font-size:13px;color:#71717a">{p.get('start_time','?')} – {p.get('end_time','?')}</span>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Notifications
# ─────────────────────────────────────────────────────────────────────────────
with tab_notif:
    _tab_head("Notifications", "Your alerts and updates.")
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("✓ Mark all read"):
            _, err = api_patch("/api/notifications/read-all")
            if not err:
                st.success("All marked as read!")
                st.rerun()
    data, err = api_get("/api/notifications?page_size=50", timeout=15)
    if err:
        st.error(err)
    else:
        notifications = data or []
        if not notifications:
            st.info("No notifications yet.")
        TYPE_ICON = {"assignment":"📋","marks":"📊","timetable":"📅","announcement":"📢",
                     "submission":"✅","note":"📁","general":"🔔"}
        for n in notifications:
            is_read = n.get("is_read", False)
            bg = "#18181b" if is_read else "#1e1b4b"
            border = "#27272a" if is_read else "#6366f1"
            icon = TYPE_ICON.get(n.get("notif_type", "general"), "🔔")
            created = n.get("created_at", "")[:16].replace("T", " ")
            col_n, col_btn = st.columns([10, 1])
            with col_n:
                st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;padding:.875rem 1.25rem;margin:.4rem 0">
  <div style="display:flex;justify-content:space-between">
    <p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{icon} {n.get('title','')}</p>
    <span style="font-size:11px;color:#52525b">{created}</span>
  </div>
  <p style="margin:4px 0 0;font-size:13px;color:#a1a1aa">{n.get('message','')}</p>
</div>""", unsafe_allow_html=True)
            with col_btn:
                if not is_read:
                    if st.button("✓", key=f"notif_{n['id']}"):
                        api_patch(f"/api/notifications/{n['id']}/read")
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Notes
# ─────────────────────────────────────────────────────────────────────────────
with tab_notes:
    _tab_head("Notes & Resources", "Share and discover study notes.")
    upload_tab, browse_tab = st.tabs(["📤 Upload Note", "📚 Browse Notes"])

    with upload_tab:
        with st.form("upload_note_form"):
            title       = st.text_input("Title *")
            description = st.text_area("Description", height=80)
            c1, c2 = st.columns(2)
            subject    = c1.text_input("Subject")
            semester   = c2.text_input("Semester")
            c3, c4 = st.columns(2)
            course     = c3.text_input("Course")
            visibility = c4.selectbox("Visibility", ["connections", "class", "public"])
            tags       = st.text_input("Tags (comma-separated)", placeholder="maths, calculus")
            file       = st.file_uploader("File *",
                                           type=["pdf","docx","doc","pptx","ppt","png","jpg","jpeg","txt","gif"])
            submit_n   = st.form_submit_button("Upload Note", type="primary")

        if submit_n:
            if not title or not file:
                st.error("Title and file are required.")
            else:
                files_data = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
                form_data  = {"title": title, "description": description, "subject": subject,
                               "semester": semester, "course": course, "visibility": visibility, "tags": tags}
                _, err = api_request("POST", "/api/notes", timeout=60, data=form_data, files=files_data)
                if err:
                    st.error(err)
                else:
                    st.success("Note uploaded!")
                    st.rerun()

    with browse_tab:
        search = st.text_input("Search notes", placeholder="Search by title, subject or tags…")
        data, err = api_get(f"/api/notes?search={search}" if search else "/api/notes", timeout=15)
        if err:
            st.error(err)
        else:
            notes = data or []
            if not notes:
                st.info("No notes found.")
            for n in notes:
                with st.expander(f"📄 {n.get('title','')}  —  {n.get('subject','')}", expanded=False):
                    st.markdown(badge(n.get('visibility','?'), 'blue'), unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Semester",  n.get("semester") or "—")
                    c2.metric("Course",    n.get("course") or "—")
                    c3.metric("Shared by", n.get("uploader_name", "?"))
                    if n.get("description"):
                        st.caption(n["description"])
                    st.markdown(f'<a href="{BACKEND_URL}/api/notes/{n["id"]}/download" target="_blank" style="display:inline-block;background:#6366f1;color:#fff;padding:6px 14px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none">⬇️ Download</a>',
                                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: Connections
# ─────────────────────────────────────────────────────────────────────────────
with tab_conn:
    _tab_head("Connections", "Connect with classmates to share notes and collaborate.")
    conn_tab, search_tab, req_tab = st.tabs(["👥 My Connections", "🔍 Find Students", "📨 Requests"])

    with conn_tab:
        data, err = api_get("/api/connections", timeout=15)
        if err:
            st.error(err)
        else:
            connections = data or []
            if not connections:
                st.info("No connections yet.")
            for c in connections:
                peer = c.get("user", {})
                col_peer, col_rm = st.columns([4, 1])
                with col_peer:
                    card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{peer.get('full_name','?')}</p>
<p style="margin:3px 0 0;font-size:12px;color:#71717a">{peer.get('course','')} {peer.get('branch','')} · Sem {peer.get('semester','?')}</p>""")
                with col_rm:
                    if st.button("Remove", key=f"remove_{c['id']}"):
                        _, err = api_delete(f"/api/connections/{c['id']}")
                        if not err:
                            st.rerun()

    with search_tab:
        search = st.text_input("Search by name, student ID, course or semester")
        if search:
            data, err = api_get(f"/api/connections/search?q={search}", timeout=15)
            if err:
                st.error(err)
            else:
                for s in (data or []):
                    col_s, col_btn = st.columns([4, 1])
                    with col_s:
                        card(f"""
<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{s.get('full_name','?')}</p>
<p style="margin:3px 0 0;font-size:12px;color:#71717a">{s.get('course','')} · {s.get('branch','')} · Sem {s.get('semester','?')}</p>""")
                    with col_btn:
                        cs = s.get("connection_status", "none")
                        if cs == "none":
                            if st.button("Connect", key=f"conn_{s['user_id']}"):
                                api_post("/api/connections/request", json={"to_user_id": s["user_id"]})
                                st.rerun()
                        elif cs == "pending":
                            st.caption("⏳ Pending")
                        else:
                            st.caption("✅ Connected")

    with req_tab:
        data, err = api_get("/api/connections/requests/incoming", timeout=15)
        if err:
            st.error(err)
        else:
            reqs = data or []
            if not reqs:
                st.info("No pending requests.")
            for r in reqs:
                sender = r.get("from_user", {})
                col_r, col_acc, col_rej = st.columns([4, 1, 1])
                with col_r:
                    card(f'<p style="margin:0;font-size:14px;font-weight:600;color:#fafafa">{sender.get("full_name","?")}</p>')
                with col_acc:
                    if st.button("✅", key=f"acc_{r['id']}"):
                        api_patch(f"/api/connections/request/{r['id']}", json={"action": "accept"})
                        st.rerun()
                with col_rej:
                    if st.button("❌", key=f"rej_{r['id']}"):
                        api_patch(f"/api/connections/request/{r['id']}", json={"action": "reject"})
                        st.rerun()
