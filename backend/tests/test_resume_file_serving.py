"""Tests for resume file serving endpoint: authentication, user isolation, MIME types, safe headers, and security."""
import io
import os
from pathlib import Path
import shutil
import tempfile
import uuid

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


async def create_test_user(email: str = "applicant@example.com") -> tuple[User, str]:
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name="Test User",
            onboarding_completed=False,
            onboarding_step=2,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return user, token


@pytest.mark.anyio
async def test_unauthenticated_current_file_returns_401():
    """Unauthenticated requests to /current/file and /current/download must return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp_file = await ac.get("/api/v1/resumes/current/file")
        assert resp_file.status_code == 401

        resp_dl = await ac.get("/api/v1/resumes/current/download")
        assert resp_dl.status_code == 401


@pytest.mark.anyio
async def test_no_current_resume_returns_404():
    """User with no uploaded resume receives 404 Not Found."""
    _, token = await create_test_user("noresume@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/resumes/current/file", headers=headers)
        assert resp.status_code == 404
        assert "No active resume found" in resp.json()["detail"]


@pytest.mark.anyio
async def test_pdf_returns_application_pdf_and_inline_disposition():
    """PDF resumes must return application/pdf and Content-Disposition: inline."""
    user, token = await create_test_user("pdfview@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = b"%PDF-1.4\n%Aptly resume stream test\n%%EOF"
    files = {"file": ("Candidate_Resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        upload_resp = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert upload_resp.status_code == 200

        resp = await ac.get("/api/v1/resumes/current/file", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "no-store" in resp.headers.get("cache-control", "")
        assert "inline" in resp.headers["content-disposition"].lower()
        assert "Candidate_Resume.pdf" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 0
        assert resp.content == pdf_bytes


@pytest.mark.anyio
async def test_docx_returns_correct_office_mime_and_attachment_disposition():
    """DOCX resumes must return OpenXML MIME and Content-Disposition: attachment."""
    user, token = await create_test_user("docxview@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    docx_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00DocxBinaryContent"
    files = {
        "file": (
            "Candidate_Resume.docx",
            io.BytesIO(docx_bytes),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        upload_resp = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert upload_resp.status_code == 200

        resp = await ac.get("/api/v1/resumes/current/file", headers=headers)
        assert resp.status_code == 200
        expected_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert resp.headers["content-type"] == expected_mime
        assert "no-store" in resp.headers.get("cache-control", "")
        assert "attachment" in resp.headers["content-disposition"].lower()
        assert "Candidate_Resume.docx" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"PK")
        assert len(resp.content) > 0
        assert resp.content == docx_bytes


@pytest.mark.anyio
async def test_user_gets_only_their_own_resume():
    """User isolation: User A receives only Resume A, User B receives only Resume B."""
    user_a, token_a = await create_test_user("usera@example.com")
    user_b, token_b = await create_test_user("userb@example.com")

    content_a = b"%PDF-1.4\nResume of User A\n%%EOF"
    content_b = b"%PDF-1.4\nResume of User B\n%%EOF"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Upload for A
        await ac.post(
            "/api/v1/resumes/upload",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("Resume_A.pdf", io.BytesIO(content_a), "application/pdf")},
        )
        # Upload for B
        await ac.post(
            "/api/v1/resumes/upload",
            headers={"Authorization": f"Bearer {token_b}"},
            files={"file": ("Resume_B.pdf", io.BytesIO(content_b), "application/pdf")},
        )

        # A fetches file
        resp_a = await ac.get("/api/v1/resumes/current/file", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a.status_code == 200
        assert resp_a.content == content_a

        # B fetches file
        resp_b = await ac.get("/api/v1/resumes/current/file", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200
        assert resp_b.content == content_b


@pytest.mark.anyio
async def test_missing_file_on_disk_handled_safely():
    """If DB record exists but physical file is missing, return safe 404 without leaking disk paths."""
    user, token = await create_test_user("missingfile@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    content = b"%PDF-1.4\nTemp file\n%%EOF"
    files = {"file": ("Resume_Missing.pdf", io.BytesIO(content), "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        upload_resp = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert upload_resp.status_code == 200

        # Delete physical file from disk
        user_dir = settings.RESUME_UPLOAD_DIR / str(user.id)
        for f in user_dir.iterdir():
            f.unlink()

        resp = await ac.get("/api/v1/resumes/current/file", headers=headers)
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "not found" in detail.lower()
        # Verify no filesystem paths leaked
        assert "uploads" not in detail
        assert str(settings.RESUME_UPLOAD_DIR) not in detail


@pytest.mark.anyio
async def test_path_traversal_impossible():
    """If a resume record has a path pointing outside the upload directory, return 403 Forbidden."""
    user, token = await create_test_user("hacker@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Manually insert a resume pointing outside upload root
    outside_file = Path(tempfile.gettempdir()) / "secret.txt"
    outside_file.write_text("classified data")

    try:
        async with TestingSessionLocal() as session:
            resume = Resume(
                id=uuid.uuid4(),
                user_id=user.id,
                file_name="traversal.pdf",
                file_path=str(outside_file),
                parsed_status="uploaded",
            )
            session.add(resume)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/resumes/current/file", headers=headers)
            assert resp.status_code == 403
            assert "forbidden" in resp.json()["detail"].lower()
    finally:
        if outside_file.exists():
            outside_file.unlink()


@pytest.mark.anyio
async def test_replaced_resume_serves_newest_file():
    """Replacing a resume immediately updates the file served by /current/file."""
    user, token = await create_test_user("replacer@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = b"%PDF-1.4\nOriginal Resume\n%%EOF"
    docx_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00UpdatedDocxContent"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Upload 1: PDF
        await ac.post(
            "/api/v1/resumes/upload",
            headers=headers,
            files={"file": ("Old_Resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        resp1 = await ac.get("/api/v1/resumes/current/file", headers=headers)
        assert resp1.status_code == 200
        assert resp1.headers["content-type"] == "application/pdf"
        assert resp1.content == pdf_bytes

        # Upload 2: DOCX (replacement)
        await ac.post(
            "/api/v1/resumes/upload",
            headers=headers,
            files={
                "file": (
                    "New_Resume.docx",
                    io.BytesIO(docx_bytes),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        resp2 = await ac.get("/api/v1/resumes/current/file", headers=headers)
        assert resp2.status_code == 200
        assert "wordprocessingml" in resp2.headers["content-type"]
        assert resp2.content == docx_bytes


@pytest.mark.anyio
async def test_resume_metadata_includes_mime_type():
    """GET /current and /current/parsed must include mime_type."""
    user, token = await create_test_user("metamime@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = b"%PDF-1.4\nMetadata test\n%%EOF"
    files = {"file": ("MyResume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/resumes/upload", headers=headers, files=files)

        resp_curr = await ac.get("/api/v1/resumes/current", headers=headers)
        assert resp_curr.status_code == 200
        assert resp_curr.json()["mime_type"] == "application/pdf"

        resp_parsed = await ac.get("/api/v1/resumes/current/parsed", headers=headers)
        assert resp_parsed.status_code == 200
        assert resp_parsed.json()["mime_type"] == "application/pdf"
