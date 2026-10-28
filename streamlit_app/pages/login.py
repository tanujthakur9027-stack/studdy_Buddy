"""
pages/login.py — StudyBuddy AI Login & Registration Page.
Styled to match the modern Next.js interface with dual Student/Admin portal toggle.
"""
from __future__ import annotations

import sys
import re
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css
from core.animations import login_card_css, shake_anim, success_checkmark, page_enter
from core.auth_state import is_logged_in, do_login, do_register

inject_global_css()
login_card_css()
page_enter()

# Redirect if already logged in
if is_logged_in():
    st.rerun()

# ── Manage session state for portal mode ─────────────────────────────────────
if "_portal" not in st.session_state:
    st.session_state["_portal"] = "student"  # "student" | "admin"
if "_auth_mode" not in st.session_state:
    st.session_state["_auth_mode"] = "login"  # "login" | "register"

portal = st.session_state["_portal"]
auth_mode = st.session_state["_auth_mode"]

# ── Password strength helper ──────────────────────────────────────────────────
def _password_strength(pw: str) -> tuple[int, str]:
    score = 0
    if len(pw) >= 8:                      score += 1
    if len(pw) >= 12:                     score += 1
    if re.search(r"[A-Z]", pw):          score += 1
    if re.search(r"[0-9!@#$%^&*]", pw): score += 1
    labels = ["", "Weak", "Fair", "Good", "Strong"]
    return score, labels[score]


def _strength_bar(pw: str) -> None:
    score, label = _password_strength(pw)
    if not pw:
        return
    pct = score * 25
    colors = ["", "#ef4444", "#f59e0b", "#3b82f6", "#22c55e"]
    color = colors[max(0, score)]
    st.markdown(f"""
<div style="margin-top:.25rem">
  <div style="height:4px;background:#27272a;border-radius:99px;overflow:hidden">
    <div style="width:{pct}%;height:100%;background:{color};
         transition:width 0.3s,background 0.3s;border-radius:99px"></div>
  </div>
  <p style="font-size:11px;color:{color};margin:.2rem 0 0">{label}</p>
</div>""", unsafe_allow_html=True)


# ── CSS Overrides to match Image 1 ─────────────────────────────────────────────
is_admin_mode = (portal == "admin" and auth_mode == "login")

card_border_color = "rgba(245, 158, 11, 0.3)" if is_admin_mode else "rgba(59, 130, 246, 0.3)"
card_glow_color   = "rgba(245, 158, 11, 0.08)" if is_admin_mode else "rgba(59, 130, 246, 0.08)"
btn_gradient      = "linear-gradient(135deg, #d97706 0%, #f59e0b 50%, #eab308 100%)" if is_admin_mode else "linear-gradient(135deg, #2563eb 0%, #6366f1 50%, #9333ea 100%)"
btn_text_color    = "#000000" if is_admin_mode else "#ffffff"

