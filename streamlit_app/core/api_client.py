"""
core/api_client.py — Centralised HTTP client for all Streamlit pages.

Features:
- Injects Authorization: Bearer <token> header automatically
- Uniform (data, error) return type for all requests
- SSE helper for streaming endpoints (cheat sheet, explain/stream)
- Never logs or re-raises tokens/passwords
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import requests
import streamlit as st

logger = logging.getLogger(__name__)

def get_backend_url() -> str:
    """Read BACKEND_URL from os.environ, then st.secrets, defaulting to http://localhost:8000."""
    env_url = os.environ.get("BACKEND_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    try:
        secret_url = str(st.secrets.get("BACKEND_URL", "")).strip()
        if secret_url:
            return secret_url.rstrip("/")
    except Exception:
        pass
    return "http://localhost:8000"


BACKEND_URL = get_backend_url()
TIMEOUT_SHORT = 30
TIMEOUT_LONG  = 180


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_request(
    method: str,
    path: str,
    timeout: int = TIMEOUT_LONG,
    **kwargs: Any,
) -> tuple[Any, Optional[str]]:
    """
    Make an HTTP request to the backend.
    Returns (data, None) on success or (None, error_message) on failure.
    Never exposes raw token values in error messages.
    """
    url = f"{BACKEND_URL}{path}"
    headers = {**_auth_headers(), **kwargs.pop("headers", {})}
    try:
        resp = requests.request(method, url, timeout=timeout, headers=headers, **kwargs)
        if resp.status_code in (200, 201, 204):
            if resp.status_code == 204 or not resp.content:
                return {}, None
            try:
                return resp.json(), None
            except Exception:
                return resp.text, None
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return None, f"HTTP {resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, "Backend not reachable. Try refreshing the page."
    except requests.exceptions.Timeout:
        return None, "Request timed out. The backend may be busy — try again."
    except Exception as exc:
        return None, str(exc)


def api_get(path: str, timeout: int = TIMEOUT_SHORT, **kw):
    return api_request("GET", path, timeout, **kw)

def api_post(path: str, timeout: int = TIMEOUT_LONG, **kw):
    return api_request("POST", path, timeout, **kw)

def api_patch(path: str, timeout: int = TIMEOUT_SHORT, **kw):
    return api_request("PATCH", path, timeout, **kw)

def api_download(path: str, timeout: int = TIMEOUT_SHORT) -> tuple[Optional[bytes], Optional[str]]:
    """Download binary content (e.g. Excel / CSV files). Returns (bytes, error)."""
    url = f"{BACKEND_URL}{path}"
    headers = _auth_headers()
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
        if resp.status_code == 200:
            return resp.content, None
        return None, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as exc:
        return None, str(exc)


def api_delete(path: str, timeout: int = TIMEOUT_SHORT, **kw):
    return api_request("DELETE", path, timeout, **kw)


def stream_sse(path: str, payload: dict, timeout: int = TIMEOUT_LONG) -> str:
    """
    Consume a server-sent-events endpoint and return the concatenated text.
    Tokens are delivered as 'data: <text>' lines; '[DONE]' signals the end.
    Returns the full accumulated string, or raises on error.
    """
    url = f"{BACKEND_URL}{path}"
    headers = _auth_headers()
    resp = requests.post(url, json=payload, stream=True, timeout=timeout, headers=headers)
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    parts: list[str] = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line.startswith("data: "):
            continue
        payload_str = line[6:]
        if payload_str == "[DONE]":
            break
        if payload_str.startswith("[ERROR]"):
            raise RuntimeError(payload_str[7:])
        parts.append(payload_str.replace("\\n", "\n"))
    return "".join(parts)
