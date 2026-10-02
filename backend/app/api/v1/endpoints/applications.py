"""Job Applications CRUD endpoints for Aptly Kanban Tracker."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Annotated, Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.db.session import get_db
from app.models.application import ApplicationStatus, JobApplication, TrackingState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])

ALLOWED_STATUSES = {
    ApplicationStatus.APPLIED.value,
    ApplicationStatus.OA.value,
    ApplicationStatus.INTERVIEW.value,
    ApplicationStatus.OFFER.value,
    ApplicationStatus.REJECTED.value,
}


def _normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalize application URL for duplicate checks."""
    if not url:
        return None
    clean = url.strip().rstrip("/")
    return clean.lower()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ApplicationStartPayload(BaseModel):
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    role: str = Field(..., min_length=1, max_length=255, description="Job title / role")
    location: Optional[str] = Field(None, max_length=255)
    deadline: Optional[datetime] = None
    compensation: Optional[str] = Field(None, max_length=100)
    job_description: Optional[str] = None
    application_url: Optional[str] = Field(None, max_length=1024)
    source: Optional[str] = Field("Job Matching", max_length=255)
    source_job_id: Optional[str] = None


class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    role: str = Field(..., min_length=1, max_length=255, description="Job title / role")
    location: Optional[str] = Field(None, max_length=255)
    deadline: Optional[datetime] = None
    stipend: Optional[str] = Field(None, max_length=100)
    status: str = Field(default=ApplicationStatus.APPLIED.value)
    application_url: Optional[str] = Field(None, max_length=1024)
    job_description: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = Field(None, max_length=255)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}")
        return clean

    @field_validator("company", "role")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty or whitespace only")
        return clean


class ApplicationUpdate(BaseModel):
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = None
    deadline: Optional[datetime] = None
    stipend: Optional[str] = None
    status: Optional[str] = None
    application_url: Optional[str] = None
    job_description: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip().lower()
        if clean not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}")
        return clean

    @field_validator("company", "role")
    @classmethod
    def validate_non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty or whitespace only")
        return clean


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    company: str
    role: str
    location: Optional[str] = None
    deadline: Optional[datetime] = None
    stipend: Optional[str] = None
    status: str
    application_url: Optional[str] = None
    job_description: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    source_job_id: Optional[str] = None
    tracking_state: str = TrackingState.APPLIED.value
    application_started_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[ApplicationResponse])
