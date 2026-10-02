"""Resume management endpoints for upload, retrieval, parsing, and deletion."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
from typing import Annotated, Any, Dict, Optional
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.resume import Resume
from app.services.resume_parser import extract_raw_text, resume_parser
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resumes"])

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf", "application/x-pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/x-zip-compressed",
        "application/zip",
        "application/octet-stream",
        "application/msword",
    },
}


class ResumeResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_size_bytes: Optional[int] = None
    parsed_status: str
    created_at: datetime
    file_size: Optional[int] = None
    parsed_at: Optional[datetime] = None
    parse_error: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    mime_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ParsedResumeResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    parsed_status: str
    parsed_at: Optional[datetime] = None
    parse_error: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    chunks_stored: int = 0
    extracted_text_preview: Optional[str] = None
    mime_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


async def get_current_resume_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> Optional[Resume]:
    """Retrieve the single active current resume for the user, ordered deterministically."""
    stmt = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc(), Resume.id.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeResponse:
    """Upload and store a resume file (PDF or DOCX, max 10MB) for the authenticated user.
    Safely replaces any existing onboarding resume.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is missing.",
        )

    # Sanitize and extract extension
    raw_filename = Path(file.filename).name
    ext = Path(raw_filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file extension. Only PDF and DOCX files are allowed.",
        )

    # Validate MIME type if provided
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in ALLOWED_MIME_TYPES.get(ext, set()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid MIME type '{file.content_type}' for {ext.upper()} file.",
        )

    # Read file content safely
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file is empty.",
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed limit of 10 MB.",
        )

    # Validate file magic bytes
    if ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File content does not match a valid PDF header.",
        )
    if ext == ".docx" and not content.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File content does not match a valid DOCX package format.",
        )

    # Prepare safe storage path: uploads/resumes/{user_id}/{uuid}{ext}
    safe_display_name = "".join(
        c for c in raw_filename if c.isalnum() or c in " ._-"
    )[:200].strip() or f"resume{ext}"

    user_upload_dir = Path(settings.RESUME_UPLOAD_DIR) / str(current_user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}{ext}"
    saved_file_path = user_upload_dir / unique_filename

    # Save to disk using async file I/O
    async with aiofiles.open(saved_file_path, "wb") as f_out:
        await f_out.write(content)

    # Find any existing resumes for this user, ordered deterministically
    stmt = (
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc(), Resume.id.desc())
    )
    result = await db.execute(stmt)
    existing_resumes = result.scalars().all()

    now = datetime.now(timezone.utc)

    if existing_resumes:
        existing_resume = existing_resumes[0]
        # Clean up any extra duplicate resume records if they exist
        for dup in existing_resumes[1:]:
            if dup.file_path and dup.file_path != str(saved_file_path):
                try:
                    p = Path(dup.file_path)
                    if p.exists():
                        p.unlink()
                except Exception as exc:
                    logger.warning("Could not delete duplicate resume file %s: %s", dup.file_path, exc)
            try:
                vector_store.delete_resume_vectors(resume_id=dup.id, user_id=current_user.id)
            except Exception:
                pass
            await db.delete(dup)

        # Safely remove previous physical file
        if existing_resume.file_path and existing_resume.file_path != str(saved_file_path):
            old_file = Path(existing_resume.file_path)
            try:
                if old_file.exists():
                    old_file.unlink()
            except Exception as exc:
                logger.warning("Could not delete old resume file %s: %s", old_file, exc)

        # Clear old ChromaDB vectors for this resume
        try:
            vector_store.delete_resume_vectors(resume_id=existing_resume.id, user_id=current_user.id)
        except Exception:
            pass

        existing_resume.file_name = safe_display_name
        existing_resume.file_path = str(saved_file_path)
        existing_resume.file_size_bytes = file_size
        existing_resume.parsed_status = "uploaded"
        existing_resume.extracted_text = None
        existing_resume.parsed_data = None
        existing_resume.parse_error = None
        existing_resume.parsed_at = None
        existing_resume.created_at = now
        resume = existing_resume
    else:
        resume = Resume(
            id=uuid.uuid4(),
            user_id=current_user.id,
            file_name=safe_display_name,
            file_path=str(saved_file_path),
            file_size_bytes=file_size,
            parsed_status="uploaded",
            created_at=now,
        )
        db.add(resume)

    await db.flush()
    await db.refresh(resume)

    logger.info(
        "[ResumeReplace] user_id=%s resume_id=%s filename=%s size=%s",
        current_user.id,
        resume.id,
        resume.file_name,
        file_size,
    )

    return ResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        file_size_bytes=file_size,
        file_size=file_size,
        parsed_status=resume.parsed_status,
        created_at=resume.created_at,
        parsed_at=resume.parsed_at,
        parse_error=resume.parse_error,
        parsed_data=resume.parsed_data,
        mime_type=resume.mime_type,
    )


