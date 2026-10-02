"""Base abstract provider and data structure for job sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class JobListingData:
    company: str
    role_title: str
    description: str
    source: str = "mock"
    external_id: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = "full_time"  # "full_time", "internship", "contract"
    application_url: Optional[str] = None
    deadline: Optional[datetime] = None
    compensation: Optional[str] = None
    posted_at: Optional[datetime] = None


class BaseJobSource(ABC):
    """Abstract base class for job listing providers."""

    @abstractmethod
    async def fetch_jobs(self) -> List[JobListingData]:
        """Fetch and return normalized job listing records."""
        pass
