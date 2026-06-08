"""Unit tests for the TelegramClientHolder connection manager."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from telethon.errors import AuthKeyUnregisteredError

from forward_bot.config import Settings
from forward_bot.infrastructure.telegram.client import TelegramClientHolder


@pytest.fixture
def temp_session_dir(tmp_path):
    """Fixture providing a temporary directory for session files."""
    return tmp_path


@pytest.fixture
def mock_settings(temp_session_dir):
    """Fixture providing mock settings with a temp session path."""
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=12345,
        telegram_api_hash="test-api-hash",
        telegram_session_path=str(temp_session_dir / "test.session"),
        _env_file=None
    )


@pytest.mark.asyncio
async def test_connect_no_session_file(mock_settings):
    """Test that connect remains disconnected if no session file exists."""
    holder = TelegramClientHolder()
    
    # Ensure no session file exists
    session_file = Path(mock_settings.telegram_session_path)
    if session_file.exists():
        session_file.unlink()
        
    await holder.connect(mock_settings)
    
    assert holder.status == "disconnected"
    assert holder.client is None
    assert holder.is_connected is False


@pytest.mark.asyncio
@patch("forward_bot.infrastructure.telegram.client.TelegramClient")
async def test_connect_success(mock_telegram_client, mock_settings):
    """Test successful connection and authorization."""
    holder = TelegramClientHolder()
    
    # Create a dummy session file to simulate an existing session
    session_file = Path(mock_settings.telegram_session_path)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.touch()

    # Mock TelegramClient instance
    mock_client_instance = AsyncMock()
    mock_client_instance.connect = AsyncMock()
    mock_client_instance.is_user_authorized = AsyncMock(return_value=True)
    mock_client_instance.is_connected = MagicMock(return_value=True)
    mock_telegram_client.return_value = mock_client_instance

    await holder.connect(mock_settings)

    assert holder.status == "connected"
    assert holder.client is not None
    assert holder.is_connected is True
    
    mock_client_instance.connect.assert_called_once()
    mock_client_instance.is_user_authorized.assert_called_once()


@pytest.mark.asyncio
@patch("forward_bot.infrastructure.telegram.client.TelegramClient")
async def test_connect_session_invalidated(mock_telegram_client, mock_settings):
    """Test behavior when session exists but user is not authorized (invalidated)."""
    holder = TelegramClientHolder()
    
    # Create a dummy session file
    session_file = Path(mock_settings.telegram_session_path)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.touch()

    # Mock TelegramClient instance returning unauthorized
    mock_client_instance = AsyncMock()
    mock_client_instance.connect = AsyncMock()
    mock_client_instance.is_user_authorized = AsyncMock(return_value=False)
    mock_client_instance.disconnect = AsyncMock()
    mock_telegram_client.return_value = mock_client_instance

    with pytest.raises(RuntimeError, match="Telegram session is invalid"):
        await holder.connect(mock_settings)

    assert holder.status == "disconnected"
    assert holder.client is None
    assert holder.last_event is not None  # timestamp updated on invalidation


@pytest.mark.asyncio
@patch("forward_bot.infrastructure.telegram.client.TelegramClient")
async def test_connect_auth_key_error(mock_telegram_client, mock_settings):
    """Test behavior when connection raises AuthKeyUnregisteredError."""
    holder = TelegramClientHolder()
    
    # Create dummy session file
    session_file = Path(mock_settings.telegram_session_path)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.touch()

    # Mock TelegramClient raising AuthKeyUnregisteredError on is_user_authorized
    mock_client_instance = AsyncMock()
    mock_client_instance.connect = AsyncMock()
    mock_client_instance.is_user_authorized = AsyncMock(side_effect=AuthKeyUnregisteredError(MagicMock()))
    mock_client_instance.disconnect = AsyncMock()
    mock_telegram_client.return_value = mock_client_instance

    with pytest.raises(RuntimeError, match="Telegram session is invalid"):
        await holder.connect(mock_settings)

    assert holder.status == "disconnected"
    assert holder.last_event is not None  # timestamp updated on invalidation


@pytest.mark.asyncio
@patch("forward_bot.infrastructure.telegram.client.TelegramClient")
async def test_disconnect(mock_telegram_client, mock_settings):
    """Test clean disconnection."""
    holder = TelegramClientHolder()
    mock_client_instance = AsyncMock()
    mock_client_instance.disconnect = AsyncMock()
    
    holder.client = mock_client_instance
    holder.status = "connected"

    await holder.disconnect()

    assert holder.status == "disconnected"
    assert holder.client is None
    mock_client_instance.disconnect.assert_called_once()
