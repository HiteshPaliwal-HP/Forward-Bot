import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from forward_bot.app import create_app
from forward_bot.config import Settings
import forward_bot.infrastructure.logging.ring_buffer as rb
from forward_bot.infrastructure.logging.ring_buffer import init_ring_buffer

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

@pytest.fixture(autouse=True)
def setup_buffer():
    # Initialize the ring buffer with 24 hours log window
    init_ring_buffer(24)
    if rb._ring_buffer is not None:
        rb._ring_buffer.clear()

@pytest.mark.asyncio
async def test_stats_summary(app):
    headers = {"X-API-Key": "test-api-key"}
    
    # 1. Test empty summary
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/stats/summary", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "forwarded_24h": 0,
        "failed_24h": 0,
        "blocked_24h": 0
    }

    # 2. Test populated summary within 24h
    now = datetime.now(timezone.utc)
    ts_now = now.isoformat()
    ts_10h_ago = (now - timedelta(hours=10)).isoformat()
    ts_25h_ago = (now - timedelta(hours=25)).isoformat()

    # Log 1: Forwarded within 24h
    rb._ring_buffer.append({"event": "forward_succeeded", "level": "info", "timestamp": ts_now})
    # Log 2: Blocked within 24h
    rb._ring_buffer.append({"event": "pipeline_blocked", "level": "info", "timestamp": ts_10h_ago})
    # Log 3: Failure within 24h (Error level)
    rb._ring_buffer.append({"event": "worker_dispatch_failed", "level": "error", "timestamp": ts_now})
    # Log 4: Blocked older than 24h (should be ignored)
    rb._ring_buffer.append({"event": "pipeline_blocked", "level": "info", "timestamp": ts_25h_ago})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/stats/summary", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "forwarded_24h": 1,
        "failed_24h": 1,
        "blocked_24h": 1
    }
