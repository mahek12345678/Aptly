"""Assistant context retrieval service.

Retrieves selective, grounded context based on the user query and intent,
strictly adhering to canonical JobApplication statuses and real database models.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import ApplicationStatus, JobApplication, TrackingState
from app.models.job_match import DailyMatch, JobListing
from app.models.resume import Resume


def _filter_upcoming_deadlines(applications: List[JobApplication], days: int = 7) -> List[Dict[str, Any]]:
    """Filter applications with deadlines falling within the next N days."""
    now = datetime.now(timezone.utc)
    max_date = now + timedelta(days=days)
    upcoming: List[Dict[str, Any]] = []

    for app in applications:
        if app.deadline:
            deadline = app.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if now <= deadline <= max_date:
                upcoming.append({
                    "company": app.company,
                    "role": app.role,
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "status": app.status,
                })

    upcoming.sort(key=lambda x: x["deadline"])
    return upcoming


async def get_briefing_context(session: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Construct minimal grounded context for the daily briefing."""
    # 1. Active matches (not dismissed) with job listing details
    matches_stmt = (
        select(DailyMatch)
        .options(selectinload(DailyMatch.job_listing))
        .where(DailyMatch.user_id == user_id, DailyMatch.dismissed.is_(False))
        .order_by(DailyMatch.final_score.desc())
    )
    matches_res = await session.execute(matches_stmt)
    all_matches: List[DailyMatch] = list(matches_res.scalars().all())
    top_matches = all_matches[:3]

    # 2. Applications for user
    apps_stmt = (
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .order_by(JobApplication.created_at.desc())
    )
    apps_res = await session.execute(apps_stmt)
    all_applications: List[JobApplication] = list(apps_res.scalars().all())

    # Count pending confirmations (application_started)
    pending_confirmations = [
        app for app in all_applications
        if getattr(app, "tracking_state", TrackingState.APPLIED.value) == TrackingState.APPLICATION_STARTED.value
    ]

    # Confirmed applications (applied state)
    confirmed_applications = [
        app for app in all_applications
        if getattr(app, "tracking_state", TrackingState.APPLIED.value) == TrackingState.APPLIED.value
    ]

    # Canonical status counts: applied, oa, interview, offer, rejected
    canonical_statuses = [
        ApplicationStatus.APPLIED.value,
        ApplicationStatus.OA.value,
        ApplicationStatus.INTERVIEW.value,
        ApplicationStatus.OFFER.value,
        ApplicationStatus.REJECTED.value,
    ]
    status_counts = {s: 0 for s in canonical_statuses}
    for app in confirmed_applications:
        if app.status in status_counts:
            status_counts[app.status] += 1

    # Replies received = sum of oa + interview + offer + rejected (progressed beyond applied)
    replies_received = (
        status_counts[ApplicationStatus.OA.value]
        + status_counts[ApplicationStatus.INTERVIEW.value]
        + status_counts[ApplicationStatus.OFFER.value]
        + status_counts[ApplicationStatus.REJECTED.value]
    )

    upcoming_deadlines = _filter_upcoming_deadlines(confirmed_applications, days=7)

    has_data = bool(all_matches or all_applications)

    return {
        "has_data": has_data,
        "active_matches_count": len(all_matches),
        "top_matches": [
            {
                "company": m.job_listing.company if m.job_listing else "Unknown",
                "role": m.job_listing.role_title if m.job_listing else "Unknown",
                "score_pct": round(m.final_score * 100),
                "reasons": m.match_reasons or [],
            }
            for m in top_matches
        ],
        "applications_total": len(confirmed_applications),
        "status_counts": status_counts,
        "replies_received": replies_received,
        "offers_count": status_counts[ApplicationStatus.OFFER.value],
        "oa_count": status_counts[ApplicationStatus.OA.value],
        "interview_count": status_counts[ApplicationStatus.INTERVIEW.value],
        "pending_confirmations_count": len(pending_confirmations),
        "pending_confirmations": [
            {"company": app.company, "role": app.role}
            for app in pending_confirmations[:3]
        ],
        "upcoming_deadlines_7d_count": len(upcoming_deadlines),
        "upcoming_deadlines": upcoming_deadlines,
    }


