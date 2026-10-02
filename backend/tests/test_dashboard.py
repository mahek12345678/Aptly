import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.application import JobApplication
from app.models.user import User
from tests.conftest import TestingSessionLocal


async def create_user_helper(email: str = "dash_user@example.com", name: str = "Alice Walker") -> tuple[User, str]:
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


@pytest.mark.anyio
async def test_dashboard_unauthenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/dashboard/summary")
        assert response.status_code == 401


@pytest.mark.anyio
async def test_dashboard_empty_state():
    user, token = await create_user_helper("empty_dash@example.com", "Sarah Connor")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["user"]["first_name"] == "Sarah"
        assert data["user"]["name"] == "Sarah Connor"
        assert data["metrics"]["jobs_applied"] == 0
        assert data["metrics"]["replies_received"] == 0
        assert data["metrics"]["offers_received"] == 0
        assert "rejected" not in data["metrics"]
        assert "rejections" not in data["metrics"]
        assert data["recent_activity"] == []
        assert data["upcoming_reminders"] == []


@pytest.mark.anyio
async def test_dashboard_metrics_and_user_isolation():
    now = datetime.now(timezone.utc)
    user_a, token_a = await create_user_helper("alice@example.com", "Alice Smith")
    user_b, token_b = await create_user_helper("bob@example.com", "Bob Jones")

    async with TestingSessionLocal() as session:
        # User A's applications:
        # 1. applied
        # 2. oa (replies_received) + deadline in 3 days (upcoming reminder)
        # 3. interview (replies_received) + deadline in 5 days (upcoming reminder)
        # 4. offer (replies_received + offers_received)
        # 5. rejected (replies_received)
        app1 = JobApplication(
            user_id=user_a.id,
            company="Stripe",
            role="Backend Engineer",
            status="applied",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        )
        app2 = JobApplication(
            user_id=user_a.id,
            company="Google",
            role="Software Engineer",
            status="oa",
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=2),
            deadline=now + timedelta(days=3),
        )
        app3 = JobApplication(
            user_id=user_a.id,
            company="Datadog",
            role="Distributed Systems Engineer",
            status="interview",
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=1),
            deadline=now + timedelta(days=5),
        )
        app4 = JobApplication(
            user_id=user_a.id,
            company="Figma",
            role="Product Engineer",
            status="offer",
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(hours=2),
        )
        app5 = JobApplication(
            user_id=user_a.id,
            company="Meta",
            role="Production Engineer",
            status="rejected",
            created_at=now - timedelta(days=12),
            updated_at=now - timedelta(days=8),
        )

        # User B's application (should NOT leak to User A)
        app_other = JobApplication(
            user_id=user_b.id,
            company="Apple",
            role="iOS Engineer",
            status="offer",
            created_at=now,
            updated_at=now,
            deadline=now + timedelta(days=1),
        )

        session.add_all([app1, app2, app3, app4, app5, app_other])
        await session.commit()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/dashboard/summary", headers=headers_a)
        assert response.status_code == 200

        data = response.json()
        assert data["user"]["first_name"] == "Alice"
        metrics = data["metrics"]
        # Total applied = 5
        assert metrics["jobs_applied"] == 5
        # Replies (progressed beyond applied): oa, interview, offer, rejected = 4
        assert metrics["replies_received"] == 4
        # Offers: 1
        assert metrics["offers_received"] == 1
        # Headline metrics MUST NOT have rejection
        assert "rejected" not in metrics
        assert "rejections" not in metrics

        # Recent activity ordered by updated_at DESC
        activity = data["recent_activity"]
        assert len(activity) == 5
        assert activity[0]["company"] == "Figma"
        assert activity[0]["role"] == "Product Engineer"
        assert activity[0]["raw_status"] == "offer"
        assert activity[0]["status"] == "Offer Received"

        assert activity[1]["company"] == "Datadog"
        assert activity[1]["raw_status"] == "interview"
        assert activity[1]["status"] == "Interview"

        assert activity[2]["company"] == "Google"
        assert activity[2]["raw_status"] == "oa"
        assert activity[2]["status"] == "OA/Assessment"

        assert activity[3]["company"] == "Stripe"
        assert activity[3]["raw_status"] == "applied"
        assert activity[3]["status"] == "Applied"

        assert activity[4]["company"] == "Meta"
        assert activity[4]["raw_status"] == "rejected"
        assert activity[4]["status"] == "Rejected"

        # Reminders within 7 days for User A
        reminders = data["upcoming_reminders"]
        assert len(reminders) == 2
        companies = [r["company"] for r in reminders]
        assert "Google" in companies
        assert "Datadog" in companies
        assert "Apple" not in companies
