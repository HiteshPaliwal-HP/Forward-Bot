"""
E2E & Integration Tests for Epic 1: Project Foundation & Telegram Connectivity.

Covers all four stories:
  1.1  Project Scaffold & Directory Structure
  1.2  Application Settings & MongoDB Client
  1.3  FastAPI Shell, Health Endpoints & Docker Build
  1.4  Telegram Authentication & Session Management

Each test section is labelled with the story it validates.
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from telethon.errors import AuthKeyUnregisteredError, SessionExpiredError, UserDeactivatedError

from forward_bot.__main__ import _validate_settings
from forward_bot.app import create_app, default_lifespan
from forward_bot.config import Settings
from forward_bot.infrastructure.mongo.client import MongoClientHolder
from forward_bot.infrastructure.telegram.client import TelegramClientHolder
from forward_bot.tasks import run_cache_refresher, run_mapping_sweeper, run_telegram_worker


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_settings(tmp_path):
    """Minimal valid settings with temp session path."""
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=12345,
        telegram_api_hash="test-api-hash",
        telegram_session_path=str(tmp_path / "telegram.session"),
        ui_enabled=False,
        _env_file=None,
    )


@pytest.fixture
def app_no_lifespan(base_settings):
    """App with lifespan disabled — safe for pure routing tests."""
    return create_app(base_settings, lifespan=None)


# ===========================================================================
# Story 1.1 – Project Scaffold & Directory Structure
# ===========================================================================


def test_source_package_importable():
    """Confirm all top-level forward_bot modules import without error."""
    import forward_bot  # noqa: F401
    import forward_bot.app  # noqa: F401
    import forward_bot.config  # noqa: F401
    import forward_bot.tasks  # noqa: F401
    import forward_bot.infrastructure.mongo.client  # noqa: F401
    import forward_bot.infrastructure.telegram.client  # noqa: F401
    import forward_bot.api.routers.health  # noqa: F401


def test_project_files_exist():
    """Verify critical scaffold files exist in the project root."""
    # __file__ is at forward-bot/tests/e2e/test_epic1_e2e.py
    # parents[0] = tests/e2e, parents[1] = tests, parents[2] = forward-bot/
    package_root = Path(__file__).resolve().parents[2]
    assert (package_root / "pyproject.toml").exists(), "pyproject.toml missing"
    assert (package_root / "src" / "forward_bot" / "__init__.py").exists()
    assert (package_root / "tests").is_dir()


# ===========================================================================
# Story 1.2 – Application Settings & MongoDB Client
# ===========================================================================


class TestSettingsValidation:
    """Story 1.2 AC-1: Pydantic settings loading & validation."""

    def test_required_fields_raise_on_missing(self, monkeypatch):
        for key in ["API_KEY", "SECRET_KEY", "MONGO_URI", "TELEGRAM_API_ID", "TELEGRAM_API_HASH"]:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_mongo_uri_required(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "k")
        monkeypatch.setenv("SECRET_KEY", "s")
        monkeypatch.setenv("TELEGRAM_API_ID", "1")
        monkeypatch.setenv("TELEGRAM_API_HASH", "h")
        monkeypatch.delenv("MONGO_URI", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_telegram_api_id_alias_api_id(self, monkeypatch):
        """AC-1: TELEGRAM_API_ID and API_ID aliases both resolve."""
        monkeypatch.setenv("API_KEY", "k")
        monkeypatch.setenv("SECRET_KEY", "s")
        monkeypatch.setenv("MONGO_URI", "mongodb://localhost/db")
        monkeypatch.setenv("API_ID", "99999")
        monkeypatch.setenv("API_HASH", "hash-via-alias")
        s = Settings(_env_file=None)
        assert s.telegram_api_id == 99999
        assert s.telegram_api_hash == "hash-via-alias"

    def test_telegram_api_id_primary_key(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "k")
        monkeypatch.setenv("SECRET_KEY", "s")
        monkeypatch.setenv("MONGO_URI", "mongodb://localhost/db")
        monkeypatch.setenv("TELEGRAM_API_ID", "77777")
        monkeypatch.setenv("TELEGRAM_API_HASH", "hash-primary")
        s = Settings(_env_file=None)
        assert s.telegram_api_id == 77777

    def test_default_telegram_session_path(self):
        s = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        assert s.telegram_session_path == "./data/telegram.session"

    def test_defaults_media_replacement_dir(self):
        s = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        assert s.media_replacement_base_dir == "./data/replacement-images"

    def test_defaults_numeric_fields(self):
        s = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        assert s.mapping_retention_days == 30
        assert s.log_ring_buffer_hours == 1
        assert s.hot_reload_interval == 30
        assert s.port == 8000

    def test_hot_reload_interval_zero_rejected(self):
        with pytest.raises(ValidationError):
            Settings(
                api_key="k",
                secret_key="s",
                mongo_uri="mongodb://localhost/db",
                telegram_api_id=1,
                telegram_api_hash="h",
                hot_reload_interval=0,
                _env_file=None,
            )

    def test_hot_reload_interval_negative_rejected(self):
        with pytest.raises(ValidationError):
            Settings(
                api_key="k",
                secret_key="s",
                mongo_uri="mongodb://localhost/db",
                telegram_api_id=1,
                telegram_api_hash="h",
                hot_reload_interval=-5,
                _env_file=None,
            )

    def test_get_telegram_session_path_returns_path_object(self):
        s = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        result = s.get_telegram_session_path()
        assert isinstance(result, Path)

    def test_get_media_replacement_dir_returns_path_object(self):
        s = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        result = s.get_media_replacement_dir()
        assert isinstance(result, Path)


class TestValidateSettingsHelper:
    """Story 1.2: _validate_settings helper edge cases."""

    def _base(self, **kwargs):
        defaults = dict(
            api_key="real-key",
            secret_key="real-secret",
            mongo_uri="mongodb://localhost:27017/test_db",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        defaults.update(kwargs)
        return Settings(**defaults)

    def test_blank_api_key_raises(self):
        s = self._base(api_key="   ")
        with pytest.raises(ValueError, match="API_KEY environment variable is required"):
            _validate_settings(s)

    def test_placeholder_api_key_raises(self):
        s = self._base(api_key="your-api-key-here")
        with pytest.raises(ValueError, match="API_KEY must be set to a real value"):
            _validate_settings(s)

    def test_blank_secret_key_raises(self):
        s = self._base(secret_key="   ")
        with pytest.raises(ValueError, match="SECRET_KEY environment variable is required"):
            _validate_settings(s)

    def test_placeholder_secret_key_raises(self):
        s = self._base(secret_key="your-secret-key-here")
        with pytest.raises(ValueError, match="SECRET_KEY must be set to a real value"):
            _validate_settings(s)

    def test_blank_mongo_uri_raises(self):
        s = self._base(mongo_uri="   ")
        with pytest.raises(ValueError, match="MONGO_URI environment variable is required"):
            _validate_settings(s)

    def test_valid_settings_pass(self):
        s = self._base()
        _validate_settings(s)  # Should NOT raise


class TestMongoClientHolder:
    """Story 1.2: MongoClientHolder connect / close lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_sets_client_and_db(self):
        holder = MongoClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost:27017/mydb",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        with patch("forward_bot.infrastructure.mongo.client.AsyncIOMotorClient") as mock_motor:
            mock_motor_instance = MagicMock()
            mock_motor.return_value = mock_motor_instance
            await holder.connect(settings)
        assert holder.client is not None
        assert holder.db is not None

    @pytest.mark.asyncio
    async def test_close_clears_client_and_db(self):
        holder = MongoClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost:27017/mydb",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        with patch("forward_bot.infrastructure.mongo.client.AsyncIOMotorClient"):
            await holder.connect(settings)
        holder.close()
        assert holder.client is None
        assert holder.db is None

    def test_close_is_idempotent_when_already_closed(self):
        """close() on a fresh/already-closed holder must not raise."""
        holder = MongoClientHolder()
        holder.close()  # first call
        holder.close()  # second call should not raise

    @pytest.mark.asyncio
    async def test_db_name_fallback_when_empty_path(self):
        holder = MongoClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost:27017/",
            telegram_api_id=1,
            telegram_api_hash="h",
            _env_file=None,
        )
        with patch("forward_bot.infrastructure.mongo.client.AsyncIOMotorClient") as mock_motor:
            mock_client = MagicMock()
            mock_motor.return_value = mock_client
            await holder.connect(settings)
        # fallback database name is "forward_bot"
        assert holder.db == mock_client["forward_bot"]


