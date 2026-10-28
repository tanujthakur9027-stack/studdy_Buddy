"""
pages/notes.py — Study Notes & Resource Repository (matching Next.js /notes)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login
from core.api_client import api_get, api_request, BACKEND_URL
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Render top identity header banner
render_identity_header()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    📁 Notes &amp; Study Materials
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Discover and contribute lecture summaries, cheat sheets, and academic resources.
  </p>
</div>""", unsafe_allow_html=True)

tab_browse, tab_upload = st.tabs(["📚 Browse Resources", "📤 Upload New Material"])

with tab_browse:
    search_q = st.text_input("🔍 Search notes by title, topic or tag...", placeholder="e.g. Operating Systems, Calculus, AI")
    data, err = api_get(f"/api/notes?search={search_q}" if search_q else "/api/notes", timeout=15)
    if err:
        st.error(f"Failed to load notes: {err}")
    else:
        notes = data or []
        if not notes:
            st.info("No study notes found matching your criteria.")
        else:
            st.caption(f"Showing {len(notes)} resource(s)")
            for n in notes:
                with st.expander(f"📄 {n.get('title','Untitled')}  —  {n.get('subject','General')}", expanded=False):
                    st.markdown(f"Visibility: {badge(n.get('visibility','class').title(), 'blue')}", unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Semester", n.get("semester") or "—")
                    c2.metric("Course", n.get("course") or "—")
                    c3.metric("Uploaded By", n.get("uploader_name", "Student"))

                    if n.get("description"):
                        st.markdown(f'<p style="font-size:13px;color:#d1d5db;margin:.75rem 0">{n["description"]}</p>', unsafe_allow_html=True)

                    dl_url = f"{BACKEND_URL}/api/notes/{n['id']}/download"
                    st.markdown(
                        f'<a href="{dl_url}" target="_blank" style="display:inline-block;background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;padding:8px 18px;border-radius:10px;font-size:13px;font-weight:700;text-decoration:none;margin-top:0.5rem">'
                        f'⬇️ Download Resource'
                        f'</a>',
                        unsafe_allow_html=True,
                    )

with tab_upload:
    with st.form("upload_study_note_form"):
        st.markdown("**Share Note with Peers**")
        note_title = st.text_input("Title *", placeholder="e.g. Data Structures Unit 3 Summary")
        note_desc = st.text_area("Description / Summary", height=80, placeholder="Key topics covered in this document...")

        c1, c2 = st.columns(2)
        subj = c1.text_input("Subject", placeholder="e.g. Computer Science")
        sem = c2.text_input("Semester", placeholder="e.g. 4")

        c3, c4 = st.columns(2)
        crs = c3.text_input("Course", placeholder="e.g. B.Tech CSE")
        vis = c4.selectbox("Visibility", ["connections", "class", "public"])

        tags_str = st.text_input("Tags (comma-separated)", placeholder="graphs, sorting, algorithms")
        file_obj = st.file_uploader(
            "Document File * (PDF, DOCX, PPTX, PNG, GIF, TXT...)",
            type=["pdf", "docx", "doc", "pptx", "ppt", "png", "jpg", "jpeg", "txt", "gif"],
        )

        sub_note = st.form_submit_button("Upload Material →", type="primary")

    if sub_note:
        if not note_title or not file_obj:
            st.error("Title and document file are required.")
        else:
            files_payload = {"file": (file_obj.name, file_obj.getvalue(), file_obj.type or "application/octet-stream")}
            form_payload = {
                "title": note_title,
                "description": note_desc,
                "subject": subj,
                "semester": sem,
                "course": crs,
                "visibility": vis,
                "tags": tags_str,
            }
            _, upload_err = api_request("POST", "/api/notes", timeout=60, data=form_payload, files=files_payload)
            if upload_err:
                st.error(upload_err)
            else:
                st.success("Note uploaded and shared successfully!")
                st.rerun()
