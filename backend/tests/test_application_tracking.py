"""Tests for Aptly's automatic application-intent tracking flow."""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models.application import ApplicationStatus, JobApplication, TrackingState
from app.models.user import User
from tests.conftest import TestingSessionLocal


async def create_tracking_user(prefix: str = "track") -> tuple[User, str]:
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=f"{prefix}_{user_id.hex[:6]}@example.com",
            name="Tracking Test User",
            onboarding_completed=True,
            onboarding_step=4,
        )
        session.add(user)
        await session.commit()
    token = create_access_token(data={"sub": str(user_id)})
    return user, token


@pytest.mark.anyio
async def test_unauthenticated_tracking_endpoints_fail():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start
        res = await client.post(
            "/api/v1/applications/start",
            json={"company": "Acme", "role": "Engineer"},
        )
        assert res.status_code == 401

        # Pending
        res = await client.get("/api/v1/applications/pending")
        assert res.status_code == 401

        # Confirm & Not yet
        fake_id = str(uuid.uuid4())
        res = await client.post(f"/api/v1/applications/{fake_id}/confirm-applied")
        assert res.status_code == 401

        res = await client.post(f"/api/v1/applications/{fake_id}/not-yet")
        assert res.status_code == 401


@pytest.mark.anyio
async def test_start_application_creates_application_started():
    user, token = await create_tracking_user("start_user")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start_payload = {
            "company": "Stripe",
            "role": "Backend Engineer",
            "location": "San Francisco, CA (Hybrid)",
            "compensation": "$175k - $210k",
            "job_description": "Build high-throughput global payment APIs.",
            "application_url": "https://stripe.com/jobs/backend-eng-101",
            "source": "Job Matching",
            "source_job_id": "stripe-backend-101",
        }

        res = await client.post(
            "/api/v1/applications/start",
            json=start_payload,
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["company"] == "Stripe"
        assert data["role"] == "Backend Engineer"
        assert data["tracking_state"] == "application_started"
        assert data["application_started_at"] is not None
        assert data["applied_at"] is None
        assert data["source_job_id"] == "stripe-backend-101"
        assert data["application_url"] == "https://stripe.com/jobs/backend-eng-101"

        app_id = data["id"]

        # Verify DB directly
        async with TestingSessionLocal() as session:
            db_app = await session.get(JobApplication, uuid.UUID(app_id))
            assert db_app is not None
            assert db_app.tracking_state == TrackingState.APPLICATION_STARTED.value
            assert db_app.application_started_at is not None
            assert db_app.applied_at is None


@pytest.mark.anyio
async def test_duplicate_prevention_by_job_id_and_url():
    user, token = await create_tracking_user("dup_user")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call with source_job_id
        res1 = await client.post(
            "/api/v1/applications/start",
            json={
                "company": "Datadog",
                "role": "Software Engineer",
                "application_url": "https://datadog.com/careers/se-1",
                "source_job_id": "datadog-se-1",
            },
            headers=headers,
        )
        assert res1.status_code == 200
        id1 = res1.json()["id"]

        # Second call with the same source_job_id
        res2 = await client.post(
            "/api/v1/applications/start",
            json={
                "company": "Datadog",
                "role": "Software Engineer",
                "application_url": "https://datadog.com/careers/se-1-diff",
                "source_job_id": "datadog-se-1",
            },
            headers=headers,
        )
        assert res2.status_code == 200
        assert res2.json()["id"] == id1

        # Third call with same URL (with trailing slash) and no source_job_id
        res3 = await client.post(
            "/api/v1/applications/start",
            json={
                "company": "Datadog",
                "role": "Software Engineer",
                "application_url": "https://datadog.com/careers/se-1/",
                "source_job_id": None,
            },
            headers=headers,
        )
        assert res3.status_code == 200
        assert res3.json()["id"] == id1

        # Verify only 1 application row exists for Datadog in database
        async with TestingSessionLocal() as session:
            stmt = select(JobApplication).where(
                JobApplication.user_id == user.id,
                JobApplication.company == "Datadog",
            )
            result = await session.execute(stmt)
            apps = result.scalars().all()
            assert len(apps) == 1


@pytest.mark.anyio
async def test_confirm_applied_and_not_yet_flow():
    user, token = await create_tracking_user("conf_user")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start application
        res = await client.post(
            "/api/v1/applications/start",
            json={
                "company": "Figma",
                "role": "Systems Engineer",
                "application_url": "https://figma.com/careers/systems",
                "source_job_id": "figma-sys",
            },
            headers=headers,
        )
        app_id = res.json()["id"]

        # Call not-yet
        ny_res = await client.post(
            f"/api/v1/applications/{app_id}/not-yet",
            headers=headers,
        )
        assert ny_res.status_code == 200
        assert ny_res.json()["tracking_state"] == "application_started"
        assert ny_res.json()["applied_at"] is None

        # Confirm applied
        conf_res = await client.post(
            f"/api/v1/applications/{app_id}/confirm-applied",
            headers=headers,
        )
        assert conf_res.status_code == 200
        conf_data = conf_res.json()
        assert conf_data["tracking_state"] == "applied"
        assert conf_data["status"] == "applied"
        assert conf_data["applied_at"] is not None


@pytest.mark.anyio
async def test_pending_endpoint_and_user_isolation():
    user1, token1 = await create_tracking_user("user1")
    user2, token2 = await create_tracking_user("user2")
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User 1 starts an application
        res1 = await client.post(
            "/api/v1/applications/start",
            json={
                "company": "Linear",
                "role": "Fullstack Engineer",
                "application_url": "https://linear.app/careers/fullstack",
                "source_job_id": "linear-fs",
            },
            headers=headers1,
        )
        user1_app_id = res1.json()["id"]

        # User 2 lists pending - should NOT see User 1's pending application
        u2_pending = await client.get(
            "/api/v1/applications/pending",
            headers=headers2,
        )
        assert u2_pending.status_code == 200
        assert not any(app["id"] == user1_app_id for app in u2_pending.json())

        # User 2 attempts to confirm User 1's application - must 404
        u2_hijack = await client.post(
            f"/api/v1/applications/{user1_app_id}/confirm-applied",
            headers=headers2,
        )
        assert u2_hijack.status_code == 404

        # User 1 lists pending - sees it
        u1_pending = await client.get(
            "/api/v1/applications/pending",
            headers=headers1,
        )
        assert u1_pending.status_code == 200
        assert any(app["id"] == user1_app_id for app in u1_pending.json())


@pytest.mark.anyio
async def test_dashboard_and_kanban_exclude_unconfirmed_applications():
    user, token = await create_tracking_user("dash_user")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check initial dashboard metrics
        dash_initial = await client.get(
            "/api/v1/dashboard/summary",
            headers=headers,
        )
        assert dash_initial.status_code == 200
        initial_applied_count = dash_initial.json()["metrics"]["jobs_applied"]

        # User starts application (NOT yet confirmed)
        res_start = await client.post(
            "/api/v1/applications/start",
            json={
                "company": "OpenAI",
                "role": "Research Engineer",
                "application_url": "https://openai.com/careers/re",
                "source_job_id": "openai-re",
            },
            headers=headers,
        )
        app_id = res_start.json()["id"]

        # 1. Kanban list endpoint (GET /api/v1/applications) must EXCLUDE unconfirmed application
        kanban_res = await client.get(
            "/api/v1/applications",
            headers=headers,
        )
        assert kanban_res.status_code == 200
        assert not any(a["id"] == app_id for a in kanban_res.json())

        # 2. Dashboard summary must NOT increment jobs_applied
        dash_after_start = await client.get(
            "/api/v1/dashboard/summary",
            headers=headers,
        )
        assert dash_after_start.status_code == 200
        assert dash_after_start.json()["metrics"]["jobs_applied"] == initial_applied_count
        # Recent activity must NOT include the started application
        assert not any(
            act["id"] == app_id for act in dash_after_start.json()["recent_activity"]
        )

        # 3. User confirms application
        confirm_res = await client.post(
            f"/api/v1/applications/{app_id}/confirm-applied",
            headers=headers,
        )
        assert confirm_res.status_code == 200

        # 4. Now Kanban list endpoint MUST include the confirmed application
        kanban_after = await client.get(
            "/api/v1/applications",
            headers=headers,
        )
        assert kanban_after.status_code == 200
        assert any(a["id"] == app_id for a in kanban_after.json())

        # 5. Dashboard summary now reflects the confirmed application
        dash_after_confirm = await client.get(
            "/api/v1/dashboard/summary",
            headers=headers,
        )
        assert dash_after_confirm.status_code == 200
        assert (
            dash_after_confirm.json()["metrics"]["jobs_applied"]
            == initial_applied_count + 1
        )
        assert any(
            act["id"] == app_id for act in dash_after_confirm.json()["recent_activity"]
        )
