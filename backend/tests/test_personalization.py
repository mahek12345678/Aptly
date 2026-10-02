"""Tests for Onboarding Step 3 Personalization and Step 4 All Set endpoints."""
from __future__ import annotations

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.preference import UserPreference
from app.models.user import User
from tests.conftest import TestingSessionLocal


async def create_test_user(email: str = "copilot_user@example.com") -> tuple[User, str]:
    """Helper to create a test user and generate a JWT access token."""
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name="Copilot Tester",
            onboarding_completed=False,
            onboarding_step=3,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return user, token


@pytest.mark.anyio
async def test_get_default_personalization():
    """Verify fresh user receives sensible default copilot preferences."""
    user, token = await create_test_user("fresh_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/onboarding/personalization", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["focus_opportunity_matching"] is True
        assert data["focus_resume_tailoring"] is True
        assert data["focus_deadline_tracking"] is True
        assert data["update_frequency"] == "daily"
        assert data["additional_notes"] is None
        assert data["onboarding_step"] == 3
        assert data["onboarding_completed"] is False


@pytest.mark.anyio
async def test_save_and_reload_personalization():
    """Verify user can save preferences, which persist and update onboarding_step to 4."""
    user, token = await create_test_user("saver_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "focus_opportunity_matching": True,
        "focus_resume_tailoring": False,
        "focus_deadline_tracking": True,
        "update_frequency": "important_only",
        "additional_notes": "Prefer early-stage startups and remote AI engineer roles.",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Save preferences (PUT)
        put_resp = await ac.put("/api/v1/onboarding/personalization", headers=headers, json=payload)
        assert put_resp.status_code == 200
        saved_data = put_resp.json()

        assert saved_data["focus_opportunity_matching"] is True
        assert saved_data["focus_resume_tailoring"] is False
        assert saved_data["focus_deadline_tracking"] is True
        assert saved_data["update_frequency"] == "important_only"
        assert saved_data["additional_notes"] == payload["additional_notes"]
        assert saved_data["onboarding_step"] == 4
        assert saved_data["onboarding_completed"] is False

        # Reload preferences (GET)
        get_resp = await ac.get("/api/v1/onboarding/personalization", headers=headers)
        assert get_resp.status_code == 200
        reloaded_data = get_resp.json()

        assert reloaded_data["focus_opportunity_matching"] is True
        assert reloaded_data["focus_resume_tailoring"] is False
        assert reloaded_data["focus_deadline_tracking"] is True
        assert reloaded_data["update_frequency"] == "important_only"
        assert reloaded_data["additional_notes"] == payload["additional_notes"]
        assert reloaded_data["onboarding_step"] == 4


@pytest.mark.anyio
async def test_update_frequency_validation():
    """Verify invalid update frequencies are rejected."""
    _, token = await create_test_user("freq_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "focus_opportunity_matching": True,
        "focus_resume_tailoring": True,
        "focus_deadline_tracking": True,
        "update_frequency": "hourly",  # Invalid
        "additional_notes": None,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/v1/onboarding/personalization", headers=headers, json=payload)
        assert response.status_code == 422


@pytest.mark.anyio
async def test_additional_notes_length_validation():
    """Verify additional_notes exceeding 300 characters is rejected."""
    _, token = await create_test_user("notes_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    long_notes = "a" * 301
    payload = {
        "focus_opportunity_matching": True,
        "focus_resume_tailoring": True,
        "focus_deadline_tracking": True,
        "update_frequency": "daily",
        "additional_notes": long_notes,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/v1/onboarding/personalization", headers=headers, json=payload)
        assert response.status_code == 422


@pytest.mark.anyio
async def test_step4_complete_onboarding():
    """Verify Step 4 completion marks onboarding_completed = True and keeps step 4."""
    user, token = await create_test_user("finisher_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First save personalization
        await ac.put(
            "/api/v1/onboarding/personalization",
            headers=headers,
            json={
                "focus_opportunity_matching": True,
                "focus_resume_tailoring": True,
                "focus_deadline_tracking": True,
                "update_frequency": "weekly",
            },
        )

        # Call complete
        complete_resp = await ac.post("/api/v1/onboarding/complete", headers=headers)
        assert complete_resp.status_code == 200
        completed_user = complete_resp.json()
        assert completed_user["onboarding_completed"] is True
        assert completed_user["onboarding_step"] == 4

        # Verify DB persisted state
        async with TestingSessionLocal() as session:
            db_user = await session.get(User, user.id)
            assert db_user.onboarding_completed is True
            assert db_user.onboarding_step == 4


@pytest.mark.anyio
async def test_user_isolation_for_personalization():
    """Verify User A and User B preferences remain isolated."""
    user_a, token_a = await create_test_user("usera_pref@example.com")
    user_b, token_b = await create_test_user("userb_pref@example.com")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User A saves custom notes and weekly frequency
        await ac.put(
            "/api/v1/onboarding/personalization",
            headers=headers_a,
            json={
                "focus_opportunity_matching": True,
                "focus_resume_tailoring": False,
                "focus_deadline_tracking": False,
                "update_frequency": "weekly",
                "additional_notes": "User A confidential notes",
            },
        )

        # User B reads preferences -> should get default values, not User A's data
        resp_b = await ac.get("/api/v1/onboarding/personalization", headers=headers_b)
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        assert data_b["additional_notes"] is None
        assert data_b["update_frequency"] == "daily"
        assert data_b["focus_resume_tailoring"] is True


@pytest.mark.anyio
async def test_unauthenticated_requests_fail():
    """Verify unauthenticated access to personalization endpoints is rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        get_resp = await ac.get("/api/v1/onboarding/personalization")
        assert get_resp.status_code == 401

        put_resp = await ac.put("/api/v1/onboarding/personalization", json={"update_frequency": "daily"})
        assert put_resp.status_code == 401
