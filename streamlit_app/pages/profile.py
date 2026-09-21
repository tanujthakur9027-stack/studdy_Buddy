"""
pages/profile.py — User Profile, Avatar (GIF-capable), Change Password, Backend Health, Logout.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css, heading
from core.animations import page_enter
from core.auth_state import require_login, current_user, do_logout
from core.api_client import api_post, api_patch, api_get, api_request
from core.media_uploader import render_media_uploader

st.set_page_config(page_title="Profile — StudyBuddy", page_icon="👤", layout="centered")
inject_global_css()
require_login()
page_enter()

user = current_user()

heading("Profile", f"Manage your account — {user.get('email','')}")

# ── Avatar upload ─────────────────────────────────────────────────────────────
st.markdown("### 🖼️ Avatar")
st.caption("Upload a PNG, JPG, WEBP or animated GIF (max 5 MB).")
file_bytes, metadata = render_media_uploader(
    label="Choose avatar",
    key="avatar_upload",
    allowed=("gif", "png", "jpg", "jpeg", "webp"),
    max_mb=5,
)
if file_bytes and metadata:
    if st.button("Save Avatar", type="primary"):
        data, err = api_request(
            "POST", "/api/media/upload", timeout=60,
            files={"file": (metadata["original_name"], file_bytes, metadata["mime"])},
        )
        if err:
            st.error(err)
        else:
            st.success(f"Avatar saved! Media ID: {data['id']}")

st.divider()

# ── Edit username ──────────────────────────────────────────────────────────────
st.markdown("### ✏️ Edit Name")
with st.form("edit_name_form"):
    new_name = st.text_input("Full Name", value=user.get("full_name", ""))
    if st.form_submit_button("Update Name", type="primary"):
        if new_name.strip():
            data, err = api_patch("/api/profile", json={"full_name": new_name.strip()})
            if err:
                st.error(err)
            else:
                st.session_state["_user"]["full_name"] = new_name.strip()
                st.success("Name updated!")
        else:
            st.error("Name cannot be empty.")

st.divider()

# ── Change password ───────────────────────────────────────────────────────────
st.markdown("### 🔑 Change Password")
with st.form("change_pw_form"):
    old_pw  = st.text_input("Current Password", type="password")
    new_pw  = st.text_input("New Password (min 8 chars)", type="password")
    new_pw2 = st.text_input("Confirm New Password", type="password")
    if st.form_submit_button("Change Password", type="primary"):
        if not old_pw or not new_pw:
            st.error("All password fields are required.")
        elif len(new_pw) < 8:
            st.error("New password must be at least 8 characters.")
        elif new_pw != new_pw2:
            st.error("New passwords do not match.")
        else:
            data, err = api_post("/api/auth/change-password",
                                  json={"old_password": old_pw, "new_password": new_pw})
            if err:
                st.error(err)
            else:
                st.success("Password changed successfully!")

st.divider()

# ── Backend health ────────────────────────────────────────────────────────────
st.markdown("### 🔧 Backend Status")
if st.button("Check backend health"):
    data, err = api_get("/health", timeout=10)
    if err:
        st.error(err)
    else:
        ok = data.get("status") == "ok"
        colour = "#22c55e" if ok else "#f59e0b"
        st.markdown(
            f'<span style="color:{colour};font-size:14px;font-weight:600">'
            f'{"● Operational" if ok else "⚠ Degraded"}</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Provider: {data.get('provider','?')} · "
            f"Model: {data.get('model','?')} · "
            f"Documents indexed: {data.get('indexed_documents',0)}"
        )
        st.caption("⚠️ Note: data/ directory resets on Streamlit Cloud redeployment. "
                   "For persistent storage configure a PostgreSQL URL and external file storage.")

st.divider()

# ── Logout ────────────────────────────────────────────────────────────────────
st.markdown("### 🚪 Logout")
if st.button("Sign Out", type="secondary"):
    do_logout()
    st.switch_page("pages/login.py")
    st.stop()
