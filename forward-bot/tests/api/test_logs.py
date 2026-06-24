import pytest
import json
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from forward_bot.app import create_app
from forward_bot.config import Settings
import forward_bot.infrastructure.logging.ring_buffer as rb
from forward_bot.infrastructure.logging.ring_buffer import init_ring_buffer
from forward_bot.infrastructure.logging.sse_broadcaster import broadcast_log

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
    # Initialize the ring buffer with a 1 hour window
    init_ring_buffer(1)
    if rb._ring_buffer is not None:
        rb._ring_buffer.clear()

@pytest.mark.asyncio
async def test_logs_recent_empty(app):
    headers = {"X-API-Key": "test-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/logs/recent", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"items": []}

@pytest.mark.asyncio
async def test_logs_recent_with_data(app):
    headers = {"X-API-Key": "test-api-key"}
    # Populate mock logs
    log1 = {"event": "forward_succeeded", "level": "info", "timestamp": "2026-06-23T12:00:00Z", "correlation_id": "c1"}
    log2 = {"event": "pipeline_blocked", "level": "info", "timestamp": "2026-06-23T12:01:00Z", "correlation_id": "c2"}
    rb._ring_buffer.append(log1)
    rb._ring_buffer.append(log2)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test basic list
        response = await ac.get("/api/v1/logs/recent", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

        # Test limit
        response = await ac.get("/api/v1/logs/recent?limit=1", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["correlation_id"] == "c2"

        # Test filter by event
        response = await ac.get("/api/v1/logs/recent?event=forward_succeeded", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["correlation_id"] == "c1"

        # Test filter by correlation_id
        response = await ac.get("/api/v1/logs/recent?correlation_id=c2", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["event"] == "pipeline_blocked"

@pytest.mark.asyncio
async def test_logs_search(app):
    headers = {"X-API-Key": "test-api-key"}
    now_str = datetime.now(timezone.utc).isoformat()
    log1 = {"event": "forward_succeeded", "level": "info", "timestamp": now_str, "correlation_id": "c1"}
    rb._ring_buffer.append(log1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/logs/search?correlation_id=c1", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["correlation_id"] == "c1"

        # Search with correlation_id not found
        response = await ac.get("/api/v1/logs/search?correlation_id=c99", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 0

@pytest.mark.asyncio
async def test_logs_stream(app):
    from forward_bot.api.routers.logs import stream_logs

    log1 = {"event": "forward_succeeded", "level": "info", "timestamp": "2026-06-23T12:00:00Z", "correlation_id": "c1"}
    rb._ring_buffer.append(log1)

    async def broadcast_delayed():
        await asyncio.sleep(0.1)
        broadcast_log({"event": "pipeline_blocked", "level": "info", "timestamp": "2026-06-23T12:05:00Z", "correlation_id": "c_new"})

    broadcast_task = asyncio.create_task(broadcast_delayed())

    # Call endpoint directly with mocked authentication
    response = await stream_logs(event=None, correlation_id=None)
    body_iterator = response.body_iterator

    events_received = []
    async for item in body_iterator:
        if item.startswith("data:"):
            data = json.loads(item[5:].strip())
            events_received.append(data)
            if len(events_received) == 2:
                break

    assert len(events_received) == 2
    assert events_received[0]["correlation_id"] == "c1"
    assert events_received[1]["correlation_id"] == "c_new"
    await broadcast_task