@router.get("/current", response_model=ResumeResponse)
async def get_current_resume(
    response: Response,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeResponse:
    """Retrieve the active resume for the current user."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    resume = await get_current_resume_for_user(db, current_user.id)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found",
        )

    file_size = resume.file_size_bytes
    if file_size is None and resume.file_path and Path(resume.file_path).exists():
        file_size = Path(resume.file_path).stat().st_size

    return ResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        file_size_bytes=file_size,
        file_size=file_size,
        parsed_status=resume.parsed_status,
        created_at=resume.created_at,
        parsed_at=resume.parsed_at,
        parse_error=resume.parse_error,
        parsed_data=resume.parsed_data,
        mime_type=resume.mime_type,
    )


@router.get("/current/file")
@router.get("/current/download")
async def get_current_resume_file(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve and stream the current user's active resume file with user isolation and secure headers."""
    resume = await get_current_resume_for_user(db, current_user.id)

    if not resume or not resume.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume found.",
        )

    file_path = Path(resume.file_path).resolve()
    upload_root = Path(settings.RESUME_UPLOAD_DIR).resolve()

    # Security: Prevent directory traversal - ensure resolved file is inside upload root
    try:
        file_path.relative_to(upload_root)
    except ValueError:
        logger.error(
            "Security alert: Path traversal or unauthorized file path access attempt: user_id=%s, resume_id=%s, file_exists=%s, exception=ValueError",
            current_user.id,
            resume.id,
            file_path.is_file(),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the requested file path is forbidden.",
        )

    if not file_path.is_file():
        logger.warning(
            "Resume file missing on server: user_id=%s, resume_id=%s, file_exists=False, file_size=0, mime=%s",
            current_user.id,
            resume.id,
            resume.mime_type,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found on server.",
        )

    # Determine extension and validate MIME type safely
    ext = file_path.suffix.lower()
    if not ext and resume.file_name:
        ext = Path(resume.file_name).suffix.lower()

    # Sanitize filename for safe Content-Disposition
    raw_name = Path(resume.file_name or f"resume{ext}").name
    safe_filename = re.sub(r'[^\w\s.-]', '_', raw_name).strip() or f"resume{ext}"

    if ext == ".pdf":
        media_type = "application/pdf"
        content_disposition_type = "inline"
    elif ext == ".docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        content_disposition_type = "attachment"
    else:
        media_type = "application/octet-stream"
        content_disposition_type = "attachment"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename,
        content_disposition_type=content_disposition_type,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.post("/{resume_id}/parse", response_model=ParsedResumeResponse)
async def parse_resume(
    resume_id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ParsedResumeResponse:
    """Extract clean text, parse sections, generate vector embeddings, and store in ChromaDB."""
    # 1. Verify resume existence and user ownership
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resume.",
        )

    # 2. Set status = "parsing"
    resume.parsed_status = "parsing"
    resume.parse_error = None
    await db.flush()

    try:
        # 3. Extract text
        raw_text = extract_raw_text(resume.file_path)
        if not raw_text.strip():
            raise ValueError("The resume file does not contain readable text content.")

        # 4. Deterministic section parsing & structuring
        parsed_dict = resume_parser.parse(raw_text)

        # 5. Embeddings & ChromaDB vector storage
        chunks_stored = vector_store.store_resume_chunks(
            resume_id=resume.id,
            user_id=current_user.id,
            parsed_data=parsed_dict,
            raw_text=raw_text,
        )

        # 6. Mark status = "parsed"
        now = datetime.now(timezone.utc)
        resume.extracted_text = raw_text
        resume.parsed_data = parsed_dict
        resume.parsed_status = "parsed"
        resume.parsed_at = now
        resume.parse_error = None
        await db.flush()
        await db.refresh(resume)

        preview = (raw_text[:250] + "...") if len(raw_text) > 250 else raw_text

        return ParsedResumeResponse(
            id=resume.id,
            file_name=resume.file_name,
            parsed_status=resume.parsed_status,
            parsed_at=resume.parsed_at,
            parse_error=None,
            parsed_data=resume.parsed_data,
            chunks_stored=chunks_stored,
            extracted_text_preview=preview,
        )

    except Exception as exc:
        logger.exception("Resume parsing failed for resume_id=%s: %s", resume_id, exc)
        resume.parsed_status = "failed"
        safe_msg = str(exc) if str(exc) else "An unexpected error occurred during resume parsing."
        resume.parse_error = safe_msg[:500]
        await db.flush()
        await db.refresh(resume)

        return ParsedResumeResponse(
            id=resume.id,
            file_name=resume.file_name,
            parsed_status="failed",
            parsed_at=None,
            parse_error=resume.parse_error,
            parsed_data=None,
            chunks_stored=0,
            extracted_text_preview=None,
        )


@router.get("/current/parsed", response_model=ParsedResumeResponse)
async def get_current_parsed_resume(
    response: Response,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ParsedResumeResponse:
    """Retrieve structured parsed data and status for the current user's active resume."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    resume = await get_current_resume_for_user(db, current_user.id)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found",
        )

    preview = None
    if resume.extracted_text:
        preview = (resume.extracted_text[:250] + "...") if len(resume.extracted_text) > 250 else resume.extracted_text

    return ParsedResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        parsed_status=resume.parsed_status,
        parsed_at=resume.parsed_at,
        parse_error=resume.parse_error,
        parsed_data=resume.parsed_data,
        chunks_stored=0,
        extracted_text_preview=preview,
        mime_type=resume.mime_type,
    )


@router.delete("/current", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_resume(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Delete the active resume for the current user from disk, ChromaDB, and database."""
    resume = await get_current_resume_for_user(db, current_user.id)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found to delete",
        )

    # Safely remove physical file
    if resume.file_path:
        target_file = Path(resume.file_path)
        try:
            if target_file.exists():
                target_file.unlink()
        except Exception as exc:
            logger.warning("Could not delete resume file %s: %s", target_file, exc)

    # Clean ChromaDB vectors for this resume
    try:
        vector_store.delete_resume_vectors(resume_id=resume.id, user_id=current_user.id)
    except Exception:
        pass

    await db.delete(resume)
    await db.flush()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
