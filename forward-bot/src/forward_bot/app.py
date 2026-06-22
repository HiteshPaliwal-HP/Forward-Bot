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
from forward_bot.infrastructure.telegram import telegram_client
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
            
            # Create background indexes for sources and source_folders collections
            try:
                from forward_bot.api.schemas.base import SOURCES, SOURCE_FOLDERS
                await mongo_client.db[SOURCES].create_index("telegram_id", unique=True, background=True)
                await mongo_client.db[SOURCES].create_index("telegram_username", unique=True, background=True, sparse=True)
                await mongo_client.db[SOURCE_FOLDERS].create_index("name", unique=True, background=True)
                # Forwarding rule indexes (Story 3.1)
                from forward_bot.api.schemas.base import FORWARDING_RULES
                await mongo_client.db[FORWARDING_RULES].create_index(
                    [("source_id", 1), ("is_active", 1)], background=True
                )
                await mongo_client.db[FORWARDING_RULES].create_index(
                    [("is_active", 1)], background=True
                )
                # Replacement rule index (Story 3.2)
                from forward_bot.api.schemas.base import REPLACEMENT_RULES
                await mongo_client.db[REPLACEMENT_RULES].create_index(
                    [("forwarding_rule_id", 1), ("is_active", 1), ("created_at", 1)], background=True
                )
                # Message mapping compound index (pre-created for Epic 4 Story 4.1)
                from forward_bot.api.schemas.base import MESSAGE_MAPPINGS
                await mongo_client.db[MESSAGE_MAPPINGS].create_index(
                    [
                        ("forwarding_rule_id", 1),
                        ("source_channel_id", 1),
                        ("source_message_id", 1),
                    ],
                    background=True
                )
                logger.info("mongodb_indexes_created", message="MongoDB indexes verified/created successfully")
            except Exception as e:
                logger.error("mongodb_index_creation_failed", error=str(e), message="Failed to create MongoDB indexes")
        else:
            raise ValueError("MongoDB database reference is None")
    except Exception as e:
        logger.critical("mongodb_startup_check_failed", error=str(e), message="MongoDB startup connection check failed or timed out")
        raise RuntimeError("MongoDB startup connection check failed or timed out") from e

    # Connect to Telegram
    try:
        await telegram_client.connect(settings)
    except Exception as e:
        logger.critical("telegram_connection_failed", error=str(e), message="Telegram client startup check failed or timed out")
        # Clean up database client
        mongo_client.close()
        raise e

    # Start background tasks
    cache_task = asyncio.create_task(run_cache_refresher(settings, mongo_client.db))
    sweeper_task = asyncio.create_task(run_mapping_sweeper(settings, mongo_client.db))
    worker_task = asyncio.create_task(run_telegram_worker(settings, mongo_client.db))

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
        
        # Disconnect from Telegram
        await telegram_client.disconnect()

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
    from forward_bot.api.routers.sources import router as sources_router
    app.include_router(sources_router)
    from forward_bot.api.routers.folders import router as folders_router
    app.include_router(folders_router)
    from forward_bot.api.routers.rules import router as rules_router
    app.include_router(rules_router)

    # Register Exception Handlers for standard error response envelopes
    from fastapi.responses import JSONResponse
    from fastapi import Request, HTTPException
    from forward_bot.domain.exceptions import (
        DomainException,
        TelegramUnavailableException,
        SourceAlreadyExistsException,
        TelegramResolveFailedException,
        SourceNotFoundException,
        SourceInUseException,
        FolderNotFoundException,
        SourceUsernameAlreadyExistsException,
        FolderNameInUseException,
        FolderReferenceNotFoundException,
        RuleNotFoundException,
        RuleSourceNotFoundException,
        RuleInvalidRegexException,
        RuleSelfReferentialException,
        RuleInvalidTimezoneException,
        RuleMediaReplacementPathRequiredException,
        ReplacementRuleNotFoundException,
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}}
        )

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        if isinstance(exc, TelegramUnavailableException):
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "telegram_unavailable",
                        "message": "Telegram client is not connected. Cannot resolve source reference."
                    }
                }
            )
        elif isinstance(exc, SourceAlreadyExistsException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "source_already_exists",
                        "message": f"Source with Telegram ID {exc.telegram_id} already exists."
                    }
                }
            )
        elif isinstance(exc, SourceUsernameAlreadyExistsException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "source_already_exists",
                        "message": f"Source with username {exc.username} already exists."
                    }
                }
            )
        elif isinstance(exc, TelegramResolveFailedException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "telegram_resolve_failed",
                        "message": f"Failed to resolve Telegram reference: {exc.details}"
                    }
                }
            )
        elif isinstance(exc, SourceNotFoundException):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "source_not_found",
                        "message": f"Source {exc.source_id} not found."
                    }
                }
            )
        elif isinstance(exc, SourceInUseException):
            return JSONResponse(
                status_code=409,
                content={
                    "error": {
                        "code": "source_in_use",
                        "message": f"Source {exc.source_id} is referenced by {exc.rule_count} rules."
                    }
                }
            )
        elif isinstance(exc, FolderNotFoundException):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "folder_not_found",
                        "message": f"Folder with ID {exc.folder_id} does not exist."
                    }
                }
            )
        elif isinstance(exc, FolderReferenceNotFoundException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "folder_not_found",
                        "message": f"Folder with ID {exc.folder_id} does not exist."
                    }
                }
            )
        elif isinstance(exc, FolderNameInUseException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "folder_name_in_use",
                        "message": f"Folder name in use: {exc.name}."
                    }
                }
            )
        elif isinstance(exc, RuleNotFoundException):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "rule_not_found",
                        "message": f"Rule {exc.rule_id} not found."
                    }
                }
            )
        elif isinstance(exc, RuleSourceNotFoundException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "source_not_found",
                        "message": f"Source {exc.source_id} not found."
                    }
                }
            )
        elif isinstance(exc, RuleInvalidRegexException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "invalid_regex",
                        "message": f"Invalid regex /{exc.pattern}/: {exc.reason}."
                    }
                }
            )
        elif isinstance(exc, RuleSelfReferentialException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "self_referential_rule",
                        "message": "Cannot create rule: source equals destination."
                    }
                }
            )
        elif isinstance(exc, RuleInvalidTimezoneException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "invalid_timezone",
                        "message": f"Invalid timezone: {exc.timezone}."
                    }
                }
            )
        elif isinstance(exc, RuleMediaReplacementPathRequiredException):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "media_replacement_path_required",
                        "message": "media_replacement.replacement_image_path is required when enabled=true."
                    }
                }
            )
        elif isinstance(exc, ReplacementRuleNotFoundException):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "replacement_rule_not_found",
                        "message": f"Replacement rule {exc.replacement_id} not found."
                    }
                }
            )
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "bad_request",
                    "message": str(exc)
                }
            }
        )

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

