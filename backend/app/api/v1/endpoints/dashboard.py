"""Dashboard summary endpoint for authenticated user metrics, activity, and reminders."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.db.session import get_db
from app.models.application import JobApplication, TrackingState
from app.models.job_match import DailyMatch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

STATUS_DISPLAY_MAP = {
    "applied": "Applied",
    "oa": "OA/Assessment",
    "interview": "Interview",
    "offer": "Offer Received",
    "rejected": "Rejected",
}


def _format_relative_time(dt: datetime, now: datetime) -> str:
    """Format datetime into human-friendly relative label."""
    if not dt:
        return "Recently"
    # Ensure UTC timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h ago"
    days = int(hours // 24)
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    weeks = int(days // 7)
    if weeks == 1:
        return "1 week ago"
    if weeks < 5:
        return f"{weeks} weeks ago"
    return dt.strftime("%d %b %Y")


def _format_due_text(deadline: datetime, now: datetime) -> str:
    """Format upcoming deadline into relative text."""
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    diff = deadline - now
    hours = diff.total_seconds() / 3600
    if hours <= 0:
        return "Due today"
    if hours <= 24:
        return "Due tomorrow"
    days = int(diff.days)
    if days <= 1:
        return "Due tomorrow"
    return f"In {days} days"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DashboardUser(BaseModel):
    name: str
    first_name: str
    email: Optional[str] = None
    profile_picture_url: Optional[str] = None


class DashboardMetrics(BaseModel):
    jobs_applied: int
    replies_received: int
    offers_received: int


class RecentActivityItemResponse(BaseModel):
    id: uuid.UUID
    company: str
    role: str
    status: str
    raw_status: str
    updated_at: str
    updated_at_iso: datetime
    deadline: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UpcomingReminderItemResponse(BaseModel):
    id: uuid.UUID
    title: str
    due_text: str
    due_date: datetime
    type: str  # "application" | "assessment" | "interview" | "followup"
    company: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    user: DashboardUser
    metrics: DashboardMetrics
    recent_activity: List[RecentActivityItemResponse]
    upcoming_reminders: List[UpcomingReminderItemResponse]
    job_matches_count: int = 0


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardSummaryResponse:
    """Return dashboard summary for the currently authenticated user with real application metrics."""
    # 1. Fetch all confirmed job applications for the authenticated user
    stmt = (
        select(JobApplication)
        .where(
            JobApplication.user_id == current_user.id,
            JobApplication.tracking_state != TrackingState.APPLICATION_STARTED.value,
        )
        .order_by(JobApplication.updated_at.desc())
    )
    result = await db.execute(stmt)
    applications = result.scalars().all()

    now = datetime.now(timezone.utc)

    # 2. Compute the 3 headline metrics
    # Jobs Applied: Total count of applications
    jobs_applied = len(applications)

    # Replies Received: Applications that progressed beyond "applied" (e.g. oa, interview, offer, rejected)
    replies_received = sum(
        1 for app in applications if app.status and app.status.lower() != "applied"
    )

    # Offers Received: Applications with status = offer
    offers_received = sum(
        1 for app in applications if app.status and app.status.lower() == "offer"
    )

    # 3. Format recent activity (latest applications)
    recent_activity: list[RecentActivityItemResponse] = []
    for app in applications[:10]:
        status_key = app.status.lower() if app.status else "applied"
        status_display = STATUS_DISPLAY_MAP.get(status_key, app.status.title())
        recent_activity.append(
            RecentActivityItemResponse(
                id=app.id,
                company=app.company,
                role=app.role,
                status=status_display,
                raw_status=status_key,
                updated_at=_format_relative_time(app.updated_at, now),
                updated_at_iso=app.updated_at,
                deadline=app.deadline,
            )
        )

    # 4. Format upcoming reminders (deadlines within the next 7 days)
    upcoming_reminders: list[UpcomingReminderItemResponse] = []
    seven_days_later = now + timedelta(days=7)

    for app in applications:
        if app.deadline:
            dl = app.deadline
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)

            # Check if within next 7 days (and not expired past 1 day)
            if now - timedelta(hours=12) <= dl <= seven_days_later:
                # Determine reminder type
                st = app.status.lower() if app.status else "applied"
                if st == "oa":
                    rem_type = "assessment"
                    title = f"Complete {app.company} OA"
                elif st == "interview":
                    rem_type = "interview"
                    title = f"Interview with {app.company}"
                else:
                    rem_type = "application"
                    title = f"Submit {app.company} application"

                upcoming_reminders.append(
                    UpcomingReminderItemResponse(
                        id=app.id,
                        title=title,
                        due_text=_format_due_text(dl, now),
                        due_date=dl,
                        type=rem_type,
                        company=app.company,
                    )
                )

    # Sort reminders by nearest deadline
    upcoming_reminders.sort(key=lambda r: r.due_date)

    first_name = (
        current_user.name.strip().split()[0]
        if current_user.name and current_user.name.strip()
        else "there"
    )

    # 5. Fetch count of active personalized matches for the candidate
    match_stmt = select(func.count(DailyMatch.id)).where(
        DailyMatch.user_id == current_user.id,
        DailyMatch.dismissed == False,
    )
    match_res = await db.execute(match_stmt)
    job_matches_count = match_res.scalar_one() or 0

    return DashboardSummaryResponse(
        user=DashboardUser(
            name=current_user.name or "User",
            first_name=first_name,
            email=current_user.email,
            profile_picture_url=current_user.profile_picture_url,
        ),
        metrics=DashboardMetrics(
            jobs_applied=jobs_applied,
            replies_received=replies_received,
            offers_received=offers_received,
        ),
        recent_activity=recent_activity,
        upcoming_reminders=upcoming_reminders,
        job_matches_count=job_matches_count,
    )