# ===========================================================================
# Story 1.3 – FastAPI Shell, Health Endpoints & Background Tasks
# ===========================================================================


class TestHealthEndpoints:
    """Story 1.3 AC-1/2/3: Health routes return correct payloads."""

    @pytest.mark.asyncio
    async def test_liveness_returns_200_ok(self, app_no_lifespan):
        async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
            response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_telegram_stub_disconnected(self, app_no_lifespan):
        async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
            response = await ac.get("/health/telegram")
        assert response.status_code == 503
        body = response.json()
        assert body["telegram"] == "disconnected"
        assert body["last_event"] is None

    @pytest.mark.asyncio
    async def test_readiness_mongodb_up(self, app_no_lifespan):
        mock_db = MagicMock()

        async def mock_command(cmd):
            return {"ok": 1}

        mock_db.command = mock_command
        with patch("forward_bot.api.routers.health.mongo_client") as mc:
            mc.db = mock_db
            async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
                response = await ac.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"mongodb": "up"}

    @pytest.mark.asyncio
    async def test_readiness_mongodb_down_exception(self, app_no_lifespan):
        mock_db = MagicMock()

        async def mock_command(_):
            raise ConnectionError("timeout")

        mock_db.command = mock_command
        with patch("forward_bot.api.routers.health.mongo_client") as mc:
            mc.db = mock_db
            async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
                response = await ac.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"mongodb": "down"}

    @pytest.mark.asyncio
    async def test_readiness_mongodb_client_none(self, app_no_lifespan):
        with patch("forward_bot.api.routers.health.mongo_client") as mc:
            mc.db = None
            async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
                response = await ac.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"mongodb": "down"}

    @pytest.mark.asyncio
    async def test_api_docs_accessible(self, app_no_lifespan):
        async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
            response = await ac.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_accessible(self, app_no_lifespan):
        async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
            response = await ac.get("/redoc")
        assert response.status_code == 200


