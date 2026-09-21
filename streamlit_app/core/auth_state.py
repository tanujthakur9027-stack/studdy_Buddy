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


# Absolute pages directory — always resolved from this file's own location.
# This is identical to what app.py registers with st.Page(), because app.py
# also derives _PAGES from Path(__file__).resolve().parent / "pages".
# We never rely on session_state here so the path is always consistent,
# even on the very first run before app.py has written to session_state.
_PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"


def _p(name: str) -> str:
    """
    Return the absolute path string for a page file, matching exactly what
    st.Page() registered in app.py.  Derived from this file's own location —
    never depends on CWD or session_state.
    """
    return str(_PAGES_DIR / name)


# ── Public helpers ─────────────────────────────────────────────────────────────

def is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))


def current_user() -> dict:
    return st.session_state.get("_user", {})


def is_admin() -> bool:
    return current_user().get("role") == "admin"


def require_login() -> None:
    """Guard for protected pages. Redirects to login if not authenticated.
    
    Uses st.rerun() so that app.py can re-evaluate navigation state and
    serve the login page — avoids st.switch_page() trying to navigate to
    a page that may not be registered in the current navigation set.
    """
    if not is_logged_in():
        # Clear any stale state so app.py rebuilds navigation for the
        # unauthenticated case and shows login.py.
        for k in ("_token", "_user", "documents_loaded", "documents", "active_doc"):
            st.session_state.pop(k, None)
        st.rerun()


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
