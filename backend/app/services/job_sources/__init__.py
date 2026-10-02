"""Job Sources package for fetching job listings from pluggable providers."""
from app.core.config import settings
from app.services.job_sources.adzuna import AdzunaJobSource
from app.services.job_sources.base import BaseJobSource, JobListingData
from app.services.job_sources.mock_provider import MockJobSource
from app.services.job_sources.remotive_provider import RemotiveJobSource


def get_job_source(provider_name: str | None = None) -> BaseJobSource:
    """Factory to retrieve configured or requested job provider instance."""
    name = (provider_name or settings.JOB_PROVIDER or "adzuna").lower().strip()
    if name == "mock":
        return MockJobSource()
    elif name == "adzuna":
        return AdzunaJobSource()
    elif name == "remotive":
        return RemotiveJobSource()
    # Default fallback
    return AdzunaJobSource()


__all__ = [
    "AdzunaJobSource",
    "BaseJobSource",
    "JobListingData",
    "MockJobSource",
    "RemotiveJobSource",
    "get_job_source",
]
