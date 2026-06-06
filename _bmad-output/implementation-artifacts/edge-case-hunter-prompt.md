# Edge Case Hunter - Code Review Prompt

You are the **Edge Case Hunter**. Your goal is to walk every branching path, boundary condition, and edge case in the code changes below. Analyze how it handles failures, invalid inputs, system signals, and file system or database boundary errors.

## Target Codebase Changes

Please review the code changes below. (Note: These files define the initial project scaffold and settings configuration).

### 1. `forward-bot/src/forward_bot/settings.py`
```python
"""Configuration settings for Forward Bot using Pydantic Settings."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    # Core settings with validation
    api_key: str = Field(
        default="your-api-key-here",
        description="API key for authentication (required for production)",
    )
    secret_key: str = Field(
        default="your-secret-key-here",
        description="Secret key for signing (required for production)",
    )

    # Database
    mongo_uri: str = Field(
        default="mongodb://localhost:27017/forward_bot",
        description="MongoDB connection URI",
    )

    # Telegram
    telegram_session_path: str = Field(
        default="/app/data/telegram.session",
        description="Path to store Telegram session data",
    )

    # Media handling
    media_replacement_base_dir: str = Field(
        default="/app/data/replacement-images",
        description="Base directory for replacement media files",
    )

    # Timezone and sampling
    timezone_default: str = Field(
        default="UTC",
        description="Default timezone for timestamp operations",
    )
    sampling_persist: bool = Field(
        default=False,
        description="Whether to persist sampling counters across restarts",
    )

    # UI and server
    ui_enabled: bool = Field(
        default=True,
        description="Whether to serve the React dashboard UI",
    )
    bind_host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)",
    )

    # Logging and caching
    log_ring_buffer_hours: int = Field(
        default=1,
        description="Ring buffer size in hours for structured logging",
    )
    hot_reload_interval: int = Field(
        default=30,
        description="Cache refresh interval in seconds",
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_telegram_session_path(self) -> Path:
        """Get the telegram session path as a Path object."""
        return Path(self.telegram_session_path).expanduser()

    def get_media_replacement_dir(self) -> Path:
        """Get the media replacement directory as a Path object."""
        return Path(self.media_replacement_base_dir).expanduser()
```

### 2. `forward-bot/src/forward_bot/__main__.py`
```python
"""Entry point for the Forward Bot application."""
import asyncio
import signal
from contextlib import asynccontextmanager

import uvicorn

from forward_bot.app import create_app
from forward_bot.settings import Settings


@asynccontextmanager
async def lifespan(app):
    """Handle application startup and shutdown."""
    # Startup
    print("Forward Bot starting up...")
    yield
    # Shutdown
    print("Forward Bot shutting down gracefully...")


async def main() -> None:
    """Main entry point for the application."""
    settings = Settings()

    # Validate settings on startup
    try:
        _validate_settings(settings)
    except ValueError as e:
        print(f"Configuration error: {e}")
        return

    # Create FastAPI app
    app = create_app(settings)
    app.router.lifespan_context = lifespan

    # Print startup info
    print(f"Forward Bot starting on {settings.bind_host}:8000")
    print(f"MongoDB: {settings.mongo_uri}")
    print(f"UI Enabled: {settings.ui_enabled}")
    print(f"Telegram Session: {settings.telegram_session_path}")

    # Configure graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start uvicorn server
    config = uvicorn.Config(
        app,
        host=settings.bind_host,
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        print("Server stopped")


def _validate_settings(settings: Settings) -> None:
    """Validate critical settings on startup."""
    if settings.api_key == "your-api-key-here":
        raise ValueError("API_KEY must be set to a real value (not placeholder)")

    if settings.secret_key == "your-secret-key-here":
        raise ValueError("SECRET_KEY must be set to a real value (not placeholder)")

    if not settings.mongo_uri or settings.mongo_uri == "mongodb://localhost:27017/forward_bot":
        print("⚠️  Using default MongoDB URI — ensure MongoDB is running on localhost:27017")

    if not settings.api_key:
        raise ValueError("API_KEY environment variable is required")

    if not settings.secret_key:
        raise ValueError("SECRET_KEY environment variable is required")


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. `forward-bot/src/forward_bot/app.py`
```python
"""FastAPI application factory and configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forward_bot.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Forward Bot API",
        version="0.1.0",
        description="Self-hosted Telegram forwarding worker with operator dashboard",
    )

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Liveness probe for Kubernetes/Docker health checks."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def readiness_check() -> dict[str, str]:
        """Readiness probe — checks if app is ready to serve requests."""
        return {"status": "ready"}

    return app
```

## Review Guidelines for Edge Cases
Identify:
1. Signal Handling issues: What happens if `KeyboardInterrupt` is raised inside `uvicorn.Server.serve()`? Does it clean up correctly? What about signal handler platform compatibility (e.g. Windows doesn't fully support `SIGTERM` in standard Python signal modules in the same way, or behaves differently when running inside `asyncio`)?
2. Path expansion exceptions: What happens if `settings.telegram_session_path` cannot be expanded or contains invalid characters?
3. Environment variables validation: What happens if API_KEY/SECRET_KEY are empty or whitespace?
4. CORS configurations: Are origins wildcardable or hardcoded? What happens in production?
5. Port collisions: Is port `8000` hardcoded or customizable?

Output findings as a list of unhandled edge cases with potential failure paths and suggested resolutions.
