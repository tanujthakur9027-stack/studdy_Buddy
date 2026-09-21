"""
core/auth_state.py — Login, logout, token persistence, and page guards.
"""
from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from core.api_client import api_post, api_get

logger = logging.getLogger(__name__)


def _page(name: str) -> str:
    """Return the same path string that st.Page() was registered with in app.py."""
    prefix = st.session_state.get("_page_prefix", "pages")
    return f"{prefix}/{name}"


def _cookie_manager():
    """No-op: streamlit-cookies-manager uses @st.cache removed in Streamlit 1.36+."""
    return None


def restore_session_from_cookie() -> None:
    """No-op — token lives in session_state only."""
    pass


def save_token_to_cookie(token: str) -> None:
    pass


def delete_token_cookie() -> None:
    pass


# ── Public helpers ─────────────────────────────────────────────────────────────

def is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))


def current_user() -> dict:
    return st.session_state.get("_user", {})


def is_admin() -> bool:
    return current_user().get("role") == "admin"


def require_login() -> None:
    """Guard for protected pages. Redirects to login if not authenticated."""
    if not is_logged_in():
        st.switch_page(_page("login.py"))
        st.stop()


def do_login(email: str, password: str) -> Optional[str]:
    """Attempt login. Returns None on success, error string on failure."""
    data, err = api_post("/api/auth/login", json={"email": email, "password": password})
    if err:
        return err
    st.session_state["_token"] = data["access_token"]
    st.session_state["_user"]  = data["user"]
    st.session_state["documents_loaded"] = False
    return None


def do_register(payload: dict) -> Optional[str]:
    """Attempt registration. Returns None on success, error string on failure."""
    data, err = api_post("/api/auth/register", json=payload)
    if err:
        return err
    st.session_state["_token"] = data["access_token"]
    st.session_state["_user"]  = data["user"]
    st.session_state["documents_loaded"] = False
    return None


def do_logout() -> None:
    api_post("/api/auth/logout")
    for k in ["_token", "_user", "documents_loaded", "documents", "active_doc"]:
        st.session_state.pop(k, None)
