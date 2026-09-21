"""
pages/login.py — Login & Registration page with animations.
"""
import sys
import re
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, heading
from core.animations import login_card_css, shake_anim, success_checkmark, page_enter
from core.auth_state import is_logged_in, do_login, do_register, _p

inject_global_css()
login_card_css()
page_enter()

# Redirect if already logged in
if is_logged_in():
    st.switch_page(_p("dashboard.py"))
    st.stop()


def _password_strength(pw: str) -> tuple[int, str]:
    score = 0
    if len(pw) >= 8:   score += 1
    if len(pw) >= 12:  score += 1
    if re.search(r"[A-Z]", pw): score += 1
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


# ── Logo / Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;animation:fadeUp 0.5s both">
  <div style="width:64px;height:64px;border-radius:18px;
       background:linear-gradient(135deg,#6366f1,#8b5cf6);
       display:inline-flex;align-items:center;justify-content:center;
       box-shadow:0 0 32px rgba(99,102,241,0.4);margin-bottom:1rem">
    <svg width="36" height="36" viewBox="0 0 44 44" fill="none">
      <path d="M22 4L4 15l18 11 18-11L22 4z" stroke="rgba(255,255,255,0.95)"
            stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 29l18 11 18-11" stroke="rgba(255,255,255,0.95)"
            stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 22l18 11 18-11" stroke="rgba(255,255,255,0.7)"
            stroke-width="2.5" stroke-linejoin="round"/>
    </svg>
  </div>
  <h1 style="font-size:28px;font-weight:800;color:#fafafa;margin:0">
    Study Buddy <span style="color:#a78bfa">AI</span>
  </h1>
  <p style="color:#71717a;font-size:14px;margin:.25rem 0 0">
    Your personalised AI learning companion
  </p>
</div>
""", unsafe_allow_html=True)

login_tab, reg_tab = st.tabs(["🔑 Sign In", "📝 Create Account"])

# ── Login ──────────────────────────────────────────────────────────────────────
with login_tab:
    if st.session_state.get("_login_shake"):
        shake_anim()
        st.session_state["_login_shake"] = False

    with st.form("login_form"):
        email    = st.text_input("Email", placeholder="you@example.com")
        # NOTE: st.text_input type must be a literal — dynamic toggle not allowed in forms.
        # Show password toggle is placed OUTSIDE the form below.
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Email and password are required.")
        else:
            err = do_login(email.strip().lower(), password)
            if err:
                st.session_state["_login_shake"] = True
                st.error(f"❌ {err}")
                st.rerun()
            else:
                success_checkmark(
                    f"Welcome back, {st.session_state['_user'].get('full_name', '')}!"
                )
                st.session_state["_login_shake"] = False
                time.sleep(1.0)
                st.switch_page(_p("dashboard.py"))
                st.stop()

    st.markdown("""
<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;
     padding:.875rem 1.25rem;margin-top:1rem">
  <p style="margin:0;font-size:12px;font-weight:600;color:#f59e0b">🔐 Demo credentials</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">
    Email: <span style="color:#d4d4d8">admin@studybuddy.com</span><br>
    Password: <span style="color:#d4d4d8">Admin@StudyBuddy2024</span>
  </p>
</div>""", unsafe_allow_html=True)


# ── Register ───────────────────────────────────────────────────────────────────
with reg_tab:
    with st.form("register_form"):
        st.markdown("**Personal Information**")
        c1, c2 = st.columns(2)
        full_name  = c1.text_input("Full Name *")
        student_id = c2.text_input("Student ID *")
        email_r    = st.text_input("Email *", placeholder="you@example.com", key="reg_email")
        c3, c4 = st.columns(2)
        pwd1       = c3.text_input("Password *", type="password", key="reg_pwd1")
        pwd2       = c4.text_input("Confirm Password *", type="password", key="reg_pwd2")

        st.markdown("**Academic Details**")
        c5, c6 = st.columns(2)
        course   = c5.text_input("Course", placeholder="B.Tech")
        branch   = c6.text_input("Branch", placeholder="CSE")
        c7, c8, c9 = st.columns(3)
        semester   = c7.text_input("Semester", placeholder="3rd")
        section    = c8.text_input("Section",  placeholder="A")
        phone      = c9.text_input("Phone (optional)")
        submitted_r = st.form_submit_button(
            "Create Account →", type="primary", use_container_width=True
        )

    # Password strength bar rendered outside form (no dynamic widget issue)
    if pwd1:
        _strength_bar(pwd1)

    if submitted_r:
        errors = []
        if not all([full_name, student_id, email_r, pwd1, pwd2]):
            errors.append("All starred fields are required.")
        if pwd1 and len(pwd1) < 8:
            errors.append("Password must be at least 8 characters.")
        if pwd1 != pwd2:
            errors.append("Passwords do not match.")
        if email_r and ("@" not in email_r or "." not in email_r.split("@")[-1]):
            errors.append("Enter a valid email address.")
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
                "branch":        branch.strip(),
                "semester":      semester.strip(),
                "section":       section.strip(),
                "academic_year": "",
            })
            if err:
                st.error(f"❌ {err}")
            else:
                success_checkmark(
                    f"Account created! Welcome, {full_name.split()[0]}!"
                )
                time.sleep(1.0)
                st.switch_page(_p("dashboard.py"))
                st.stop()