st.markdown(f"""
<style>
/* Centered container with max width matching Next.js app */
.block-container {{
  max-width: 480px !important;
  margin: 0 auto !important;
  padding-top: 2rem !important;
  padding-bottom: 3.5rem !important;
}}

/* Top atmospheric background glow */
.stApp::before {{
  content: "";
  position: fixed;
  top: 10%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 520px;
  height: 300px;
  background: radial-gradient(circle, rgba(99,102,241,0.18) 0%, rgba(37,99,235,0.08) 50%, transparent 80%);
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}}

/* Dual Portal Switcher buttons */
div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {{
  border-radius: 14px !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  height: 46px !important;
  transition: all 0.2s ease !important;
}}

div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {{
  background: rgba(17, 24, 39, 0.7) !important;
  border: 1px solid #1f2937 !important;
  color: #9ca3af !important;
}}
div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[data-testid="baseButton-secondary"]:hover {{
  background: rgba(31, 41, 55, 0.9) !important;
  color: #ffffff !important;
  border-color: #374151 !important;
}}

/* Active button style */
div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {{
  background: {btn_gradient} !important;
  border: 1px solid {card_border_color} !important;
  color: {btn_text_color} !important;
  box-shadow: 0 4px 18px {card_glow_color} !important;
}}

/* Card Container */
div[data-testid="stForm"] {{
  background: rgba(17, 24, 39, 0.92) !important;
  border: 1px solid {card_border_color} !important;
  border-radius: 26px !important;
  padding: 1.85rem 1.75rem 1.6rem !important;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6), 0 0 35px {card_glow_color} !important;
  backdrop-filter: blur(16px);
  position: relative;
  z-index: 10;
}}

/* Form Input Fields */
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] {{
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  border-radius: 14px !important;
  color: #ffffff !important;
  padding: 10px 14px !important;
  font-size: 13.5px !important;
}}
[data-testid="stTextInput"] input:focus {{
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.3) !important;
}}
[data-testid="stTextInput"] label {{
  font-size: 12px !important;
  font-weight: 600 !important;
  color: #cbd5e1 !important;
  margin-bottom: 5px !important;
}}

/* Form Submit Button */
div[data-testid="stForm"] button[data-testid="baseButton-primary"] {{
  background: {btn_gradient} !important;
  border: none !important;
  border-radius: 14px !important;
  color: {btn_text_color} !important;
  font-weight: 800 !important;
  font-size: 13.5px !important;
  height: 48px !important;
  box-shadow: 0 6px 20px {card_glow_color} !important;
  margin-top: 0.5rem !important;
}}
div[data-testid="stForm"] button[data-testid="baseButton-primary"]:hover {{
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 26px {card_glow_color} !important;
}}

/* Link / footer secondary buttons */
.footer-link-btn button {{
  background: transparent !important;
  border: none !important;
  color: #60a5fa !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  padding: 4px 8px !important;
  text-decoration: underline !important;
}}
.footer-link-btn button:hover {{
  color: #93c5fd !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Top Branding / Logo Header (Exact match to Image 1) ────────────────────────
st.markdown("""
<div style="text-align: center; margin-bottom: 1.25rem; position: relative; z-index: 10;">
  <div style="display:inline-flex; width:52px; height:52px; border-radius:16px;
       background:linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
       align-items:center; justify-content:center;
       box-shadow:0 8px 24px rgba(99,102,241,0.38); margin-bottom:0.75rem;">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"></path>
      <path d="M6 2v20"></path>
    </svg>
  </div>
  <h1 style="font-size:26px; font-weight:800; color:#ffffff; margin:0; letter-spacing:-0.5px;">
    StudyBuddy <span style="color:#818cf8;">AI</span>
  </h1>
  <p style="color:#9ca3af; font-size:12.5px; margin:5px 0 0 0; font-weight:500;">
    Personalized AI Learning &amp; Campus Management Platform
  </p>
</div>
""", unsafe_allow_html=True)


# ── Dual Portal Switcher Tabs (Only shown on Login mode) ───────────────────────
if auth_mode == "login":
    col_tab_s, col_tab_a = st.columns(2)
    with col_tab_s:
        if st.button(
            "🎓 Student Login",
            key="btn_portal_s",
            use_container_width=True,
            type="primary" if portal == "student" else "secondary",
        ):
            st.session_state["_portal"] = "student"
            st.session_state["_auth_mode"] = "login"
            st.rerun()

    with col_tab_a:
        if st.button(
            "🛡️ Admin Login",
            key="btn_portal_a",
            use_container_width=True,
            type="primary" if portal == "admin" else "secondary",
        ):
            st.session_state["_portal"] = "admin"
            st.session_state["_auth_mode"] = "login"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. STUDENT LOGIN FORM (Exact match to Image 1)
# ═══════════════════════════════════════════════════════════════════════════════
if auth_mode == "login" and portal == "student":
    if st.session_state.get("_login_shake"):
        shake_anim()
        st.session_state["_login_shake"] = False

    with st.form("student_login_form"):
        # Header Badge & Title
        st.markdown("""
        <div style="margin-bottom: 1.15rem;">
          <span style="display:inline-flex; align-items:center; gap:6px;
                background:rgba(37,99,235,0.12); color:#60a5fa;
                border:1px solid rgba(59,130,246,0.3); padding:3px 11px;
                border-radius:99px; font-size:10px; font-weight:800;
                letter-spacing:0.06em; text-transform:uppercase;">
            🎓 STUDENT LEARNING PORTAL
          </span>
          <h2 style="font-size:22px; font-weight:800; color:#ffffff; margin:10px 0 4px 0;">Student Sign In</h2>
          <p style="font-size:12.5px; color:#9ca3af; margin:0;">
            Access your AI study assistant, assignments, grades, notes &amp; timetables.
          </p>
        </div>
        """, unsafe_allow_html=True)

        email = st.text_input("Student Email Address", placeholder="student@example.com", key="s_email")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="s_pwd")

        submitted = st.form_submit_button("Enter Student Learning Hub →", type="primary", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            err = do_login(email.strip().lower(), password)
            if err:
                st.session_state["_login_shake"] = True
                st.error(f"❌ {err}")
                st.rerun()
            else:
                success_checkmark(f"Welcome back, {st.session_state['_user'].get('full_name', '')}!")
                st.session_state["_login_shake"] = False
                time.sleep(0.8)
                st.rerun()

    # Footer navigation
    st.markdown("""
    <div style="text-align:center; margin-top:1rem; font-size:12px; color:#9ca3af;">
      New student joining StudyBuddy?
    </div>
    """, unsafe_allow_html=True)

    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        if st.button("Create Student Account", key="goto_reg", use_container_width=True):
            st.session_state["_auth_mode"] = "register"
            st.rerun()
    with col_f2:
        if st.button("🛡️ Switch to Admin Login →", key="goto_adm", use_container_width=True):
            st.session_state["_portal"] = "admin"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ADMINISTRATOR LOGIN FORM
# ═══════════════════════════════════════════════════════════════════════════════
elif auth_mode == "login" and portal == "admin":
    if st.session_state.get("_login_shake"):
        shake_anim()
        st.session_state["_login_shake"] = False

    # Quick fill admin credentials if requested
    admin_default_email = "admin@studybuddy.com"
    admin_default_pwd   = "Admin@StudyBuddy2024"

    with st.form("admin_login_form"):
        # Header Badge & Title
        st.markdown("""
        <div style="margin-bottom: 1.15rem;">
          <span style="display:inline-flex; align-items:center; gap:6px;
                background:rgba(245,158,11,0.12); color:#fcd34d;
                border:1px solid rgba(245,158,11,0.3); padding:3px 11px;
                border-radius:99px; font-size:10px; font-weight:800;
                letter-spacing:0.06em; text-transform:uppercase;">
            🛡️ FACULTY &amp; STAFF PORTAL
          </span>
          <h2 style="font-size:22px; font-weight:800; color:#ffffff; margin:10px 0 4px 0;">Administrator Sign In</h2>
          <p style="font-size:12.5px; color:#9ca3af; margin:0;">
            Manage classes, student enrollments, exam marks, timetables &amp; broadcasts.
          </p>
        </div>
        """, unsafe_allow_html=True)

        a_email = st.text_input(
            "Admin Staff Email",
            value=st.session_state.get("_admin_autofill_email", ""),
            placeholder="admin@studybuddy.com",
            key="a_email_inp",
        )
        a_password = st.text_input(
            "Password",
            value=st.session_state.get("_admin_autofill_pwd", ""),
            type="password",
            placeholder="••••••••",
            key="a_pwd_inp",
        )

        submitted_a = st.form_submit_button("Access Admin Command Hub →", type="primary", use_container_width=True)

    if submitted_a:
        if not a_email or not a_password:
            st.error("Please enter both administrator email and password.")
        else:
            err = do_login(a_email.strip().lower(), a_password)
            if err:
                st.session_state["_login_shake"] = True
                st.error(f"❌ {err}")
                st.rerun()
            else:
                success_checkmark("Welcome to Admin Command Hub!")
                st.session_state["_login_shake"] = False
                time.sleep(0.8)
                st.rerun()

    # Demo Credentials helper card
    st.markdown(f"""
    <div style="background:rgba(24,24,27,0.8); border:1px solid rgba(245,158,11,0.25);
         border-radius:14px; padding:12px 14px; margin-top:0.75rem;">
      <p style="margin:0; font-size:11px; font-weight:700; color:#f59e0b;">✨ Default Administrator Credentials</p>
      <p style="margin:4px 0 0; font-size:11.5px; font-family:monospace; color:#cbd5e1;">
        Email: <strong style="color:#ffffff;">{admin_default_email}</strong><br>
        Password: <strong style="color:#ffffff;">{admin_default_pwd}</strong>
      </p>
    </div>
    """, unsafe_allow_html=True)

    col_af, col_bk = st.columns(2)
    with col_af:
        if st.button("⚡ Fill Demo Credentials", key="btn_fill_adm", use_container_width=True):
            st.session_state["_admin_autofill_email"] = admin_default_email
            st.session_state["_admin_autofill_pwd"]   = admin_default_pwd
            st.rerun()

    with col_bk:
        if st.button("🎓 Switch to Student Login →", key="goto_stud", use_container_width=True):
            st.session_state["_portal"] = "student"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CREATE STUDENT ACCOUNT (REGISTRATION)
# ═══════════════════════════════════════════════════════════════════════════════
elif auth_mode == "register":
    # Institution selector outside form
    inst_type = st.selectbox(
        "I am a student at…",
        [
            "🏫 School (Class 1–12)",
            "🎓 College / University (UG / PG)",
            "🏛️ Professional / Diploma Programme",
            "💻 Online / Self-Directed Learner",
        ],
        key="reg_inst_type",
    )
    is_school  = inst_type.startswith("🏫")
    is_college = inst_type.startswith("🎓")
    is_prof    = inst_type.startswith("🏛️")

    with st.form("register_form_styled"):
        st.markdown("""
        <div style="margin-bottom: 1.15rem;">
          <span style="display:inline-flex; align-items:center; gap:6px;
                background:rgba(37,99,235,0.12); color:#60a5fa;
                border:1px solid rgba(59,130,246,0.3); padding:3px 11px;
                border-radius:99px; font-size:10px; font-weight:800;
                letter-spacing:0.06em; text-transform:uppercase;">
            🎓 NEW STUDENT REGISTRATION
          </span>
          <h2 style="font-size:22px; font-weight:800; color:#ffffff; margin:10px 0 4px 0;">Create Student Account</h2>
          <p style="font-size:12.5px; color:#9ca3af; margin:0;">
            Join StudyBuddy to access AI study tools, assignments &amp; class resources.
          </p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full Name *", placeholder="e.g. Tanuj Singh", key="reg_full_name")
        id_label = "Roll Number *" if is_school else ("Enrollment / Registration No. *" if is_college or is_prof else "Learner ID *")
        student_id = c2.text_input(id_label, placeholder="e.g. 2024CSE0042", key="reg_student_id")

        email_r = st.text_input("Student Email *", placeholder="you@example.com", key="reg_email")

        c3, c4 = st.columns(2)
        pwd1 = c3.text_input("Password *", type="password", key="reg_pwd1")
        pwd2 = c4.text_input("Confirm Password *", type="password", key="reg_pwd2")

        if is_school:
            c5, c6, c7 = st.columns(3)
            course        = ""
            branch        = ""
            semester      = c5.text_input("Class / Grade *", placeholder="e.g. 10", key="reg_semester")
            section       = c6.text_input("Section", placeholder="e.g. A", key="reg_section")
            academic_year = c7.text_input("Academic Year", placeholder="e.g. 2024-25", key="reg_acyear")
        elif is_college:
            c5, c6 = st.columns(2)
            course  = c5.text_input("Programme *", placeholder="e.g. B.Tech / B.Sc / MBA", key="reg_course")
            branch  = c6.text_input("Branch / Specialisation", placeholder="e.g. CSE / IT / Physics", key="reg_branch")
            c7, c8, c9 = st.columns(3)
            semester      = c7.text_input("Semester / Year", placeholder="e.g. 3rd Sem", key="reg_semester")
            section       = c8.text_input("Section", placeholder="e.g. A", key="reg_section")
            academic_year = c9.text_input("Academic Year", placeholder="e.g. 2024-25", key="reg_acyear")
        elif is_prof:
            c5, c6 = st.columns(2)
            course  = c5.text_input("Programme *", placeholder="e.g. Diploma in Electronics", key="reg_course")
            branch  = c6.text_input("Specialisation", placeholder="e.g. Embedded Systems", key="reg_branch")
            c7, c8 = st.columns(2)
            semester      = c7.text_input("Year / Term", placeholder="e.g. 2nd Year", key="reg_semester")
            section       = ""
            academic_year = c8.text_input("Batch / Year", placeholder="e.g. 2024-26", key="reg_acyear")
        else:
            course        = st.text_input("Subject / Topic you are studying", placeholder="e.g. Machine Learning, IELTS", key="reg_course")
            branch        = st.text_input("Platform / Source (optional)", placeholder="e.g. Coursera, Self-Study", key="reg_branch")
            semester      = ""
            section       = ""
            academic_year = st.text_input("Target Year / Goal", placeholder="e.g. 2025 exam", key="reg_acyear")

        phone = st.text_input("Phone (optional)", placeholder="+91 9876543210", key="reg_phone")

        submitted_r = st.form_submit_button("Complete Student Registration →", type="primary", use_container_width=True)

    if st.session_state.get("reg_pwd1"):
        _strength_bar(st.session_state["reg_pwd1"])

    if submitted_r:
        errors: list[str] = []
        if not full_name.strip():
            errors.append("Full name is required.")
        if not student_id.strip():
            errors.append(f"{id_label.rstrip(' *')} is required.")
        if not email_r.strip():
            errors.append("Email is required.")
        elif "@" not in email_r or "." not in email_r.split("@")[-1]:
            errors.append("Enter a valid email address.")
        if not pwd1:
            errors.append("Password is required.")
        elif len(pwd1) < 8:
            errors.append("Password must be at least 8 characters.")
        elif pwd1 != pwd2:
            errors.append("Passwords do not match.")
        if (is_college or is_prof) and not course.strip():
            errors.append("Programme name is required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            err = do_register({
                "full_name":     full_name.strip(),
                "student_id":    student_id.strip(),
                "email":         email_r.strip().lower(),
                "password":      pwd1,
                "phone":         phone.strip(),
                "course":        course.strip(),
                "branch":        branch.strip() if isinstance(branch, str) else "",
                "semester":      semester.strip() if isinstance(semester, str) else "",
                "section":       section.strip() if isinstance(section, str) else "",
                "academic_year": academic_year.strip() if isinstance(academic_year, str) else "",
            })
            if err:
                st.error(f"❌ {err}")
            else:
                success_checkmark(f"Account created! Welcome, {full_name.strip().split()[0]}! 🎉")
                time.sleep(1.0)
                st.rerun()

    if st.button("← Already have an account? Back to Student Sign In", key="back_to_login", use_container_width=True):
        st.session_state["_auth_mode"] = "login"
        st.session_state["_portal"] = "student"
        st.rerun()
