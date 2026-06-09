"""API tests for the /api/v1/sources endpoints."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId
from telethon.tl.types import Channel, Chat

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source import Source
from forward_bot.domain.exceptions import (
    TelegramUnavailableException,
    SourceAlreadyExistsException,
    TelegramResolveFailedException,
    SourceNotFoundException,
    SourceInUseException,
)
from forward_bot.api.dependencies.providers import get_source_repository, get_telegram_client


@pytest.fixture(autouse=True)
def mock_db_and_telegram():
    """Globally mock MongoDB and Telegram clients for these API tests to avoid connection errors."""
    with patch("forward_bot.api.dependencies.providers.mongo_client") as mock_mongo, \
         patch("forward_bot.api.dependencies.providers.telegram_client") as mock_tg:
        mock_mongo.db = MagicMock()
        yield mock_mongo, mock_tg


@pytest.fixture
def settings():
    return Settings(
        api_key="valid-api-key",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/test_db",
        ui_enabled=False,
    )


@pytest.fixture
def app(settings):
    return create_app(settings, lifespan=None)


@pytest.mark.asyncio
async def test_sources_endpoints_require_authentication(app):
    """Confirm that endpoints fail with 401 when no credentials are provided."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # GET /api/v1/sources/{id}
        res1 = await ac.get("/api/v1/sources/65c52c6f1f2e3d4a5b6c7d8e")
        assert res1.status_code == 401

        # POST /api/v1/sources
        res2 = await ac.post("/api/v1/sources", json={"telegram_reference": "ref", "display_name": "disp"})
        assert res2.status_code == 401

        # DELETE /api/v1/sources/{id}
        res3 = await ac.delete("/api/v1/sources/65c52c6f1f2e3d4a5b6c7d8e")
        assert res3.status_code == 401


