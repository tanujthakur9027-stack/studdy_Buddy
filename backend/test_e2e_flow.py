"""
test_e2e_flow.py — Comprehensive End-to-End Test for Admin/Student Authentication,
Class-Based Management System, Permission Isolation, and EduGuard ML Early Warning System.
"""
from __future__ import annotations

import asyncio
import os
import random
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
                is_super_admin=True,
            )
            db.add(adm)
        else:
            adm.password_hash = hash_password("TestAdminSecret2026!")
            adm.is_active = True
            adm.is_super_admin = True
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
        super_admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"  ✓ Admin logged in directly! Token generated. Admin ID: {data['user']['id']}")

        # ------------------------------------------------------------------
        # TEST 2: Student Direct Registration & Login
        # ------------------------------------------------------------------
        print("\n[Test 2] Testing Student Direct Registration (No OTP Required)...")
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
        admin_lookup = await client.get(f"/api/admin/students/{target_sid}", headers=super_admin_headers)
        assert admin_lookup.status_code == 200, f"Admin lookup by Student ID failed: {admin_lookup.text}"
        stu_details = admin_lookup.json()
        print(f"  ✓ Admin found student by Roll Number '{target_sid}': {stu_details.get('full_name')}")

        # ------------------------------------------------------------------
        # TEST 5: Admin Broadcast Notification
        # ------------------------------------------------------------------
        print("\n[Test 5] Testing Admin Notification Broadcast...")
        broadcast_resp = await client.post("/api/notifications/broadcast", headers=super_admin_headers, json={
            "title": "Semester Examination Schedule",
            "message": "Final examinations will commence next Monday. Check your timetable.",
            "target": "all",
            "send_email": False,
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

        # ------------------------------------------------------------------
        # TEST 8: CLASS-BASED MANAGEMENT SYSTEM FULL E2E WORKFLOW
        # ------------------------------------------------------------------
        print("\n[Test 8] Testing Complete Class-Based Management Flow...")
        tag = uuid.uuid4().hex[:4]
        cname_a = f"10_{tag}"
        cname_b = f"10_{tag}"

        # 1. Create class "10-A" and "10-B"
        print("  1. Creating classes '10-A' and '10-B'...")
        c_a_resp = await client.post("/api/classes", headers=super_admin_headers, json={
            "name": cname_a,
            "section": "A",
            "academic_year": "2026-2027",
        })
        assert c_a_resp.status_code == 201, f"Create class A failed: {c_a_resp.text}"
        class_a_id = c_a_resp.json()["id"]

        c_b_resp = await client.post("/api/classes", headers=super_admin_headers, json={
            "name": cname_b,
            "section": "B",
            "academic_year": "2026-2027",
        })
        assert c_b_resp.status_code == 201, f"Create class B failed: {c_b_resp.text}"
        class_b_id = c_b_resp.json()["id"]
        print(f"     ✓ Created Class A ({class_a_id}) and Class B ({class_b_id})")

        # 2. Enroll 2 students in "10-A", 1 in "10-B"
        print("  2. Enrolling 2 students in 10-A and 1 student in 10-B...")
        s1_email = f"s1_{uuid.uuid4().hex[:6]}@school.org"
        s1_resp = await client.post(f"/api/classes/{class_a_id}/students", headers=super_admin_headers, json={
            "email": s1_email,
            "password": "Password123!",
            "full_name": "Student One 10-A",
            "roll_number": "10A-01",
        })
        assert s1_resp.status_code == 201, f"Enroll s1 failed: {s1_resp.text}"

        s2_email = f"s2_{uuid.uuid4().hex[:6]}@school.org"
        s2_resp = await client.post(f"/api/classes/{class_a_id}/students", headers=super_admin_headers, json={
            "email": s2_email,
            "password": "Password123!",
            "full_name": "Student Two 10-A",
            "roll_number": "10A-02",
        })
        assert s2_resp.status_code == 201, f"Enroll s2 failed: {s2_resp.text}"

        s3_email = f"s3_{uuid.uuid4().hex[:6]}@school.org"
        s3_resp = await client.post(f"/api/classes/{class_b_id}/students", headers=super_admin_headers, json={
            "email": s3_email,
            "password": "Password123!",
            "full_name": "Student Three 10-B",
            "roll_number": "10B-01",
        })
        assert s3_resp.status_code == 201, f"Enroll s3 failed: {s3_resp.text}"

        # Login students to get tokens
        s1_login = await client.post("/api/auth/login", json={"email": s1_email, "password": "Password123!"})
        s1_token = s1_login.json()["access_token"]
        s1_headers = {"Authorization": f"Bearer {s1_token}"}

        s3_login = await client.post("/api/auth/login", json={"email": s3_email, "password": "Password123!"})
        s3_token = s3_login.json()["access_token"]
        s3_headers = {"Authorization": f"Bearer {s3_token}"}
        print("     ✓ Enrolled and verified login sessions for Students in 10-A and 10-B")

        # 3. Create class admin for "10-A"
        print("  3. Assigning new admin as Class Admin for 10-A...")
        admin_a_email = f"admin_10a_{uuid.uuid4().hex[:6]}@school.org"
        reg_admin_a = await client.post("/api/auth/register-admin", json={
            "email": admin_a_email,
            "password": "Admin10APassword123!",
            "full_name": "Class Admin 10-A",
            "admin_key": "TestAdminSecret2026!",
            "student_id": f"EMP-10A-{uuid.uuid4().hex[:4]}",
        })
        assert reg_admin_a.status_code == 201
        admin_a_user_id = reg_admin_a.json()["user"]["id"]
        admin_a_token = reg_admin_a.json()["access_token"]
        admin_a_headers = {"Authorization": f"Bearer {admin_a_token}"}

        # Demote admin_a from super_admin to regular class admin
        async with AsyncSessionLocal() as db:
            adm_res = await db.execute(select(User).where(User.id == admin_a_user_id))
            adm_obj = adm_res.scalar_one()
            adm_obj.is_super_admin = False
            await db.commit()

        # Assign to 10-A
        assign_resp = await client.post(f"/api/classes/{class_a_id}/admins", headers=super_admin_headers, json={
            "admin_user_id": admin_a_user_id,
        })
        assert assign_resp.status_code == 200, f"Assign class admin failed: {assign_resp.text}"
        print("     ✓ Class Admin assigned to 10-A successfully.")

        # 4. Class admin creates assignment for "10-A" → 201
        print("  4. Class admin creating assignment for 10-A...")
        create_asgn_resp = await client.post(
            "/api/admin/assignments",
            headers=admin_a_headers,
            data={
                "title": "Algebra Quadratics",
                "subject_id": "MATH-10",
                "class_id": class_a_id,
                "due_date": "2026-12-15",
                "due_time": "23:59",
                "max_marks": 100,
            },
        )
        assert create_asgn_resp.status_code == 201, f"Assignment create failed: {create_asgn_resp.text}"
        asgn_10a_id = create_asgn_resp.json()["id"]
        print(f"     ✓ Assignment successfully created for 10-A: ID={asgn_10a_id}")

        # 5. Class admin attempts assignment for "10-B" → 403 Forbidden
        print("  5. Class admin attempting assignment for 10-B (expecting 403 Forbidden)...")
        forbidden_asgn_resp = await client.post(
            "/api/admin/assignments",
            headers=admin_a_headers,
            data={
                "title": "Calculus Intrusion",
                "subject_id": "MATH-10",
                "class_id": class_b_id,
                "due_date": "2026-12-15",
                "due_time": "23:59",
                "max_marks": 100,
            },
        )
        assert forbidden_asgn_resp.status_code == 403, f"Expected 403, got {forbidden_asgn_resp.status_code}: {forbidden_asgn_resp.text}"
        print("     ✓ Class Admin was blocked with 403 Forbidden on 10-B assignment creation.")

        # 6. Post announcement for "10-A"
        print("  6. Posting announcement targeted to 10-A...")
        ann_resp = await client.post(
            "/api/admin/announcements",
            headers=admin_a_headers,
            json={
                "title": "10-A Parent Teacher Meeting",
                "content": "PTM scheduled for Friday afternoon.",
                "class_id": class_a_id,
            },
        )
        assert ann_resp.status_code == 201, f"Announcement post failed: {ann_resp.text}"
        ann_id = ann_resp.json()["id"]
        print(f"     ✓ Announcement created for 10-A: ID={ann_id}")

        # 7. Student in "10-A" fetches announcements → sees it
        print("  7. Student in 10-A fetching announcements...")
        s1_anns = await client.get("/api/announcements", headers=s1_headers)
        assert s1_anns.status_code == 200
        s1_ann_ids = [a["id"] for a in s1_anns.json()]
        assert ann_id in s1_ann_ids, "Student 1 in 10-A should see the 10-A announcement!"
        print("     ✓ Student in 10-A successfully sees the 10-A announcement.")

        # 8. Student in "10-B" fetches announcements → does NOT see it
        print("  8. Student in 10-B fetching announcements...")
        s3_anns = await client.get("/api/announcements", headers=s3_headers)
        assert s3_anns.status_code == 200
        s3_ann_ids = [a["id"] for a in s3_anns.json()]
        assert ann_id not in s3_ann_ids, "Student 3 in 10-B must NOT see the 10-A announcement!"
        print("     ✓ Student in 10-B correctly does NOT see the 10-A announcement (Strict Isolation verified).")

        # 9. Send marks for "10-A" students
        print("  9. Creating assessment category and entering marks for 10-A students...")
        cat_resp = await client.post(
            "/api/admin/assessment-categories",
            headers=admin_a_headers,
            json={
                "name": "Mid-Term Exam",
                "subject_id": "MATH-10",
                "class_id": class_a_id,
                "max_marks": 100,
                "weightage": 50,
            },
        )
        assert cat_resp.status_code == 201, f"Category creation failed: {cat_resp.text}"
        cat_id = cat_resp.json()["id"]

        marks_resp = await client.post(
            "/api/admin/marks",
            headers=admin_a_headers,
            json=[
                {
                    "student_id": "10A-01",
                    "category_id": cat_id,
                    "class_id": class_a_id,
                    "obtained_marks": 92.5,
                    "remarks": "Excellent grasp of concepts",
                },
                {
                    "student_id": "10A-02",
                    "category_id": cat_id,
                    "class_id": class_a_id,
                    "obtained_marks": 85.0,
                    "remarks": "Very good performance",
                },
            ],
        )
        assert marks_resp.status_code == 201, f"Marks entry failed: {marks_resp.text}"
        print("     ✓ Marks entered and saved for 10-A students successfully.")

        # ------------------------------------------------------------------
        # TEST 9: EDUGUARD AI ATTRITION ML MODEL VERIFICATION
        # ------------------------------------------------------------------
        print("\n[Test 9] Testing EduGuard Dropout Risk ML Prediction Model...")
        ml_resp = await client.post(
            "/api/admin/attrition/evaluate",
            headers=super_admin_headers,
            json={
                "debtor": 0,
                "scholarship_holder": 1,
                "age_at_enrollment": 19.5,
                "gender": 1,
                "first_sem_grade": 16.5,
                "attendance_rate": 92.0,
            },
        )
        assert ml_resp.status_code == 200, f"EduGuard evaluation failed: {ml_resp.text}"
        ml_data = ml_resp.json()
        assert "risk_probability" in ml_data, "Missing risk_probability"
        assert "risk_level" in ml_data, "Missing risk_level"
        assert "recommendations" in ml_data, "Missing recommendations"
        print(f"  ✓ EduGuard ML model online! Risk probability: {ml_data['risk_probability']:.2f}%, Level: {ml_data['risk_level']}")

        # Test listing student retention risk records
        list_attr_resp = await client.get("/api/admin/attrition/students", headers=super_admin_headers)
        assert list_attr_resp.status_code == 200, f"EduGuard students list failed: {list_attr_resp.text}"
        attr_students = list_attr_resp.json()
        print(f"  ✓ EduGuard analyzed {len(attr_students)} registered students across academic records.")

    print("\n==================================================")
    print("   ✓ ALL E2E VERIFICATION CHECKS PASSED (100%)    ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_e2e())
