"""
pages/connections.py — Peer Network & Study Connections (matching Next.js /connections)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login
from core.api_client import api_get, api_post, api_patch, api_delete
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Render top identity header banner
render_identity_header()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    👥 Peer Network &amp; Connections
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Connect with classmates, share peer notes, collaborate, and study together.
  </p>
</div>""", unsafe_allow_html=True)

tab_my, tab_find, tab_requests = st.tabs(["👥 Connected Peers", "🔍 Find Students", "📨 Incoming Requests"])

with tab_my:
    data, err = api_get("/api/connections", timeout=15)
    if err:
        st.error(f"Failed to load connections: {err}")
    else:
        connections = data or []
        if not connections:
            st.info("You haven't added any peer connections yet. Use the 'Find Students' tab to connect!")
        else:
            st.caption(f"{len(connections)} peer connection(s)")
            for c in connections:
                peer = c.get("user", {})
                col_peer, col_rm = st.columns([5, 1.5])
                with col_peer:
                    course_info = f"{peer.get('course','')} {peer.get('branch','')}"
                    sem_info = f"Sem {peer.get('semester','?')}" if peer.get('semester') else ""
                    st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-radius:14px;padding:1rem 1.25rem;margin:0.4rem 0">
  <p style="margin:0;font-size:15px;font-weight:700;color:#ffffff">{peer.get('full_name','Student')}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#9ca3af">{peer.get('email','')} · {course_info} {sem_info}</p>
</div>
""", unsafe_allow_html=True)
                with col_rm:
                    if st.button("Remove", key=f"rm_peer_{c['id']}", use_container_width=True):
                        _, rm_err = api_delete(f"/api/connections/{c['id']}")
                        if not rm_err:
                            st.success("Connection removed.")
                            st.rerun()

with tab_find:
    query = st.text_input("Search classmates by name, student ID, course or semester...", placeholder="e.g. John, CSE, 2024")
    if query:
        res, err = api_get(f"/api/connections/search?q={query}", timeout=15)
        if err:
            st.error(err)
        else:
            students = res or []
            if not students:
                st.info("No students found matching your search.")
            else:
                for s in students:
                    col_info, col_act = st.columns([5, 2])
                    with col_info:
                        st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-radius:14px;padding:1rem 1.25rem;margin:0.4rem 0">
  <p style="margin:0;font-size:15px;font-weight:700;color:#ffffff">{s.get('full_name','Student')}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#9ca3af">{s.get('course','')} · {s.get('branch','')} · Sem {s.get('semester','?')}</p>
</div>
""", unsafe_allow_html=True)
                    with col_act:
                        status = s.get("connection_status", "none")
                        if status == "none":
                            if st.button("Connect +", key=f"req_{s['user_id']}", use_container_width=True):
                                api_post("/api/connections/request", json={"to_user_id": s["user_id"]})
                                st.success("Request sent!")
                                st.rerun()
                        elif status == "pending":
                            st.markdown('<span style="color:#f59e0b;font-weight:600;font-size:13px;display:block;margin-top:1rem">⏳ Pending</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span style="color:#10b981;font-weight:600;font-size:13px;display:block;margin-top:1rem">✅ Connected</span>', unsafe_allow_html=True)

with tab_requests:
    reqs_data, err = api_get("/api/connections/requests/incoming", timeout=15)
    if err:
        st.error(err)
    else:
        incoming = reqs_data or []
        if not incoming:
            st.info("No pending connection requests.")
        else:
            for r in incoming:
                sender = r.get("from_user", {})
                col_snd, col_ok, col_no = st.columns([5, 1.2, 1.2])
                with col_snd:
                    st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-radius:14px;padding:1rem 1.25rem;margin:0.4rem 0">
  <p style="margin:0;font-size:15px;font-weight:700;color:#ffffff">{sender.get('full_name','Classmate')}</p>
  <p style="margin:4px 0 0;font-size:12px;color:#9ca3af">{sender.get('email','')}</p>
</div>
""", unsafe_allow_html=True)
                with col_ok:
                    if st.button("Accept", key=f"acc_{r['id']}", use_container_width=True):
                        api_patch(f"/api/connections/request/{r['id']}", json={"action": "accept"})
                        st.success("Accepted!")
                        st.rerun()
                with col_no:
                    if st.button("Decline", key=f"dec_{r['id']}", use_container_width=True):
                        api_patch(f"/api/connections/request/{r['id']}", json={"action": "reject"})
                        st.rerun()
