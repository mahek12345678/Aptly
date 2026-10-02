"""Unit and integration tests for Aptly Voice Assistant endpoints and services."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.application import ApplicationStatus, JobApplication, TrackingState
from app.models.job_match import DailyMatch, JobListing
from app.models.resume import Resume
from app.models.user import User
from app.services.assistant_context import (
    get_application_progress_context,
    get_briefing_context,
    get_matches_context,
    get_resume_skill_context,
    get_upcoming_deadlines_context,
)
from app.services.tts_service import generate_speech
from tests.conftest import TestingSessionLocal


async def create_user_helper(email: str = "assistant_user@example.com", name: str = "Assistant Tester") -> tuple[User, str]:
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name=name,
            onboarding_completed=True,
            onboarding_step=4,
        )
        session.add(user)
        await session.commit()
    token = create_access_token(data={"sub": str(user_id)})
    return user, token


# ---------------------------------------------------------------------------
# 1. Authentication & Route Security
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_unauthenticated_assistant_endpoints_fail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/api/v1/assistant/query", json={"message": "What is my status?"})
        assert r1.status_code == 401

        r2 = await ac.get("/api/v1/assistant/briefing")
        assert r2.status_code == 401

        r3 = await ac.post("/api/v1/assistant/speech", json={"text": "Hello world"})
        assert r3.status_code == 401


# ---------------------------------------------------------------------------
# 2. Context Retrieval & Canonical Statuses
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_assistant_context_canonical_statuses_and_zero_state():
    user, _ = await create_user_helper("ctx_zero@example.com", "Zero Context")

    async with TestingSessionLocal() as session:
        ctx = await get_briefing_context(session, user.id)
        assert ctx["has_data"] is False
        assert ctx["active_matches_count"] == 0
        assert ctx["applications_total"] == 0
        assert ctx["replies_received"] == 0
        assert ctx["status_counts"] == {"applied": 0, "oa": 0, "interview": 0, "offer": 0, "rejected": 0}


@pytest.mark.anyio
async def test_assistant_context_pipeline_and_deadlines():
    user, _ = await create_user_helper("ctx_pipeline@example.com", "Pipeline User")
    now = datetime.now(timezone.utc)

    async with TestingSessionLocal() as session:
        # Create applications with various canonical statuses
        apps = [
            JobApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                company="Google",
                role="Software Engineer",
                status=ApplicationStatus.APPLIED.value,
                tracking_state=TrackingState.APPLIED.value,
                deadline=now + timedelta(days=2),
                created_at=now,
            ),
            JobApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                company="Meta",
                role="Production Engineer",
                status=ApplicationStatus.OA.value,
                tracking_state=TrackingState.APPLIED.value,
                deadline=now + timedelta(days=4),
                created_at=now,
            ),
            JobApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                company="Apple",
                role="iOS Developer",
                status=ApplicationStatus.INTERVIEW.value,
                tracking_state=TrackingState.APPLIED.value,
                deadline=now + timedelta(days=10),  # beyond 7 days
                created_at=now,
            ),
            JobApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                company="Stripe",
                role="Backend Engineer",
                status=ApplicationStatus.OFFER.value,
                tracking_state=TrackingState.APPLIED.value,
                created_at=now,
            ),
            JobApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                company="Netflix",
                role="Systems Engineer",
                status=ApplicationStatus.REJECTED.value,
                tracking_state=TrackingState.APPLIED.value,
                created_at=now,
            ),
            # Pending confirmation intent
            JobApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                company="Uber",
                role="Infra Engineer",
                status=ApplicationStatus.APPLIED.value,
                tracking_state=TrackingState.APPLICATION_STARTED.value,
                created_at=now,
            ),
        ]
        session.add_all(apps)

        # Create a JobListing and DailyMatch
        listing = JobListing(
            id=uuid.uuid4(),
            company="Datadog",
            role_title="Observability Engineer",
            description="Build robust telemetry pipelines.",
            source="mock",
            created_at=now,
            updated_at=now,
        )
        session.add(listing)
        await session.flush()

        match = DailyMatch(
            id=uuid.uuid4(),
            user_id=user.id,
            job_listing_id=listing.id,
            similarity_score=0.92,
            preference_score=0.88,
            final_score=0.90,
            match_reasons=["Matches Python skill", "Target role alignment"],
            dismissed=False,
            saved=True,
            matched_at=now,
        )
        session.add(match)

        # Resume with skills
        resume = Resume(
            id=uuid.uuid4(),
            user_id=user.id,
            file_name="resume.pdf",
            file_path="/uploads/resumes/resume.pdf",
            extracted_text="Experienced in Python, PostgreSQL, and Distributed Systems.",
            parsed_status="parsed",
            parsed_data={"skills": ["Python", "PostgreSQL", "Docker"]},
            created_at=now,
        )
        session.add(resume)
        await session.commit()

        # Test briefing context
        ctx = await get_briefing_context(session, user.id)
        assert ctx["has_data"] is True
        assert ctx["active_matches_count"] == 1
        assert ctx["top_matches"][0]["company"] == "Datadog"
        assert ctx["top_matches"][0]["score_pct"] == 90
        assert ctx["applications_total"] == 5  # Confirmed apps
        assert ctx["pending_confirmations_count"] == 1  # 1 application_started
        # Replies received = oa (1) + interview (1) + offer (1) + rejected (1) = 4
        assert ctx["replies_received"] == 4
        assert ctx["offers_count"] == 1
        assert ctx["oa_count"] == 1
        assert ctx["interview_count"] == 1
        # Upcoming deadlines in 7 days: Google (2d) and Meta (4d) -> 2
        assert ctx["upcoming_deadlines_7d_count"] == 2

        # Test deadlines context
        deadlines_ctx = await get_upcoming_deadlines_context(session, user.id)
        assert len(deadlines_ctx["upcoming_deadlines_next_7_days"]) == 2
        assert len(deadlines_ctx["upcoming_deadlines_next_14_days"]) == 3
        assert len(deadlines_ctx["active_oa_assessments"]) == 1
        assert len(deadlines_ctx["active_interviews"]) == 1

        # Test matches context
        matches_ctx = await get_matches_context(session, user.id)
        assert matches_ctx["matches_count"] == 1
        assert matches_ctx["top_matches"][0]["company"] == "Datadog"

        # Test application progress context
        prog_ctx = await get_application_progress_context(session, user.id)
        assert prog_ctx["total_confirmed_applications"] == 5
        assert prog_ctx["replies_received"] == 4
        assert prog_ctx["offers"] == 1

        # Test resume skill verification context
        skill_ctx_py = await get_resume_skill_context(session, user.id, "Python")
        assert skill_ctx_py["skill_found"] is True
        assert skill_ctx_py["verified_in_skills_section"] is True

        skill_ctx_rust = await get_resume_skill_context(session, user.id, "Rust")
        assert skill_ctx_rust["skill_found"] is False


# ---------------------------------------------------------------------------
# 3. User Isolation
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_assistant_user_isolation():
    user_a, token_a = await create_user_helper("user_a@example.com", "Alice User")
    user_b, token_b = await create_user_helper("user_b@example.com", "Bob User")

    now = datetime.now(timezone.utc)
    async with TestingSessionLocal() as session:
        # Give User A an application and a match
        app_a = JobApplication(
            id=uuid.uuid4(),
            user_id=user_a.id,
            company="Confidential A Corp",
            role="Lead Engineer",
            status=ApplicationStatus.OFFER.value,
            tracking_state=TrackingState.APPLIED.value,
            created_at=now,
        )
        session.add(app_a)
        await session.commit()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User B fetches briefing
        res_b = await ac.get("/api/v1/assistant/briefing", headers=headers_b)
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["summary"]["active_matches_count"] == 0
        assert data_b["summary"]["top_matches"] == []
        assert "Confidential A Corp" not in data_b["answer"]

        # User A fetches briefing
        res_a = await ac.get("/api/v1/assistant/briefing", headers=headers_a)
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["summary"]["pending_confirmations_count"] == 0


# ---------------------------------------------------------------------------
# 4. Assistant Query & Suggested Actions Flow
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_assistant_query_endpoints_and_actions():
    user, token = await create_user_helper("query_flow@example.com", "Query Flow User")
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.llm_service.llm_service.generate_text", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "You currently have 2 deadlines coming up this week for Google and Meta."

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/assistant/query",
                json={"message": "What deadlines do I have coming up?"},
                headers=headers,
            )
            assert res.status_code == 200
            data = res.json()
            assert data["intent"] == "deadlines"
            assert "Google and Meta" in data["answer"]
            assert "suggested_actions" in data
            assert len(data["suggested_actions"]) > 0
            # Ensure actions link only to valid routes
            valid_routes = {"/track-jobs", "/find-positions", "/jd-analyzer", "/dashboard", "/onboarding/resume"}
            for action in data["suggested_actions"]:
                assert action["route"] in valid_routes


# ---------------------------------------------------------------------------
# 5. ElevenLabs Service & Error Fallbacks
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_elevenlabs_service_unconfigured():
    # When ElevenLabs is unconfigured (empty credentials), it raises 503 cleanly
    with patch.object(settings, "ELEVENLABS_API_KEY", ""):
        with pytest.raises(Exception) as exc_info:
            generate_speech("Testing voice synthesis")
        assert "503" in str(exc_info.value)


@pytest.mark.anyio
async def test_assistant_speech_endpoint_and_failure_tolerance():
    user, token = await create_user_helper("tts_flow@example.com", "TTS User")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test missing text validation
        bad_req = await ac.post("/api/v1/assistant/speech", json={"text": ""}, headers=headers)
        assert bad_req.status_code == 422  # pydantic min_length validation

        # Test ElevenLabs unconfigured returns 503 without crashing app
        with patch.object(settings, "ELEVENLABS_API_KEY", ""):
            speech_res = await ac.post("/api/v1/assistant/speech", json={"text": "Hello world"}, headers=headers)
            assert speech_res.status_code == 503
            assert "Voice service unavailable" in speech_res.json()["detail"]

        # Text assistant continues to work even if voice is unavailable
        with patch("app.services.llm_service.llm_service.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Text answer works independently."
            query_res = await ac.post("/api/v1/assistant/query", json={"message": "Status?"}, headers=headers)
            assert query_res.status_code == 200
            assert query_res.json()["answer"] == "Text answer works independently."


# ---------------------------------------------------------------------------
# 6. Speech Rate Limiting & 429 Handling
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_speech_rate_limiter_clean_429():
    from app.api.v1.endpoints.assistant import speech_rate_limit_callback
    from starlette.requests import Request
    from starlette.responses import Response

    mock_req = MagicMock(spec=Request)
    mock_resp = MagicMock(spec=Response)

    with pytest.raises(Exception) as exc_info:
        await speech_rate_limit_callback(mock_req, mock_resp, pexpire=15000)

    exc = exc_info.value
    assert exc.status_code == 429
    assert "Speech generation limit reached" in exc.detail
    assert exc.headers.get("Retry-After") == "15"


@pytest.mark.anyio
async def test_api_keys_never_exposed_in_briefing_or_query():
    user, token = await create_user_helper("security_test@example.com", "Security User")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/assistant/briefing", headers=headers)
        assert res.status_code == 200
        text = res.text
        assert settings.GROQ_API_KEY not in text
        if settings.ELEVENLABS_API_KEY:
            assert settings.ELEVENLABS_API_KEY not in text
