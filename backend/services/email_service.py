"""
services/email_service.py — Async email via SMTP using Jinja2 templates.

Reads SMTP credentials from environment variables.
If SMTP_HOST is not configured, all send calls are no-ops (log warning only).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"

# Lazy-initialise Jinja2 environment (Jinja2 is a FastAPI/Starlette dependency)
_jinja_env = None


def _get_jinja_env():
    global _jinja_env
    if _jinja_env is None:
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            _jinja_env = Environment(
                loader=FileSystemLoader(str(_TEMPLATE_DIR)),
                autoescape=select_autoescape(["html"]),
            )
        except ImportError:
            _jinja_env = None  # Jinja2 not available — fallback to plain text
    return _jinja_env


def _render_template(name: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 HTML template. Falls back to plain-text key:value list."""
    env = _get_jinja_env()
    template_path = _TEMPLATE_DIR / name

    if env and template_path.exists():
        try:
            tmpl = env.get_template(name)
            return tmpl.render(**context)
        except Exception as exc:
            logger.warning("email_template_render_error", extra={"name": name, "error": str(exc)})

    # Plain-text fallback
    if template_path.exists():
        # Try simple {{key}} replacement as last resort
        html = template_path.read_text(encoding="utf-8")
        for key, value in context.items():
            html = html.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")
        return html

    return "\n".join(f"{k}: {v}" for k, v in context.items())


async def send_email(
    to: str | list[str],
    subject: str,
    template_name: str,
    context: dict[str, Any] | None = None,
) -> bool:
    """
    Send an HTML email using a Jinja2 template.
    Returns True on success, False on failure.
    Silently skips (returns False) if SMTP_HOST is not configured.
    """
    if not settings.smtp_host:
        logger.debug("email_skipped_no_smtp", extra={"to": to, "subject": subject})
        return False

    context = context or {}
    context.setdefault("app_name", "Study Buddy")
    context.setdefault("app_url", settings.app_base_url)

    html_body = _render_template(template_name, context)
    recipients = [to] if isinstance(to, str) else to

    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_pass or None,
            start_tls=settings.smtp_port == 587,
        )
        logger.info("email_sent", extra={"to": recipients, "subject": subject})
        return True
    except Exception as exc:
        logger.warning("email_failed", extra={"error": str(exc), "to": to})
        return False
