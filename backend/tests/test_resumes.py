import io
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
async def setup_test_env():
    # Setup test uploads dir
    temp_dir = tempfile.mkdtemp()
    orig_upload_dir = settings.RESUME_UPLOAD_DIR
    settings.RESUME_UPLOAD_DIR = Path(temp_dir)
    yield
    # Teardown temp dir
    settings.RESUME_UPLOAD_DIR = orig_upload_dir
    shutil.rmtree(temp_dir, ignore_errors=True)



async def create_test_user(email: str = "applicant@example.com") -> tuple[User, str]:
    """Helper to create a verified test user and JWT token."""
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name="Test Applicant",
            onboarding_completed=False,
            onboarding_step=2,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return user, token


@pytest.mark.anyio
async def test_upload_valid_pdf():
    user, token = await create_test_user("pdfuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4\n%Fake PDF content for resume testing\n%%EOF"
    files = {
        "file": ("John_Doe_Resume.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_name"] == "John_Doe_Resume.pdf"
        assert data["file_size"] == len(pdf_content)
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
async def test_upload_valid_docx():
    user, token = await create_test_user("docxuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    docx_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00Fake docx binary stream"
    files = {
        "file": (
            "Jane_Doe_Resume.docx",
            io.BytesIO(docx_content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["file_name"] == "Jane_Doe_Resume.docx"
        assert data["file_size"] == len(docx_content)
        assert data["parsed_status"] == "uploaded"


@pytest.mark.anyio
async def test_upload_file_size_exceeded():
    _, token = await create_test_user("largefile@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 10 MB + 1 byte
    oversized_content = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 10)
    files = {
        "file": ("Huge_Resume.pdf", io.BytesIO(oversized_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert response.status_code == 413
        assert "exceeds maximum allowed limit" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_invalid_extension():
    _, token = await create_test_user("invalidekst@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    files = {
        "file": ("script.exe", io.BytesIO(b"MZ\x90\x00..."), "application/octet-stream")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert response.status_code == 422
        assert "Only PDF and DOCX files are allowed" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_spoofed_pdf_magic_bytes():
    _, token = await create_test_user("spoofed@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Plain text file disguised as .pdf
    fake_content = b"This is plain text, not a real PDF document!"
    files = {
        "file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert response.status_code == 422
        assert "valid PDF header" in response.json()["detail"]


@pytest.mark.anyio
async def test_replace_existing_resume():
    user, token = await create_test_user("replacer@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First upload
        pdf1 = b"%PDF-1.4\nVersion 1\n%%EOF"
        files1 = {"file": ("Resume_V1.pdf", io.BytesIO(pdf1), "application/pdf")}
        resp1 = await ac.post("/api/v1/resumes/upload", headers=headers, files=files1)
        assert resp1.status_code == 200
        resume_id_1 = resp1.json()["id"]

        user_dir = settings.RESUME_UPLOAD_DIR / str(user.id)
        files_after_1 = list(user_dir.iterdir())
        assert len(files_after_1) == 1
        old_file_path = files_after_1[0]

        # Second upload (replace)
        docx2 = b"PK\x03\x04\x14\x00Version 2 Docx"
        files2 = {
            "file": (
                "Resume_V2.docx",
                io.BytesIO(docx2),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        resp2 = await ac.post("/api/v1/resumes/upload", headers=headers, files=files2)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["id"] == resume_id_1  # Replaces existing record
        assert data2["file_name"] == "Resume_V2.docx"

        # Verify old file was deleted and only new file exists
        files_after_2 = list(user_dir.iterdir())
        assert len(files_after_2) == 1
        assert not old_file_path.exists()
        assert files_after_2[0].read_bytes() == docx2


@pytest.mark.anyio
async def test_get_current_resume():
    user, token = await create_test_user("getter@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 404 before upload
        get_none = await ac.get("/api/v1/resumes/current", headers=headers)
        assert get_none.status_code == 404

        # Upload resume
        content = b"%PDF-1.4\nMy Resume Data\n%%EOF"
        files = {"file": ("My_Resume.pdf", io.BytesIO(content), "application/pdf")}
        upload_resp = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert upload_resp.status_code == 200

        # Get current
        get_resp = await ac.get("/api/v1/resumes/current", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["file_name"] == "My_Resume.pdf"
        assert data["file_size"] == len(content)
        assert data["parsed_status"] == "uploaded"


@pytest.mark.anyio
async def test_delete_current_resume():
    user, token = await create_test_user("deleter@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Upload
        content = b"%PDF-1.4\nTo be deleted\n%%EOF"
        files = {"file": ("Delete_Me.pdf", io.BytesIO(content), "application/pdf")}
        await ac.post("/api/v1/resumes/upload", headers=headers, files=files)

        user_dir = settings.RESUME_UPLOAD_DIR / str(user.id)
        assert len(list(user_dir.iterdir())) == 1

        # Delete
        del_resp = await ac.delete("/api/v1/resumes/current", headers=headers)
        assert del_resp.status_code == 204

        # File is gone from disk
        assert len(list(user_dir.iterdir())) == 0

        # Subsequent GET is 404
        get_resp = await ac.get("/api/v1/resumes/current", headers=headers)
        assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated_requests_fail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Upload
        resp_upload = await ac.post("/api/v1/resumes/upload", files={"file": ("f.pdf", b"%PDF-", "application/pdf")})
        assert resp_upload.status_code == 401

        # Get
        resp_get = await ac.get("/api/v1/resumes/current")
        assert resp_get.status_code == 401

        # Delete
        resp_delete = await ac.delete("/api/v1/resumes/current")
        assert resp_delete.status_code == 401