async def list_applications(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = Query(None, description="Filter by status (applied, oa, interview, offer, rejected)"),
    search: Optional[str] = Query(None, description="Search company or role"),
    sort_by: Optional[str] = Query("updated_at", description="Sort by field: updated_at, deadline, created_at"),
    order: Optional[str] = Query("desc", description="Order direction: desc, asc"),
) -> List[ApplicationResponse]:
    """List applications for the authenticated user only (excludes unconfirmed application_started)."""
    stmt = select(JobApplication).where(
        JobApplication.user_id == current_user.id,
        JobApplication.tracking_state != TrackingState.APPLICATION_STARTED.value,
    )

    if status:
        clean_status = status.strip().lower()
        if clean_status in ALLOWED_STATUSES:
            stmt = stmt.where(JobApplication.status == clean_status)

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                JobApplication.company.ilike(search_pattern),
                JobApplication.role.ilike(search_pattern),
            )
        )

    # Sort
    if sort_by == "deadline":
        sort_col = JobApplication.deadline
    elif sort_by == "created_at":
        sort_col = JobApplication.created_at
    else:
        sort_col = JobApplication.updated_at

    if order == "asc":
        stmt = stmt.order_by(sort_col.asc().nulls_last())
    else:
        stmt = stmt.order_by(sort_col.desc().nulls_last())

    result = await db.execute(stmt)
    apps = result.scalars().all()
    return [ApplicationResponse.model_validate(app) for app in apps]


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Create a new job application for the authenticated user."""
    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=current_user.id,
        company=payload.company,
        role=payload.role,
        location=payload.location,
        deadline=payload.deadline,
        stipend=payload.stipend,
        status=payload.status,
        application_url=payload.application_url,
        job_description=payload.job_description,
        notes=payload.notes,
        source=payload.source,
        tracking_state=TrackingState.APPLIED.value,
        applied_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.post("/start", response_model=ApplicationResponse)
async def start_application_intent(
    payload: ApplicationStartPayload,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Record initial application intent before opening external application page. Avoids duplicates."""
    now = datetime.now(timezone.utc)

    # Check for existing application by same user + same source_job_id OR same normalized application_url
    match_clauses = []
    if payload.source_job_id:
        match_clauses.append(JobApplication.source_job_id == str(payload.source_job_id))
    if payload.application_url:
        clean_raw = payload.application_url.strip()
        match_clauses.append(JobApplication.application_url == clean_raw)
        match_clauses.append(JobApplication.application_url == clean_raw.rstrip("/"))

    existing = None
    if match_clauses:
        check_stmt = (
            select(JobApplication)
            .where(
                JobApplication.user_id == current_user.id,
                or_(*match_clauses),
            )
            .order_by(JobApplication.updated_at.desc())
        )
        res = await db.execute(check_stmt)
        existing = res.scalars().first()

    if existing:
        # If still in application_started, refresh the timestamp
        if existing.tracking_state == TrackingState.APPLICATION_STARTED.value:
            existing.application_started_at = now
            if payload.compensation and not existing.stipend:
                existing.stipend = payload.compensation
            if payload.deadline and not existing.deadline:
                existing.deadline = payload.deadline
            if payload.job_description and not existing.job_description:
                existing.job_description = payload.job_description
            existing.updated_at = now
            await db.commit()
            await db.refresh(existing)
        return ApplicationResponse.model_validate(existing)

    # Create new application_started record
    app = JobApplication(
        user_id=current_user.id,
        company=payload.company.strip(),
        role=payload.role.strip(),
        location=payload.location,
        deadline=payload.deadline,
        stipend=payload.compensation,
        status=ApplicationStatus.APPLIED.value,
        application_url=payload.application_url,
        job_description=payload.job_description,
        source=payload.source or "Job Matching",
        source_job_id=str(payload.source_job_id) if payload.source_job_id else None,
        tracking_state=TrackingState.APPLICATION_STARTED.value,
        application_started_at=now,
        applied_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.get("/pending", response_model=List[ApplicationResponse])
async def list_pending_applications(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[ApplicationResponse]:
    """List in-progress applications that have been started but not yet confirmed."""
    stmt = (
        select(JobApplication)
        .where(
            JobApplication.user_id == current_user.id,
            JobApplication.tracking_state == TrackingState.APPLICATION_STARTED.value,
        )
        .order_by(JobApplication.application_started_at.desc().nulls_last())
    )
    res = await db.execute(stmt)
    apps = res.scalars().all()
    return [ApplicationResponse.model_validate(app) for app in apps]


@router.post("/{id}/confirm-applied", response_model=ApplicationResponse)
async def confirm_applied(
    id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Confirm that the user completed and submitted their external application."""
    stmt = select(JobApplication).where(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    now = datetime.now(timezone.utc)
    app.tracking_state = TrackingState.APPLIED.value
    app.status = ApplicationStatus.APPLIED.value
    app.applied_at = now
    app.updated_at = now
    await db.commit()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.post("/{id}/not-yet", response_model=ApplicationResponse)
async def not_yet_applied(
    id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Record that user has not finished applying yet, keeping application in progress."""
    stmt = select(JobApplication).where(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    now = datetime.now(timezone.utc)
    app.tracking_state = TrackingState.APPLICATION_STARTED.value
    app.updated_at = now
    await db.commit()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.get("/{id}", response_model=ApplicationResponse)
async def get_application(
    id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Get single application details. 404 if not found or unauthorized."""
    stmt = select(JobApplication).where(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return ApplicationResponse.model_validate(app)


@router.patch("/{id}", response_model=ApplicationResponse)
async def patch_application(
    id: uuid.UUID,
    payload: ApplicationUpdate,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Partially update an application (e.g. status change on drag-and-drop or edit form)."""
    stmt = select(JobApplication).where(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Exclude unset fields so we only touch what was sent
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(app, field_name, value)

    app.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an application. Requires user ownership."""
    stmt = select(JobApplication).where(
        JobApplication.id == id,
        JobApplication.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    await db.delete(app)
    await db.commit()
    return None
