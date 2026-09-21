"""
core/auth_state.py — Login, logout, and page guards.
Token lives in st.session_state (no cookie library needed).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import streamlit as st
from core.api_client import api_post, api_get

logger = logging.getLogger(__name__)


def _p(name: str) -> str:
    """
    Return the absolute path string for a page file, matching exactly what
    st.Page() was registered with in app.py.
    Falls back to a path relative to this file if session_state not yet set.
    """
    pages_dir = st.session_state.get("_pages_dir")
    if pages_dir:
        return str(Path(pages_dir) / name)
    # Fallback: compute from this file's location
    return str(Path(__file__).resolve().parent.parent / "pages" / name)


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
        st.switch_page(_p("login.py"))
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
