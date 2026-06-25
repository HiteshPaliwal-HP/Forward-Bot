import pytest
from httpx import AsyncClient, ASGITransport
from itsdangerous import TimestampSigner
from forward_bot.app import create_app
from forward_bot.config import Settings


@pytest.fixture
def settings():
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        ui_enabled=False,
    )


@pytest.fixture
def app(settings):
    return create_app(settings, lifespan=None)


@pytest.mark.asyncio
async def test_auth_me_unauthorized(app):
    """Test GET /api/v1/auth/me returns 401 without cookie or api key."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.asyncio
async def test_auth_me_api_key(app):
    """Test GET /api/v1/auth/me returns 200 with X-API-Key header."""
    headers = {"X-API-Key": "test-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_login_success(app):
    """Test POST /api/v1/auth/login sets session cookie on success."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/login", json={"api_key": "test-api-key"})
    
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_login_failure(app):
    """Test POST /api/v1/auth/login returns 401 on incorrect credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/login", json={"api_key": "wrong-key"})
    
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert "session" not in response.cookies


@pytest.mark.asyncio
async def test_auth_me_with_cookie(app, settings):
    """Test GET /api/v1/auth/me validates session cookie correctly."""
    signer = TimestampSigner(settings.secret_key)
    session_val = signer.sign(b"operator").decode("utf-8")
    cookies = {"session": session_val}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/auth/me", cookies=cookies)
    
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_logout(app):
    """Test POST /api/v1/auth/logout clears session cookie."""
    cookies = {"session": "some-session-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/logout", cookies=cookies)
    
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    cookie = response.cookies.get("session")
    assert cookie is None or cookie == ""
