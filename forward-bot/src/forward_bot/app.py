"""FastAPI application factory and configuration."""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from forward_bot.config import Settings
from forward_bot.infrastructure.mongo import mongo_client
from forward_bot.infrastructure.logging import logger
from forward_bot.tasks import run_cache_refresher, run_mapping_sweeper, run_telegram_worker
from forward_bot.api.routers.health import router as health_router


@asynccontextmanager
async def default_lifespan(app: FastAPI):
    """Handle application startup and shutdown lifespan events."""
    settings = app.state.settings
    logger.info("app_starting", message="Forward Bot starting up...")

    # Connect to MongoDB
    try:
        await mongo_client.connect(settings)
    except Exception as e:
        logger.critical("mongodb_connection_failed", error=str(e), message="Failed to initialize MongoDB client")
        raise RuntimeError("Failed to initialize MongoDB client") from e

    # Perform startup health check verifying MongoDB reachability (ping) with 30s timeout
    try:
        if mongo_client.db is not None:
            await asyncio.wait_for(mongo_client.db.command("ping"), timeout=30.0)
            logger.info("mongodb_connected", message="Connected to MongoDB successfully")
        else:
            raise ValueError("MongoDB database reference is None")
    except Exception as e:
        logger.critical("mongodb_startup_check_failed", error=str(e), message="MongoDB startup connection check failed or timed out")
        raise RuntimeError("MongoDB startup connection check failed or timed out") from e

    # Start background task stubs
    cache_task = asyncio.create_task(run_cache_refresher())
    sweeper_task = asyncio.create_task(run_mapping_sweeper())
    worker_task = asyncio.create_task(run_telegram_worker())

    try:
        yield
    finally:
        logger.info("app_stopping", message="Forward Bot shutting down gracefully...")
        # Cancel background tasks
        cache_task.cancel()
        sweeper_task.cancel()
        worker_task.cancel()
        
        # Await tasks cancellation
        await asyncio.gather(cache_task, sweeper_task, worker_task, return_exceptions=True)
        
        # Close MongoDB connection
        mongo_client.close()
        logger.info("app_stopped", message="Forward Bot stopped")


def create_app(settings: Settings | None = None, lifespan=None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if settings is None:
        settings = Settings()

    if lifespan is None:
        lifespan = default_lifespan

    app = FastAPI(
        title="Forward Bot API",
        version="0.1.0",
        description="Self-hosted Telegram forwarding worker with operator dashboard",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API Routers
    app.include_router(health_router)

    # Serve UI static files
    if settings.ui_enabled:
        static_dir = "/app/static"
        if not os.path.exists(static_dir):
            # Fallback for local development
            fallback = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../web/dist"))
            if os.path.exists(fallback):
                static_dir = fallback

        if os.path.exists(static_dir):
            # Mount assets subfolder first if it exists
            assets_dir = os.path.join(static_dir, "assets")
            if os.path.exists(assets_dir):
                app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
                
            # Mount the full static folder under /static
            app.mount("/static", StaticFiles(directory=static_dir), name="static")

            # SPA router: serve files if they exist, else fallback to index.html
            @app.get("/{catchall:path}")
            async def serve_spa(catchall: str):
                if catchall.startswith("api") or catchall.startswith("health"):
                    return {"detail": "Not Found"}
                
                # Check if file exists in static_dir
                file_path = os.path.join(static_dir, catchall)
                if catchall and os.path.exists(file_path) and os.path.isfile(file_path):
                    return FileResponse(file_path)

                # Return index.html
                index_path = os.path.join(static_dir, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
                return {"detail": "Not Found"}

    return app

