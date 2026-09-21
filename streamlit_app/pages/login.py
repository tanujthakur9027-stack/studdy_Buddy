"""
pages/login.py — Login & Registration page.

Universal design — works for students from any school, college, university,
or online course. No institution-specific terminology is hardcoded.
"""
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

# Redirect if already logged in.
# Uses st.rerun() so app.py rebuilds navigation for the authenticated state.
if is_logged_in():
    st.rerun()


# ── Password strength ──────────────────────────────────────────────────────────

def _password_strength(pw: str) -> tuple[int, str]:
    score = 0
    if len(pw) >= 8:                        score += 1
    if len(pw) >= 12:                       score += 1
    if re.search(r"[A-Z]", pw):            score += 1
    if re.search(r"[0-9!@#$%^&*]", pw):   score += 1
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
<div style="text-align:center;padding:2rem 0 1.25rem;animation:fadeUp 0.5s both">
  <div style="width:68px;height:68px;border-radius:20px;
       background:linear-gradient(135deg,#6366f1,#8b5cf6);
       display:inline-flex;align-items:center;justify-content:center;
       box-shadow:0 0 40px rgba(99,102,241,0.45);margin-bottom:1rem">
    <svg width="38" height="38" viewBox="0 0 44 44" fill="none">
      <path d="M22 4L4 15l18 11 18-11L22 4z" stroke="rgba(255,255,255,0.95)"
            stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 29l18 11 18-11" stroke="rgba(255,255,255,0.95)"
            stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M4 22l18 11 18-11" stroke="rgba(255,255,255,0.7)"
            stroke-width="2.5" stroke-linejoin="round"/>
    </svg>
  </div>
  <h1 style="font-size:30px;font-weight:800;color:#fafafa;margin:0;letter-spacing:-.5px">
    Study Buddy <span style="color:#a78bfa">AI</span>
  </h1>
  <p style="color:#71717a;font-size:14px;margin:.35rem 0 0">
    AI-powered learning — for every student, every level
  </p>
  <div style="display:flex;justify-content:center;gap:10px;margin-top:.85rem;flex-wrap:wrap">
    <span style="background:#1e1b4b;color:#a5b4fc;border:1px solid #3730a3;
          font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px">🏫 Schools</span>
    <span style="background:#14532d;color:#86efac;border:1px solid #166534;
          font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px">🎓 Colleges</span>
    <span style="background:#422006;color:#fcd34d;border:1px solid #92400e;
          font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px">🏛️ Universities</span>
    <span style="background:#1e1b4b;color:#c4b5fd;border:1px solid #4c1d95;
          font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px">💻 Online Learners</span>
  </div>
</div>
""", unsafe_allow_html=True)

login_tab, reg_tab = st.tabs(["🔑 Sign In", "📝 Create Account"])


# ── Sign In ────────────────────────────────────────────────────────────────────
with login_tab:
    if st.session_state.get("_login_shake"):
        shake_anim()
        st.session_state["_login_shake"] = False

    with st.form("login_form"):
        email    = st.text_input("Email", placeholder="you@example.com")
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
                st.rerun()

    # Demo credentials hint
    st.markdown("""
<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;
     padding:.875rem 1.25rem;margin-top:1rem">
  <p style="margin:0;font-size:12px;font-weight:600;color:#f59e0b">🔐 Demo credentials</p>
  <p style="margin:4px 0 0;font-size:12px;color:#71717a">
    Email: <span style="color:#d4d4d8">admin@studybuddy.com</span><br>
    Password: <span style="color:#d4d4d8">Admin@StudyBuddy2024</span>
  </p>
</div>""", unsafe_allow_html=True)


# ── Create Account ─────────────────────────────────────────────────────────────
with reg_tab:

    # ── Institution type selector (outside form so it can drive field visibility)
    inst_type = st.selectbox(
        "I am a student at…",
        ["🏫 School (Class 1–12)",
         "🎓 College / University (UG / PG)",
         "🏛️ Professional / Diploma Programme",
         "💻 Online / Self-Directed Learner"],
        key="reg_inst_type",
        label_visibility="visible",
    )
    is_school    = inst_type.startswith("🏫")
    is_college   = inst_type.startswith("🎓")
    is_prof      = inst_type.startswith("🏛️")
    is_online    = inst_type.startswith("💻")

    st.markdown("---")

    with st.form("register_form"):
        # ── Personal information ───────────────────────────────────────────────
        st.markdown(
            '<p style="font-size:13px;font-weight:700;color:#a78bfa;'
            'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">'
            '👤 Personal Information</p>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full Name *", placeholder="e.g. Priya Sharma",
                                   key="reg_full_name")
        # ID field label adapts to institution type but always uses the same key
        if is_school:
            id_label      = "Roll Number *"
            id_placeholder = "e.g. 24"
        elif is_college or is_prof:
            id_label      = "Enrollment / Registration No. *"
            id_placeholder = "e.g. 2024CSE0042"
        else:
            id_label      = "Learner ID *"
            id_placeholder = "e.g. LEARN2024001  (or create your own)"
        student_id = c2.text_input(id_label, placeholder=id_placeholder, key="reg_student_id")

        email_r = st.text_input("Email *", placeholder="you@example.com", key="reg_email")

        c3, c4 = st.columns(2)
        pwd1 = c3.text_input("Password *",        type="password", key="reg_pwd1")
        pwd2 = c4.text_input("Confirm Password *", type="password", key="reg_pwd2")

        # ── Academic details — vary by institution type ────────────────────────
        st.markdown(
            '<p style="font-size:13px;font-weight:700;color:#a78bfa;'
            'text-transform:uppercase;letter-spacing:.07em;margin:.75rem 0 .5rem">'
            '🏫 Academic Details</p>',
            unsafe_allow_html=True,
        )

        if is_school:
            c5, c6, c7 = st.columns(3)
            course        = ""    # not applicable for school
            branch        = ""
            semester      = c5.text_input("Class / Grade *", placeholder="e.g. 10",      key="reg_semester")
            section       = c6.text_input("Section",          placeholder="e.g. A",        key="reg_section")
            academic_year = c7.text_input("Academic Year",    placeholder="e.g. 2024-25",  key="reg_acyear")

        elif is_college:
            c5, c6 = st.columns(2)
            course  = c5.text_input("Programme *",             placeholder="e.g. B.Tech / B.Sc / MBA",       key="reg_course")
            branch  = c6.text_input("Branch / Specialisation", placeholder="e.g. CSE / Physics / Finance",   key="reg_branch")
            c7, c8, c9 = st.columns(3)
            semester      = c7.text_input("Semester / Year",   placeholder="e.g. 3rd Sem",  key="reg_semester")
            section       = c8.text_input("Section / Division", placeholder="e.g. A",        key="reg_section")
            academic_year = c9.text_input("Academic Year",     placeholder="e.g. 2024-25",  key="reg_acyear")

        elif is_prof:
            c5, c6 = st.columns(2)
            course  = c5.text_input("Programme *",               placeholder="e.g. Diploma in Electronics", key="reg_course")
            branch  = c6.text_input("Specialisation (optional)", placeholder="e.g. Embedded Systems",       key="reg_branch")
            c7, c8 = st.columns(2)
            semester      = c7.text_input("Year / Term", placeholder="e.g. 2nd Year",  key="reg_semester")
            section       = ""
            academic_year = c8.text_input("Batch / Year", placeholder="e.g. 2024-26", key="reg_acyear")

        else:  # online / self-directed
            course  = st.text_input("Subject / Topic you are studying",
                                    placeholder="e.g. Machine Learning, UPSC Mains, IELTS Prep",
                                    key="reg_course")
            branch  = st.text_input("Platform / Source (optional)",
                                    placeholder="e.g. Coursera, YouTube, Self-Study",
                                    key="reg_branch")
            semester      = ""
            section       = ""
            academic_year = st.text_input("Target Year / Goal (optional)",
                                          placeholder="e.g. 2025 exam, 6 months",
                                          key="reg_acyear")

        # ── Optional contact ───────────────────────────────────────────────────
        phone = st.text_input("Phone (optional)", placeholder="+91 9876543210", key="reg_phone")

        submitted_r = st.form_submit_button(
            "Create Account →", type="primary", use_container_width=True
        )

    # Password strength bar (outside form — cannot use dynamic widgets inside)
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
        # Course required for college / professional
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
                success_checkmark(
                    f"Account created! Welcome, {full_name.strip().split()[0]}! 🎉"
                )
                time.sleep(1.0)
                # Rerun so app.py rebuilds navigation for the authenticated state.
                st.rerun()
