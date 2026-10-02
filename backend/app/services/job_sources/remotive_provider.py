"""Remotive API real job source integration.

Fetches current live remote software, engineering, and tech listings
from Remotive's legitimate public API, normalizing records into JobListingData.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import html
import logging
import re
from typing import Any, Dict, List, Optional
import urllib.parse

import httpx

from app.core.config import settings
from app.services.job_sources.base import BaseJobSource, JobListingData

logger = logging.getLogger(__name__)


from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result: list[str] = []
        self._block_tags = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() in self._block_tags:
            self.result.append("\n")

    def handle_endtag(self, tag: str):
        if tag.lower() in self._block_tags:
            self.result.append("\n")

    def handle_data(self, data: str):
        self.result.append(data)

    def get_text(self) -> str:
        raw = "".join(self.result)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def clean_html_description(raw_html: str) -> str:
    """Convert HTML job descriptions into clean, readable text."""
    if not raw_html:
        return ""
    try:
        parser = HTMLTextExtractor()
        parser.feed(raw_html)
        return parser.get_text()
    except Exception:
        # Fallback simple tag stripping
        text = re.sub(r"<[^>]+>", "", raw_html)
        return re.sub(r"\s+", " ", text).strip()


def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string safely into timezone-aware datetime."""
    if not date_str:
        return None
    try:
        # Handle trailing Z or offsets
        clean_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def normalize_employment_type(job_type_str: Optional[str]) -> str:
    """Normalize raw provider job type into standard Aptly employment type."""
    if not job_type_str:
        return "full_time"

    jt = job_type_str.lower().strip().replace("-", "_")
    if "intern" in jt:
        return "internship"
    if "contract" in jt or "freelance" in jt:
        return "contract"
    if "part" in jt:
        return "part_time"
    return "full_time"


class RemotiveJobSource(BaseJobSource):
    """Job source integration for Remotive API (https://remotive.com/api/remote-jobs)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        limit: int = 50,
        timeout: float = 15.0,
    ):
        self.base_url = (base_url or settings.JOB_PROVIDER_BASE_URL or "https://remotive.com/api/remote-jobs").strip()
        self.api_key = api_key or settings.JOB_PROVIDER_API_KEY or ""
        self.limit = limit or settings.JOB_PROVIDER_LIMIT or 50
        self.timeout = timeout

    async def fetch_jobs(self, category: Optional[str] = "software-dev") -> List[JobListingData]:
        """Fetch remote job listings from Remotive API with retries and exponential backoff."""
        params: Dict[str, Any] = {}
        if self.limit:
            params["limit"] = self.limit
        if category:
            params["category"] = category

        headers = {
            "User-Agent": "Aptly-Career-Intelligence/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        max_retries = 3
        backoff_seconds = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(self.base_url, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    jobs_raw = data.get("jobs", [])
                    logger.info("Successfully fetched %d raw jobs from Remotive", len(jobs_raw))
                    return self._normalize_jobs(jobs_raw)

                if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    logger.warning(
                        "Remotive API returned status %d (attempt %d/%d). Retrying in %.1fs...",
                        response.status_code,
                        attempt,
                        max_retries,
                        backoff_seconds,
                    )
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds *= 2
                    continue

                logger.error("Remotive API request failed with status code %d", response.status_code)
                return []

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt < max_retries:
                    logger.warning(
                        "Remotive API network error (%s) on attempt %d/%d. Retrying in %.1fs...",
                        type(exc).__name__,
                        attempt,
                        max_retries,
                        backoff_seconds,
                    )
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds *= 2
                else:
                    logger.error(
                        "Remotive API connection failed after %d attempts: %s",
                        max_retries,
                        type(exc).__name__,
                    )
                    return []
            except Exception as exc:
                logger.error("Unexpected error fetching from Remotive API: %s", type(exc).__name__, exc_info=True)
                return []

        return []

    def _normalize_jobs(self, jobs_raw: List[Dict[str, Any]]) -> List[JobListingData]:
        """Normalize raw Remotive records into canonical JobListingData."""
        normalized: List[JobListingData] = []

        for item in jobs_raw:
            try:
                title = str(item.get("title") or "").strip()
                company = str(item.get("company_name") or "").strip()
                if not title or not company:
                    continue

                raw_id = item.get("id")
                external_id = str(raw_id).strip() if raw_id is not None else None

                raw_desc = item.get("description") or ""
                cleaned_desc = clean_html_description(raw_desc)
                if not cleaned_desc:
                    cleaned_desc = f"{title} at {company}."

                location = item.get("candidate_required_location")
                if not location or location.lower() == "anywhere":
                    location = "Remote"
                else:
                    location = location.strip()

                raw_salary = item.get("salary")
                compensation = str(raw_salary).strip() if raw_salary else None

                posted_at = parse_iso_datetime(item.get("publication_date"))
                emp_type = normalize_employment_type(item.get("job_type"))
                app_url = item.get("url") or None

                listing = JobListingData(
                    external_id=external_id,
                    source="remotive",
                    company=company,
                    role_title=title,
                    location=location,
                    employment_type=emp_type,
                    description=cleaned_desc,
                    application_url=app_url,
                    deadline=None,
                    compensation=compensation,
                    posted_at=posted_at,
                )
                normalized.append(listing)
            except Exception as item_err:
                logger.debug("Skipping unparseable Remotive listing: %s", item_err)
                continue

        return normalized
