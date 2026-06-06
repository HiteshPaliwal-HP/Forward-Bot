"""Entry point for the Forward Bot application."""
import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn

from pydantic import ValidationError

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.infrastructure.mongo import mongo_client
from forward_bot.infrastructure.logging import setup_logging, logger


@asynccontextmanager
async def lifespan(app):
    """Handle application startup and shutdown."""
    settings = app.state.settings
    logger.info("app_starting", message="Forward Bot starting up...")

    # Connect MongoDB
    try:
        await mongo_client.connect(settings)
        # Ping the DB to ensure readiness check behaves correctly on start
        await mongo_client.db.command("ping")
        logger.info("mongodb_connected", message="Connected to MongoDB successfully")
    except Exception as e:
        logger.critical("mongodb_connection_failed", error=str(e), message="MongoDB connection failed")
        # Let startup fail fast if MongoDB is unreachable (or let lifespan fail)
        raise e

    try:
        yield
    finally:
        logger.info("app_stopping", message="Forward Bot shutting down gracefully...")
        mongo_client.close()
        logger.info("app_stopped", message="Forward Bot stopped")


async def main() -> None:
    """Main entry point for the application."""
    # Validate settings on startup
    try:
        settings = Settings()
        _validate_settings(settings)
    except (ValidationError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize structured logging
    setup_logging(settings)

    # Create FastAPI app with lifespan
    app = create_app(settings, lifespan=lifespan)

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


