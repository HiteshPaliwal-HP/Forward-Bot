"""Entry point for the Forward Bot application."""
import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn

from forward_bot.app import create_app
from forward_bot.settings import Settings


@asynccontextmanager
async def lifespan(app):
    """Handle application startup and shutdown."""
    # Startup
    print("Forward Bot starting up...")
    try:
        yield
    finally:
        # Shutdown
        print("Forward Bot shutting down gracefully...")


async def main() -> None:
    """Main entry point for the application."""
    settings = Settings()

    # Validate settings on startup
    try:
        _validate_settings(settings)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create FastAPI app with lifespan
    app = create_app(settings, lifespan=lifespan)

    # Print startup info
    print(f"Forward Bot starting on {settings.bind_host}:{settings.port}")
    print(f"MongoDB: {settings.mongo_uri}")
    print(f"UI Enabled: {settings.ui_enabled}")
    print(f"Telegram Session: {settings.telegram_session_path}")

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
        print("Server stopped")


def _validate_settings(settings: Settings) -> None:
    """Validate critical settings on startup."""
    # Validate emptiness / whitespace first
    if not settings.api_key or not settings.api_key.strip():
        raise ValueError("API_KEY environment variable is required and cannot be empty")

    if not settings.secret_key or not settings.secret_key.strip():
        raise ValueError("SECRET_KEY environment variable is required and cannot be empty")

    # Validate placeholders
    if settings.api_key == "your-api-key-here":
        raise ValueError("API_KEY must be set to a real value (not placeholder)")

    if settings.secret_key == "your-secret-key-here":
        raise ValueError("SECRET_KEY must be set to a real value (not placeholder)")

    if not settings.mongo_uri or settings.mongo_uri == "mongodb://localhost:27017/forward_bot":
        print("⚠️  Using default MongoDB URI — ensure MongoDB is running on localhost:27017")


if __name__ == "__main__":
    asyncio.run(main())

