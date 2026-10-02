"""Adzuna Job Source implementation.
Fetches, normalizes, and cleans live job listings from the official Adzuna Search API.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import html
from html.parser import HTMLParser
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.job_sources.base import BaseJobSource, JobListingData

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Clean HTML tags and convert block tags to appropriate whitespace."""

    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self._block_tags = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section"}

    def handle_starttag(self, tag: str, attrs: list):
        if tag.lower() in self._block_tags:
            self.text_parts.append("\n")
        elif tag.lower() == "li":
            self.text_parts.append("\n• ")

    def handle_endtag(self, tag: str):
        if tag.lower() in self._block_tags:
            self.text_parts.append("\n")

    def handle_data(self, data: str):
        self.text_parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self.text_parts)
        # Normalize excessive whitespace and consecutive blank lines
        lines = [line.strip() for line in raw.split("\n")]
        cleaned = "\n".join(line for line in lines if line)
        return cleaned


def clean_html_text(text: Optional[str]) -> str:
    """Convert HTML snippet to clean formatted plain text."""
    if not text:
        return ""
    # Fast path: if no tags present
    if "<" not in text and "&" not in text:
        return re.sub(r"[ \t]+", " ", text).strip()
    
    unescaped = html.unescape(text)
    try:
        extractor = HTMLTextExtractor()
        extractor.feed(unescaped)
        result = extractor.get_text()
        return result if result else re.sub(r"<[^>]+>", " ", unescaped).strip()
    except Exception:
        # Fallback to simple regex strip
        stripped = re.sub(r"<[^>]+>", " ", unescaped)
        return re.sub(r"\s+", " ", stripped).strip()


