"""
test_smtp.py — Test SMTP connectivity and real email dispatch.
Usage:
  python backend/test_smtp.py <recipient_email> [host] [port] [user] [pass]
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import get_settings
from services.email_service import send_email


async def main():
    settings = get_settings()
    recipient = sys.argv[1] if len(sys.argv) > 1 else settings.smtp_user

    print("==================================================")
    print("       STUDYBUDDY SMTP REAL EMAIL VERIFIER        ")
    print("==================================================")
    print(f"SMTP Host: {settings.smtp_host or '[NOT SET]'}")
    print(f"SMTP Port: {settings.smtp_port}")
    print(f"SMTP User: {settings.smtp_user or '[NOT SET]'}")
    print(f"SMTP From: {settings.smtp_from}")
    print(f"Target Recipient: {recipient or '[NOT SET]'}")
    print("--------------------------------------------------")

    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_pass:
        print("❌ SMTP configuration is incomplete in backend/.env!")
        print("\nTo send real emails and real OTP codes:")
        print("1. Open backend/.env")
        print("2. Set your SMTP settings, for example Gmail:")
        print("     SMTP_HOST=smtp.gmail.com")
        print("     SMTP_PORT=587")
        print("     SMTP_USER=your-email@gmail.com")
        print("     SMTP_PASS=xxxx-xxxx-xxxx-xxxx  (Google 16-char App Password)")
        print("     SMTP_FROM=StudyBuddy <your-email@gmail.com>")
        print("3. Run: python backend/test_smtp.py your-email@gmail.com")
        print("==================================================")
        return

    print("Attempting to connect to SMTP server and dispatch real email...")
    test_otp = "849201"
    body_html = f"""
    <p>Hello,</p>
    <p>This is a test verification email from your StudyBuddy AI platform.</p>
    <p>Your one-time security code is:</p>
    <div style="font-size:32px;font-weight:900;letter-spacing:8px;color:#818cf8;background:#1e1b4b;padding:14px 20px;border-radius:10px;text-align:center;margin:16px 0;display:inline-block;">{test_otp}</div>
    <p>If you received this email, your real email sending and real OTP system is 100% operational!</p>
    """

    success = await send_email(
        to=recipient,
        subject="[StudyBuddy AI] Real Email Dispatch Verification",
        body=body_html,
    )

    if success:
        print("\n🎉 SUCCESS! Real verification email was dispatched successfully.")
        print(f"Check the inbox (and spam folder) of: {recipient}")
    else:
        print("\n❌ FAILED to send email. Check your SMTP credentials, port, and password.")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
