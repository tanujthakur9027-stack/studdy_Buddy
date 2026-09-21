"""
core/auth_state.py — Login, logout, token persistence, and page guards.

Token storage: st.session_state (RAM) + browser cookie via extra-streamlit-components
CookieManager. On page refresh the token is restored from the cookie.

Security tradeoffs documented here:
- Cookies are httponly=False (Streamlit renders JS cookies). The token is short-lived
  (default 24h). For a production deployment with custom SSL, set Secure + SameSite=Strict
  at the reverse-proxy level.
- Never put tokens in the URL — query strings are logged by CDNs and appear in browser history.
"""
from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from core.api_client import api_post, api_get

logger = logging.getLogger(__name__)

_COOKIE_KEY = "sb_token"
_COOKIE_MAX_AGE = 86400  # 24 hours


def _cookie_manager():
    """Lazily initialise CookieManager if extra-streamlit-components is installed."""
    try:
        from streamlit_cookies_manager import EncryptedCookieManager  # type: ignore
        # Use a stable key so cookies survive reruns; value kept out of logs.
        key = st.secrets.get("COOKIE_SECRET", "studybuddy-cookie-secret")
        mgr = EncryptedCookieManager(prefix="sb_", password=key)
        if not mgr.ready():
            mgr.save()
        return mgr
    except ImportError:
        return None


def restore_session_from_cookie() -> None:
    """
    Called once at app startup. If no token is in session_state but there is
    a valid cookie, restore the token and fetch the user profile.
    """
    if st.session_state.get("_token"):
        return  # already logged in

    mgr = _cookie_manager()
    if mgr is None:
        return

    token = mgr.get(_COOKIE_KEY)
    if not token:
        return

    # Validate by hitting /api/auth/me
    st.session_state["_token"] = token
    data, err = api_get("/api/auth/me", timeout=10)
    if err or not data:
        st.session_state.pop("_token", None)
        try:
            mgr[_COOKIE_KEY] = ""
            mgr.save()
        except Exception:
            pass
        return

    st.session_state["_user"] = data


def save_token_to_cookie(token: str) -> None:
    mgr = _cookie_manager()
    if mgr is None:
        return
    try:
        mgr[_COOKIE_KEY] = token
        mgr.save()
    except Exception:
        pass


def delete_token_cookie() -> None:
    mgr = _cookie_manager()
    if mgr is None:
        return
    try:
        mgr[_COOKIE_KEY] = ""
        mgr.save()
    except Exception:
        pass


# ── Public helpers ────────────────────────────────────────────────────────────

def is_logged_in() -> bool:
    return bool(st.session_state.get("_token"))


def current_user() -> dict:
    return st.session_state.get("_user", {})


def is_admin() -> bool:
    return current_user().get("role") == "admin"


def require_login() -> None:
    """
    Guard for protected pages. If the user is not logged in, redirects to
    the login page and stops execution of the calling page.
    Call at the very top of every protected page.
    """
    if not is_logged_in():
        st.switch_page("pages/login.py")
        st.stop()


def do_login(email: str, password: str) -> Optional[str]:
    """Attempt login. Returns None on success, error string on failure."""
    data, err = api_post("/api/auth/login", json={"email": email, "password": password})
    if err:
        return err
    st.session_state["_token"] = data["access_token"]
    st.session_state["_user"] = data["user"]
    st.session_state["documents_loaded"] = False  # force refresh
    save_token_to_cookie(data["access_token"])
    return None


def do_register(payload: dict) -> Optional[str]:
    """Attempt registration. Returns None on success, error string on failure."""
    data, err = api_post("/api/auth/register", json=payload)
    if err:
        return err
    st.session_state["_token"] = data["access_token"]
    st.session_state["_user"] = data["user"]
    st.session_state["documents_loaded"] = False
    save_token_to_cookie(data["access_token"])
    return None


def do_logout() -> None:
    api_post("/api/auth/logout")
    for k in ["_token", "_user", "documents_loaded", "documents", "active_doc"]:
        st.session_state.pop(k, None)
    delete_token_cookie()
