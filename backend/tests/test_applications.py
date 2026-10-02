import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.application import JobApplication
from app.models.user import User
from tests.conftest import TestingSessionLocal


async def create_user_helper(email: str = "app_user@example.com", name: str = "Test Developer") -> tuple[User, str]:
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
async def test_unauthenticated_applications_endpoints_fail():
    app_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.get("/api/v1/applications")
        assert r1.status_code == 401

        r2 = await ac.post("/api/v1/applications", json={"company": "Acme", "role": "Eng"})
        assert r2.status_code == 401

        r3 = await ac.get(f"/api/v1/applications/{app_id}")
        assert r3.status_code == 401

        r4 = await ac.patch(f"/api/v1/applications/{app_id}", json={"status": "interview"})
        assert r4.status_code == 401

        r5 = await ac.delete(f"/api/v1/applications/{app_id}")
        assert r5.status_code == 401


@pytest.mark.anyio
async def test_create_application():
    user, token = await create_user_helper("create_test@example.com", "Dev Alice")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "company": "Linear",
        "role": "Full Stack Engineer",
        "location": "San Francisco, CA (Hybrid)",
        "stipend": "$160k - $190k",
        "status": "applied",
        "application_url": "https://jobs.linear.app/123",
        "notes": "Referred by Sarah from design team",
        "source": "Company Website",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/applications", json=payload, headers=headers)
        assert response.status_code == 201

        data = response.json()
        assert data["company"] == "Linear"
        assert data["role"] == "Full Stack Engineer"
        assert data["location"] == "San Francisco, CA (Hybrid)"
        assert data["stipend"] == "$160k - $190k"
        assert data["status"] == "applied"
        assert data["application_url"] == "https://jobs.linear.app/123"
        assert data["notes"] == "Referred by Sarah from design team"
        assert data["source"] == "Company Website"
        assert data["user_id"] == str(user.id)
        assert "id" in data


@pytest.mark.anyio
async def test_create_application_validation():
    user, token = await create_user_helper("valid_test@example.com", "Dev Bob")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Missing company
        r1 = await ac.post("/api/v1/applications", json={"role": "Engineer"}, headers=headers)
        assert r1.status_code == 422

        # Empty company
        r2 = await ac.post("/api/v1/applications", json={"company": "   ", "role": "Engineer"}, headers=headers)
        assert r2.status_code == 422

        # Invalid status (e.g. wishlist not allowed)
        r3 = await ac.post(
            "/api/v1/applications",
            json={"company": "Meta", "role": "Staff Engineer", "status": "wishlist"},
            headers=headers,
        )
        assert r3.status_code == 422


@pytest.mark.anyio
async def test_list_applications_user_isolation():
    user_a, token_a = await create_user_helper("iso_a@example.com", "User A")
    user_b, token_b = await create_user_helper("iso_b@example.com", "User B")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User A creates 2 applications
        await ac.post("/api/v1/applications", json={"company": "Company A1", "role": "Role 1"}, headers=headers_a)
        await ac.post("/api/v1/applications", json={"company": "Company A2", "role": "Role 2"}, headers=headers_a)

        # User B creates 1 application
        await ac.post("/api/v1/applications", json={"company": "Company B1", "role": "Role 3"}, headers=headers_b)

        # User A lists applications
        res_a = await ac.get("/api/v1/applications", headers=headers_a)
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert len(data_a) == 2
        companies_a = [x["company"] for x in data_a]
        assert "Company A1" in companies_a
        assert "Company A2" in companies_a
        assert "Company B1" not in companies_a

        # User B lists applications
        res_b = await ac.get("/api/v1/applications", headers=headers_b)
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert len(data_b) == 1
        assert data_b[0]["company"] == "Company B1"


