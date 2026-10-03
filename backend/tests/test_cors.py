import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_cors_preflight_google_login_allowed():
    """Verify OPTIONS preflight request for POST /api/auth/google/login succeeds with production Vercel origin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        response = await ac.options(
            "/api/auth/google/login",
            headers={
                "Origin": "https://aptly-seven.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://aptly-seven.vercel.app"
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in response.headers.get("access-control-allow-methods", "")


@pytest.mark.anyio
async def test_cors_preflight_google_signup_allowed():
    """Verify OPTIONS preflight request for POST /api/auth/google/signup succeeds with production Vercel origin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        response = await ac.options(
            "/api/auth/google/signup",
            headers={
                "Origin": "https://aptly-seven.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://aptly-seven.vercel.app"
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in response.headers.get("access-control-allow-methods", "")


@pytest.mark.anyio
async def test_cors_preflight_malicious_origin_rejected():
    """Verify OPTIONS preflight request from an unauthorized malicious origin is rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        response = await ac.options(
            "/api/auth/google/login",
            headers={
                "Origin": "https://evil-malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        # Starlette CORSMiddleware responds with 400 Disallowed CORS origin and no allow-origin header
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


@pytest.mark.anyio
async def test_cors_actual_post_request_allowed_origin():
    """Verify actual request from allowed origin includes Access-Control-Allow-Origin header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        response = await ac.post(
            "/api/auth/google/login",
            json={"credential": "dummy_invalid_token"},
            headers={"Origin": "https://aptly-seven.vercel.app"},
        )
        # The endpoint may return 400/401 for dummy token, but CORS header MUST be present
        assert response.headers.get("access-control-allow-origin") == "https://aptly-seven.vercel.app"
