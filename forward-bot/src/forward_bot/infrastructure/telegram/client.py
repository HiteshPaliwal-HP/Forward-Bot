"""Telegram connection client holder using Telethon."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, UserDeactivatedError, SessionExpiredError

from forward_bot.config import Settings
from forward_bot.infrastructure.logging import logger


class TelegramClientHolder:
    """Holder for the Telethon client and connection state."""

    def __init__(self) -> None:
        self.client: TelegramClient | None = None
        self.settings: Settings | None = None
        self.status: str = "disconnected"
        self.last_event: str | None = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if client is initialized, connected, and authorized."""
        return self.status == "connected" and self.client is not None and self.client.is_connected()

    async def connect(self, settings: Settings) -> None:
        """Initialize and connect the Telegram client if a valid session exists."""
        async with self._lock:
            if self.status == "connected":
                logger.info(
                    "telegram_client_already_connected",
                    message="Telegram client is already connected. Skipping connect."
                )
                return
            self.settings = settings
            session_path = Path(settings.telegram_session_path).resolve()

            # Telethon SQLiteSession appends .session if the path doesn't end with it.
            # We want to check if the session file exists to know if we should connect.
            actual_session_file = session_path
            if not session_path.name.endswith(".session"):
                actual_session_file = session_path.with_name(session_path.name + ".session")

            # If the session file does not exist, remain disconnected.
            if not actual_session_file.exists():
                self.status = "disconnected"
                logger.info(
                    "telegram_client_no_session",
                    message="No saved Telegram session found. Telegram client remains disconnected."
                )
                return

            self.status = "connecting"
            logger.info("telegram_client_connecting", message="Connecting to Telegram...")

            try:
                # Ensure the parent folder exists
                session_path.parent.mkdir(parents=True, exist_ok=True)

                self.client = TelegramClient(
                    str(session_path),
                    settings.telegram_api_id,
                    settings.telegram_api_hash,
                )

                await self.client.connect()

                # Verify if user is authorized with this session
                if not await self.client.is_user_authorized():
                    # Invalid or expired session
                    self.status = "disconnected"
                    await self.client.disconnect()
                    self.client = None
                    self._handle_session_invalidated(None)
                    return

                self.status = "connected"
                self.last_event = datetime.now(timezone.utc).isoformat()
                logger.info(
                    "telegram_client_connected",
                    message="Telegram client connected and authorized successfully"
                )

            except (AuthKeyUnregisteredError, UserDeactivatedError, SessionExpiredError) as e:
                self.status = "disconnected"
                if self.client:
                    await self.client.disconnect()
                    self.client = None
                self._handle_session_invalidated(e)
            except Exception as e:
                self.status = "disconnected"
                if self.client:
                    await self.client.disconnect()
                    self.client = None
                logger.error(
                    "telegram_connection_failed",
                    error=str(e),
                    message="Failed to connect to Telegram client"
                )
                raise

    async def disconnect(self) -> None:
        """Disconnect the Telegram client cleanly."""
        async with self._lock:
            if self.client:
                await self.client.disconnect()
                self.client = None
            self.status = "disconnected"
            self.last_event = datetime.now(timezone.utc).isoformat()
            logger.info("telegram_client_disconnected", message="Telegram client disconnected")

    def _handle_session_invalidated(self, exc: Exception | None) -> None:
        """Handle server-side session invalidation by logging and raising to abort startup.

        The RuntimeError propagates out of connect() through the FastAPI lifespan,
        which uvicorn treats as a fatal startup failure and exits cleanly.
        """
        self.last_event = datetime.now(timezone.utc).isoformat()
        logger.critical(
            "telegram_session_invalidated",
            level="critical",
            error=str(exc) if exc else "User not authorized",
            message="Telegram session is invalid or has been invalidated server-side"
        )
        raise RuntimeError("Telegram session is invalid or has been invalidated server-side")


# Global singleton instance
telegram_client = TelegramClientHolder()