class TestBackgroundTaskStubs:
    """Story 1.3 AC-4: Background task stubs start and cancel cleanly."""

    @pytest.mark.asyncio
    async def test_cache_refresher_cancels_cleanly(self):
        task = asyncio.create_task(run_cache_refresher())
        await asyncio.sleep(0)  # let it start
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_mapping_sweeper_cancels_cleanly(self):
        task = asyncio.create_task(run_mapping_sweeper())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_telegram_worker_cancels_cleanly(self):
        task = asyncio.create_task(run_telegram_worker())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


class TestLifespanIntegration:
    """Story 1.3 AC-4: Lifespan startup failure paths."""

    @pytest.mark.asyncio
    async def test_lifespan_raises_if_mongodb_connect_fails(self, base_settings):
        """AC-4: MongoDB connect failure aborts startup with RuntimeError."""
        app = create_app(base_settings)

        with patch("forward_bot.app.mongo_client") as mc, patch(
            "forward_bot.app.telegram_client"
        ) as tc:
            mc.connect = AsyncMock(side_effect=ConnectionError("mongo down"))
            tc.connect = AsyncMock()
            tc.disconnect = AsyncMock()
            mc.close = MagicMock()

            with pytest.raises(RuntimeError, match="Failed to initialize MongoDB client"):
                async with default_lifespan(app):
                    pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_lifespan_raises_if_mongodb_ping_fails(self, base_settings):
        """AC-4: MongoDB ping timeout during startup aborts with RuntimeError."""
        app = create_app(base_settings)

        mock_db = MagicMock()

        async def failing_ping(_):
            raise TimeoutError("ping timeout")

        mock_db.command = failing_ping

        with patch("forward_bot.app.mongo_client") as mc, patch(
            "forward_bot.app.telegram_client"
        ) as tc:
            mc.connect = AsyncMock()
            mc.db = mock_db
            mc.close = MagicMock()
            tc.connect = AsyncMock()
            tc.disconnect = AsyncMock()

            with pytest.raises(RuntimeError, match="MongoDB startup connection check failed"):
                async with default_lifespan(app):
                    pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_lifespan_raises_if_mongodb_db_none(self, base_settings):
        """AC-4: MongoDB db being None after connect aborts startup."""
        app = create_app(base_settings)

        with patch("forward_bot.app.mongo_client") as mc, patch(
            "forward_bot.app.telegram_client"
        ) as tc:
            mc.connect = AsyncMock()
            mc.db = None  # simulates a situation where db reference is lost
            mc.close = MagicMock()
            tc.connect = AsyncMock()
            tc.disconnect = AsyncMock()

            with pytest.raises(RuntimeError, match="MongoDB startup connection check failed"):
                async with default_lifespan(app):
                    pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_lifespan_raises_and_closes_mongo_when_telegram_fails(self, base_settings):
        """AC-4: Telegram connect failure after MongoDB success still closes MongoDB."""
        app = create_app(base_settings)

        mock_db = MagicMock()

        async def ok_ping(_):
            return {"ok": 1}

        mock_db.command = ok_ping
        mongo_close_called = []

        with patch("forward_bot.app.mongo_client") as mc, patch(
            "forward_bot.app.telegram_client"
        ) as tc:
            mc.connect = AsyncMock()
            mc.db = mock_db
            mc.close = MagicMock(side_effect=lambda: mongo_close_called.append(True))
            tc.connect = AsyncMock(side_effect=RuntimeError("telegram session invalid"))
            tc.disconnect = AsyncMock()

            with pytest.raises(RuntimeError):
                async with default_lifespan(app):
                    pass  # pragma: no cover

        assert mongo_close_called, "mongo_client.close() must be called when Telegram startup fails"

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_cancels_tasks_and_disconnects(self, base_settings):
        """AC-4: Clean shutdown cancels all background tasks and disconnects clients."""
        app = create_app(base_settings)

        mock_db = MagicMock()

        async def ok_ping(_):
            return {"ok": 1}

        mock_db.command = ok_ping

        disconnect_calls = []

        # Use side_effect callables so each call produces a fresh coroutine,
        # avoiding the "coroutine was never awaited" ResourceWarning.
        async def _forever():
            await asyncio.sleep(float("inf"))

        with patch("forward_bot.app.mongo_client") as mc, patch(
            "forward_bot.app.telegram_client"
        ) as tc, patch("forward_bot.app.run_cache_refresher", side_effect=_forever), patch(
            "forward_bot.app.run_mapping_sweeper", side_effect=_forever
        ), patch(
            "forward_bot.app.run_telegram_worker", side_effect=_forever
        ):
            mc.connect = AsyncMock()
            mc.db = mock_db
            mc.close = MagicMock()
            tc.connect = AsyncMock()
            tc.disconnect = AsyncMock(side_effect=lambda: disconnect_calls.append(True))

            async with default_lifespan(app):
                pass  # exit immediately — triggers shutdown

        assert disconnect_calls, "telegram_client.disconnect() must be called on shutdown"
        mc.close.assert_called_once()


