import pytest
from pydantic import ValidationError
from forward_bot.config import Settings
from forward_bot.__main__ import _validate_settings


def test_settings_required_fields(monkeypatch):
    """Test that Settings raises ValidationError if required fields are missing."""
    # Clear environment variables
    for key in ["API_KEY", "SECRET_KEY", "MONGO_URI", "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "api_id", "api_hash"]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    
    errors = exc_info.value.errors()
    missing_fields = {err["loc"][0] for err in errors}
    assert "api_key" in missing_fields
    assert "secret_key" in missing_fields
    assert "mongo_uri" in missing_fields
    assert "telegram_api_id" in missing_fields
    assert "telegram_api_hash" in missing_fields


def test_settings_valid_initialization(monkeypatch):
    """Test that Settings initializes successfully when all required fields are provided."""
    # Clear env just in case
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_db")
    monkeypatch.setenv("TELEGRAM_API_ID", "123456")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test-hash")

    settings = Settings(_env_file=None)
    assert settings.api_key == "test-api-key"
    assert settings.secret_key == "test-secret-key"
    assert settings.mongo_uri == "mongodb://localhost:27017/test_db"
    assert settings.telegram_api_id == 123456
    assert settings.telegram_api_hash == "test-hash"


def test_settings_defaults(monkeypatch):
    """Test that default values are correctly populated."""
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_db")
    monkeypatch.setenv("TELEGRAM_API_ID", "123456")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test-hash")

    settings = Settings(_env_file=None)
    assert settings.telegram_session_path == "./data/telegram.session"
    assert settings.media_replacement_base_dir == "./data/replacement-images"
    assert settings.sampling_persist is False
    assert settings.ui_enabled is True
    assert settings.mapping_retention_days == 30
    assert settings.log_ring_buffer_hours == 1
    assert settings.hot_reload_interval == 30
    assert settings.bind_host == "127.0.0.1"
    assert settings.timezone_default == "UTC"
    assert settings.delivery_max_retries == 3
    assert settings.delivery_backoff_factor == 2.0
    assert settings.delivery_base_delay == 1.0


def test_settings_case_insensitivity(monkeypatch):
    """Test that env vars are parsed case-insensitively."""
    monkeypatch.setenv("api_key", "lowercase-api-key")
    monkeypatch.setenv("Secret_Key", "mixedcase-secret-key")
    monkeypatch.setenv("mongo_uri", "mongodb://localhost:27017/test_db")
    monkeypatch.setenv("telegram_api_id", "123456")
    monkeypatch.setenv("telegram_api_hash", "test-hash")

    settings = Settings(_env_file=None)
    assert settings.api_key == "lowercase-api-key"
    assert settings.secret_key == "mixedcase-secret-key"


from unittest.mock import patch


def test_settings_timezone_validation(monkeypatch):
    """Test timezone validation rules."""
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_db")
    monkeypatch.setenv("TELEGRAM_API_ID", "123456")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test-hash")

    with patch("forward_bot.config.ZoneInfo") as mock_zoneinfo:
        def side_effect(key):
            if key == "Invalid/Timezone":
                raise KeyError(key)
            return mock_zoneinfo
        mock_zoneinfo.side_effect = side_effect

        # Valid timezone
        monkeypatch.setenv("TIMEZONE_DEFAULT", "America/New_York")
        settings = Settings(_env_file=None)
        assert settings.timezone_default == "America/New_York"

        # Invalid timezone
        monkeypatch.setenv("TIMEZONE_DEFAULT", "Invalid/Timezone")
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        assert "Invalid timezone" in str(exc_info.value)


def test_settings_hot_reload_validation(monkeypatch):
    """Test hot_reload_interval validation rules."""
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_db")
    monkeypatch.setenv("TELEGRAM_API_ID", "123456")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test-hash")

    # Valid hot reload
    monkeypatch.setenv("HOT_RELOAD_INTERVAL", "15")
    settings = Settings(_env_file=None)
    assert settings.hot_reload_interval == 15

    # Invalid hot reload (<= 0)
    monkeypatch.setenv("HOT_RELOAD_INTERVAL", "0")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "hot_reload_interval must be greater than 0" in str(exc_info.value)


def test_validate_settings_helper():
    """Test _validate_settings validation function."""
    # Blank / whitespace tests
    settings_blank_api = Settings(
        api_key="   ",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=123456,
        telegram_api_hash="hash",
        _env_file=None
    )
    with pytest.raises(ValueError, match="API_KEY environment variable is required and cannot be empty"):
        _validate_settings(settings_blank_api)

    # Placeholder tests
    settings_placeholder = Settings(
        api_key="your-api-key-here",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=123456,
        telegram_api_hash="hash",
        _env_file=None
    )
    with pytest.raises(ValueError, match="API_KEY must be set to a real value"):
        _validate_settings(settings_placeholder)

