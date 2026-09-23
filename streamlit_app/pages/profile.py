"""
pages/profile.py — User Profile, Avatar, Change Password, Backend Health, Logout.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.styles import inject_global_css
from core.animations import page_enter
from core.auth_state import require_login, current_user, do_logout, _p
from core.api_client import api_post, api_patch, api_get, api_request
from core.media_uploader import render_media_uploader

inject_global_css()
require_login()
page_enter()

user = current_user()

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem;animation:fadeUp .4s both">
  <h1 style="font-size:1.6rem;font-weight:800;color:#fafafa;margin:0 0 .25rem;letter-spacing:-.03em">
    👤 Profile
  </h1>
  <p style="font-size:.875rem;color:#71717a;margin:0">{user.get('email','')}</p>
</div>""", unsafe_allow_html=True)

# ── Profile card ──────────────────────────────────────────────────────────────
role_color = "#a78bfa" if user.get("role") == "admin" else "#6366f1"
st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:16px;
     padding:1.5rem 2rem;margin-bottom:1.5rem;display:flex;align-items:center;gap:1.5rem">
  <div style="width:56px;height:56px;border-radius:14px;flex-shrink:0;
       background:linear-gradient(135deg,#6366f1,#8b5cf6);
       display:flex;align-items:center;justify-content:center;
       font-size:1.5rem;font-weight:800;color:#fff">
    {user.get('full_name','?')[0].upper()}
  </div>
  <div>
    <div style="font-size:1.1rem;font-weight:700;color:#fafafa">{user.get('full_name','User')}</div>
    <div style="font-size:.8rem;color:#71717a;margin-top:.2rem">{user.get('email','')}</div>
    <div style="margin-top:.4rem">
      <span style="background:{role_color}22;color:{role_color};border:1px solid {role_color}44;
           border-radius:99px;font-size:11px;font-weight:600;padding:2px 10px">
        {user.get('role','student').title()}
      </span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Sections ──────────────────────────────────────────────────────────────────
def _sec(title: str) -> None:
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:.5rem;margin:1.5rem 0 .75rem">
  <div style="flex:1;height:1px;background:#27272a"></div>
  <span style="font-size:11px;font-weight:600;color:#52525b;
       text-transform:uppercase;letter-spacing:.07em;white-space:nowrap">{title}</span>
  <div style="flex:1;height:1px;background:#27272a"></div>
</div>""", unsafe_allow_html=True)


# ── Avatar upload ─────────────────────────────────────────────────────────────
_sec("🖼️ Avatar")
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
            st.success(f"✅ Avatar saved!")

# ── Edit name ─────────────────────────────────────────────────────────────────
_sec("✏️ Edit Name")
with st.form("edit_name_form"):
    new_name = st.text_input("Full Name", value=user.get("full_name", ""))
    if st.form_submit_button("Update Name", type="primary"):
        if new_name.strip():
            data, err = api_patch("/api/profile", json={"full_name": new_name.strip()})
            if err:
                st.error(err)
            else:
                st.session_state["_user"]["full_name"] = new_name.strip()
                st.success("✅ Name updated!")
        else:
            st.error("Name cannot be empty.")

# ── Change password ───────────────────────────────────────────────────────────
_sec("🔑 Change Password")
with st.form("change_pw_form"):
    old_pw  = st.text_input("Current Password", type="password")
    c1, c2  = st.columns(2)
    new_pw  = c1.text_input("New Password (min 8 chars)", type="password")
    new_pw2 = c2.text_input("Confirm New Password", type="password")
    if st.form_submit_button("Change Password", type="primary"):
        if not old_pw or not new_pw:
            st.error("All password fields are required.")
        elif len(new_pw) < 8:
            st.error("New password must be at least 8 characters.")
        elif new_pw != new_pw2:
            st.error("Passwords do not match.")
        else:
            data, err = api_post("/api/auth/change-password",
                                  json={"current_password": old_pw, "new_password": new_pw})
            if err:
                st.error(err)
            else:
                st.success("✅ Password changed successfully!")

# ── Backend health ────────────────────────────────────────────────────────────
_sec("🔧 Backend Status")
if st.button("Check Backend Health", type="secondary"):
    data, err = api_get("/health", timeout=10)
    if err:
        st.error(err)
    else:
        ok = data.get("status") == "ok"
        color = "#22c55e" if ok else "#f59e0b"
        label = "● Operational" if ok else "⚠ Degraded"
        st.markdown(f"""
<div style="background:#18181b;border:1px solid #27272a;border-radius:12px;
     padding:1rem 1.25rem;margin-top:.5rem">
  <span style="color:{color};font-size:14px;font-weight:700">{label}</span>
  <p style="margin:.5rem 0 0;font-size:12px;color:#71717a">
    Provider: <span style="color:#d4d4d8">{data.get('provider','?')}</span> ·
    Model: <span style="color:#d4d4d8">{data.get('model','?')}</span> ·
    Documents: <span style="color:#d4d4d8">{data.get('indexed_documents',0)}</span>
  </p>
</div>""", unsafe_allow_html=True)

# ── Logout ────────────────────────────────────────────────────────────────────
_sec("🚪 Session")
if st.button("Sign Out", type="secondary"):
    do_logout()
    st.rerun()
