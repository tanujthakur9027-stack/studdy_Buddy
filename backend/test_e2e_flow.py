"""
test_e2e_flow.py — End-to-End Test for Admin/Student OTP Login, ID resolution, and Notifications.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from httpx import AsyncClient, ASGITransport
from main import app
from database import init_db


async def run_e2e():
    print("==================================================")
    print("      STUDYBUDDY E2E VERIFICATION TEST RUNNER     ")
    print("==================================================")

    # 1. Initialize DB
    await init_db()
    print("✓ Database initialized.")

    from config import get_settings
    settings = get_settings()
    settings.otp_auth_enabled = False
    settings.otp_simulation_mode = False
    settings.environment = "development"
    settings.admin_keys = "TestAdminSecret2026!"

    from main import limiter
    from routers.auth import limiter as auth_limiter
    limiter.enabled = False
    auth_limiter.enabled = False

    from database import AsyncSessionLocal
    from models.db_models import User
    from services.auth_service import hash_password
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "admin@studybuddy.com"))
        adm = res.scalar_one_or_none()
        if not adm:
            adm = User(
                email="admin@studybuddy.com",
                password_hash=hash_password("TestAdminSecret2026!"),
                full_name="Admin",
                role="admin",
                is_active=True,
            )
            db.add(adm)
        else:
            adm.password_hash = hash_password("TestAdminSecret2026!")
            adm.is_active = True
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ------------------------------------------------------------------
        # TEST 1: Admin Direct Login (No OTP / No SMTP Required)
        # ------------------------------------------------------------------
        print("\n[Test 1] Testing Admin Direct Login (Password Authentication)...")
        resp = await client.post("/api/auth/login", json={
            "email": "admin@studybuddy.com",
            "password": "TestAdminSecret2026!",
        })
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        data = resp.json()
        assert data.get("otp_required") is False, f"Expected otp_required=False, got: {data}"
        assert data.get("access_token") is not None, "Missing access_token"
        assert data.get("user", {}).get("role") == "admin", "User role is not admin"
        admin_token = data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"  ✓ Admin logged in directly! Token generated. Admin ID: {data['user']['id']}")

        # ------------------------------------------------------------------
        # TEST 2: Student Direct Registration & Login
        # ------------------------------------------------------------------
        print("\n[Test 2] Testing Student Direct Registration (No OTP Required)...")
        import random
        stu_rand = uuid.uuid4().hex[:6]
        test_stu_email = f"student_{stu_rand}@example.com"
        test_stu_sid = f"CS{random.randint(20000, 99999)}"
        reg_resp = await client.post("/api/auth/register", json={
            "email": test_stu_email,
            "password": "TestPassword123!",
            "full_name": "Test Student Direct",
            "student_id": test_stu_sid,
            "course": "B.Tech CSE",
            "semester": "6",
            "section": "A",
        })
        assert reg_resp.status_code == 201, f"Student register failed: {reg_resp.text}"
        reg_data = reg_resp.json()
        assert reg_data.get("otp_required") is False, "Expected otp_required=False on registration"
        assert reg_data.get("access_token") is not None, "Expected immediate access_token"
        stu_token = reg_data["access_token"]
        print(f"  ✓ Registered student and obtained immediate access token: {reg_data['user']['student_id']}")

        stu_headers = {"Authorization": f"Bearer {stu_token}"}

        # ------------------------------------------------------------------
        # TEST 3: Student Profile & ID lookup
        # ------------------------------------------------------------------
        print("\n[Test 3] Testing Student Profile endpoint...")
        prof_resp = await client.get("/api/students/profile", headers=stu_headers)
        assert prof_resp.status_code == 200, f"Profile fetch failed: {prof_resp.text}"
        profile = prof_resp.json()
        print(f"  ✓ Student Profile retrieved: ID='{profile.get('student_id')}', Name='{profile.get('full_name')}'")
        assert profile.get("student_id"), "student_id must not be empty or unassigned!"

        # ------------------------------------------------------------------
        # TEST 4: Admin Student Lookup by Student ID (Roll Number)
        # ------------------------------------------------------------------
        target_sid = profile.get("student_id")
        print(f"\n[Test 4] Testing Admin lookup by Student ID ('{target_sid}')...")
        admin_lookup = await client.get(f"/api/admin/students/{target_sid}", headers=admin_headers)
        assert admin_lookup.status_code == 200, f"Admin lookup by Student ID failed: {admin_lookup.text}"
        stu_details = admin_lookup.json()
        print(f"  ✓ Admin found student by Roll Number '{target_sid}': {stu_details.get('full_name')}")

        # ------------------------------------------------------------------
        # TEST 5: Admin Broadcast Notification & Email Dispatch
        # ------------------------------------------------------------------
        print("\n[Test 5] Testing Admin Notification Broadcast...")
        broadcast_resp = await client.post("/api/notifications/broadcast", headers=admin_headers, json={
            "title": "Semester Examination Schedule",
            "message": "Final examinations will commence next Monday. Check your timetable.",
            "target": "all",
            "send_email": True,
        })
        assert broadcast_resp.status_code == 201, f"Broadcast failed: {broadcast_resp.text}"
        bcast_data = broadcast_resp.json()
        print(f"  ✓ Broadcast result: {bcast_data['message']}")

        # ------------------------------------------------------------------
        # TEST 6: Student Receives Broadcast Notification
        # ------------------------------------------------------------------
        print("\n[Test 6] Testing Student Notification Inbox...")
        notif_resp = await client.get("/api/notifications", headers=stu_headers)
        assert notif_resp.status_code == 200, f"Fetch notifications failed: {notif_resp.text}"
        notifs = notif_resp.json()
        assert len(notifs) > 0, "Student should have at least one notification"
        latest = notifs[0]
        print(f"  ✓ Latest notification in student inbox: '{latest['title']}' - '{latest['message'][:50]}...'")

        # ------------------------------------------------------------------
        # TEST 7: Register Brand New Admin Account (No OTP Required)
        # ------------------------------------------------------------------
        print("\n[Test 7] Testing New Admin Direct Registration...")
        random_suffix = uuid.uuid4().hex[:6]
        new_admin_email = f"dean_{random_suffix}@university.edu"
        reg_admin_resp = await client.post("/api/auth/register-admin", json={
            "email": new_admin_email,
            "password": "DeanPassword2024!",
            "full_name": "Dean Ada Lovelace",
            "admin_key": "TestAdminSecret2026!",
            "phone": "+91 9123456789",
            "student_id": f"EMP-DEAN-{random_suffix.upper()}",
            "role": "admin",
        })
        assert reg_admin_resp.status_code == 201, f"Admin register failed: {reg_admin_resp.text}"
        reg_admin_data = reg_admin_resp.json()
        assert reg_admin_data.get("otp_required") is False, "Expected otp_required=False on admin reg"
        assert reg_admin_data.get("access_token") is not None, "Missing access_token"
        new_admin_token = reg_admin_data["access_token"]
        assert reg_admin_data["user"]["role"] == "admin"
        assert reg_admin_data["user"]["email"] == new_admin_email
        print(f"  ✓ New Admin registered directly! Role: {reg_admin_data['user']['role']}, Admin ID: {reg_admin_data['user']['student_id']}")

        # Verify New Admin can access Admin Dashboard / Classes API
        new_admin_headers = {"Authorization": f"Bearer {new_admin_token}"}
        classes_resp = await client.get("/api/admin/classes", headers=new_admin_headers)
        assert classes_resp.status_code == 200, f"New admin classes check failed: {classes_resp.text}"
        print(f"  ✓ New Admin successfully accessed Admin Portal API (/api/admin/classes)!")

    print("\n==================================================")
    print("   ✓ ALL E2E VERIFICATION CHECKS PASSED (100%)    ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_e2e())
