"""Entry point for the Forward Bot application."""
import asyncio
import sys

import uvicorn

from pydantic import ValidationError
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.infrastructure.mongo import mongo_client
from forward_bot.infrastructure.logging import setup_logging, logger




async def main() -> None:
    """Main entry point for the application."""
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        await main_auth()
        return

    # Validate settings on startup
    try:
        settings = Settings()
        _validate_settings(settings)
    except (ValidationError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize structured logging
    setup_logging(settings)

    # Create FastAPI app (default_lifespan handles MongoDB and Telegram)
    app = create_app(settings)

    logger.info(
        "server_starting",
        host=settings.bind_host,
        port=settings.port,
        ui_enabled=settings.ui_enabled,
        message=f"Forward Bot starting on {settings.bind_host}:{settings.port}",
    )

    # Start uvicorn server (uvicorn handles SIGINT and SIGTERM natively)
    config = uvicorn.Config(
        app,
        host=settings.bind_host,
        port=settings.port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("server_interrupted", message="Server interrupted by user")


async def main_auth() -> None:
    """Interactive authentication CLI flow for Telegram."""
    try:
        settings = Settings()
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured for authentication.")
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== Telegram Authentication CLI ===")
    session_path = Path(settings.telegram_session_path).resolve()
    print(f"Using session path: {session_path}")

    # Ensure parent directory exists
    session_path.parent.mkdir(parents=True, exist_ok=True)

    actual_session_file = session_path
    if not session_path.name.endswith(".session"):
        actual_session_file = session_path.with_name(session_path.name + ".session")

    client = TelegramClient(
        str(session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    try:
        await client.connect()
        if await client.is_user_authorized():
            print(f"Already authorized! Session is valid at {actual_session_file}")
            await client.disconnect()
            sys.exit(0)

        phone = input("Enter your phone number (with country code, e.g. +1234567890): ").strip()
        if not phone:
            raise ValueError("Phone number cannot be empty")

        await client.send_code_request(phone)
        code = input("Enter the SMS code you received: ").strip()
        if not code:
            raise ValueError("SMS code cannot be empty")

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            import getpass
            password = getpass.getpass("Enter your 2FA password: ").strip()
            await client.sign_in(password=password)

        if await client.is_user_authorized():
            print(f"Authentication successful. Session saved to {actual_session_file}.")
            await client.disconnect()
            sys.exit(0)
        else:
            raise RuntimeError("Authentication succeeded but client is still unauthorized.")

    except Exception as e:
        await client.disconnect()
        # Clean up any created session files on failure (avoid leaving half-configured sessions)
        for suffix in ["", ".journal", "-journal"]:
            p = Path(str(actual_session_file) + suffix)
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
            p_orig = Path(str(session_path) + suffix)
            if p_orig.exists():
                try:
                    p_orig.unlink()
                except Exception:
                    pass

        # Print a generic message to avoid leaking Telethon error details (phone, codes, etc.)
        print("Authentication failed. Check your credentials and network, then try again.", file=sys.stderr)
        logger.error("telegram_auth_failed", error=type(e).__name__, message="Interactive authentication failed")
        sys.exit(1)


def run_auth() -> None:
    """Entrypoint for the auth command line script."""
    asyncio.run(main_auth())


def _validate_settings(settings: Settings) -> None:
    """Validate critical settings on startup."""
    # Validate emptiness / whitespace first
    if not settings.mongo_uri or not settings.mongo_uri.strip():
        raise ValueError("MONGO_URI environment variable is required and cannot be empty")

    if not settings.api_key or not settings.api_key.strip():
        raise ValueError("API_KEY environment variable is required and cannot be empty")

    if not settings.secret_key or not settings.secret_key.strip():
        raise ValueError("SECRET_KEY environment variable is required and cannot be empty")

    # Validate placeholders
    if settings.api_key == "your-api-key-here":
        raise ValueError("API_KEY must be set to a real value (not placeholder)")

    if settings.secret_key == "your-secret-key-here":
        raise ValueError("SECRET_KEY must be set to a real value (not placeholder)")

    if settings.mongo_uri == "mongodb://localhost:27017/forward_bot":
        print("⚠️  Using default MongoDB URI — ensure MongoDB is running on localhost:27017")


if __name__ == "__main__":
    asyncio.run(main())