@pytest.mark.asyncio
async def test_get_source_success(app):
    """Verify successful retrieval of a registered source."""
    mock_repo = MagicMock()
    mock_repo.get_source_by_id = AsyncMock(return_value=Source(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        telegram_id=123456,
        telegram_username="testchannel",
        display_name="Test Channel",
        type="channel",
        folder_id=None,
        created_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc),
    ))

    app.dependency_overrides[get_source_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/sources/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert data["telegram_id"] == 123456
    assert data["telegram_username"] == "testchannel"
    assert data["type"] == "channel"
    assert data["created_at"] == "2026-06-09T12:00:00Z"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_source_not_found(app):
    """Verify retrieval fails with 404 if source does not exist."""
    mock_repo = MagicMock()
    mock_repo.get_source_by_id = AsyncMock(return_value=None)
    app.dependency_overrides[get_source_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/sources/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "source_not_found"
    assert "not found" in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_source_telegram_disconnected(app):
    """Verify registration fails with 503 if Telegram client is not connected."""
    mock_tg = MagicMock()
    mock_tg.is_connected = False
    app.dependency_overrides[get_telegram_client] = lambda: mock_tg

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "testchannel", "display_name": "Test"},
            headers=headers
        )

    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "telegram_unavailable"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_source_success_channel(app):
    """Verify successful channel registration and resolution."""
    mock_repo = MagicMock()
    mock_repo.get_source_by_telegram_id = AsyncMock(return_value=None)
    mock_repo.get_source_by_username = AsyncMock(return_value=None)
    mock_repo.add_source = AsyncMock(side_effect=lambda s: setattr(s, "id", "65c52c6f1f2e3d4a5b6c7d8e") or "65c52c6f1f2e3d4a5b6c7d8e")

    mock_tg = MagicMock()
    mock_tg.is_connected = True
    mock_client = AsyncMock()
    
    # Mock Telethon channel entity
    mock_channel = MagicMock(spec=Channel)
    mock_channel.id = 123456789
    mock_channel.username = "my_channel"
    mock_channel.megagroup = False
    mock_client.get_entity = AsyncMock(return_value=mock_channel)
    mock_tg.client = mock_client

    app.dependency_overrides[get_source_repository] = lambda: mock_repo
    app.dependency_overrides[get_telegram_client] = lambda: mock_tg

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "@my_channel", "display_name": "My Channel"},
            headers=headers
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert data["telegram_id"] == 123456789
    assert data["telegram_username"] == "my_channel"
    assert data["type"] == "channel"
    assert data["folder_id"] is None
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_source_success_group(app):
    """Verify successful group resolution and registration."""
    mock_repo = MagicMock()
    mock_repo.get_source_by_telegram_id = AsyncMock(return_value=None)
    mock_repo.get_source_by_username = AsyncMock(return_value=None)
    mock_repo.add_source = AsyncMock(side_effect=lambda s: setattr(s, "id", "65c52c6f1f2e3d4a5b6c7d8e") or "65c52c6f1f2e3d4a5b6c7d8e")

    mock_tg = MagicMock()
    mock_tg.is_connected = True
    mock_client = AsyncMock()
    
    # Mock Telethon Chat entity (which is a group)
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = 987654321
    mock_chat.username = None
    mock_client.get_entity = AsyncMock(return_value=mock_chat)
    mock_tg.client = mock_client

    app.dependency_overrides[get_source_repository] = lambda: mock_repo
    app.dependency_overrides[get_telegram_client] = lambda: mock_tg

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": -987654321, "display_name": "My Group"},
            headers=headers
        )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "group"
    assert data["telegram_username"] is None
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_source_duplicate_check(app):
    """Verify duplicate check triggers 422 with source_already_exists code."""
    mock_repo = MagicMock()
    mock_repo.get_source_by_telegram_id = AsyncMock(return_value=Source(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        telegram_id=123456789,
        telegram_username="my_channel",
        display_name="Existing Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    ))

    mock_tg = MagicMock()
    mock_tg.is_connected = True
    mock_client = AsyncMock()
    
    mock_channel = MagicMock(spec=Channel)
    mock_channel.id = 123456789
    mock_channel.username = "my_channel"
    mock_channel.megagroup = False
    mock_client.get_entity = AsyncMock(return_value=mock_channel)
    mock_tg.client = mock_client

    app.dependency_overrides[get_source_repository] = lambda: mock_repo
    app.dependency_overrides[get_telegram_client] = lambda: mock_tg

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "my_channel", "display_name": "Another"},
            headers=headers
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "source_already_exists"
    assert "already exists" in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_source_resolve_failed(app):
    """Verify Telethon errors trigger 422 with telegram_resolve_failed code."""
    mock_tg = MagicMock()
    mock_tg.is_connected = True
    mock_client = AsyncMock()
    mock_client.get_entity = AsyncMock(side_effect=ValueError("Cannot find entity"))
    mock_tg.client = mock_client

    app.dependency_overrides[get_telegram_client] = lambda: mock_tg

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "non_existent", "display_name": "Non"},
            headers=headers
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "telegram_resolve_failed"
    assert "Cannot find entity" in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_source_success(app):
    """Verify successful deletion of an unreferenced source."""
    mock_repo = MagicMock()
    # Mock source exists
    mock_repo.get_source_by_id = AsyncMock(return_value=Source(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        telegram_id=123,
        telegram_username="unreferenced",
        display_name="Delete Me",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    ))
    mock_repo.get_referencing_rules_count = AsyncMock(return_value=0)
    mock_repo.delete_source = AsyncMock(return_value=True)

    app.dependency_overrides[get_source_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/api/v1/sources/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)

    assert response.status_code == 204
    mock_repo.delete_source.assert_called_once_with("65c52c6f1f2e3d4a5b6c7d8e")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_source_in_use_rejection(app):
    """Verify deletion is blocked and returns 409 if source is referenced by rules."""
    mock_repo = MagicMock()
    mock_repo.get_source_by_id = AsyncMock(return_value=Source(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        telegram_id=123,
        telegram_username="in_use",
        display_name="In Use",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    ))
    mock_repo.get_referencing_rules_count = AsyncMock(return_value=5)

    app.dependency_overrides[get_source_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/api/v1/sources/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)

    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "source_in_use"
    assert "referenced by 5 rules" in data["error"]["message"]
    app.dependency_overrides.clear()
