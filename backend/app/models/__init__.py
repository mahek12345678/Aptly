"""SQLAlchemy ORM models export for discovery and Alembic migrations."""
from app.db.base import Base
from app.models.application import ApplicationStatus, JobApplication
from app.models.job_match import DailyMatch, JobListing
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "UserPreference",
    "Resume",
    "JobApplication",
    "ApplicationStatus",
    "JobListing",
    "DailyMatch",
]