def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Safely parse ISO datetime string from Adzuna into a UTC datetime object."""
    if not date_str:
        return None
    try:
        clean_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def format_compensation(
    salary_min: Optional[float | int],
    salary_max: Optional[float | int],
    country: str = "in",
) -> Optional[str]:
    """Derive formatted compensation string from Adzuna salary fields."""
    if salary_min is None and salary_max is None:
        return None

    currency_symbol = "₹" if country.lower() == "in" else "$"
    
    # Check if numbers are valid
    s_min = int(salary_min) if salary_min is not None and salary_min > 0 else None
    s_max = int(salary_max) if salary_max is not None and salary_max > 0 else None

    if s_min is not None and s_max is not None:
        if s_min == s_max:
            return f"{currency_symbol}{s_min:,}"
        return f"{currency_symbol}{s_min:,} – {currency_symbol}{s_max:,}"
    elif s_min is not None:
        return f"From {currency_symbol}{s_min:,}"
    elif s_max is not None:
        return f"Up to {currency_symbol}{s_max:,}"

    return None


def derive_employment_type(
    contract_time: Optional[str],
    contract_type: Optional[str],
    title: str,
    description: str,
) -> str:
    """Normalize Adzuna employment type into canonical enum."""
    t_lower = title.lower()
    d_lower = description[:300].lower()

    if "intern" in t_lower or "internship" in t_lower or "intern" in d_lower:
        return "internship"

    c_time = (contract_time or "").lower().strip()
    c_type = (contract_type or "").lower().strip()

    if "part_time" in c_time or "part" in c_time:
        return "part_time"
    if "contract" in c_type or "contract" in c_time or "temporary" in c_type:
        return "contract"
    if "full_time" in c_time or "permanent" in c_type:
        return "full_time"

    return "full_time"


class AdzunaJobSource(BaseJobSource):
    """
    Real job provider fetching live developer listings from the official Adzuna Search API.
    Handles rate-limits, exponential backoff, pagination, and multi-query batching.
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        country: Optional[str] = None,
        base_url: Optional[str] = None,
        results_per_page: Optional[int] = None,
        queries: Optional[List[str]] = None,
    ):
        self.app_id = (app_id or settings.ADZUNA_APP_ID or "").strip()
        self.app_key = (app_key or settings.ADZUNA_APP_KEY or "").strip()
        self.country = (country or settings.ADZUNA_COUNTRY or "in").strip().lower()
        self.base_url = (base_url or settings.JOB_PROVIDER_BASE_URL or "https://api.adzuna.com/v1/api/jobs").rstrip("/")
        self.results_per_page = results_per_page or settings.ADZUNA_RESULTS_PER_PAGE or 15
        self.queries = queries or settings.ADZUNA_QUERIES

    async def fetch_jobs(
        self,
        queries: Optional[List[str]] = None,
        country: Optional[str] = None,
        max_pages: Optional[int] = None,
    ) -> List[JobListingData]:
        """
        Fetch listings from Adzuna for configured search terms.
        Safely aggregates results and prevents duplicate processing across queries.
        """
        if not self.app_id or not self.app_key:
            logger.warning(
                "Adzuna credentials (ADZUNA_APP_ID / ADZUNA_APP_KEY) not configured. Cannot fetch live listings."
            )
            return []

        target_country = (country or self.country).strip().lower()
        search_queries = queries or self.queries
        pages_to_fetch = max_pages or settings.ADZUNA_MAX_PAGES_PER_QUERY or 1

        all_listings: List[JobListingData] = []
        seen_external_ids: set[str] = set()

        async with httpx.AsyncClient(timeout=14.0) as client:
            for query in search_queries:
                for page in range(1, pages_to_fetch + 1):
                    endpoint_url = f"{self.base_url}/{target_country}/search/{page}"
                    params = {
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "results_per_page": self.results_per_page,
                        "what": query,
                        "content-type": "application/json",
                    }

                    results = await self._fetch_with_backoff(client, endpoint_url, params, query)
                    if not results:
                        continue

                    for item in results:
                        normalized = self._normalize_item(item, target_country)
                        if normalized and normalized.external_id:
                            if normalized.external_id in seen_external_ids:
                                continue
                            seen_external_ids.add(normalized.external_id)
                            all_listings.append(normalized)

                # Polite spacing between distinct queries to respect rate limits
                await asyncio.sleep(0.35)

        logger.info(
            "Adzuna fetch completed: %d unique job listings retrieved across %d queries.",
            len(all_listings),
            len(search_queries),
        )
        return all_listings

    async def _fetch_with_backoff(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Dict[str, Any],
        query: str,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """Fetch endpoint with exponential backoff on transient errors."""
        backoff = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("results", [])

                elif resp.status_code in (401, 403):
                    # Never log credentials in error messages
                    logger.error(
                        "Adzuna authorization failed (HTTP %d). Please check ADZUNA_APP_ID / ADZUNA_APP_KEY.",
                        resp.status_code,
                    )
                    return []

                elif resp.status_code == 429:
                    logger.warning(
                        "Adzuna rate limit reached (attempt %d/%d). Backing off for %.1fs.",
                        attempt,
                        max_retries,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue

                else:
                    logger.warning(
                        "Adzuna API returned non-200 status %d for query '%s' (attempt %d/%d).",
                        resp.status_code,
                        query,
                        attempt,
                        max_retries,
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(backoff)
                        backoff *= 1.5

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                logger.warning(
                    "Network error connecting to Adzuna for query '%s' (%s, attempt %d/%d).",
                    query,
                    type(net_err).__name__,
                    attempt,
                    max_retries,
                )
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
            except Exception as exc:
                logger.error("Unexpected error fetching from Adzuna: %s", exc, exc_info=True)
                return []

        return []

    def _normalize_item(self, item: Dict[str, Any], country: str) -> Optional[JobListingData]:
        """Normalize a single raw Adzuna job item into JobListingData."""
        if not isinstance(item, dict):
            return None

        raw_id = item.get("id")
        external_id = str(raw_id).strip() if raw_id is not None else None

        raw_title = item.get("title") or ""
        role_title = clean_html_text(raw_title)
        if not role_title:
            return None

        # Company mapping
        company_obj = item.get("company")
        company_name = ""
        if isinstance(company_obj, dict):
            company_name = clean_html_text(company_obj.get("display_name"))
        elif isinstance(company_obj, str):
            company_name = clean_html_text(company_obj)

        if not company_name:
            company_name = "Confidential Employer"

        # Location mapping
        loc_obj = item.get("location")
        location_display = ""
        if isinstance(loc_obj, dict):
            location_display = clean_html_text(loc_obj.get("display_name"))
            if not location_display and isinstance(loc_obj.get("area"), list):
                location_display = ", ".join(clean_html_text(a) for a in loc_obj["area"] if a)
        elif isinstance(loc_obj, str):
            location_display = clean_html_text(loc_obj)

        if not location_display:
            location_display = "India" if country == "in" else None

        # Description mapping & cleaning
        raw_desc = item.get("description") or ""
        description = clean_html_text(raw_desc)
        if not description:
            description = f"Role: {role_title} at {company_name}."

        # Application URL
        application_url = (item.get("redirect_url") or "").strip() or None

        # Posted At
        posted_at = parse_iso_datetime(item.get("created"))

        # Employment Type
        employment_type = derive_employment_type(
            item.get("contract_time"),
            item.get("contract_type"),
            role_title,
            description,
        )

        # Compensation
        compensation = format_compensation(
            item.get("salary_min"),
            item.get("salary_max"),
            country=country,
        )

        return JobListingData(
            company=company_name,
            role_title=role_title,
            description=description,
            source="adzuna",
            external_id=external_id,
            location=location_display,
            employment_type=employment_type,
            application_url=application_url,
            deadline=None,
            compensation=compensation,
            posted_at=posted_at,
        )
