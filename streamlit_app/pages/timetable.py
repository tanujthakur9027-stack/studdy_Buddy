"""
pages/timetable.py — Student Weekly Schedule & Timetable (matching Next.js /timetable)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, badge, card
from core.animations import page_enter
from core.auth_state import require_login, is_admin
from core.api_client import api_get
from core.header import render_identity_header

inject_global_css()
require_login()
page_enter()

# Render top identity header banner
render_identity_header()

if is_admin():
    st.info("👆 You are logged in as **Admin**. Use the **⚙️ Admin Hub** to configure schedules.")
    st.stop()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    📅 Class Timetable &amp; Schedule
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Weekly lecture schedule, classrooms, break intervals, and subject distribution.
  </p>
</div>""", unsafe_allow_html=True)

data, err = api_get("/api/timetable", timeout=15)
if err:
    st.error(f"Failed to load timetable: {err}")
    st.stop()

if not data or not data.get("schedule"):
    st.info("No schedule published for your enrolled class yet.")
    st.stop()

schedule = data["schedule"]
lunch_start = data.get("lunch_start", "")
lunch_end = data.get("lunch_end", "")
lunch_after = data.get("lunch_after_period", 4)

day_names = [d["day"] for d in schedule if d.get("periods")]
if not day_names:
    st.info("No active lecture periods found in the schedule.")
    st.stop()

selected_day = st.selectbox("Select Day of Week", day_names, index=0)
day_data = next((d for d in schedule if d["day"] == selected_day), None)

if day_data:
    periods = day_data.get("periods", [])
    if not periods:
        st.info(f"No classes scheduled for {selected_day}.")
    else:
        for p in periods:
            # Check for lunch break
            if p["period_number"] == lunch_after + 1 and lunch_start:
                st.markdown(f"""
<div style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:0.75rem 1rem;margin:0.6rem 0;text-align:center">
  <span style="color:#fbbf24;font-weight:700;font-size:13px">🍽️ Lunch &amp; Refreshment Break · {lunch_start} – {lunch_end}</span>
</div>
""", unsafe_allow_html=True)

            subj = p.get("subject") or "Free Period"
            is_free = not bool(p.get("subject"))
            accent = "#4b5563" if is_free else "#3b82f6"
            room_text = f"🏫 Room / Lab: {p['room']}" if p.get("room") else ""

            st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(31,41,55,0.9);border-left:4px solid {accent};border-radius:14px;padding:1rem 1.25rem;margin:0.5rem 0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
  <div>
    <span style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase">Period {p['period_number']}</span>
    <p style="font-size:15px;font-weight:700;color:#ffffff;margin:2px 0">{subj}</p>
    <p style="font-size:12px;color:#9ca3af;margin:0">{room_text}</p>
  </div>
  <div style="font-family:monospace;font-size:13px;font-weight:600;color:#60a5fa;background:rgba(59,130,246,0.1);padding:4px 12px;border-radius:8px;border:1px solid rgba(59,130,246,0.2)">
    {p.get('start_time', '?')} – {p.get('end_time', '?')}
  </div>
</div>
""", unsafe_allow_html=True)
