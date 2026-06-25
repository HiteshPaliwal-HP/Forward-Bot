import pytest
from httpx import AsyncClient, ASGITransport
from forward_bot.app import create_app
from forward_bot.config import Settings
import tempfile
from pathlib import Path


@pytest.fixture
def temp_media_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def settings(temp_media_dir):
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        media_replacement_base_dir=str(temp_media_dir),
        ui_enabled=False,
    )


@pytest.fixture
def app(settings):
    return create_app(settings, lifespan=None)


@pytest.mark.asyncio
async def test_list_replacement_images_empty(app):
    """Test list_replacement_images returns empty list when directory is empty."""
    headers = {"X-API-Key": "test-api-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/media/replacement-images", headers=headers)
    
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_replacement_images_with_files(app, temp_media_dir):
    """Test list_replacement_images lists files (excluding directories) in MEDIA_REPLACEMENT_BASE_DIR."""
    headers = {"X-API-Key": "test-api-key"}
    
    # Create some dummy files and a directory
    (temp_media_dir / "img1.png").write_text("dummy")
    (temp_media_dir / "img2.jpg").write_text("dummy")
    (temp_media_dir / "subdir").mkdir()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/media/replacement-images", headers=headers)
    
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 2
    assert "img1.png" in files
    assert "img2.jpg" in files
    assert "subdir" not in files


@pytest.mark.asyncio
async def test_list_replacement_images_unauthorized(app):
    """Test list_replacement_images returns 401 for unauthorized operators."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/media/replacement-images")
    assert response.status_code == 401