# ===========================================================================
# Story 1.4 – Telegram Authentication & Session Management
# ===========================================================================


class TestTelegramClientHolder:
    """Story 1.4 AC-4/5/6/7: TelegramClientHolder state machine."""

    @pytest.mark.asyncio
    async def test_connect_no_session_remains_disconnected(self, tmp_path):
        """AC-4: No session file → stays disconnected, no exception."""
        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(tmp_path / "missing.session"),
            _env_file=None,
        )
        await holder.connect(settings)
        assert holder.status == "disconnected"
        assert holder.client is None
        assert holder.is_connected is False

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_connect_success_sets_status_connected(self, mock_tg_cls, tmp_path):
        """AC-4: Valid session + authorized → status='connected', is_connected=True."""
        session_file = tmp_path / "valid.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(return_value=True)
        mock_instance.is_connected = MagicMock(return_value=True)
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        await holder.connect(settings)

        assert holder.status == "connected"
        assert holder.client is not None
        assert holder.is_connected is True
        assert holder.last_event is not None  # timestamp set on connect

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_connect_unauthorized_session_raises_runtime_error(self, mock_tg_cls, tmp_path):
        """AC-6: Session exists but is_user_authorized=False → RuntimeError raised."""
        session_file = tmp_path / "invalid.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(return_value=False)
        mock_instance.disconnect = AsyncMock()
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        with pytest.raises(RuntimeError, match="Telegram session is invalid"):
            await holder.connect(settings)

        assert holder.status == "disconnected"
        assert holder.client is None
        assert holder.last_event is not None

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_connect_auth_key_unregistered_raises(self, mock_tg_cls, tmp_path):
        """AC-6: AuthKeyUnregisteredError → RuntimeError with session invalidated."""
        session_file = tmp_path / "bad.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(
            side_effect=AuthKeyUnregisteredError(MagicMock())
        )
        mock_instance.disconnect = AsyncMock()
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        with pytest.raises(RuntimeError, match="Telegram session is invalid"):
            await holder.connect(settings)

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_connect_user_deactivated_raises(self, mock_tg_cls, tmp_path):
        """AC-6: UserDeactivatedError is treated as session invalidation."""
        session_file = tmp_path / "deactivated.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(
            side_effect=UserDeactivatedError(MagicMock())
        )
        mock_instance.disconnect = AsyncMock()
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        with pytest.raises(RuntimeError, match="Telegram session is invalid"):
            await holder.connect(settings)
        assert holder.status == "disconnected"

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_connect_session_expired_raises(self, mock_tg_cls, tmp_path):
        """AC-6: SessionExpiredError is treated as session invalidation."""
        session_file = tmp_path / "expired.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(
            side_effect=SessionExpiredError(MagicMock())
        )
        mock_instance.disconnect = AsyncMock()
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        with pytest.raises(RuntimeError, match="Telegram session is invalid"):
            await holder.connect(settings)

    @pytest.mark.asyncio
    async def test_disconnect_clears_client_and_status(self):
        """AC-4: disconnect() sets status='disconnected' and client=None."""
        holder = TelegramClientHolder()
        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()

        holder.client = mock_client
        holder.status = "connected"

        await holder.disconnect()

        assert holder.status == "disconnected"
        assert holder.client is None
        mock_client.disconnect.assert_called_once()
        assert holder.last_event is not None  # timestamp set on disconnect

    @pytest.mark.asyncio
    async def test_disconnect_when_already_disconnected(self):
        """disconnect() on an already-disconnected holder must not raise."""
        holder = TelegramClientHolder()
        await holder.disconnect()  # no client set — should be a no-op
        assert holder.status == "disconnected"

    def test_is_connected_false_when_status_not_connected(self):
        holder = TelegramClientHolder()
        holder.status = "disconnected"
        assert holder.is_connected is False

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_is_connected_false_when_client_not_connected(self, mock_tg_cls, tmp_path):
        """is_connected property returns False if Telethon client reports not connected."""
        session_file = tmp_path / "conn_check.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(return_value=True)
        mock_instance.is_connected = MagicMock(return_value=False)  # network drop
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        await holder.connect(settings)

        # Even though status was set to "connected", the property checks live client state
        assert holder.is_connected is False

    def test_last_event_initially_none(self):
        holder = TelegramClientHolder()
        assert holder.last_event is None

    @pytest.mark.asyncio
    @patch("forward_bot.infrastructure.telegram.client.TelegramClient")
    async def test_last_event_set_to_iso_string_on_connect(self, mock_tg_cls, tmp_path):
        """AC-7: last_event is an ISO timestamp string after successful connect."""
        import re

        session_file = tmp_path / "timestamp.session"
        session_file.touch()

        mock_instance = AsyncMock()
        mock_instance.is_user_authorized = AsyncMock(return_value=True)
        mock_instance.is_connected = MagicMock(return_value=True)
        mock_tg_cls.return_value = mock_instance

        holder = TelegramClientHolder()
        settings = Settings(
            api_key="k",
            secret_key="s",
            mongo_uri="mongodb://localhost/db",
            telegram_api_id=1,
            telegram_api_hash="h",
            telegram_session_path=str(session_file),
            _env_file=None,
        )
        await holder.connect(settings)

        assert holder.last_event is not None
        # Verify it is a valid ISO 8601 timestamp string
        iso_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        assert iso_pattern.search(holder.last_event), f"Unexpected format: {holder.last_event}"


class TestTelegramHealthEndpoint:
    """Story 1.4 AC-7: /health/telegram reflects live connection status."""

    @pytest.mark.asyncio
    @patch("forward_bot.api.routers.health.telegram_client")
    async def test_health_telegram_connected_status(self, mock_tc, app_no_lifespan):
        mock_tc.status = "connected"
        mock_tc.last_event = "2026-06-08T12:00:00+00:00"

        async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
            response = await ac.get("/health/telegram")

        assert response.status_code == 200
        body = response.json()
        assert body["telegram"] == "connected"
        assert body["last_event"] == "2026-06-08T12:00:00+00:00"

    @pytest.mark.asyncio
    @patch("forward_bot.api.routers.health.telegram_client")
    async def test_health_telegram_reconnecting_status(self, mock_tc, app_no_lifespan):
        mock_tc.status = "reconnecting"
        mock_tc.last_event = "2026-06-08T11:00:00+00:00"

        async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
            response = await ac.get("/health/telegram")

        assert response.status_code == 503
        assert response.json()["telegram"] == "reconnecting"
