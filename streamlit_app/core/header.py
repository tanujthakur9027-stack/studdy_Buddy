"""
core/header.py — Universal Identity Identification Header for Streamlit.
Matches the Next.js header banner (Header.tsx) 1:1:
  - User avatar with initial (gold for admin, blue for student)
  - Full name, role badge (ADMIN / STUDENT), student ID pill
  - Email & class / course subtitle
  - Notification count indicator
  - Contact Staff action (student)
  - Admin Hub shortcut (admin)
  - Sign Out button
"""
from __future__ import annotations
import streamlit as st
from core.auth_state import current_user, is_admin, logout, _p
from core.api_client import api_get, api_post


def render_identity_header() -> None:
    """Render the top identity identification banner on any Streamlit page."""
    user = current_user()
    if not user:
        return

    admin_mode = is_admin()
    full_name = user.get("full_name", "User")
    email = user.get("email", "")
    student_id = user.get("student_id") or ""
    class_name = user.get("class_name") or user.get("course") or ""
    initial = (full_name[:1] or "U").upper()

    # Fetch unread notifications count
    unread_data, _ = api_get("/api/notifications/unread-count", timeout=5)
    unread_count = (unread_data or {}).get("count", 0)

    # Gradient & role badge colors
    if admin_mode:
        avatar_bg = "linear-gradient(135deg, #d97706 0%, #eab308 100%)"
        avatar_color = "#000"
        role_label = "ADMIN"
        role_bg = "rgba(245, 158, 11, 0.15)"
        role_text = "#fbbf24"
        role_border = "rgba(245, 158, 11, 0.3)"
        role_icon = "🛡️"
    else:
        avatar_bg = "linear-gradient(135deg, #2563eb 0%, #6366f1 100%)"
        avatar_color = "#fff"
        role_label = "STUDENT"
        role_bg = "rgba(59, 130, 246, 0.15)"
        role_text = "#60a5fa"
        role_border = "rgba(59, 130, 246, 0.3)"
        role_icon = "🎓"

    student_id_html = (
        f'<span style="font-family:monospace;font-size:11px;font-weight:600;background:rgba(31,41,55,0.8);color:#d1d5db;padding:2px 8px;border-radius:6px;border:1px solid rgba(75,85,99,0.5)">ID: {student_id}</span>'
        if student_id else ""
    )

    class_html = (
        f'<span style="color:#4b5563">•</span> <span style="color:#818cf8;font-weight:600">{class_name}</span>'
        if class_name else ""
    )

    notif_badge_html = (
        f'<span style="background:#ef4444;color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:99px;margin-left:4px">{unread_count if unread_count <= 9 else "9+"}</span>'
        if unread_count > 0 else ""
    )

    # ── Top HTML Banner ──
    st.markdown(f"""
<div style="background:rgba(17,24,39,0.95);border:1px solid rgba(31,41,55,0.9);border-radius:18px;padding:0.9rem 1.25rem;margin-bottom:1.5rem;box-shadow:0 10px 25px -5px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
  <div style="display:flex;align-items:center;gap:14px">
    <div style="width:44px;height:44px;border-radius:14px;background:{avatar_bg};color:{avatar_color};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:18px;box-shadow:0 4px 14px rgba(0,0,0,0.3);flex-shrink:0">
      {initial}
    </div>
    <div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span style="font-size:15px;font-weight:700;color:#ffffff;letter-spacing:-0.02em">{full_name}</span>
        <span style="font-size:10px;font-weight:800;background:{role_bg};color:{role_text};border:1px solid {role_border};padding:2px 8px;border-radius:99px;letter-spacing:0.04em">
          {role_icon} {role_label}
        </span>
        {student_id_html}
      </div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px;display:flex;align-items:center;gap:6px">
        <span>{email}</span>
        {class_html}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Action Buttons Bar ──
    cols = st.columns([6, 1.8, 1.8, 1.6] if not admin_mode else [7, 2, 2])
    with cols[0]:
        pass  # Spacer to keep buttons right-aligned

    if not admin_mode:
        with cols[1]:
            contact_clicked = st.button("✉️ Contact Staff", key="hdr_contact_btn", use_container_width=True)
            if contact_clicked:
                st.session_state["_show_contact_modal"] = not st.session_state.get("_show_contact_modal", False)
        with cols[2]:
            notif_label = f"🔔 Alerts ({unread_count})" if unread_count else "🔔 Alerts"
            if st.button(notif_label, key="hdr_notif_btn", use_container_width=True):
                st.switch_page(_p("notifications.py"))
        with cols[3]:
            if st.button("🚪 Logout", key="hdr_logout_btn", use_container_width=True):
                logout()
                st.rerun()
    else:
        with cols[1]:
            if st.button("⚙️ Admin Hub", key="hdr_admin_hub_btn", use_container_width=True):
                st.switch_page(_p("admin.py"))
        with cols[2]:
            if st.button("🚪 Logout", key="hdr_logout_btn", use_container_width=True):
                logout()
                st.rerun()

    # ── Interactive Contact Staff Dialog ──
    if st.session_state.get("_show_contact_modal") and not admin_mode:
        with st.expander("📝 Send Inquiry to Staff & Administration", expanded=True):
            st.markdown(
                '<p style="font-size:12px;color:#9ca3af;margin-bottom:0.75rem">'
                'Direct message to teachers, faculty, and administrative staff. You will receive replies in your Notification Center.'
                '</p>',
                unsafe_allow_html=True,
            )
            with st.form("hdr_contact_form"):
                cat = st.selectbox(
                    "Inquiry Category",
                    ["academic", "assignment", "technical", "general"],
                    format_func=lambda c: {
                        "academic": "Academic & Subject Question",
                        "assignment": "Assignment / Grade Issue",
                        "technical": "Technical Support",
                        "general": "Administrative Inquiry",
                    }.get(c, c),
                )
                title = st.text_input("Subject / Title", placeholder="e.g. Question regarding Assignment 2 deadline")
                msg = st.text_area("Message", placeholder="Describe your question or issue in detail...", height=100)
                send_col1, send_col2 = st.columns([4, 1])
                with send_col2:
                    submitted = st.form_submit_button("Send Inquiry →", type="primary")

                if submitted:
                    if not title.strip() or not msg.strip():
                        st.error("Please fill in both a title and message.")
                    else:
                        _, err = api_post("/api/notifications/contact-admin", json={
                            "title": title.strip(),
                            "message": msg.strip(),
                            "category": cat,
                        })
                        if err:
                            st.error(err)
                        else:
                            st.success("Your message has been delivered to staff and administration!")
                            st.session_state["_show_contact_modal"] = False
                            st.rerun()
