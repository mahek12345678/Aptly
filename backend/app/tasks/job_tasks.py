"""Celery tasks for scheduled and asynchronous job discovery and matching."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.job_matcher import job_matcher

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Execute an async coroutine within Celery's synchronous task worker."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Task 1: Global Job Listings Ingestion & Vector Caching
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.refresh_global_job_listings",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def refresh_global_job_listings(self) -> Dict[str, Any]:
    """
    Fetch new jobs from configured providers once globally,
    normalize fields, deduplicate, and embed only new/changed jobs in ChromaDB.
    """
    logger.info("Executing scheduled global job listings refresh...")

    async def _execute() -> int:
        async with AsyncSessionLocal() as session:
            count = await job_matcher.ingest_and_embed_listings(session)
            return count

    try:
        refreshed_count = _run_async(_execute())
        logger.info("Global job refresh finished successfully: %d listings verified/embedded.", refreshed_count)
        return {
            "status": "success",
            "refreshed_count": refreshed_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Failed to execute global job refresh: %s", exc, exc_info=True)
        raise exc


# ---------------------------------------------------------------------------
# Task 2: Candidate Ranking for All Onboarded Users
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.rank_jobs_for_all_users",
    bind=True,
)
def rank_jobs_for_all_users(self) -> Dict[str, Any]:
    """
    Calculate personalized matches for all users with completed onboarding
    and store/update DailyMatch records.
    Fault-tolerant: error on one user does NOT fail remaining users.
    """
    logger.info("Executing scheduled ranking for all onboarded candidates...")

    async def _execute() -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.onboarding_completed == True)  # noqa: E712
            result = await session.execute(stmt)
            users = result.scalars().all()

            total_users = len(users)
            successful_users = 0
            failed_users = 0
            errors: List[str] = []

            for u in users:
                try:
                    matches = await job_matcher.rank_jobs_for_user(session, u.id)
                    successful_users += 1
                    logger.debug("Ranked %d jobs for candidate %s", len(matches), u.id)
                except Exception as user_exc:
                    failed_users += 1
                    err_msg = f"User {u.id}: {str(user_exc)}"
                    logger.error("Failed to rank jobs for candidate: %s", err_msg, exc_info=True)
                    errors.append(err_msg)
                    # Continue loop - do not abort for other candidates

            return {
                "total_users": total_users,
                "successful_users": successful_users,
                "failed_users": failed_users,
                "errors": errors[:10],
            }

    summary = _run_async(_execute())
    logger.info(
        "Candidate ranking complete: %d/%d candidates updated successfully.",
        summary["successful_users"],
        summary["total_users"],
    )
    return {
        "status": "success",
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Task 3: Per-User Match Ranking (Reusable for manual UI refresh)
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.refresh_matches_for_user",
    bind=True,
)
def refresh_matches_for_user(self, user_id_str: str) -> Dict[str, Any]:
    """
    Asynchronous per-user ranking task invoked when a user clicks 'Refresh matches' in the UI.
    Updates or inserts DailyMatch records idempotently.
    """
    logger.info("Starting on-demand match refresh for user %s", user_id_str)
    candidate_id = uuid.UUID(user_id_str)

    async def _execute() -> int:
        async with AsyncSessionLocal() as session:
            # 1. Ingest any newly available global postings
            await job_matcher.ingest_and_embed_listings(session)
            # 2. Re-score and rank for this candidate
            matches = await job_matcher.rank_jobs_for_user(session, candidate_id)
            return len(matches)

    try:
        matches_count = _run_async(_execute())
        logger.info("On-demand match refresh completed for user %s (%d matches)", user_id_str, matches_count)
        return {
            "status": "success",
            "user_id": user_id_str,
            "matches_count": matches_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("On-demand refresh failed for user %s: %s", user_id_str, exc, exc_info=True)
        raise exc
