"""Job discovery and personalized matching endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Annotated, Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.db.session import get_db
from app.models.job_match import DailyMatch, JobListing
from app.services.job_matcher import job_matcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs & Matching"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class JobListingDetailResponse(BaseModel):
    id: uuid.UUID
    company: str
    role_title: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description: str
    application_url: Optional[str] = None
    deadline: Optional[datetime] = None
    compensation: Optional[str] = None
    posted_at: Optional[datetime] = None
    source: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class JobMatchResponseItem(BaseModel):
    id: uuid.UUID
    similarity_score: float
    preference_score: float
    final_score: float
    match_reasons: List[str] = []
    saved: bool
    dismissed: bool
    matched_at: datetime
    job: JobListingDetailResponse

    model_config = ConfigDict(from_attributes=True)


class JobMatchesListResponse(BaseModel):
    items: List[JobMatchResponseItem]
    total: int
    page: int
    limit: int
    last_refreshed_at: Optional[datetime] = None


class ToggleSaveResponse(BaseModel):
    id: uuid.UUID
    saved: bool


class DismissMatchResponse(BaseModel):
    id: uuid.UUID
    dismissed: bool


class RefreshMatchesResponse(BaseModel):
    task_id: Optional[str] = None
    status: str = "completed"
    refreshed_count: int = 0
    matches_count: int = 0
    refreshed_at: datetime


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    ready: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/matches", response_model=JobMatchesListResponse)
async def list_personalized_matches(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    min_score: Optional[float] = Query(None, description="Minimum match score (0-100)"),
    sort: Optional[str] = Query("score", description="Sort by 'score' or 'posted_at'"),
    saved_only: bool = Query(False, description="Filter for saved listings only"),
    employment_type: Optional[str] = Query(None, description="Filter: full_time, internship, etc."),
) -> JobMatchesListResponse:
    """Retrieve personalized job matches for the authenticated user."""
    # Check if user has any matches yet; if not, automatically perform first rank
    check_stmt = select(func.count(DailyMatch.id)).where(DailyMatch.user_id == current_user.id)
    count_res = await db.execute(check_stmt)
    existing_count = count_res.scalar_one() or 0

    if existing_count == 0:
        await job_matcher.rank_jobs_for_user(db, current_user.id)

    # Build query
    stmt = (
        select(DailyMatch)
        .options(selectinload(DailyMatch.job_listing))
        .where(DailyMatch.user_id == current_user.id)
    )

    if saved_only:
        stmt = stmt.where(DailyMatch.saved == True)  # noqa: E712
    else:
        stmt = stmt.where(DailyMatch.dismissed == False)  # noqa: E712

    if min_score is not None:
        stmt = stmt.where(DailyMatch.final_score >= min_score)

    need_job_join = bool(employment_type or sort in ("posted_at", "newest", "recently_posted"))
    if need_job_join:
        stmt = stmt.join(DailyMatch.job_listing)

    if employment_type:
        stmt = stmt.where(JobListing.employment_type == employment_type)

    # Sort strictly by final_score descending when 'score' or 'best_match'
    if sort in ("posted_at", "newest", "recently_posted"):
        stmt = stmt.order_by(JobListing.posted_at.desc().nullslast(), DailyMatch.final_score.desc())
    else:
        stmt = stmt.order_by(DailyMatch.final_score.desc(), DailyMatch.matched_at.desc())

    # Count total matching query
    count_query = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_query)
    total_records = total_res.scalar_one() or 0

    # Paginate
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    matches = result.scalars().all()

    # Get last refreshed time
    last_refreshed_at = matches[0].matched_at if matches else None

    items = []
    for m in matches:
        sim_val = m.similarity_score * 100.0 if (0.0 <= m.similarity_score <= 1.0 and m.final_score > 1.0) else m.similarity_score
        pref_val = m.preference_score * 100.0 if (0.0 <= m.preference_score <= 1.0 and m.final_score > 1.0) else m.preference_score
        fin_val = m.final_score * 100.0 if (0.0 <= m.final_score <= 1.0) else m.final_score
        items.append(
            JobMatchResponseItem(
                id=m.id,
                similarity_score=round(sim_val, 1),
                preference_score=round(pref_val, 1),
                final_score=round(fin_val, 1),
                match_reasons=m.match_reasons or [],
                saved=m.saved,
                dismissed=m.dismissed,
                matched_at=m.matched_at,
                job=JobListingDetailResponse.model_validate(m.job_listing),
            )
        )

    return JobMatchesListResponse(
        items=items,
        total=total_records,
        page=page,
        limit=limit,
        last_refreshed_at=last_refreshed_at,
    )


@router.post("/matches/refresh", response_model=RefreshMatchesResponse)
async def refresh_personalized_matches(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    sync: bool = Query(False, description="Run synchronously if True"),
) -> RefreshMatchesResponse:
    """Fetch fresh listings, embed new jobs, and re-rank matches for the authenticated user."""
    # If caller explicitly asked for synchronous execution:
    if sync:
        refreshed_count = await job_matcher.ingest_and_embed_listings(db)
        matches = await job_matcher.rank_jobs_for_user(db, current_user.id)
        return RefreshMatchesResponse(
            task_id=None,
            status="completed",
            refreshed_count=refreshed_count,
            matches_count=len(matches),
            refreshed_at=datetime.now(timezone.utc),
        )

    # Attempt to dispatch to Celery background worker
    try:
        from app.core.celery_app import celery_app
        from app.tasks.job_tasks import refresh_matches_for_user

        # If Celery is configured in eager mode (e.g. testing), run directly
        if getattr(celery_app.conf, "task_always_eager", False):
            refreshed_count = await job_matcher.ingest_and_embed_listings(db)
            matches = await job_matcher.rank_jobs_for_user(db, current_user.id)
            return RefreshMatchesResponse(
                task_id="eager-local-sync",
                status="completed",
                refreshed_count=refreshed_count,
                matches_count=len(matches),
                refreshed_at=datetime.now(timezone.utc),
            )

        task = refresh_matches_for_user.delay(str(current_user.id))
        return RefreshMatchesResponse(
            task_id=task.id,
            status="queued",
            refreshed_count=0,
            matches_count=0,
            refreshed_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.warning("Celery dispatch unavailable (%s), falling back to synchronous execution", exc)
        refreshed_count = await job_matcher.ingest_and_embed_listings(db)
        matches = await job_matcher.rank_jobs_for_user(db, current_user.id)
        return RefreshMatchesResponse(
            task_id=None,
            status="completed",
            refreshed_count=refreshed_count,
            matches_count=len(matches),
            refreshed_at=datetime.now(timezone.utc),
        )


@router.get("/matches/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_match_task_status(
    task_id: str,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
) -> TaskStatusResponse:
    """Check status of an asynchronous match refresh background task."""
    try:
        from celery.result import AsyncResult
        from app.core.celery_app import celery_app

        res = AsyncResult(task_id, app=celery_app)
        state = res.state
        ready = res.ready()
        result_data = None
        error_msg = None
        if ready:
            if res.successful():
                result_data = res.result if isinstance(res.result, dict) else {"result": str(res.result)}
            elif res.failed():
                error_msg = str(res.result)
        return TaskStatusResponse(
            task_id=task_id,
            status=state.lower() if state else "unknown",
            ready=ready,
            result=result_data,
            error=error_msg,
        )
    except Exception as exc:
        logger.error("Error checking task status %s: %s", task_id, exc)
        return TaskStatusResponse(
            task_id=task_id,
            status="unknown",
            ready=False,
            error=str(exc),
        )



@router.post("/matches/{match_id}/save", response_model=ToggleSaveResponse)
async def toggle_save_match(
    match_id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToggleSaveResponse:
    """Toggle bookmark saved state for a job match."""
    stmt = select(DailyMatch).where(
        DailyMatch.id == match_id,
        DailyMatch.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    match_record = result.scalar_one_or_none()

    if not match_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found",
        )

    match_record.saved = not match_record.saved
    await db.commit()
    return ToggleSaveResponse(id=match_record.id, saved=match_record.saved)


@router.post("/matches/{match_id}/dismiss", response_model=DismissMatchResponse)
async def dismiss_match(
    match_id: uuid.UUID,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DismissMatchResponse:
    """Dismiss a job match from active results."""
    stmt = select(DailyMatch).where(
        DailyMatch.id == match_id,
        DailyMatch.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    match_record = result.scalar_one_or_none()

    if not match_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found",
        )

    match_record.dismissed = True
    await db.commit()
    return DismissMatchResponse(id=match_record.id, dismissed=True)


@router.get("/{job_id}", response_model=JobListingDetailResponse)
async def get_job_listing_detail(
    job_id: str,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobListingDetailResponse:
    """Retrieve full canonical details for a single job listing by ID."""
    listing_record = None
    clean_id = str(job_id).strip()
    try:
        job_uuid = uuid.UUID(clean_id)
        stmt = select(JobListing).where(JobListing.id == job_uuid)
        res = await db.execute(stmt)
        listing_record = res.scalar_one_or_none()
    except ValueError:
        pass

    if not listing_record:
        try:
            stmt = select(JobListing).where(JobListing.external_id == clean_id)
            res = await db.execute(stmt)
            listing_record = res.scalar_one_or_none()
        except Exception:
            pass

    if not listing_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found",
        )

    return JobListingDetailResponse.model_validate(listing_record)

