"""
services/email_service.py — Async email via SMTP using Jinja2 templates or direct HTML/text.

Reads SMTP credentials from environment variables.
If SMTP_HOST is not configured, logs the message and returns False cleanly (simulation mode).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"
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
            _jinja_env = None
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

    if template_path.exists():
        html = template_path.read_text(encoding="utf-8")
        for key, value in context.items():
            html = html.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")
        return html

    return "\n".join(f"{k}: {v}" for k, v in context.items())


def wrap_html_email(title: str, content: str) -> str:
    """Wrap raw message content into a branded StudyBuddy responsive email design."""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#090d16;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e5e7eb;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#090d16;padding:30px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:580px;background:#111827;border:1px solid #1f2937;border-radius:16px;overflow:hidden;box-shadow:0 10px 25px rgba(0,0,0,0.4);" cellspacing="0" cellpadding="0">
          <tr>
            <td style="padding:28px 32px;background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 100%);border-bottom:1px solid #1f2937;">
              <div style="display:flex;align-items:center;">
                <span style="font-size:24px;margin-right:10px;">🎓</span>
                <span style="font-size:20px;font-weight:800;color:#ffffff;letter-spacing:-0.03em;">StudyBuddy <span style="color:#818cf8;">AI</span></span>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 32px 24px;">
              <h2 style="margin:0 0 16px;font-size:18px;font-weight:700;color:#ffffff;">{title}</h2>
              <div style="font-size:14px;line-height:1.6;color:#d1d5db;margin-bottom:24px;">
                {content.replace(chr(10), '<br>')}
              </div>
              <div style="border-top:1px solid #1f2937;padding-top:20px;font-size:12px;color:#6b7280;">
                Sent via StudyBuddy AI Automated Notification Relay &bull; Mangalayatan University
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def send_email(
    to: str | list[str],
    subject: str,
    template_name: str = "",
    context: dict[str, Any] | None = None,
    body: str = "",
) -> bool:
    """
    Send an HTML email using a Jinja2 template or direct body.
    Returns True on success, False on failure.
    If SMTP_HOST is not configured, logs in simulation mode and returns False.
    """
    current_settings = get_settings()
    recipients = [to] if isinstance(to, str) else to
    context = context or {}
    context.setdefault("app_name", "Study Buddy")
    context.setdefault("app_url", current_settings.app_base_url)

    if body:
        html_body = body if ("<html" in body.lower() or "<body" in body.lower()) else wrap_html_email(subject, body)
    elif template_name:
        html_body = _render_template(template_name, context)
    else:
        html_body = wrap_html_email(subject, "\n".join(f"{k}: {v}" for k, v in context.items()))

    if not current_settings.smtp_host or not current_settings.smtp_user or not current_settings.smtp_pass:
        logger.info("[SMTP SIMULATION] Email to %s | Subject: '%s' | Body Preview: %s", recipients, subject, html_body[:120].replace('\n', ' '))
        return False

    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.utils import formatdate, make_msgid
        import re

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = current_settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg["Date"] = formatdate(localtime=True)
        try:
            domain = current_settings.smtp_host.split(".")[-2] + "." + current_settings.smtp_host.split(".")[-1]
        except Exception:
            domain = "studybuddy.ai"
        msg["Message-ID"] = make_msgid(domain=domain)

        # Plain-text alternative reduces spam scores significantly
        plain_text = re.sub(r"<[^>]+>", " ", html_body)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        use_tls = current_settings.smtp_port == 465
        start_tls = current_settings.smtp_port == 587 or (not use_tls and current_settings.smtp_port != 25)

        await aiosmtplib.send(
            msg,
            hostname=current_settings.smtp_host,
            port=current_settings.smtp_port,
            username=current_settings.smtp_user or None,
            password=current_settings.smtp_pass or None,
            use_tls=use_tls,
            start_tls=start_tls,
        )
        logger.info("email_sent", extra={"to": recipients, "subject": subject})
        print(f"📧 [EMAIL DISPATCH SUCCESS] Real email sent to {recipients} | Subject: '{subject}'", flush=True)
        return True
    except Exception as exc:
        logger.warning("email_failed", extra={"error": str(exc), "to": to})
        print(f"❌ [EMAIL DISPATCH FAILED] Real email failed for {recipients}: {exc}", flush=True)
        return False
