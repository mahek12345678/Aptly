import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_cors_preflight_google_login_allowed():
    """Verify OPTIONS preflight request for POST /api/v1/auth/google/login succeeds with production Vercel origin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        response = await ac.options(
            "/api/v1/auth/google/login",
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
    """Verify OPTIONS preflight request for POST /api/v1/auth/google/signup succeeds with production Vercel origin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        response = await ac.options(
            "/api/v1/auth/google/signup",
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
            "/api/v1/auth/google/login",
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
            "/api/v1/auth/google/login",
            json={"credential": "dummy_invalid_token"},
            headers={"Origin": "https://aptly-seven.vercel.app"},
        )
        # The endpoint returns 401 for dummy token, but CORS header MUST be present and route must exist (not 404)
        assert response.status_code != 404
        assert response.headers.get("access-control-allow-origin") == "https://aptly-seven.vercel.app"


@pytest.mark.anyio
async def test_canonical_routes_exist():
    """Verify backend routes existence for canonical /api/v1/auth/google endpoints."""
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/v1/auth/google/login" in paths or any("/api/v1/auth/google/login" in str(r) for r in app.routes)
    assert "/api/v1/auth/google/signup" in paths or any("/api/v1/auth/google/signup" in str(r) for r in app.routes)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://aptly-pa4w.onrender.com") as ac:
        res_login = await ac.post("/api/v1/auth/google/login", json={"credential": "dummy"})
        assert res_login.status_code != 404

        res_signup = await ac.post("/api/v1/auth/google/signup", json={"credential": "dummy"})
        assert res_signup.status_code != 404
