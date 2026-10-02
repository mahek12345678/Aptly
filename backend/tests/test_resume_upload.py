"""Tests for Onboarding Step 2: Resume Upload API endpoints."""
import io
from pathlib import Path
import shutil
import tempfile
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.resume import Resume
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
async def setup_test_env():
    """Isolate uploads directory for testing."""
    temp_dir = tempfile.mkdtemp()
    orig_upload_dir = settings.RESUME_UPLOAD_DIR
    settings.RESUME_UPLOAD_DIR = Path(temp_dir)
    yield
    settings.RESUME_UPLOAD_DIR = orig_upload_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


async def create_test_user(email: str = "applicant_step2@example.com") -> tuple[User, str]:
    """Helper to create a test user and valid JWT token."""
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name="Step2 Applicant",
            onboarding_completed=False,
            onboarding_step=2,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return user, token


@pytest.mark.anyio
async def test_upload_pdf_success():
    """Test POST /api/resumes/upload with PDF returns 200 with ResumeResponse."""
    user, token = await create_test_user("pdf_success@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4\n%Fake PDF content for resume testing\n%%EOF"
    files = {
        "file": ("My_Software_Resume.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/resumes/upload", headers=headers, files=files)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_name"] == "My_Software_Resume.pdf"
        assert data["file_size_bytes"] == len(pdf_content)
        assert data["parsed_status"] == "uploaded"
        assert "id" in data
        assert "created_at" in data

        # Check physical file on disk
        user_dir = settings.RESUME_UPLOAD_DIR / str(user.id)
        assert user_dir.exists()
        files_in_dir = list(user_dir.iterdir())
        assert len(files_in_dir) == 1
        assert files_in_dir[0].read_bytes() == pdf_content


@pytest.mark.anyio
async def test_upload_invalid_extension():
    """Test upload with invalid extension (.exe) returns 422."""
    _, token = await create_test_user("invalid_ext@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    files = {
        "file": ("malicious_script.exe", io.BytesIO(b"MZ\x90\x00..."), "application/octet-stream")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/resumes/upload", headers=headers, files=files)
        assert response.status_code == 422
        assert "Only PDF and DOCX files are allowed" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_exceeding_10mb():
    """Test upload exceeding 10 MB returns 413."""
    _, token = await create_test_user("oversized@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 10 MB + 10 bytes
    oversized_content = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 10)
    files = {
        "file": ("Huge_Resume.pdf", io.BytesIO(oversized_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/resumes/upload", headers=headers, files=files)
        assert response.status_code == 413
        assert "exceeds maximum allowed limit" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_current_resume_saved():
    """Test GET /api/resumes/current returns saved resume."""
    user, token = await create_test_user("get_current@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4\nTest Resume\n%%EOF"
    files = {
        "file": ("Jane_Doe_Resume.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        upload_resp = await ac.post("/api/resumes/upload", headers=headers, files=files)
        assert upload_resp.status_code == 200

        get_resp = await ac.get("/api/resumes/current", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["file_name"] == "Jane_Doe_Resume.pdf"
        assert data["file_size_bytes"] == len(pdf_content)
        assert data["parsed_status"] == "uploaded"


@pytest.mark.anyio
async def test_get_current_resume_not_found():
    """Test GET /api/resumes/current with no resume returns 404."""
    _, token = await create_test_user("no_resume@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/resumes/current", headers=headers)
        assert response.status_code == 404
        assert "No resume found" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_current_resume():
    """Test DELETE /api/resumes/current returns 204, file deleted."""
    user, token = await create_test_user("delete_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4\nDelete Me\n%%EOF"
    files = {
        "file": ("To_Delete.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        upload_resp = await ac.post("/api/resumes/upload", headers=headers, files=files)
        assert upload_resp.status_code == 200

        user_dir = settings.RESUME_UPLOAD_DIR / str(user.id)
        assert len(list(user_dir.iterdir())) == 1

        del_resp = await ac.delete("/api/resumes/current", headers=headers)
        assert del_resp.status_code == 204

        # File is deleted from disk
        assert len(list(user_dir.iterdir())) == 0

        # Subsequent GET returns 404
        get_resp = await ac.get("/api/resumes/current", headers=headers)
        assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_reupload_replaces_old_resume():
    """Test re-upload replaces the old resume (only one row per user)."""
    user, token = await create_test_user("replace_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First upload (PDF)
        pdf1 = b"%PDF-1.4\nVersion 1\n%%EOF"
        files1 = {"file": ("Resume_V1.pdf", io.BytesIO(pdf1), "application/pdf")}
        resp1 = await ac.post("/api/resumes/upload", headers=headers, files=files1)
        assert resp1.status_code == 200
        resume_id_1 = resp1.json()["id"]

        user_dir = settings.RESUME_UPLOAD_DIR / str(user.id)
        files_after_1 = list(user_dir.iterdir())
        assert len(files_after_1) == 1
        old_file_path = files_after_1[0]

        # Second upload (DOCX replaces PDF)
        docx2 = b"PK\x03\x04\x14\x00Version 2 Docx"
        files2 = {
            "file": (
                "Resume_V2.docx",
                io.BytesIO(docx2),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        resp2 = await ac.post("/api/resumes/upload", headers=headers, files=files2)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["id"] == resume_id_1  # Replaces existing record
        assert data2["file_name"] == "Resume_V2.docx"
        assert data2["file_size_bytes"] == len(docx2)

        # Verify old file was deleted and only new file exists on disk
        files_after_2 = list(user_dir.iterdir())
        assert len(files_after_2) == 1
        assert not old_file_path.exists()
        assert files_after_2[0].read_bytes() == docx2

        # Verify only 1 row in DB for this user
        async with TestingSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(Resume).where(Resume.user_id == user.id)
            result = await session.execute(stmt)
            resumes = result.scalars().all()
            assert len(resumes) == 1
            assert resumes[0].file_name == "Resume_V2.docx"
            assert resumes[0].file_size_bytes == len(docx2)


@pytest.mark.anyio
async def test_unauthenticated_upload():
    """Test unauthenticated upload returns 401."""
    pdf_content = b"%PDF-1.4\nUnauth Test\n%%EOF"
    files = {"file": ("unauth.pdf", io.BytesIO(pdf_content), "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp_upload = await ac.post("/api/resumes/upload", files=files)
        assert resp_upload.status_code == 401

        resp_get = await ac.get("/api/resumes/current")
        assert resp_get.status_code == 401

        resp_delete = await ac.delete("/api/resumes/current")
        assert resp_delete.status_code == 401
