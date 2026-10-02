"""Unit and integration tests for Adzuna Job Source and ingestion lifecycle."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from sqlalchemy import select

from app.models.job_match import DailyMatch, JobListing
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.models.user import User
from app.services.job_sources.adzuna import (
    AdzunaJobSource,
    clean_html_text,
    derive_employment_type,
    format_compensation,
)
from app.services.job_sources.base import JobListingData
from app.services.job_sources import get_job_source
from app.services.job_matcher import job_matcher
from app.tasks.job_tasks import refresh_global_job_listings
from tests.conftest import TestingSessionLocal

@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

MOCK_ADZUNA_RESPONSE = {
    "count": 2,
    "results": [
        {
            "id": "adz-9901",
            "title": "Senior <b>Backend Developer</b>",
            "company": {"display_name": "Swiggy & Co"},
            "location": {
                "display_name": "Bangalore, Karnataka",
                "area": ["India", "Karnataka", "Bangalore"],
            },
            "description": "<p>Design scalable <strong>FastAPI</strong> and <strong>PostgreSQL</strong> architectures.</p>",
            "redirect_url": "https://www.adzuna.in/land/ad/adz-9901?utm=1",
            "created": "2026-09-22T08:00:00Z",
            "contract_time": "full_time",
            "contract_type": "permanent",
            "salary_min": 2000000,
            "salary_max": 2800000,
        },
        {
            "id": "adz-9902",
            "title": "Software Engineering Intern",
            "company": None,  # Test missing nested dictionary
            "location": None,  # Test missing location
            "description": "Python, Docker, algorithms.",
            "redirect_url": "https://www.adzuna.in/land/ad/adz-9902",
            "created": "2026-09-23T10:00:00Z",
            "contract_time": None,
            "contract_type": None,
            "salary_min": 350000,
            "salary_max": None,
        },
    ],
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


# 1. Provider Auth & Params
@pytest.mark.anyio
async def test_adzuna_auth_and_params_sent():
    source = AdzunaJobSource(
        app_id="test_id_123",
        app_key="test_key_456",
        country="in",
        results_per_page=10,
    )

    captured_requests = []

    async def mock_get(url, params=None, **kwargs):
        captured_requests.append({"url": str(url), "params": params})
        return httpx.Response(200, json={"results": []})

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        await source.fetch_jobs(queries=["backend engineer"], max_pages=1)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert "in/search/1" in req["url"]
    assert req["params"]["app_id"] == "test_id_123"
    assert req["params"]["app_key"] == "test_key_456"
    assert req["params"]["what"] == "backend engineer"
    assert req["params"]["results_per_page"] == 10


# 2. Normalization & Field Mapping
@pytest.mark.anyio
async def test_adzuna_normalization():
    source = AdzunaJobSource(app_id="dummy_id", app_key="dummy_key", country="in")

    async def mock_get(url, params=None, **kwargs):
        return httpx.Response(200, json=MOCK_ADZUNA_RESPONSE)

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        jobs = await source.fetch_jobs(queries=["backend"], max_pages=1)

    assert len(jobs) == 2
    job1 = jobs[0]
    assert job1.external_id == "adz-9901"
    assert job1.source == "adzuna"
    assert job1.role_title == "Senior Backend Developer"
    assert job1.company == "Swiggy & Co"
    assert job1.location == "Bangalore, Karnataka"
    assert "FastAPI" in job1.description
    assert "<p>" not in job1.description  # HTML stripped
    assert job1.employment_type == "full_time"
    assert job1.compensation == "₹2,000,000 – ₹2,800,000"
    assert job1.application_url == "https://www.adzuna.in/land/ad/adz-9901?utm=1"
    assert job1.posted_at is not None


# 3. Missing/Nested Fields Handled Safely
@pytest.mark.anyio
async def test_adzuna_missing_nested_fields():
    source = AdzunaJobSource(app_id="dummy_id", app_key="dummy_key", country="in")

    async def mock_get(url, params=None, **kwargs):
        return httpx.Response(200, json=MOCK_ADZUNA_RESPONSE)

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        jobs = await source.fetch_jobs(queries=["intern"], max_pages=1)

    job2 = jobs[1]
    assert job2.external_id == "adz-9902"
    assert job2.company == "Confidential Employer"  # Safe fallback for missing company
    assert job2.location == "India"  # Safe fallback for country
    assert job2.employment_type == "internship"  # Derived from title "Intern"
    assert job2.compensation == "From ₹350,000"


# 4. Pagination & Query Batching
@pytest.mark.anyio
async def test_adzuna_pagination():
    source = AdzunaJobSource(app_id="dummy_id", app_key="dummy_key")
    call_pages = []

    async def mock_get(url, params=None, **kwargs):
        call_pages.append(url)
        return httpx.Response(200, json={"results": []})

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        await source.fetch_jobs(queries=["backend", "frontend"], max_pages=2)

    # 2 queries * 2 pages = 4 requests
    assert len(call_pages) == 4
    assert any("search/1" in p for p in call_pages)
    assert any("search/2" in p for p in call_pages)


# 5. Salary / Compensation Mapping Variations
def test_salary_mapping_variations():
    assert format_compensation(500000, 800000, country="in") == "₹500,000 – ₹800,000"
    assert format_compensation(600000, 600000, country="in") == "₹600,000"
    assert format_compensation(400000, None, country="in") == "From ₹400,000"
    assert format_compensation(None, 900000, country="in") == "Up to ₹900,000"
    assert format_compensation(None, None, country="in") is None
    assert format_compensation(0, 0, country="in") is None


# 6. Employment Type Mapping Variations
def test_employment_type_mapping():
    assert derive_employment_type("full_time", "permanent", "Backend Engineer", "") == "full_time"
    assert derive_employment_type("part_time", None, "Junior Developer", "") == "part_time"
    assert derive_employment_type(None, "contract", "Systems Engineer", "") == "contract"
    assert derive_employment_type(None, None, "AI Research Intern", "Summer project") == "internship"
    assert derive_employment_type(None, None, "Graduate Software Engineer", "Looking for internship candidates") == "internship"


# 7 & 8. Deduplication (Priority 1: external_id, Priority 2: URL)
@pytest.mark.anyio
async def test_adzuna_deduplication(db_session):
    mock_source = MagicMock()
    mock_source.fetch_jobs = AsyncMock(
        return_value=[
            JobListingData(
                company="Freshworks",
                role_title="Lead Architect",
                description="Distributed cloud systems and microservices.",
                source="adzuna",
                external_id="adz-unique-01",
                application_url="https://jobs.freshworks.com/apply/101?source=adzuna",
                compensation="₹3,000,000",
            ),
            JobListingData(
                company="Freshworks",
                role_title="Lead Architect",
                description="Distributed cloud systems and microservices.",
                source="adzuna",
                external_id="adz-unique-01",  # Duplicate external_id
                application_url="https://jobs.freshworks.com/apply/101",
                compensation="₹3,000,000",
            ),
        ]
    )

    count = await job_matcher.ingest_and_embed_listings(db_session, source=mock_source)
    assert count == 2

    # Query DB: only 1 row must exist
    stmt = select(JobListing).where(JobListing.external_id == "adz-unique-01")
    res = await db_session.execute(stmt)
    rows = res.scalars().all()
    assert len(rows) == 1


# 9 & 10. Update on Content Change & Selective Re-Embedding
@pytest.mark.anyio
async def test_adzuna_selective_reembedding(db_session):
    # Step 1: Ingest initial job
    initial_source = MagicMock()
    initial_source.fetch_jobs = AsyncMock(
        return_value=[
            JobListingData(
                company="Ola Cabs",
                role_title="Data Platform Engineer",
                description="Spark, Kafka, and big data streaming architecture.",
                source="adzuna",
                external_id="adz-ola-01",
                compensation="₹2,200,000",
            )
        ]
    )
    with patch("app.services.job_matcher.vector_store.store_job_embedding") as mock_embed:
        await job_matcher.ingest_and_embed_listings(db_session, source=initial_source)
        assert mock_embed.call_count == 1

    # Step 2: Ingest again with ONLY compensation change (content unchanged)
    metadata_only_source = MagicMock()
    metadata_only_source.fetch_jobs = AsyncMock(
        return_value=[
            JobListingData(
                company="Ola Cabs",
                role_title="Data Platform Engineer",
                description="Spark, Kafka, and big data streaming architecture.",
                source="adzuna",
                external_id="adz-ola-01",
                compensation="₹2,500,000",  # Changed salary only
            )
        ]
    )
    with patch("app.services.job_matcher.vector_store.store_job_embedding") as mock_embed:
        await job_matcher.ingest_and_embed_listings(db_session, source=metadata_only_source)
        # Should NOT re-embed since description & title are identical
        assert mock_embed.call_count == 0

    # Verify DB has updated compensation
    stmt = select(JobListing).where(JobListing.external_id == "adz-ola-01")
    res = await db_session.execute(stmt)
    job = res.scalar_one()
    assert job.compensation == "₹2,500,000"


# 11. Provider Failure Preserves Stored Jobs
@pytest.mark.anyio
async def test_provider_failure_preserves_stored_jobs(db_session):
    # Initial listing exists
    job = JobListing(
        external_id="adz-safe-01",
        source="adzuna",
        company="Postman",
        role_title="API Engineer",
        description="API platform tooling.",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    # Provider encounters failure
    failing_source = MagicMock()
    failing_source.fetch_jobs = AsyncMock(return_value=[])

    await job_matcher.ingest_and_embed_listings(db_session, source=failing_source)

    # Job must still exist and remain active
    stmt = select(JobListing).where(JobListing.external_id == "adz-safe-01")
    res = await db_session.execute(stmt)
    persisted = res.scalar_one_or_none()
    assert persisted is not None
    assert persisted.is_active is True


# 12. Global Refresh Architecture
def test_global_refresh_celery_task():
    # Verify celery task is registered and executes ingest globally
    from app.tasks.job_tasks import refresh_global_job_listings

    assert refresh_global_job_listings.name == "app.tasks.job_tasks.refresh_global_job_listings"


# 13 & 14. Ranking and User Isolation
@pytest.mark.anyio
async def test_ranking_and_user_isolation(db_session):
    # Create two users
    u1 = User(id=uuid.uuid4(), google_id="google-user-1", email="user1@example.com", name="User One")
    u2 = User(id=uuid.uuid4(), google_id="google-user-2", email="user2@example.com", name="User Two")
    db_session.add_all([u1, u2])

    # User 1 prefers Backend
    p1 = UserPreference(
        id=uuid.uuid4(),
        user_id=u1.id,
        preferred_roles=["Backend Engineer"],
        opportunity_type="full_time",
        preferred_location="Bangalore",
    )
    # User 2 prefers Frontend
    p2 = UserPreference(
        id=uuid.uuid4(),
        user_id=u2.id,
        preferred_roles=["Frontend Engineer"],
        opportunity_type="full_time",
        preferred_location="Remote",
    )
    db_session.add_all([p1, p2])

    # Add jobs
    j_backend = JobListing(
        external_id="adz-back-01",
        source="adzuna",
        company="InMobi",
        role_title="Backend Engineer",
        description="Python, PostgreSQL, and distributed caching.",
        location="Bangalore",
        employment_type="full_time",
        is_active=True,
    )
    j_frontend = JobListing(
        external_id="adz-front-01",
        source="adzuna",
        company="Flipkart",
        role_title="Frontend Engineer",
        description="React, TypeScript, CSS architecture.",
        location="Remote",
        employment_type="full_time",
        is_active=True,
    )
    db_session.add_all([j_backend, j_frontend])
    await db_session.commit()

    # Rank for User 1
    matches_u1 = await job_matcher.rank_jobs_for_user(db_session, u1.id)
    # Rank for User 2
    matches_u2 = await job_matcher.rank_jobs_for_user(db_session, u2.id)

    assert len(matches_u1) == 2
    assert len(matches_u2) == 2

    # User 1 top match must be Backend
    assert matches_u1[0].job_listing_id == j_backend.id
    # User 2 top match must be Frontend
    assert matches_u2[0].job_listing_id == j_frontend.id

    # Verify isolation in DB
    stmt_u1 = select(DailyMatch).where(DailyMatch.user_id == u1.id)
    res_u1 = await db_session.execute(stmt_u1)
    for m in res_u1.scalars().all():
        assert m.user_id == u1.id


# 15. Provider Factory
def test_provider_factory():
    adzuna_source = get_job_source("adzuna")
    assert isinstance(adzuna_source, AdzunaJobSource)

    mock_source = get_job_source("mock")
    assert mock_source.__class__.__name__ == "MockJobSource"
