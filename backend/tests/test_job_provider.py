"""Tests for real job provider integration, normalization, deduplication, and freshness."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import httpx
import pytest
from sqlalchemy import func, select

from app.models.job_match import DailyMatch, JobListing
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.models.user import User
from app.services.job_matcher import JobMatcherService, normalize_text, normalize_url
from app.services.job_sources import BaseJobSource, JobListingData, MockJobSource, RemotiveJobSource, get_job_source
from app.services.job_sources.remotive_provider import clean_html_description, normalize_employment_type, parse_iso_datetime
from tests.conftest import TestingSessionLocal


# ---------------------------------------------------------------------------
# 1. Normalization & Helper Unit Tests
# ---------------------------------------------------------------------------

def test_clean_html_description():
    raw_html = "<p>We are hiring a <strong>Senior Engineer</strong>!</p><br/><div>Requirements:<ul><li>Python</li><li>Docker</li></ul></div>"
    cleaned = clean_html_description(raw_html)
    assert "We are hiring a Senior Engineer!" in cleaned
    assert "Requirements:" in cleaned
    assert "Python" in cleaned
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned
    assert "<ul>" not in cleaned


def test_parse_iso_datetime():
    dt = parse_iso_datetime("2026-09-20T14:30:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 20
    assert dt.tzinfo is not None

    invalid_dt = parse_iso_datetime("not-a-date")
    assert invalid_dt is None


def test_normalize_employment_type():
    assert normalize_employment_type("full_time") == "full_time"
    assert normalize_employment_type("full-time") == "full_time"
    assert normalize_employment_type("internship") == "internship"
    assert normalize_employment_type("summer_intern") == "internship"
    assert normalize_employment_type("contract") == "contract"
    assert normalize_employment_type("freelance") == "contract"
    assert normalize_employment_type("") == "full_time"


def test_url_and_text_normalization():
    url1 = "https://www.company.com/jobs/123/?utm_source=google#apply"
    url2 = "http://company.com/jobs/123"
    assert normalize_url(url1) == "company.com/jobs/123"
    assert normalize_url(url2) == "company.com/jobs/123"

    assert normalize_text("  Senior   Software   Engineer  ") == "senior software engineer"


# ---------------------------------------------------------------------------
# 2. Provider Fetch & Mock HTTP Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_remotive_fetch_jobs_success():
    provider = RemotiveJobSource(limit=10)

    sample_api_response = {
        "job-count": 2,
        "jobs": [
            {
                "id": 8801,
                "url": "https://remotive.com/remote-jobs/software-dev/stripe-lead-engineer-8801",
                "title": "Lead Backend Engineer",
                "company_name": "Stripe",
                "category": "software-dev",
                "job_type": "full_time",
                "publication_date": "2026-09-22T10:00:00Z",
                "candidate_required_location": "USA Only",
                "salary": "$190k - $240k",
                "description": "<p>Build core payment systems using <strong>Python</strong> and <strong>PostgreSQL</strong>.</p>",
            },
            {
                "id": 8802,
                "url": "https://remotive.com/remote-jobs/software-dev/brex-platform-engineer-8802",
                "title": "Platform Engineer",
                "company_name": "Brex",
                "category": "software-dev",
                "job_type": "full_time",
                "publication_date": "2026-09-21T08:00:00Z",
                "candidate_required_location": "Worldwide",
                "salary": "$180k - $220k",
                "description": "<p>Develop distributed infrastructure.</p>",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_api_response

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await provider.fetch_jobs()

    assert len(jobs) == 2
    assert jobs[0].company == "Stripe"
    assert jobs[0].role_title == "Lead Backend Engineer"
    assert jobs[0].external_id == "8801"
    assert jobs[0].source == "remotive"
    assert jobs[0].compensation == "$190k - $240k"
    assert "Python" in jobs[0].description
    assert "<p>" not in jobs[0].description
    assert jobs[0].posted_at is not None
    assert jobs[0].application_url == "https://remotive.com/remote-jobs/software-dev/stripe-lead-engineer-8801"


@pytest.mark.anyio
async def test_remotive_fetch_jobs_failure_returns_empty():
    provider = RemotiveJobSource(limit=10, timeout=1.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await provider.fetch_jobs()

    assert jobs == []


def test_provider_factory():
    p_mock = get_job_source("mock")
    assert isinstance(p_mock, MockJobSource)

    p_remotive = get_job_source("remotive")
    assert isinstance(p_remotive, RemotiveJobSource)


# ---------------------------------------------------------------------------
# 3. Ingestion, Multi-Tier Deduplication & Re-Embedding Tests
# ---------------------------------------------------------------------------

class StaticTestJobSource(BaseJobSource):
    def __init__(self, listings: list[JobListingData]):
        self.listings = listings

    async def fetch_jobs(self) -> list[JobListingData]:
        return self.listings


@pytest.mark.anyio
async def test_deduplication_and_selective_reembedding():
    matcher = JobMatcherService()

    initial_listings = [
        JobListingData(
            external_id="ext-001",
            source="remotive",
            company="Linear",
            role_title="Backend Engineer",
            location="Remote",
            employment_type="full_time",
            description="Build sync engines with TypeScript and PostgreSQL.",
            application_url="https://linear.app/careers/backend-1",
            compensation="$160k - $200k",
            posted_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
        ),
        JobListingData(
            external_id="ext-002",
            source="remotive",
            company="Datadog",
            role_title="Infrastructure Architect",
            location="New York",
            employment_type="full_time",
            description="Manage scalable cloud systems.",
            application_url="https://datadog.com/jobs/infra-1",
            compensation="$180k - $230k",
            posted_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
        ),
    ]

    async with TestingSessionLocal() as session:
        # First ingestion
        with patch("app.services.vector_store.vector_store.store_job_embedding") as mock_embed:
            count1 = await matcher.ingest_and_embed_listings(session, StaticTestJobSource(initial_listings))
            assert count1 == 2
            assert mock_embed.call_count == 2

        # Verify 2 rows in DB
        res = await session.execute(select(func.count(JobListing.id)))
        assert res.scalar_one() == 2

        # Second ingestion:
        # - Job 1 is UNCHANGED in description/role (only salary updated) -> MUST NOT re-embed
        # - Job 2 has CHANGED description -> MUST re-embed
        # - Job 3 is NEW -> MUST embed
        updated_listings = [
            JobListingData(
                external_id="ext-001",
                source="remotive",
                company="Linear",
                role_title="Backend Engineer",
                location="Remote",
                employment_type="full_time",
                description="Build sync engines with TypeScript and PostgreSQL.",  # unchanged
                application_url="https://linear.app/careers/backend-1",
                compensation="$170k - $210k",  # changed salary
                posted_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
            ),
            JobListingData(
                external_id="ext-002",
                source="remotive",
                company="Datadog",
                role_title="Infrastructure Architect",
                location="New York",
                employment_type="full_time",
                description="Manage scalable cloud systems with Kubernetes and Rust.",  # CHANGED description
                application_url="https://datadog.com/jobs/infra-1",
                compensation="$180k - $230k",
                posted_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
            ),
            JobListingData(
                external_id="ext-003",
                source="remotive",
                company="Figma",
                role_title="Systems Designer",
                location="San Francisco",
                employment_type="full_time",
                description="Create robust design systems.",
                application_url="https://figma.com/careers/systems",
                compensation="$175k - $220k",
                posted_at=datetime(2026, 9, 22, tzinfo=timezone.utc),
            ),
        ]

        with patch("app.services.vector_store.vector_store.store_job_embedding") as mock_embed:
            count2 = await matcher.ingest_and_embed_listings(session, StaticTestJobSource(updated_listings))
            assert count2 == 3
            # Only ext-002 (changed) and ext-003 (new) should be embedded; ext-001 was skipped!
            assert mock_embed.call_count == 2

        # Total rows should now be 3 (not 5 - deduplicated!)
        res = await session.execute(select(func.count(JobListing.id)))
        assert res.scalar_one() == 3

        # Verify ext-001 has updated compensation
        res_job = await session.execute(select(JobListing).where(JobListing.external_id == "ext-001"))
        job1 = res_job.scalar_one()
        assert job1.compensation == "$170k - $210k"
        assert job1.is_active is True
        assert job1.last_seen_at is not None


@pytest.mark.anyio
async def test_deduplication_fallbacks_url_and_company_role():
    matcher = JobMatcherService()

    # Pre-populate one listing
    async with TestingSessionLocal() as session:
        j1 = JobListing(
            external_id="some-id",
            source="remotive",
            company="Notion",
            role_title="Product Engineer",
            location="Remote",
            employment_type="full_time",
            description="Work on block editor.",
            application_url="https://notion.so/careers/100",
            embedding_status="embedded",
            is_active=True,
        )
        session.add(j1)
        await session.commit()

        # Listing with DIFFERENT external_id but identical normalized application_url:
        dup_by_url = [
            JobListingData(
                external_id="different-ext-id-999",
                source="remotive",
                company="Notion Inc",
                role_title="Product Engineer",
                location="Remote",
                employment_type="full_time",
                description="Work on block editor.",
                application_url="https://www.notion.so/careers/100/?ref=board",  # same normalized URL
            )
        ]

        with patch("app.services.vector_store.vector_store.store_job_embedding"):
            await matcher.ingest_and_embed_listings(session, StaticTestJobSource(dup_by_url))

        # Count should still be 1 (deduplicated by URL!)
        res = await session.execute(select(func.count(JobListing.id)))
        assert res.scalar_one() == 1


# ---------------------------------------------------------------------------
# 4. Inactive Jobs Hidden From Active Matching
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_inactive_jobs_hidden_from_active_matches():
    matcher = JobMatcherService()
    user_id = uuid.uuid4()

    async with TestingSessionLocal() as session:
        # Create user
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email="matcher_user@example.com",
            name="Job Matcher Tester",
            onboarding_completed=True,
            onboarding_step=4,
        )
        session.add(user)

        # Active job
        active_job = JobListing(
            external_id="active-1",
            source="remotive",
            company="ActiveCorp",
            role_title="Full Stack Engineer",
            location="Remote",
            employment_type="full_time",
            description="Active position.",
            is_active=True,
            embedding_status="embedded",
        )
        # Inactive job (expired/closed)
        inactive_job = JobListing(
            external_id="inactive-1",
            source="remotive",
            company="ClosedCorp",
            role_title="Backend Engineer",
            location="Remote",
            employment_type="full_time",
            description="Closed position.",
            is_active=False,
            embedding_status="embedded",
        )
        session.add_all([active_job, inactive_job])
        await session.commit()

        # Rank jobs for user
        with patch.object(matcher, "calculate_vector_score", return_value=0.85):
            matches = await matcher.rank_jobs_for_user(session, user_id)

        # Only active_job should be in daily matches
        matched_job_ids = [m.job_listing_id for m in matches]
        assert active_job.id in matched_job_ids
        assert inactive_job.id not in matched_job_ids
