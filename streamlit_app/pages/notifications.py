"""
pages/notifications.py — Notification Center (matching Next.js /notifications)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login
from core.api_client import api_get, api_patch
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Render top identity header banner
render_identity_header()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    🔔 Notification Center
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Campus broadcasts, staff communications, assignment alerts, and system notices.
  </p>
</div>""", unsafe_allow_html=True)

head_col1, head_col2 = st.columns([4, 1.5])
with head_col2:
    if st.button("✓ Mark All as Read", key="btn_mark_all_read", use_container_width=True):
        _, err = api_patch("/api/notifications/read-all")
        if not err:
            st.success("All notifications marked as read!")
            st.rerun()

data, err = api_get("/api/notifications?page_size=50", timeout=15)
if err:
    st.error(f"Failed to load notifications: {err}")
    st.stop()

notifications = data or []
unread_items = [n for n in notifications if not n.get("is_read")]

tab_all, tab_unread = st.tabs([f"All Notifications ({len(notifications)})", f"Unread Only ({len(unread_items)})"])

TYPE_ICON = {
    "assignment": "📋",
    "marks": "📊",
    "timetable": "📅",
    "announcement": "📢",
    "submission": "✅",
    "note": "📁",
    "contact_inquiry": "✉️",
    "general": "🔔",
}

def _render_list(items):
    if not items:
        st.info("No notifications to display.")
        return

    for n in items:
        is_read = n.get("is_read", False)
        bg = "rgba(17,24,39,0.9)" if is_read else "rgba(30,27,75,0.7)"
        border = "rgba(31,41,55,0.9)" if is_read else "rgba(99,102,241,0.5)"
        icon = TYPE_ICON.get(n.get("notif_type", "general"), "🔔")
        created = n.get("created_at", "")[:16].replace("T", " ")

        col_n, col_btn = st.columns([10, 1.5])
        with col_n:
            st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:14px;padding:1rem 1.25rem;margin:0.4rem 0">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
    <span style="font-size:14px;font-weight:700;color:#ffffff">{icon} {n.get('title','Notice')}</span>
    <span style="font-size:11px;color:#6b7280">{created}</span>
  </div>
  <p style="font-size:13px;color:#d1d5db;margin:0;line-height:1.5">{n.get('message','')}</p>
</div>
""", unsafe_allow_html=True)
        with col_btn:
            if not is_read:
                if st.button("Read", key=f"read_notif_{n['id']}", use_container_width=True):
                    api_patch(f"/api/notifications/{n['id']}/read")
                    st.rerun()

with tab_all:
    _render_list(notifications)

with tab_unread:
    _render_list(unread_items)
