import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.models.user import User
from tests.conftest import TestingSessionLocal


async def create_user_helper(
    email: str = "matching_user@example.com",
    name: str = "Matching Tester",
    preferred_roles: list[str] = None,
    opportunity_type: str = "full_time",
    preferred_location: str = "San Francisco, CA",
) -> tuple[User, str]:
    if preferred_roles is None:
        preferred_roles = ["Backend Engineer"]

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
        await session.flush()

        pref = UserPreference(
            user_id=user_id,
            user_type="professional",
            opportunity_type=opportunity_type,
            preferred_location=preferred_location,
            preferred_roles=preferred_roles,
            interests=["Distributed Systems", "Cloud"],
            focus_opportunity_matching=True,
        )
        session.add(pref)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return user, token


async def create_parsed_resume_helper(
    user_id: uuid.UUID,
    skills: list[str] = None,
    experience: list[str] = None,
) -> Resume:
    if skills is None:
        skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"]
    if experience is None:
        experience = [
            "Senior Backend Engineer: Designed scalable APIs and data pipelines using Python and PostgreSQL.",
        ]

    parsed_data = {
        "name": "Candidate Doe",
        "email": "cand@example.com",
        "skills": skills,
        "experience": experience,
        "projects": ["Distributed task queue in Python with Redis and PostgreSQL."],
        "raw_text": f"Skills: {', '.join(skills)}",
    }

    now = datetime.now(timezone.utc)
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        file_name="candidate_resume.pdf",
        file_path="/uploads/resumes/candidate_resume.pdf",
        extracted_text=parsed_data["raw_text"],
        parsed_status="parsed",
        parsed_at=now,
        parsed_data=parsed_data,
        created_at=now,
    )

    async with TestingSessionLocal() as session:
        session.add(resume)
        await session.commit()
        await session.refresh(resume)

    return resume


@pytest.mark.anyio
async def test_unauthenticated_jobs_endpoints_fail():
    match_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.get("/api/v1/jobs/matches")
        assert r1.status_code == 401

        r2 = await ac.post("/api/v1/jobs/matches/refresh")
        assert r2.status_code == 401

        r3 = await ac.post(f"/api/v1/jobs/matches/{match_id}/save")
        assert r3.status_code == 401

        r4 = await ac.post(f"/api/v1/jobs/matches/{match_id}/dismiss")
        assert r4.status_code == 401


@pytest.mark.anyio
async def test_job_source_ingestion_and_refresh():
    user, token = await create_user_helper("refresh_test@example.com", "Refresh User")
    await create_parsed_resume_helper(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Trigger refresh
        refresh_res = await ac.post("/api/v1/jobs/matches/refresh", headers=headers)
        assert refresh_res.status_code == 200
        ref_data = refresh_res.json()
        assert ref_data["refreshed_count"] >= 10
        assert ref_data["matches_count"] >= 10
        assert "refreshed_at" in ref_data

        # 2. Ingest again (should skip re-embedding already embedded listings)
        refresh_again = await ac.post("/api/v1/jobs/matches/refresh", headers=headers)
        assert refresh_again.status_code == 200


@pytest.mark.anyio
async def test_hybrid_ranking_algorithm_and_reasons():
    # User targeted at Backend Engineer in San Francisco with Python & PostgreSQL skills
    user, token = await create_user_helper(
        email="backend_target@example.com",
        name="Backend Spec",
        preferred_roles=["Backend Engineer"],
        opportunity_type="full_time",
        preferred_location="San Francisco, CA",
    )
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "PostgreSQL", "Docker", "REST API", "FastAPI"],
        experience=["Built high-throughput backend services in Python and PostgreSQL at tech scale."],
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # List matches
        res = await ac.get("/api/v1/jobs/matches", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        assert len(data["items"]) > 0

        # Check top match
        top_match = data["items"][0]
        assert top_match["final_score"] >= 65
        # Reasons should be factual and not empty
        assert len(top_match["match_reasons"]) > 0

        # Verify Stripe or Backend listing is ranked highly near top
        top_roles = [m["job"]["role_title"] for m in data["items"][:3]]
        assert any("Backend" in r or "Systems" in r for r in top_roles)

        # Check pagination & limits
        paged_res = await ac.get("/api/v1/jobs/matches?limit=3&page=1", headers=headers)
        assert paged_res.status_code == 200
        assert len(paged_res.json()["items"]) == 3


@pytest.mark.anyio
async def test_save_and_dismiss_and_user_isolation():
    user_a, token_a = await create_user_helper("user_a_jobs@example.com", "User A")
    user_b, token_b = await create_user_helper("user_b_jobs@example.com", "User B")

    await create_parsed_resume_helper(user_a.id)
    await create_parsed_resume_helper(user_b.id)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User A loads matches
        res_a = await ac.get("/api/v1/jobs/matches", headers=headers_a)
        assert res_a.status_code == 200
        items_a = res_a.json()["items"]
        match_id_a = items_a[0]["id"]

        # User B cannot save User A's match (404)
        save_other = await ac.post(f"/api/v1/jobs/matches/{match_id_a}/save", headers=headers_b)
        assert save_other.status_code == 404

        # User A saves match
        save_res = await ac.post(f"/api/v1/jobs/matches/{match_id_a}/save", headers=headers_a)
        assert save_res.status_code == 200
        assert save_res.json()["saved"] is True

        # User A queries saved_only
        saved_list = await ac.get("/api/v1/jobs/matches?saved_only=true", headers=headers_a)
        assert saved_list.status_code == 200
        assert len(saved_list.json()["items"]) == 1
        assert saved_list.json()["items"][0]["id"] == match_id_a

        # User A dismisses match
        dismiss_res = await ac.post(f"/api/v1/jobs/matches/{match_id_a}/dismiss", headers=headers_a)
        assert dismiss_res.status_code == 200
        assert dismiss_res.json()["dismissed"] is True

        # Dismissed match is now excluded from active matches
        active_list = await ac.get("/api/v1/jobs/matches", headers=headers_a)
        active_ids = [m["id"] for m in active_list.json()["items"]]
        assert match_id_a not in active_ids


@pytest.mark.anyio
async def test_dashboard_match_count_sync():
    user, token = await create_user_helper("dash_match_user@example.com", "Dash Match User")
    await create_parsed_resume_helper(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Refresh matches
        await ac.post("/api/v1/jobs/matches/refresh", headers=headers)

        # Query dashboard
        dash_res = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert dash_res.status_code == 200
        data = dash_res.json()
        assert "job_matches_count" in data
        assert data["job_matches_count"] >= 10
