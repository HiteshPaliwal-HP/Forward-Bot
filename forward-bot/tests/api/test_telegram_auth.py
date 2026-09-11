import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
)

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.api.routers.telegram_auth import AUTH_STATE
from forward_bot.api.dependencies.providers import get_telegram_client


@pytest.fixture
def settings(tmp_path):
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=12345,
        telegram_api_hash="test-api-hash",
        telegram_session_path=str(tmp_path / "test.session"),
        ui_enabled=False,
    )


@pytest.fixture
def app(settings):
    AUTH_STATE.clear()
    app_inst = create_app(settings, lifespan=None)
    return app_inst


@pytest.mark.asyncio
async def test_auth_status_disconnected(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app.state.settings
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/telegram/auth/status", headers=headers)

        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is False
        assert data["phone_required"] is True
        assert "test.session" in data["session_path"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_status_connected(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = True
    mock_holder.settings = app.state.settings
    mock_client = AsyncMock()
    me_mock = MagicMock()
    me_mock.phone = "1234567890"
    mock_client.get_me = AsyncMock(return_value=me_mock)
    mock_holder.client = mock_client
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/telegram/auth/status", headers=headers)

        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["phone"] == "+12****7890"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_start_success(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app.state.settings
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)
    res_mock = MagicMock()
    res_mock.phone_code_hash = "mock_hash_123"
    mock_client.send_code_request = AsyncMock(return_value=res_mock)
    mock_holder.client = mock_client
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/telegram/auth/start",
                headers=headers,
                json={"phone": "+1234567890"}
            )

        assert res.status_code == 200
        assert res.json() == {"status": "code_sent"}
        mock_client.send_code_request.assert_called_once_with("+1234567890")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_start_already_connected(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = True
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/telegram/auth/start",
                headers=headers,
                json={"phone": "+1234567890"}
            )

        assert res.status_code == 409
        assert res.json()["error"]["code"] == "already_connected"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_start_invalid_phone(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app.state.settings
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/telegram/auth/start",
                headers=headers,
                json={"phone": "invalid_phone"}
            )

        assert res.status_code == 400
        assert res.json()["error"]["code"] == "invalid_phone"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_verify_success(app):
    headers = {"X-API-Key": "test-api-key"}
    import time
    AUTH_STATE["current"] = {
        "phone": "+1234567890",
        "phone_code_hash": "mock_hash_123",
        "expires_at": time.time() + 300,
    }

    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app.state.settings
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)
    mock_client.sign_in = AsyncMock()
    mock_holder.client = mock_client
    mock_holder.reconnect = AsyncMock()
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/telegram/auth/verify",
                headers=headers,
                json={"otp": "123456"}
            )

        assert res.status_code == 200
        assert res.json() == {"status": "connected"}
        mock_client.sign_in.assert_called_once_with(
            phone="+1234567890",
            code="123456",
            phone_code_hash="mock_hash_123"
        )
        mock_holder.reconnect.assert_called_once_with(app.state.settings)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_verify_requires_2fa(app):
    headers = {"X-API-Key": "test-api-key"}
    import time
    AUTH_STATE["current"] = {
        "phone": "+1234567890",
        "phone_code_hash": "mock_hash_123",
        "expires_at": time.time() + 300,
    }

    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app.state.settings
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)
    mock_client.sign_in = AsyncMock(side_effect=SessionPasswordNeededError(MagicMock()))
    mock_holder.client = mock_client
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/telegram/auth/verify",
                headers=headers,
                json={"otp": "123456"}
            )

        assert res.status_code == 202
        assert res.json() == {"requires_2fa": True}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_verify_invalid_otp(app):
    headers = {"X-API-Key": "test-api-key"}
    import time
    AUTH_STATE["current"] = {
        "phone": "+1234567890",
        "phone_code_hash": "mock_hash_123",
        "expires_at": time.time() + 300,
    }

    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app.state.settings
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)
    mock_client.sign_in = AsyncMock(side_effect=PhoneCodeInvalidError(MagicMock()))
    mock_holder.client = mock_client
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/telegram/auth/verify",
                headers=headers,
                json={"otp": "000000"}
            )

        assert res.status_code == 400
        assert res.json()["error"]["code"] == "invalid_otp"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_terminate_success(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = True
    mock_holder.terminate = AsyncMock()
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/telegram/auth/terminate", headers=headers)

        assert res.status_code == 200
        assert res.json() == {"status": "terminated"}
        mock_holder.terminate.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_terminate_not_connected(app):
    headers = {"X-API-Key": "test-api-key"}
    mock_holder = MagicMock()
    mock_holder.is_connected = False
    app.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/telegram/auth/terminate", headers=headers)

        assert res.status_code == 409
        assert res.json()["error"]["code"] == "not_connected"
    finally:
        app.dependency_overrides.clear()
