"""Comprehensive end-to-end tests for resume replacement lifecycle, anti-cache headers,
same-filename replacement, format transitions, and single-active-resume enforcement.
"""
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.resume import Resume
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
async def setup_test_env():
    temp_dir = tempfile.mkdtemp()
    orig_upload_dir = settings.RESUME_UPLOAD_DIR
    settings.RESUME_UPLOAD_DIR = Path(temp_dir)
    yield
    settings.RESUME_UPLOAD_DIR = orig_upload_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


async def create_test_user(email: str = "replacer@example.com") -> tuple[User, str]:
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name="Test User",
            onboarding_completed=True,
            onboarding_step=4,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return user, token


@pytest.mark.anyio
async def test_resume_replacement_and_single_active_resume():
    """Verify that uploading Resume B cleanly replaces Resume A, updates metadata,
    serves fresh file bytes, returns anti-cache headers, and keeps exactly 1 DB row."""
    user, token = await create_test_user("lifecycle@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Step 1: Upload Resume A (PDF)
        pdf_bytes_a = b"%PDF-1.4\n1 0 obj\n<< /Title (Resume A) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        res_a = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume_a.pdf", pdf_bytes_a, "application/pdf")},
            headers=headers,
        )
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["file_name"] == "resume_a.pdf"

        # Verify current metadata & file
        curr_a = await client.get("/api/v1/resumes/current", headers=headers)
        assert curr_a.status_code == 200
        assert curr_a.json()["file_name"] == "resume_a.pdf"
        assert "no-store" in curr_a.headers.get("Cache-Control", "")

        file_a = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert file_a.status_code == 200
        assert file_a.content == pdf_bytes_a
        assert "no-store" in file_a.headers.get("Cache-Control", "")
        assert file_a.headers.get("Pragma") == "no-cache"

        # Step 2: Replace with Resume B (DOCX)
        docx_bytes_b = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"Content B" * 10
        res_b = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume_b.docx", docx_bytes_b, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["file_name"] == "resume_b.docx"

        # Verify current metadata & file now returns Resume B immediately
        curr_b = await client.get("/api/v1/resumes/current", headers=headers)
        assert curr_b.status_code == 200
        assert curr_b.json()["file_name"] == "resume_b.docx"

        file_b = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert file_b.status_code == 200
        assert file_b.content == docx_bytes_b
        assert file_b.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert "no-store" in file_b.headers.get("Cache-Control", "")

        # Verify DB has strictly ONE resume record for this user
        async with TestingSessionLocal() as session:
            stmt = select(Resume).where(Resume.user_id == user.id)
            result = await session.execute(stmt)
            resumes = result.scalars().all()
            assert len(resumes) == 1
            assert resumes[0].file_name == "resume_b.docx"


@pytest.mark.anyio
async def test_same_filename_replacement():
    """Verify that replacing a resume with a new file of the SAME filename
    serves the new file content immediately without any caching or collision issues."""
    user, token = await create_test_user("same_name@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Upload 1: resume.pdf version 1
        v1_bytes = b"%PDF-1.4\nVERSION 1 CONTENT\n%%EOF"
        res1 = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.pdf", v1_bytes, "application/pdf")},
            headers=headers,
        )
        assert res1.status_code == 200

        file1 = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert file1.content == v1_bytes

        # Upload 2: resume.pdf version 2 (same filename, distinct bytes)
        v2_bytes = b"%PDF-1.4\nVERSION 2 NEW CONTENT UPDATED\n%%EOF"
        res2 = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.pdf", v2_bytes, "application/pdf")},
            headers=headers,
        )
        assert res2.status_code == 200

        file2 = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert file2.content == v2_bytes
        assert file2.content != v1_bytes


@pytest.mark.anyio
async def test_format_transitions_pdf_to_docx_and_docx_to_pdf():
    """Verify transitions: PDF -> DOCX -> PDF."""
    user, token = await create_test_user("transitions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Phase 1: PDF
        pdf_bytes = b"%PDF-1.4\nOriginal PDF\n%%EOF"
        await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("first.pdf", pdf_bytes, "application/pdf")},
            headers=headers,
        )
        f1 = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert f1.headers["content-type"] == "application/pdf"
        assert "inline" in f1.headers.get("content-disposition", "")

        # Phase 2: DOCX
        docx_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"Word DOCX" * 10
        await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("second.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        f2 = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert f2.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert "attachment" in f2.headers.get("content-disposition", "")

        # Phase 3: Back to PDF
        new_pdf_bytes = b"%PDF-1.4\nThird PDF replacement\n%%EOF"
        await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("third.pdf", new_pdf_bytes, "application/pdf")},
            headers=headers,
        )
        f3 = await client.get("/api/v1/resumes/current/file", headers=headers)
        assert f3.headers["content-type"] == "application/pdf"
        assert f3.content == new_pdf_bytes
        assert "inline" in f3.headers.get("content-disposition", "")


@pytest.mark.anyio
async def test_user_isolation_during_replacement():
    """Verify that User 1 replacing resume has no effect on User 2's current resume."""
    u1, token1 = await create_test_user("user1@example.com")
    u2, token2 = await create_test_user("user2@example.com")

    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Both upload initial files
        u1_bytes = b"%PDF-1.4\nUser 1 Initial\n%%EOF"
        u2_bytes = b"%PDF-1.4\nUser 2 Initial\n%%EOF"

        await client.post("/api/v1/resumes/upload", files={"file": ("u1.pdf", u1_bytes, "application/pdf")}, headers=h1)
        await client.post("/api/v1/resumes/upload", files={"file": ("u2.pdf", u2_bytes, "application/pdf")}, headers=h2)

        # User 1 replaces their resume with a DOCX
        u1_new_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"User 1 New Docx" * 5
        await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("u1_new.docx", u1_new_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=h1,
        )

        # User 1 gets new file
        res1 = await client.get("/api/v1/resumes/current/file", headers=h1)
        assert res1.content == u1_new_bytes

        # User 2 still gets their original file untouched
        res2 = await client.get("/api/v1/resumes/current/file", headers=h2)
        assert res2.content == u2_bytes
        assert res2.headers["content-type"] == "application/pdf"