async def get_upcoming_deadlines_context(session: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Retrieve upcoming deadlines, assessments, and interview schedules."""
    apps_stmt = (
        select(JobApplication)
        .where(
            JobApplication.user_id == user_id,
            JobApplication.tracking_state == TrackingState.APPLIED.value,
        )
        .order_by(JobApplication.deadline.asc().nullslast())
    )
    apps_res = await session.execute(apps_stmt)
    applications: List[JobApplication] = list(apps_res.scalars().all())

    upcoming_7d = _filter_upcoming_deadlines(applications, days=7)
    upcoming_14d = _filter_upcoming_deadlines(applications, days=14)

    oas = [
        {"company": a.company, "role": a.role, "deadline": a.deadline.strftime("%Y-%m-%d") if a.deadline else None}
        for a in applications if a.status == ApplicationStatus.OA.value
    ]
    interviews = [
        {"company": a.company, "role": a.role, "deadline": a.deadline.strftime("%Y-%m-%d") if a.deadline else None}
        for a in applications if a.status == ApplicationStatus.INTERVIEW.value
    ]

    return {
        "upcoming_deadlines_next_7_days": upcoming_7d,
        "upcoming_deadlines_next_14_days": upcoming_14d,
        "active_oa_assessments": oas,
        "active_interviews": interviews,
    }


async def get_matches_context(session: AsyncSession, user_id: uuid.UUID, top_n: int = 5) -> Dict[str, Any]:
    """Retrieve top active job matches with factual scores and matching reasons."""
    stmt = (
        select(DailyMatch)
        .options(selectinload(DailyMatch.job_listing))
        .where(DailyMatch.user_id == user_id, DailyMatch.dismissed.is_(False))
        .order_by(DailyMatch.final_score.desc())
        .limit(top_n)
    )
    res = await session.execute(stmt)
    matches: List[DailyMatch] = list(res.scalars().all())

    return {
        "matches_count": len(matches),
        "top_matches": [
            {
                "company": m.job_listing.company if m.job_listing else "Unknown",
                "role": m.job_listing.role_title if m.job_listing else "Unknown",
                "location": m.job_listing.location if m.job_listing else None,
                "score_pct": round(m.final_score) if m.final_score > 1.0 else round(m.final_score * 100),
                "reasons": m.match_reasons or [],
                "application_url": m.job_listing.application_url if m.job_listing else None,
            }
            for m in matches
        ],
    }


async def get_application_progress_context(session: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Retrieve detailed application pipeline metrics and recent application states."""
    apps_stmt = (
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .order_by(JobApplication.created_at.desc())
    )
    apps_res = await session.execute(apps_stmt)
    applications: List[JobApplication] = list(apps_res.scalars().all())

    confirmed = [
        a for a in applications
        if getattr(a, "tracking_state", TrackingState.APPLIED.value) == TrackingState.APPLIED.value
    ]
    pending = [
        a for a in applications
        if getattr(a, "tracking_state", TrackingState.APPLIED.value) == TrackingState.APPLICATION_STARTED.value
    ]

    canonical_statuses = [
        ApplicationStatus.APPLIED.value,
        ApplicationStatus.OA.value,
        ApplicationStatus.INTERVIEW.value,
        ApplicationStatus.OFFER.value,
        ApplicationStatus.REJECTED.value,
    ]
    status_counts = {s: 0 for s in canonical_statuses}
    for app in confirmed:
        if app.status in status_counts:
            status_counts[app.status] += 1

    replies_received = (
        status_counts[ApplicationStatus.OA.value]
        + status_counts[ApplicationStatus.INTERVIEW.value]
        + status_counts[ApplicationStatus.OFFER.value]
        + status_counts[ApplicationStatus.REJECTED.value]
    )

    recent_apps = [
        {
            "company": a.company,
            "role": a.role,
            "status": a.status,
            "applied_date": a.created_at.strftime("%Y-%m-%d") if a.created_at else None,
        }
        for a in confirmed[:5]
    ]

    return {
        "total_confirmed_applications": len(confirmed),
        "status_breakdown": status_counts,
        "replies_received": replies_received,
        "offers": status_counts[ApplicationStatus.OFFER.value],
        "pending_confirmations_count": len(pending),
        "recent_applications": recent_apps,
    }


async def get_resume_skill_context(session: AsyncSession, user_id: uuid.UUID, skill_or_topic: str) -> Dict[str, Any]:
    """Check user's parsed resume for verified skills, experience, or keywords."""
    resume_stmt = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
    )
    resume_res = await session.execute(resume_stmt)
    resume: Optional[Resume] = resume_res.scalars().first()

    if not resume:
        return {
            "has_resume": False,
            "query": skill_or_topic,
            "skill_found": False,
            "notes": "No resume uploaded yet.",
        }

    if resume and (not resume.parsed_data or not resume.extracted_text) and resume.file_path:
        from pathlib import Path
        if Path(resume.file_path).exists():
            try:
                from app.services.resume_parser import extract_raw_text, resume_parser
                from app.services.vector_store import vector_store
                raw_text = extract_raw_text(resume.file_path)
                if raw_text.strip():
                    parsed_dict = resume_parser.parse(raw_text)
                    vector_store.store_resume_chunks(
                        resume_id=resume.id,
                        user_id=user_id,
                        parsed_data=parsed_dict,
                        raw_text=raw_text,
                    )
                    resume.extracted_text = raw_text
                    resume.parsed_data = parsed_dict
                    resume.parsed_status = "parsed"
                    resume.parsed_at = datetime.now(timezone.utc)
                    await session.flush()
            except Exception:
                pass

    skills: List[str] = []
    if resume.parsed_data and isinstance(resume.parsed_data, dict):
        skills = resume.parsed_data.get("skills", []) or []

    query_lower = skill_or_topic.strip().lower()
    in_skills_list = any(query_lower == s.lower() or query_lower in s.lower() for s in skills)
    in_raw_text = bool(resume.extracted_text and query_lower in resume.extracted_text.lower())

    return {
        "has_resume": True,
        "resume_name": resume.file_name,
        "query": skill_or_topic,
        "skill_found": in_skills_list or in_raw_text,
        "verified_in_skills_section": in_skills_list,
        "top_verified_skills": skills[:10],
    }
