"""
pages/marks.py — Student Academic Marks & Grade Report (matching Next.js /marks)
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
    st.info("👆 You are logged in as **Admin**. Use the **⚙️ Admin Hub** to publish marks.")
    st.stop()

st.markdown("""
<div style="margin-bottom:1.5rem">
  <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0 0 .25rem;letter-spacing:-.03em">
    📊 Academic Marks &amp; Progress
  </h1>
  <p style="font-size:.875rem;color:#9ca3af;margin:0">
    Detailed performance analysis, overall grade evaluation, and subject-wise scorecards.
  </p>
</div>""", unsafe_allow_html=True)

summary, err = api_get("/api/marks/summary", timeout=15)
if err:
    st.error(f"Failed to load academic records: {err}")
    st.stop()

if not summary:
    st.info("No marks records published yet for your account.")
    st.stop()

# Overall score overview card
overall_grade = summary.get("overall_grade", "—")
overall_pct = summary.get("overall_percentage", 0.0)
obtained = summary.get("overall_obtained", 0)
max_marks = summary.get("overall_max", 0)

grade_color = {
    "S": "#a855f7",
    "A": "#10b981",
    "B": "#3b82f6",
    "C": "#f59e0b",
    "D": "#ef4444",
}.get(overall_grade, "#6366f1")

st.markdown(f"""
<div style="background:rgba(17,24,39,0.9);border:1px solid rgba(55,65,81,0.8);border-radius:20px;padding:1.5rem 1.8rem;margin-bottom:1.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1.5rem">
  <div>
    <span style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em">Overall Performance</span>
    <h2 style="font-size:1.8rem;font-weight:800;color:#ffffff;margin:0.25rem 0 0.5rem">
      {obtained} <span style="font-size:1rem;color:#6b7280">/ {max_marks} marks</span>
    </h2>
    <p style="font-size:0.875rem;color:#9ca3af;margin:0">
      Academic Average: <strong style="color:#60a5fa">{overall_pct:.1f}%</strong>
    </p>
  </div>
  <div style="text-align:center;padding:0.75rem 1.5rem;background:rgba(31,41,55,0.7);border:1px solid rgba(75,85,99,0.5);border-radius:16px">
    <span style="font-size:10px;font-weight:800;color:#9ca3af;text-transform:uppercase;display:block">Letter Grade</span>
    <span style="font-size:2.8rem;font-weight:900;color:{grade_color};line-height:1">{overall_grade}</span>
  </div>
</div>
""", unsafe_allow_html=True)

subjects = summary.get("subjects", [])
if not subjects:
    st.info("No subject breakdowns published yet.")
else:
    st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">Subject Evaluations</p>', unsafe_allow_html=True)
    for subj in subjects:
        pct = subj.get("percentage", 0)
        grade = subj.get("grade", "—")
        subj_name = subj.get("subject_name", "Unknown Subject")

        with st.expander(f"📚 {subj_name}  —  {pct:.1f}% ({grade})", expanded=True):
            ca, cb, cc, cd = st.columns(4)
            ca.metric("Obtained", subj.get("total_obtained", 0))
            cb.metric("Maximum", subj.get("total_max", 0))
            cc.metric("Percentage", f"{pct:.1f}%")
            cd.metric("Grade", grade)

            marks_data, _ = api_get(f"/api/marks/subject/{subj['subject_id']}", timeout=10)
            if marks_data and marks_data.get("categories"):
                st.markdown('<p style="font-size:12px;font-weight:700;color:#9ca3af;margin:.8rem 0 .4rem">Assessment Categories</p>', unsafe_allow_html=True)
                for cat in marks_data["categories"]:
                    cat_pct = cat.get("percentage", 0)
                    bar_color = "#10b981" if cat_pct >= 75 else "#f59e0b" if cat_pct >= 50 else "#ef4444"
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;margin:.4rem 0 .2rem">'
                        f'<span style="font-size:13px;color:#d1d5db;font-weight:500">{cat.get("category_name","Assessment")}</span>'
                        f'<span style="font-size:13px;font-weight:700;color:{bar_color}">{cat.get("obtained_marks","?")} / {cat.get("max_marks","?")} ({cat_pct:.0f}%)</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.progress(min(cat_pct / 100, 1.0))
