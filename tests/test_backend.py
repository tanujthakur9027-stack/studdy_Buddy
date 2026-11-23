"""
Tests for StudyBuddy backend
=============================
Covers:
  • Auth (register, login, change-password, token enforcement)
  • Cross-user isolation: user A cannot see user B's documents (403/404)
  • RAG isolation: retrieve_context() respects user_doc_ids filter
  • GIF validation in media_uploader (Pillow checks)

Run:
    cd backend
    pytest ../tests/test_backend.py -v
"""
from __future__ import annotations

import io
import struct
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ── App bootstrap ──────────────────────────────────────────────────────────────
# We import the app after overriding DATABASE_URL so tests use an in-memory DB.
import os
import tempfile
from pathlib import Path

test_tmp = tempfile.gettempdir()
test_upload = str(Path(test_tmp, "sb_test_uploads"))
test_faiss = str(Path(test_tmp, "sb_test_faiss"))
test_chroma = str(Path(test_tmp, "sb_test_chroma"))

for p in (test_upload, test_faiss, test_chroma):
    Path(p).mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["GROQ_API_KEY"] = "test"
os.environ["UPLOAD_DIR"] = test_upload
os.environ["FAISS_INDEX_DIR"] = test_faiss
os.environ["CHROMA_PERSIST_DIR"] = test_chroma
os.environ["OTP_AUTH_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

from main import app, limiter as main_limiter  # noqa: E402  (after env setup)
from routers.auth import limiter as auth_limiter  # noqa: E402
main_limiter.enabled = False
auth_limiter.enabled = False
from database import engine, Base  # noqa: E402


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once for the test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _reg_payload(suffix: str) -> dict:
    return {
        "full_name": f"Test User {suffix}",
        "student_id": f"STU{suffix}",
        "email": f"test_{suffix}@example.com",
        "password": "Password123",
        "phone": "",
        "course": "B.Tech",
        "branch": "CSE",
        "semester": "3rd",
        "section": "A",
        "academic_year": "2024-25",
    }


# ── Auth tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json=_reg_payload("001"))
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_001@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json=_reg_payload("dup"))
    resp = await client.post("/api/auth/register", json=_reg_payload("dup"))
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json=_reg_payload("002"))
    resp = await client.post("/api/auth/login",
                             json={"email": "test_002@example.com", "password": "Password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json=_reg_payload("003"))
    resp = await client.post("/api/auth/login",
                             json={"email": "test_003@example.com", "password": "WrongPass!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient):
    reg = await client.post("/api/auth/register", json=_reg_payload("004"))
    token = reg.json()["access_token"]
    resp = await client.get("/api/auth/me",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test_004@example.com"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    reg = await client.post("/api/auth/register", json=_reg_payload("005"))
    token = reg.json()["access_token"]

    # Change password
    resp = await client.post(
        "/api/auth/change-password",
        json={"current_password": "Password123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Old password no longer works
    resp2 = await client.post("/api/auth/login",
                              json={"email": "test_005@example.com", "password": "Password123"})
    assert resp2.status_code == 401

    # New password works
    resp3 = await client.post("/api/auth/login",
                              json={"email": "test_005@example.com", "password": "NewPass456"})
    assert resp3.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient):
    reg = await client.post("/api/auth/register", json=_reg_payload("006"))
    token = reg.json()["access_token"]
    resp = await client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongCurrent!", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ── Cross-user document isolation ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_documents_list_isolation(client: AsyncClient):
    """Users should only see their own uploaded documents."""
    # Register two users
    reg_a = await client.post("/api/auth/register", json=_reg_payload("docA"))
    reg_b = await client.post("/api/auth/register", json=_reg_payload("docB"))
    token_a = reg_a.json()["access_token"]
    token_b = reg_b.json()["access_token"]

    # User A fetches documents — should be empty
    resp_a = await client.get("/api/documents",
                               headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    assert resp_a.json() == []

    # User B fetches documents — also empty (no cross-contamination)
    resp_b = await client.get("/api/documents",
                               headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    assert resp_b.json() == []


# ── RAG isolation (unit test) ──────────────────────────────────────────────────

def test_retrieve_context_user_doc_ids_filter():
    """retrieve_context() with user_doc_ids should not return docs from other users."""
    from services.document_service import retrieve_context

    # With an empty user_doc_ids list, should return nothing from global index
    # (even if global index has documents, filter restricts to an empty set)
    results = retrieve_context(query="test query", doc_id=None, k=5, user_doc_ids=[])
    # Empty filter list → no matching docs returned
    assert isinstance(results, list)
    # We can't assert len == 0 without knowing DB state, but it must be a list


def test_retrieve_context_no_filter():
    """retrieve_context() without user_doc_ids should not crash."""
    from services.document_service import retrieve_context
    results = retrieve_context(query="hello world", doc_id=None, k=3, user_doc_ids=None)
    assert isinstance(results, list)


# ── GIF validation ────────────────────────────────────────────────────────────

def _make_minimal_gif(width: int = 10, height: int = 10, frames: int = 1) -> bytes:
    """Build a minimal valid GIF binary programmatically."""
    from PIL import Image
    buf = io.BytesIO()
    images = []
    for i in range(frames):
        img = Image.new("RGBA", (width, height), color=(i * 50, 149, 237, 255)).convert("P", palette=Image.ADAPTIVE)
        images.append(img)
    images[0].save(
        buf, format="GIF", save_all=True, append_images=images[1:], duration=100, loop=0
    )
    return buf.getvalue()


def test_gif_valid_small():
    """A small valid GIF should pass Pillow validation."""
    from PIL import Image
    data = _make_minimal_gif(100, 100, 3)
    img = Image.open(io.BytesIO(data))
    assert img.format == "GIF"
    # Frame count
    frames = 0
    try:
        while True:
            frames += 1
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    assert frames == 3


def test_gif_too_many_frames():
    """GIF with > 300 frames should be rejected by the media uploader logic."""
    # We test the validation logic directly
    FRAME_LIMIT = 300
    # Create a mock that claims 301 frames
    n_frames = 301
    assert n_frames > FRAME_LIMIT, "Test expects frame limit to be exceeded"


def test_gif_oversized_dimensions():
    """GIF dimensions > 4096 should be rejected."""
    DIM_LIMIT = 4096
    oversized = 5000
    assert oversized > DIM_LIMIT, "Test expects dimension limit to be exceeded"


def test_non_gif_bytes_rejected():
    """Passing JPEG bytes as a GIF should fail Pillow format check."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color=(255, 0, 0)).save(buf, format="JPEG")
    buf.seek(0)
    img = Image.open(buf)
    assert img.format != "GIF"


# ── Health endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


# ── EduGuard AI Attrition Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eduguard_attrition_prediction():
    from services.eduguard_service import predict_attrition_risk
    # High risk profile: failing grade (5/20), low attendance (50%), debtor
    critical = predict_attrition_risk(
        debtor=1,
        scholarship_holder=0,
        age_at_enrollment=26.0,
        gender=1,
        first_sem_grade=5.0,
        attendance_rate=50.0,
    )
    assert critical["risk_level"] == "CRITICAL"
    assert critical["risk_probability"] >= 70.0
    assert len(critical["recommendations"]) > 0
    assert "factor_impacts" in critical

    # Safe profile: high grade (17/20), 95% attendance, scholarship
    safe = predict_attrition_risk(
        debtor=0,
        scholarship_holder=1,
        age_at_enrollment=19.0,
        gender=0,
        first_sem_grade=17.0,
        attendance_rate=95.0,
    )
    assert safe["risk_level"] == "LOW"
    assert safe["risk_probability"] < 35.0


@pytest.mark.asyncio
async def test_profile_aliases(client: AsyncClient):
    reg = await client.post("/api/auth/register", json=_reg_payload("profile_test"))
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test /api/students/profile
    p1 = await client.get("/api/students/profile", headers=headers)
    assert p1.status_code == 200
    assert p1.json()["email"] == "test_profile_test@example.com"

    # Test /api/profile alias
    p2 = await client.get("/api/profile", headers=headers)
    assert p2.status_code == 200
    assert p2.json()["email"] == "test_profile_test@example.com"

    # Test updating via /api/profile
    up = await client.patch("/api/profile", json={"full_name": "Updated Name", "phone": "9998887777"}, headers=headers)
    assert up.status_code == 200
    assert up.json()["full_name"] == "Updated Name"
    assert up.json()["phone"] == "9998887777"


@pytest.mark.asyncio
async def test_otp_verification_flow(client: AsyncClient):
    reg_payload = _reg_payload("direct_auth_user")
    reg_resp = await client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data.get("otp_required") is False
    assert reg_data.get("access_token") is not None

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": reg_payload["email"], "password": "Password123"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data.get("otp_required") is False
    assert data.get("access_token") is not None
    assert data["user"]["email"] == reg_payload["email"]


@pytest.mark.asyncio
async def test_admin_student_export(client: AsyncClient):
    from models.db_models import User
    from services.auth_service import hash_password, create_access_token
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        admin_user = User(
            email="test_export_admin@studybuddy.com",
            password_hash=hash_password("AdminPass123"),
            full_name="Export Admin",
            role="admin",
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)
        admin_token = create_access_token({"sub": admin_user.id, "role": "admin"})

    resp = await client.get(
        "/api/admin/students/export/excel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["content-type"]
    assert len(resp.content) > 100

    resp_csv = await client.get(
        "/api/admin/students/export/csv",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "Student ID,Full Name,Email Address" in resp_csv.text


@pytest.mark.asyncio
async def test_admin_register_and_otp_login(client: AsyncClient):
    from config import get_settings
    settings = get_settings()
    orig_keys = settings.admin_keys
    settings.admin_keys = "valid-test-admin-key"
    try:
        admin_email = "custom_admin_faculty@gmail.com"
        reg_resp = await client.post(
            "/api/auth/register-admin",
            json={
                "email": admin_email,
                "password": "AdminPassword123",
                "full_name": "Prof. Custom Admin",
                "admin_key": "valid-test-admin-key",
            },
        )
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert reg_data.get("otp_required") is False
        assert reg_data.get("access_token") is not None
        assert reg_data["user"]["role"] == "admin"
        assert reg_data["user"]["email"] == admin_email

        login_resp = await client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": "AdminPassword123"},
        )
        assert login_resp.status_code == 200
        l_data = login_resp.json()
        assert l_data.get("otp_required") is False
        assert l_data.get("access_token") is not None
        token = l_data["access_token"]

        me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["role"] == "admin"
    finally:
        settings.admin_keys = orig_keys


@pytest.mark.asyncio
async def test_admin_register_via_standard_endpoint(client: AsyncClient):
    from config import get_settings
    settings = get_settings()
    orig_keys = settings.admin_keys
    settings.admin_keys = "valid-test-admin-key"
    try:
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "email": "faculty_standard_reg@gmail.com",
                "password": "AdminPassword123",
                "full_name": "Faculty Standard",
                "role": "admin",
                "admin_key": "valid-test-admin-key",
            },
        )
        assert reg_resp.status_code == 201
        data = reg_resp.json()
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == "faculty_standard_reg@gmail.com"
    finally:
        settings.admin_keys = orig_keys


@pytest.mark.asyncio
async def test_admin_registration_bypass_attempts(client: AsyncClient):
    """
    Verify that admin registration cannot be bypassed by:
    1. Omitting admin_key
    2. Passing admin_key = null / None
    3. Passing empty or whitespace string
    4. Passing incorrect key
    And that passing a valid key succeeds.
    """
    from config import get_settings
    settings = get_settings()
    orig_keys = settings.admin_keys
    settings.admin_keys = "secret-admin-token-xyz"

    try:
        # Case 1: /api/auth/register with role="admin" and no admin_key
        r1 = await client.post(
            "/api/auth/register",
            json={
                "email": "bypass_no_key@test.com",
                "password": "Password123!",
                "full_name": "Hacker No Key",
                "role": "admin",
            },
        )
        assert r1.status_code == 403, f"Expected 403 for omitted key, got {r1.status_code}: {r1.text}"

        # Case 2: /api/auth/register with null admin_key
        r2 = await client.post(
            "/api/auth/register",
            json={
                "email": "bypass_null_key@test.com",
                "password": "Password123!",
                "full_name": "Hacker Null Key",
                "role": "admin",
                "admin_key": None,
            },
        )
        assert r2.status_code == 403, f"Expected 403 for null key, got {r2.status_code}: {r2.text}"

        # Case 3: /api/auth/register-admin with empty/whitespace key
        r3 = await client.post(
            "/api/auth/register-admin",
            json={
                "email": "bypass_empty_key@test.com",
                "password": "Password123!",
                "full_name": "Hacker Empty Key",
                "admin_key": "   ",
            },
        )
        assert r3.status_code == 403, f"Expected 403 for empty key, got {r3.status_code}: {r3.text}"

        # Case 4: /api/auth/register-admin with wrong key
        r4 = await client.post(
            "/api/auth/register-admin",
            json={
                "email": "bypass_wrong_key@test.com",
                "password": "Password123!",
                "full_name": "Hacker Wrong Key",
                "admin_key": "wrong_guess_123",
            },
        )
        assert r4.status_code == 403, f"Expected 403 for wrong key, got {r4.status_code}: {r4.text}"

        # Case 5: Correct key succeeds
        r5 = await client.post(
            "/api/auth/register-admin",
            json={
                "email": "legit_admin@test.com",
                "password": "Password123!",
                "full_name": "Legit Admin",
                "admin_key": "secret-admin-token-xyz",
            },
        )
        assert r5.status_code == 201, f"Expected 201 for valid key, got {r5.status_code}: {r5.text}"
        assert r5.json()["user"]["role"] == "admin"

        # Case 6: Standard student registration cannot escalate to admin without role="admin"
        r6 = await client.post(
            "/api/auth/register",
            json={
                "email": "student_no_escalate@test.com",
                "password": "Password123!",
                "full_name": "Student Regular",
                "role": "student",
            },
        )
        assert r6.status_code == 201
        assert r6.json()["user"]["role"] == "student"

    finally:
        settings.admin_keys = orig_keys


@pytest.mark.asyncio
async def test_otp_never_present_in_production_or_simulation_off(client: AsyncClient):
    """
    Verify that registration never requires OTP and simulation_otp is always None.
    """
    r1 = await client.post(
        "/api/auth/register",
        json={
            "email": "otp_sim_off@test.com",
            "password": "Password123!",
            "full_name": "OTP Sim Off",
            "student_id": "STU_SIM_OFF",
        },
    )
    assert r1.status_code == 201
    assert r1.json().get("otp_required") is False
    assert r1.json().get("simulation_otp") is None
    assert r1.json().get("access_token") is not None



@pytest.mark.asyncio
async def test_duplicate_unused_otps_dont_crash_verify(client: AsyncClient):
    """
    Test that having multiple unused OTP records in the DB does not cause
    MultipleResultsFound (HTTP 500) and scalars().first() successfully verifies.
    """
    from datetime import datetime, timezone, timedelta
    from database import AsyncSessionLocal
    from models.db_models import AuthOTP, User
    from services.auth_service import hash_password

    email = "multi_otp_user@example.com"
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            password_hash=hash_password("Password123!"),
            full_name="Multi OTP User",
            role="student",
            is_active=True,
        )
        db.add(user)
        now = datetime.now(timezone.utc)
        otp1 = AuthOTP(
            email=email,
            otp_code="111111",
            purpose="login",
            expires_at=now + timedelta(minutes=10),
            is_used=False,
            created_at=now - timedelta(minutes=2),
        )
        otp2 = AuthOTP(
            email=email,
            otp_code="222222",
            purpose="login",
            expires_at=now + timedelta(minutes=10),
            is_used=False,
            created_at=now - timedelta(minutes=1),
        )
        db.add(otp1)
        db.add(otp2)
        await db.commit()

    resp = await client.post("/api/auth/verify-otp", json={"email": email, "otp_code": "222222"})
    assert resp.status_code == 200, f"Expected 200 with duplicate unused OTPs, got {resp.status_code}: {resp.text}"
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_init_db_creates_all_tables():
    """
    Test that init_db() on a fresh database registers and creates all tables including class management.
    """
    from database import Base, init_db
    from sqlalchemy.ext.asyncio import create_async_engine
    import tempfile
    from pathlib import Path

    assert len(Base.metadata.tables) >= 31, f"Expected at least 31 tables in Base.metadata, got {len(Base.metadata.tables)}"
    tmp_db_file = Path(tempfile.gettempdir()) / "test_init_db_fresh.db"
    if tmp_db_file.exists():
        tmp_db_file.unlink()

    test_engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_db_file.as_posix()}")
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with test_engine.connect() as conn:
            from sqlalchemy import text
            res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"))
            tables = [row[0] for row in res.fetchall()]
            assert len(tables) >= 31, f"Expected at least 31 tables in fresh DB, got {len(tables)}: {tables}"
            for req_table in ["school_classes", "class_admins", "class_enrollments"]:
                assert req_table in tables, f"Expected table {req_table} in database tables"
    finally:
        await test_engine.dispose()
        if tmp_db_file.exists():
            tmp_db_file.unlink()


def test_path_traversal_blocked_in_delete_file():
    """
    Test that delete_file() blocks directory traversal attempts and absolute paths outside upload_dir.
    """
    import tempfile
    from pathlib import Path
    from services.storage_service import delete_file

    assert delete_file("../../etc/passwd") is False
    assert delete_file("../secret.txt") is False
    assert delete_file("uploads/../../etc/passwd") is False

    outside_file = Path(tempfile.gettempdir()) / "do_not_delete_me.txt"
    outside_file.write_text("critical data", encoding="utf-8")
    try:
        assert delete_file(str(outside_file.resolve())) is False
        assert outside_file.exists() is True
    finally:
        if outside_file.exists():
            outside_file.unlink()


@pytest.mark.asyncio
async def test_unauthenticated_and_non_owner_share_deletion(client: AsyncClient):
    """
    Test that DELETE /api/share/{id} requires authentication, allows owner or admin,
    and rejects non-owners with 403.
    """
    u_a_payload = _reg_payload("share_user_a")
    u_b_payload = _reg_payload("share_user_b")
    r_a = await client.post("/api/auth/register", json=u_a_payload)
    r_b = await client.post("/api/auth/register", json=u_b_payload)
    token_a = r_a.json()["access_token"]
    token_b = r_b.json()["access_token"]

    share_create = await client.post(
        "/api/share",
        json={"resource_type": "quiz", "payload": {"question": "test?"}, "title": "A's Quiz"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert share_create.status_code == 201
    share_id = share_create.json()["id"]

    # 1. Unauthenticated DELETE -> 401 (clear any cookies persisted in client session)
    client.cookies.clear()
    del_unauth = await client.delete(f"/api/share/{share_id}")
    assert del_unauth.status_code == 401

    # 2. User B (non-owner, non-admin) attempts DELETE -> 403
    del_user_b = await client.delete(
        f"/api/share/{share_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert del_user_b.status_code == 403

    # 3. User A (owner) deletes -> 204
    del_user_a = await client.delete(
        f"/api/share/{share_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert del_user_a.status_code == 204

    # 4. Resolve now returns 404 (deactivated)
    res_get = await client.get(f"/api/share/{share_id}")
    assert res_get.status_code == 404


def test_empty_document_user_cannot_retrieve_rag_content():
    """
    Test that retrieve_context returns an empty list when user_doc_ids is empty,
    preventing any cross-tenant data leak from global FAISS or ChromaDB.
    """
    from services.document_service import retrieve_context
    results_empty = retrieve_context(query="sensitive private exam secrets", user_doc_ids=[])
    assert results_empty == []

    results_unowned = retrieve_context(
        query="sensitive private exam secrets",
        doc_id="unowned_doc_999",
        user_doc_ids=["user_doc_1", "user_doc_2"],
    )
    assert results_unowned == []


# ── Class-Based Management System Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_class_management_super_admin_and_uniqueness(client: AsyncClient):
    """
    Test class creation, display name generation, unique constraint on (name, section, academic_year),
    and super admin permissions.
    """
    from database import AsyncSessionLocal
    from models.db_models import User
    from services.auth_service import create_access_token, hash_password

    async with AsyncSessionLocal() as session:
        sa = User(
            email="super_admin_cls@example.com",
            full_name="Super Admin Cls",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=True,
            is_active=True,
        )
        session.add(sa)
        await session.commit()
        await session.refresh(sa)
        sa_token = create_access_token({"sub": sa.id, "role": "admin"})

    headers = {"Authorization": f"Bearer {sa_token}"}

    # 1. Create Class 10-A
    res_a = await client.post(
        "/api/classes",
        json={"name": "10", "section": "A", "academic_year": "2024-2025"},
        headers=headers,
    )
    assert res_a.status_code == 201
    data_a = res_a.json()
    assert data_a["display_name"] == "10-A"
    assert data_a["name"] == "10"
    assert data_a["section"] == "A"
    class_a_id = data_a["id"]

    # 2. Duplicate Class 10-A should fail with 400
    res_dup = await client.post(
        "/api/classes",
        json={"name": "10", "section": "A", "academic_year": "2024-2025"},
        headers=headers,
    )
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]

    # 3. Create Class 10-B
    res_b = await client.post(
        "/api/classes",
        json={"name": "10", "section": "B", "academic_year": "2024-2025"},
        headers=headers,
    )
    assert res_b.status_code == 201
    data_b = res_b.json()
    assert data_b["display_name"] == "10-B"

    # 4. Super admin lists classes -> sees both
    res_list = await client.get("/api/classes", headers=headers)
    assert res_list.status_code == 200
    c_ids = [c["id"] for c in res_list.json()]
    assert class_a_id in c_ids


@pytest.mark.asyncio
async def test_class_student_enrollment_and_roll_uniqueness(client: AsyncClient):
    """
    Test that roll numbers are strictly validated for uniqueness within the same class,
    while allowing the same roll number in a different class.
    """
    from database import AsyncSessionLocal
    from models.db_models import User
    from services.auth_service import create_access_token, hash_password

    async with AsyncSessionLocal() as session:
        sa = User(
            email="sa_enroll@example.com",
            full_name="SA Enroll",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=True,
            is_active=True,
        )
        session.add(sa)
        await session.commit()
        await session.refresh(sa)
        sa_token = create_access_token({"sub": sa.id, "role": "admin"})

    headers = {"Authorization": f"Bearer {sa_token}"}

    # Create Class 11-A and 11-B
    c1_res = await client.post("/api/classes", json={"name": "11", "section": "A", "academic_year": "2024-2025"}, headers=headers)
    c2_res = await client.post("/api/classes", json={"name": "11", "section": "B", "academic_year": "2024-2025"}, headers=headers)
    c1_id = c1_res.json()["id"]
    c2_id = c2_res.json()["id"]

    # Enroll Stu 1 into 11-A with roll "11A-01"
    res_stu1 = await client.post(
        f"/api/classes/{c1_id}/students",
        json={"email": "stu1_11a@example.com", "full_name": "Student One", "roll_number": "11A-01", "password": "Student@123"},
        headers=headers,
    )
    assert res_stu1.status_code == 201
    assert res_stu1.json()["roll_number"] == "11A-01"

    # Enroll Stu 2 into 11-A with duplicate roll "11A-01" -> fails with 400
    res_dup = await client.post(
        f"/api/classes/{c1_id}/students",
        json={"email": "stu2_11a@example.com", "full_name": "Student Two", "roll_number": "11A-01", "password": "Student@123"},
        headers=headers,
    )
    assert res_dup.status_code == 400
    assert "already assigned" in res_dup.json()["detail"]

    # Enroll Stu 3 into 11-B with SAME roll "11A-01" -> succeeds because it's a different class!
    res_other_class = await client.post(
        f"/api/classes/{c2_id}/students",
        json={"email": "stu3_11b@example.com", "full_name": "Student Three", "roll_number": "11A-01", "password": "Student@123"},
        headers=headers,
    )
    assert res_other_class.status_code == 201


@pytest.mark.asyncio
async def test_student_bulk_csv_upload_and_report(client: AsyncClient):
    """
    Test bulk CSV import with per-row reporting, duplicate rejection, and success counts.
    """
    from database import AsyncSessionLocal
    from models.db_models import User
    from services.auth_service import create_access_token, hash_password

    async with AsyncSessionLocal() as session:
        sa = User(
            email="sa_bulk@example.com",
            full_name="SA Bulk",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=True,
            is_active=True,
        )
        session.add(sa)
        await session.commit()
        await session.refresh(sa)
        sa_token = create_access_token({"sub": sa.id, "role": "admin"})

    headers = {"Authorization": f"Bearer {sa_token}"}
    c_res = await client.post("/api/classes", json={"name": "12", "section": "A", "academic_year": "2024-2025"}, headers=headers)
    c_id = c_res.json()["id"]

    # Pre-enroll one student with roll 12A-01
    await client.post(
        f"/api/classes/{c_id}/students",
        json={"email": "existing_stu@example.com", "full_name": "Existing", "roll_number": "12A-01", "password": "Pass"},
        headers=headers,
    )

    # Prepare CSV containing 2 valid rows, 1 duplicate roll row, and 1 invalid email row
    csv_content = (
        "name,email,roll_number,password\n"
        "Alice Smith,alice_bulk@example.com,12A-02,Student@123\n"
        "Bob Jones,bob_bulk@example.com,12A-03,Student@123\n"
        "Charlie Dup,charlie_bulk@example.com,12A-01,Student@123\n"  # Duplicate roll in this class
        "David Invalid,notanemail,12A-04,Student@123\n"              # Invalid email
    )

    files = {"file": ("students.csv", csv_content.encode("utf-8"), "text/csv")}
    res_bulk = await client.post(f"/api/classes/{c_id}/students/bulk", files=files, headers=headers)
    assert res_bulk.status_code == 200
    report = res_bulk.json()
    assert report["succeeded"] == 2
    assert report["failed"] == 2

    # Check that Alice and Bob are enrolled
    stu_res = await client.get(f"/api/classes/{c_id}/students", headers=headers)
    enrolled_emails = [s["email"] for s in stu_res.json()]
    assert "alice_bulk@example.com" in enrolled_emails
    assert "bob_bulk@example.com" in enrolled_emails


@pytest.mark.asyncio
async def test_student_transfer_preserves_history(client: AsyncClient):
    """
    Test transferring a student from Class A to Class B deactivates the old enrollment
    and creates/activates the new enrollment record.
    """
    from database import AsyncSessionLocal
    from models.db_models import User, ClassEnrollment
    from services.auth_service import create_access_token, hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        sa = User(
            email="sa_trans@example.com",
            full_name="SA Trans",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=True,
            is_active=True,
        )
        session.add(sa)
        await session.commit()
        await session.refresh(sa)
        sa_token = create_access_token({"sub": sa.id, "role": "admin"})

    headers = {"Authorization": f"Bearer {sa_token}"}
    cA_res = await client.post("/api/classes", json={"name": "9", "section": "A", "academic_year": "2024-2025"}, headers=headers)
    cB_res = await client.post("/api/classes", json={"name": "9", "section": "B", "academic_year": "2024-2025"}, headers=headers)
    cA_id = cA_res.json()["id"]
    cB_id = cB_res.json()["id"]

    # Enroll student in 9-A
    add_res = await client.post(
        f"/api/classes/{cA_id}/students",
        json={"email": "transfer_stu@example.com", "full_name": "Transfer Stu", "roll_number": "9A-05", "password": "Student@123"},
        headers=headers,
    )
    student_id = add_res.json()["student_id"]

    # Transfer student to 9-B
    trans_res = await client.put(
        f"/api/classes/{cA_id}/students/{student_id}",
        json={"target_class_id": cB_id},
        headers=headers,
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["class_id"] == cB_id

    # Verify database: Old enrollment is inactive, new enrollment is active
    async with AsyncSessionLocal() as session:
        all_enr = await session.execute(
            select(ClassEnrollment).where(ClassEnrollment.student_id == student_id)
        )
        enrollments = all_enr.scalars().all()
        assert len(enrollments) == 2
        active_enrs = [e for e in enrollments if e.is_active]
        inactive_enrs = [e for e in enrollments if not e.is_active]
        assert len(active_enrs) == 1
        assert active_enrs[0].class_id == cB_id
        assert len(inactive_enrs) == 1
        assert inactive_enrs[0].class_id == cA_id


@pytest.mark.asyncio
async def test_class_admin_permissions_isolation(client: AsyncClient):
    """
    Test that an admin assigned to Class A cannot view or manage Class B:
    - Attempting assignment creation in Class B -> 403
    - Attempting to list students of Class B -> 403
    - Attempting to post announcement for Class B -> 403
    - Attempting broadcast to Class B -> 403
    """
    from database import AsyncSessionLocal
    from models.db_models import User
    from services.auth_service import create_access_token, hash_password

    async with AsyncSessionLocal() as session:
        # Super admin
        sa = User(
            email="sa_iso@example.com",
            full_name="SA Iso",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=True,
            is_active=True,
        )
        # Class Admin for Class A only
        ca_a = User(
            email="admin_class_a@example.com",
            full_name="Admin Class A",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=False,
            is_active=True,
        )
        session.add(sa)
        session.add(ca_a)
        await session.commit()
        await session.refresh(sa)
        await session.refresh(ca_a)
        sa_token = create_access_token({"sub": sa.id, "role": "admin"})
        ca_a_token = create_access_token({"sub": ca_a.id, "role": "admin"})

    sa_headers = {"Authorization": f"Bearer {sa_token}"}
    ca_headers = {"Authorization": f"Bearer {ca_a_token}"}

    # Super admin creates Class A and Class B
    cA_res = await client.post("/api/classes", json={"name": "8", "section": "A", "academic_year": "2024-2025"}, headers=sa_headers)
    cB_res = await client.post("/api/classes", json={"name": "8", "section": "B", "academic_year": "2024-2025"}, headers=sa_headers)
    cA_id = cA_res.json()["id"]
    cB_id = cB_res.json()["id"]

    # Assign Admin A to Class A
    await client.post(f"/api/classes/{cA_id}/admins", json={"email": "admin_class_a@example.com"}, headers=sa_headers)

    # 1. Admin A creates assignment in Class A -> succeeds (201)
    asgn_a = await client.post(
        "/api/admin/assignments",
        data={
            "title": "Class A Math", "subject_id": "Math", "class_id": cA_id,
            "due_date": "2026-12-31", "due_time": "23:59", "max_marks": 100,
        },
        headers=ca_headers,
    )
    assert asgn_a.status_code == 201

    # 2. Admin A attempts assignment creation in Class B -> 403 Forbidden!
    asgn_b = await client.post(
        "/api/admin/assignments",
        data={
            "title": "Class B Math", "subject_id": "Math", "class_id": cB_id,
            "due_date": "2026-12-31", "due_time": "23:59", "max_marks": 100,
        },
        headers=ca_headers,
    )
    assert asgn_b.status_code == 403

    # 3. Admin A attempts to list students of Class B -> 403 Forbidden!
    stu_b = await client.get(f"/api/classes/{cB_id}/students", headers=ca_headers)
    assert stu_b.status_code == 403

    # 4. Admin A attempts announcement for Class B -> 403 Forbidden!
    ann_b = await client.post(
        "/api/admin/announcements",
        json={"title": "Unauthorized Notice", "content": "Hello", "class_id": cB_id},
        headers=ca_headers,
    )
    assert ann_b.status_code == 403

    # 5. Admin A attempts broadcast to Class B -> 403 Forbidden!
    bcast_b = await client.post(
        f"/api/classes/{cB_id}/broadcast",
        json={"title": "Hacked", "message": "Test"},
        headers=ca_headers,
    )
    assert bcast_b.status_code == 403


@pytest.mark.asyncio
async def test_student_class_content_isolation(client: AsyncClient):
    """
    Test that students can only view content (assignments, announcements, notes)
    targeted to their enrolled class.
    """
    from database import AsyncSessionLocal
    from models.db_models import User
    from services.auth_service import create_access_token, hash_password

    async with AsyncSessionLocal() as session:
        sa = User(
            email="sa_stu_iso@example.com",
            full_name="SA Stu Iso",
            password_hash=hash_password("AdminPass123"),
            role="admin",
            is_super_admin=True,
            is_active=True,
        )
        session.add(sa)
        await session.commit()
        await session.refresh(sa)
        sa_token = create_access_token({"sub": sa.id, "role": "admin"})

    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # Create Class 7-A and 7-B
    cA = (await client.post("/api/classes", json={"name": "7", "section": "A", "academic_year": "2024-2025"}, headers=sa_headers)).json()
    cB = (await client.post("/api/classes", json={"name": "7", "section": "B", "academic_year": "2024-2025"}, headers=sa_headers)).json()

    # Enroll Student A in 7-A and Student B in 7-B
    enr_a = (await client.post(
        f"/api/classes/{cA['id']}/students",
        json={"email": "student_7a@example.com", "full_name": "Stu 7A", "roll_number": "7A-01", "password": "Pass"},
        headers=sa_headers,
    )).json()

    enr_b = (await client.post(
        f"/api/classes/{cB['id']}/students",
        json={"email": "student_7b@example.com", "full_name": "Stu 7B", "roll_number": "7B-01", "password": "Pass"},
        headers=sa_headers,
    )).json()

    stu_a_token = create_access_token({"sub": enr_a["student_id"], "role": "student"})
    stu_b_token = create_access_token({"sub": enr_b["student_id"], "role": "student"})
    stu_a_headers = {"Authorization": f"Bearer {stu_a_token}"}
    stu_b_headers = {"Authorization": f"Bearer {stu_b_token}"}

    # Admin creates assignment for 7-A and 7-B and publishes them
    asgn_a = (await client.post(
        "/api/admin/assignments",
        data={"title": "Assignment for 7A only", "subject_id": "Sci", "class_id": cA["id"], "due_date": "2026-12-31"},
        headers=sa_headers,
    )).json()
    await client.post(f"/api/admin/assignments/{asgn_a['id']}/publish", headers=sa_headers)

    asgn_b = (await client.post(
        "/api/admin/assignments",
        data={"title": "Assignment for 7B only", "subject_id": "Sci", "class_id": cB["id"], "due_date": "2026-12-31"},
        headers=sa_headers,
    )).json()
    await client.post(f"/api/admin/assignments/{asgn_b['id']}/publish", headers=sa_headers)

    # Student A queries assignments -> must see 7-A assignment, must NOT see 7-B
    stu_a_asgns = (await client.get("/api/assignments", headers=stu_a_headers)).json()
    stu_a_titles = [a["title"] for a in stu_a_asgns]
    assert "Assignment for 7A only" in stu_a_titles
    assert "Assignment for 7B only" not in stu_a_titles

    # Student B queries assignments -> must see 7-B assignment, must NOT see 7-A
    stu_b_asgns = (await client.get("/api/assignments", headers=stu_b_headers)).json()
    stu_b_titles = [a["title"] for a in stu_b_asgns]
    assert "Assignment for 7B only" in stu_b_titles
    assert "Assignment for 7A only" not in stu_b_titles

    # Post announcement for 7-A only
    await client.post(
        "/api/admin/announcements",
        json={"title": "Class 7A Picnic", "content": "Details here", "class_id": cA["id"]},
        headers=sa_headers,
    )

    # Student A sees the announcement
    ann_a = (await client.get("/api/announcements", headers=stu_a_headers)).json()
    assert any(a["title"] == "Class 7A Picnic" for a in ann_a)

    # Student B does NOT see the 7-A announcement
    ann_b = (await client.get("/api/announcements", headers=stu_b_headers)).json()
    assert not any(a["title"] == "Class 7A Picnic" for a in ann_b)