@pytest.mark.anyio
async def test_search_and_filter_applications():
    user, token = await create_user_helper("search_test@example.com", "Search User")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/applications", json={"company": "Netflix", "role": "Systems Engineer", "status": "applied"}, headers=headers)
        await ac.post("/api/v1/applications", json={"company": "Spotify", "role": "Backend Engineer", "status": "interview"}, headers=headers)
        await ac.post("/api/v1/applications", json={"company": "Apple", "role": "iOS Developer", "status": "interview"}, headers=headers)

        # Filter by status: interview
        res_status = await ac.get("/api/v1/applications?status=interview", headers=headers)
        assert res_status.status_code == 200
        assert len(res_status.json()) == 2

        # Search by company
        res_search_co = await ac.get("/api/v1/applications?search=netfl", headers=headers)
        assert res_search_co.status_code == 200
        assert len(res_search_co.json()) == 1
        assert res_search_co.json()[0]["company"] == "Netflix"

        # Search by role
        res_search_role = await ac.get("/api/v1/applications?search=developer", headers=headers)
        assert res_search_role.status_code == 200
        assert len(res_search_role.json()) == 1
        assert res_search_role.json()[0]["company"] == "Apple"


@pytest.mark.anyio
async def test_get_patch_and_delete_application():
    user_a, token_a = await create_user_helper("crud_a@example.com", "CRUD User A")
    user_b, token_b = await create_user_helper("crud_b@example.com", "CRUD User B")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User A creates application
        create_res = await ac.post(
            "/api/v1/applications",
            json={"company": "Airbnb", "role": "Frontend Engineer", "status": "applied"},
            headers=headers_a,
        )
        app_id = create_res.json()["id"]

        # User A can get it
        get_res = await ac.get(f"/api/v1/applications/{app_id}", headers=headers_a)
        assert get_res.status_code == 200
        assert get_res.json()["company"] == "Airbnb"

        # User B CANNOT get it (404)
        get_other = await ac.get(f"/api/v1/applications/{app_id}", headers=headers_b)
        assert get_other.status_code == 404

        # User A moves status to oa (drag-and-drop PATCH)
        patch_res = await ac.patch(
            f"/api/v1/applications/{app_id}",
            json={"status": "oa", "notes": "Received HackerRank test"},
            headers=headers_a,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "oa"
        assert patch_res.json()["notes"] == "Received HackerRank test"

        # User B CANNOT patch it (404)
        patch_other = await ac.patch(
            f"/api/v1/applications/{app_id}",
            json={"status": "rejected"},
            headers=headers_b,
        )
        assert patch_other.status_code == 404

        # User B CANNOT delete it (404)
        del_other = await ac.delete(f"/api/v1/applications/{app_id}", headers=headers_b)
        assert del_other.status_code == 404

        # User A deletes it
        del_res = await ac.delete(f"/api/v1/applications/{app_id}", headers=headers_a)
        assert del_res.status_code == 204

        # Verify it is gone
        get_again = await ac.get(f"/api/v1/applications/{app_id}", headers=headers_a)
        assert get_again.status_code == 404


@pytest.mark.anyio
async def test_dashboard_metrics_reflect_applications():
    user, token = await create_user_helper("dash_sync@example.com", "Sync User")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Dashboard initially 0
        d0 = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert d0.json()["metrics"]["jobs_applied"] == 0
        assert d0.json()["metrics"]["replies_received"] == 0
        assert d0.json()["metrics"]["offers_received"] == 0

        # Add 1 application with applied status
        app_res = await ac.post(
            "/api/v1/applications",
            json={"company": "Vercel", "role": "Solutions Architect", "status": "applied"},
            headers=headers,
        )
        app_id = app_res.json()["id"]

        # Dashboard now has 1 applied, 0 replies, 0 offers
        d1 = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert d1.json()["metrics"]["jobs_applied"] == 1
        assert d1.json()["metrics"]["replies_received"] == 0
        assert d1.json()["metrics"]["offers_received"] == 0

        # Move application to offer
        await ac.patch(
            f"/api/v1/applications/{app_id}",
            json={"status": "offer"},
            headers=headers,
        )

        # Dashboard now has 1 applied, 1 reply (offer progressed beyond applied), 1 offer
        d2 = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert d2.json()["metrics"]["jobs_applied"] == 1
        assert d2.json()["metrics"]["replies_received"] == 1
        assert d2.json()["metrics"]["offers_received"] == 1
