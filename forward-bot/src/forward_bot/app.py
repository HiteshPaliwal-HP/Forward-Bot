"""FastAPI application factory and configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forward_bot.settings import Settings


def create_app(settings: Settings | None = None, lifespan = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Forward Bot API",
        version="0.1.0",
        description="Self-hosted Telegram forwarding worker with operator dashboard",
        lifespan=lifespan,
    )

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
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
