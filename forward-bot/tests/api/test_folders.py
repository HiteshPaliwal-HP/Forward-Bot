"""API tests for the /api/v1/folders endpoints."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.entities.source import Source
from forward_bot.api.dependencies.providers import get_folder_repository, get_source_repository


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
async def test_folders_endpoints_require_authentication(app):
    """Confirm that endpoints fail with 401 when no credentials are provided."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # GET /api/v1/folders
        res1 = await ac.get("/api/v1/folders")
        assert res1.status_code == 401

        # GET /api/v1/folders/{id}
        res2 = await ac.get("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e")
        assert res2.status_code == 401

        # POST /api/v1/folders
        res3 = await ac.post("/api/v1/folders", json={"name": "Folder"})
        assert res3.status_code == 401

        # PUT /api/v1/folders/{id}
        res4 = await ac.put("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e", json={"name": "New Name"})
        assert res4.status_code == 401

        # DELETE /api/v1/folders/{id}
        res5 = await ac.delete("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e")
        assert res5.status_code == 401


@pytest.mark.asyncio
async def test_create_folder_success(app):
    """Verify successful folder creation."""
    mock_repo = MagicMock()
    mock_repo.get_folder_by_name = AsyncMock(return_value=None)
    mock_repo.add_folder = AsyncMock(side_effect=lambda f: setattr(f, "id", "65c52c6f1f2e3d4a5b6c7d8e") or "65c52c6f1f2e3d4a5b6c7d8e")

    app.dependency_overrides[get_folder_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/folders", json={"name": "Crypto Signals"}, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert data["name"] == "Crypto Signals"
    assert "created_at" in data
    assert "updated_at" in data
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_folder_duplicate_rejection(app):
    """Verify creating folder with duplicate name fails with 422."""
    mock_repo = MagicMock()
    mock_repo.get_folder_by_name = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        name="Crypto Signals",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    ))

    app.dependency_overrides[get_folder_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/folders", json={"name": "crypto signals"}, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "folder_name_in_use"
    assert "Folder name in use: crypto signals." in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_folders_success(app):
    """Verify listing folders with precalculated source count."""
    mock_repo = MagicMock()
    now = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    mock_repo.list_folders_with_source_count = AsyncMock(return_value=[
        {
            "id": "65c52c6f1f2e3d4a5b6c7d8e",
            "name": "Crypto Signals",
            "created_at": now,
            "updated_at": now,
            "source_count": 4
        }
    ])

    app.dependency_overrides[get_folder_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/folders", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert data[0]["name"] == "Crypto Signals"
    assert data[0]["source_count"] == 4
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_folder_details_success(app):
    """Verify retrieving folder details without embedded sources."""
    mock_folder_repo = MagicMock()
    mock_source_repo = MagicMock()
    now = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    mock_folder_repo.get_folder_by_id = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        name="Crypto Signals",
        created_at=now,
        updated_at=now
    ))
    mock_source_repo.collection.count_documents = AsyncMock(return_value=2)

    app.dependency_overrides[get_folder_repository] = lambda: mock_folder_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert data["name"] == "Crypto Signals"
    assert data["source_count"] == 2
    assert data["sources"] is None
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_folder_details_with_sources(app):
    """Verify retrieving folder details with embedded sources list."""
    mock_folder_repo = MagicMock()
    mock_source_repo = MagicMock()
    now = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    mock_folder_repo.get_folder_by_id = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        name="Crypto Signals",
        created_at=now,
        updated_at=now
    ))
    
    mock_sources = [
        Source(
            id="65c52c6f1f2e3d4a5b6c7d8a",
            telegram_id=123,
            telegram_username="source1",
            display_name="Source 1",
            type="channel",
            folder_id="65c52c6f1f2e3d4a5b6c7d8e",
            created_at=now,
            updated_at=now
        )
    ]
    mock_source_repo.get_sources_by_folder_id = AsyncMock(return_value=mock_sources)

    app.dependency_overrides[get_folder_repository] = lambda: mock_folder_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e?include=sources", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert data["name"] == "Crypto Signals"
    assert data["source_count"] == 1
    assert len(data["sources"]) == 1
    assert data["sources"][0]["id"] == "65c52c6f1f2e3d4a5b6c7d8a"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_folder_not_found(app):
    """Verify 404 for non-existent or invalid ID format."""
    mock_folder_repo = MagicMock()
    mock_folder_repo.get_folder_by_id = AsyncMock(return_value=None)
    app.dependency_overrides[get_folder_repository] = lambda: mock_folder_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Invalid format
        res1 = await ac.get("/api/v1/folders/invalid-id", headers=headers)
        assert res1.status_code == 404
        
        # Valid format but missing
        res2 = await ac.get("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)
        assert res2.status_code == 404
        assert res2.json()["error"]["code"] == "folder_not_found"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rename_folder_success(app):
    """Verify successful renaming (including self-rename validation)."""
    mock_repo = MagicMock()
    now = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    mock_repo.get_folder_by_id = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        name="Old Name",
        created_at=now,
        updated_at=now
    ))
    mock_repo.get_folder_by_name = AsyncMock(return_value=None)
    mock_repo.update_folder = AsyncMock(return_value=True)

    app.dependency_overrides[get_folder_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Success rename to new name
        res = await ac.put("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e", json={"name": "New Name"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rename_folder_conflict(app):
    """Verify rename conflict checks (returns 422)."""
    mock_repo = MagicMock()
    now = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    mock_repo.get_folder_by_id = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        name="Old Name",
        created_at=now,
        updated_at=now
    ))
    # Mocking another folder that already has the new name
    mock_repo.get_folder_by_name = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8f",
        name="Taken Name",
        created_at=now,
        updated_at=now
    ))

    app.dependency_overrides[get_folder_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e", json={"name": "Taken Name"}, headers=headers)
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "folder_name_in_use"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_folder_success(app):
    """Verify successful deletion of a folder (disassociating sources is done at repo level)."""
    mock_repo = MagicMock()
    now = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    mock_repo.get_folder_by_id = AsyncMock(return_value=SourceFolder(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        name="Delete Me",
        created_at=now,
        updated_at=now
    ))
    mock_repo.delete_folder = AsyncMock(return_value=True)

    app.dependency_overrides[get_folder_repository] = lambda: mock_repo

    headers = {"X-API-Key": "valid-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete("/api/v1/folders/65c52c6f1f2e3d4a5b6c7d8e", headers=headers)
        assert res.status_code == 204

    app.dependency_overrides.clear()
