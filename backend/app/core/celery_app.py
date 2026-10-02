"""Celery application and Celery Beat schedule configuration."""
from __future__ import annotations

import logging
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "aptly",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.job_tasks"],
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 min hard limit
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat Periodic Schedule
# Global listings ingestion runs once daily at 03:00 UTC (fetch jobs once, embed once)
# Followed by candidate ranking at 03:30 UTC (local ranking for each onboarded user)
celery_app.conf.beat_schedule = {
    "daily-global-job-refresh": {
        "task": "app.tasks.job_tasks.refresh_global_job_listings",
        "schedule": crontab(
            hour=settings.CELERY_BEAT_REFRESH_HOUR,
            minute=settings.CELERY_BEAT_REFRESH_MINUTE,
        ),
        "options": {"expires": 3600},
    },
    "daily-rank-jobs-all-users": {
        "task": "app.tasks.job_tasks.rank_jobs_for_all_users",
        "schedule": crontab(
            hour=settings.CELERY_BEAT_RANK_HOUR,
            minute=settings.CELERY_BEAT_RANK_MINUTE,
        ),
        "options": {"expires": 3600},
    },
}
