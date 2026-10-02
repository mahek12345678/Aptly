import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.mark.anyio
async def test_1_google_signup_new_user():
    """Case 1: New user Google signup creates user in DB, returns JWT token, step=1, onboarding_completed=False."""
    fake_claims = {
        "google_id": "google_new_123",
        "email": "new.google.user@example.com",
        "name": "New Google User",
        "picture": "https://example.com/avatar.jpg",
    }

    with patch("app.api.v1.endpoints.auth._verify_google_credential", return_value=fake_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/auth/google/signup", json={"credential": "mock_google_credential"})
            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["user"]["email"] == "new.google.user@example.com"
            assert data["user"]["name"] == "New Google User"
            assert data["user"]["onboarding_completed"] is False
            assert data["user"]["onboarding_step"] == 1

            token = data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Verify /auth/me returns this user
            me_resp = await ac.get("/api/auth/me", headers=headers)
            assert me_resp.status_code == 200
            assert me_resp.json()["email"] == "new.google.user@example.com"
            assert me_resp.json()["onboarding_step"] == 1


@pytest.mark.anyio
async def test_2_google_signup_duplicate_rejected():
    """Case 2: Google signup for existing user is rejected with 409 Conflict."""
    fake_claims = {
        "google_id": "google_existing_123",
        "email": "existing.user@example.com",
        "name": "Existing User",
        "picture": None,
    }

    with patch("app.api.v1.endpoints.auth._verify_google_credential", return_value=fake_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # First signup succeeds
            res1 = await ac.post("/api/auth/google/signup", json={"credential": "token_1"})
            assert res1.status_code == 201

            # Duplicate signup fails with 409
            res2 = await ac.post("/api/auth/google/signup", json={"credential": "token_2"})
            assert res2.status_code == 409
            assert "You already have an Aptly account" in res2.json()["detail"]


@pytest.mark.anyio
async def test_3_google_login_nonexistent_user_rejected():
    """Case 3: Google login for non-existent user returns 404 Not Found."""
    fake_claims = {
        "google_id": "google_unknown_999",
        "email": "unknown@example.com",
        "name": "Unknown User",
        "picture": None,
    }

    with patch("app.api.v1.endpoints.auth._verify_google_credential", return_value=fake_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/auth/google/login", json={"credential": "unknown_token"})
            assert res.status_code == 404
            assert "No Aptly account found. Create one first." in res.json()["detail"]


@pytest.mark.anyio
async def test_4_google_login_incomplete_onboarding():
    """Case 4: Existing user with incomplete onboarding logs in and retains onboarding step."""
    fake_claims = {
        "google_id": "google_step2_user",
        "email": "step2.user@example.com",
        "name": "Step2 User",
        "picture": None,
    }

    with patch("app.api.v1.endpoints.auth._verify_google_credential", return_value=fake_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Sign up
            signup_res = await ac.post("/api/auth/google/signup", json={"credential": "token_1"})
            assert signup_res.status_code == 201
            token = signup_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Advance to step 2 via preferences
            pref_res = await ac.put(
                "/api/onboarding/preferences",
                json={"user_type": "graduate", "opportunity_type": "full-time"},
                headers=headers,
            )
            assert pref_res.status_code == 200

            # 3. Simulate logging in again
            login_res = await ac.post("/api/auth/google/login", json={"credential": "token_2"})
            assert login_res.status_code == 200
            data = login_res.json()
            assert data["user"]["onboarding_completed"] is False
            assert data["user"]["onboarding_step"] == 2


@pytest.mark.anyio
async def test_5_google_login_completed_onboarding():
    """Case 5: Existing user with completed onboarding logs in with onboarding_completed=True, step=4."""
    fake_claims = {
        "google_id": "google_completed_user",
        "email": "completed.user@example.com",
        "name": "Completed User",
        "picture": None,
    }

    with patch("app.api.v1.endpoints.auth._verify_google_credential", return_value=fake_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Sign up
            signup_res = await ac.post("/api/auth/google/signup", json={"credential": "token_1"})
            token = signup_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Complete onboarding
            comp_res = await ac.post("/api/onboarding/complete", headers=headers)
            assert comp_res.status_code == 200
            assert comp_res.json()["onboarding_completed"] is True

            # 3. Log in again
            login_res = await ac.post("/api/auth/google/login", json={"credential": "token_2"})
            assert login_res.status_code == 200
            assert login_res.json()["user"]["onboarding_completed"] is True
            assert login_res.json()["user"]["onboarding_step"] == 4


@pytest.mark.anyio
async def test_6_obsolete_email_endpoints_removed():
    """Case 6: Obsolete email/password auth routes return 404/405 Not Found."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_signup = await ac.post("/api/auth/signup", json={"email": "a@b.com", "password": "pass"})
        assert res_signup.status_code in (404, 405)

        res_login = await ac.post("/api/auth/login", json={"email": "a@b.com", "password": "pass"})
        assert res_login.status_code in (404, 405)

        res_verify = await ac.get("/api/auth/verify-email?token=123")
        assert res_verify.status_code in (404, 405)

        res_resend = await ac.post("/api/auth/resend-verification", json={"email": "a@b.com"})
        assert res_resend.status_code in (404, 405)

        res_test = await ac.post("/api/auth/test-resend", json={"to_email": "a@b.com"})
        assert res_test.status_code in (404, 405)
