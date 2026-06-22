import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
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
    # Disable default lifespan to avoid starting real tasks and connecting to real Mongo
    return create_app(settings, lifespan=None)


@pytest.mark.asyncio
async def test_liveness_endpoint(app):
    """Test GET /health returns status: ok."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_telegram_health_endpoint(app):
    """Test GET /health/telegram returns disconnected state."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/telegram")
        
    assert response.status_code == 503
    assert response.json() == {"telegram": "disconnected", "last_event": None}


@pytest.mark.asyncio
async def test_readiness_endpoint_mongodb_up(app):
    """Test GET /health/ready returns mongodb: up when ping succeeds."""
    mock_db = MagicMock()
    # Mock database ping command (coroutine)
    async def mock_command(cmd):
        if cmd == "ping":
            return {"ok": 1}
        raise ValueError("Unknown command")
    mock_db.command = mock_command

    with patch("forward_bot.api.routers.health.mongo_client") as mock_client:
        mock_client.db = mock_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"mongodb": "up"}


@pytest.mark.asyncio
async def test_readiness_endpoint_mongodb_down(app):
    """Test GET /health/ready returns mongodb: down and HTTP 503 when ping fails."""
    mock_db = MagicMock()
    async def mock_command(cmd):
        raise Exception("Connection timeout")
    mock_db.command = mock_command

    with patch("forward_bot.api.routers.health.mongo_client") as mock_client:
        mock_client.db = mock_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"mongodb": "down"}


@pytest.mark.asyncio
async def test_readiness_endpoint_mongodb_client_none(app):
    """Test GET /health/ready returns mongodb: down and HTTP 503 when client db is None."""
    with patch("forward_bot.api.routers.health.mongo_client") as mock_client:
        mock_client.db = None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"mongodb": "down"}
