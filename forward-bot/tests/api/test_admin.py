import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
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
    app = create_app(settings, lifespan=None)
    # Set a mock worker_task on app state
    mock_task = MagicMock()
    mock_task.done.return_value = False
    app.state.worker_task = mock_task
    return app

@pytest.mark.asyncio
async def test_admin_reconnect(app):
    headers = {"X-API-Key": "test-api-key"}
    
    # Mock telegram_client, mongo_client, and run_telegram_worker task
    with patch("forward_bot.api.routers.admin.telegram_client") as mock_tc, \
         patch("forward_bot.api.routers.admin.mongo_client") as mock_mc, \
         patch("forward_bot.tasks.run_telegram_worker") as mock_worker_run:
        
        mock_tc.disconnect = AsyncMock()
        mock_tc.connect = AsyncMock()
        type(mock_tc).is_connected = MagicMock(return_value=True)
        mock_mc.db = MagicMock()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/admin/reconnect", headers=headers)
            
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        
        # Allow background task to execute
        await asyncio.sleep(0.1)
        
        mock_tc.disconnect.assert_called_once()
        mock_tc.connect.assert_called_once_with(app.state.settings)
        # Verify old worker_task was cancelled
        app.state.worker_task.cancel.assert_called_once()
