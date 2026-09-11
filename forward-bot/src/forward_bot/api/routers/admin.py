"""FastAPI router for administrative tasks."""
import asyncio
from fastapi import APIRouter, Depends, status, Request
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import get_db
from forward_bot.infrastructure.cache.cache_refresher import trigger_cache_rebuild
from forward_bot.infrastructure.logging import logger
from forward_bot.infrastructure.telegram import telegram_client
from forward_bot.infrastructure.mongo import mongo_client

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AdminReconnectResponse(BaseModel):
    ok: bool


class CacheRefreshResponse(BaseModel):
    version: int
    rule_count: int
    source_count: int
    refreshed_at: datetime | None = None



async def perform_reconnect(app_instance) -> None:
    """Background task to reconnect the Telegram client and restart the worker."""
    settings = app_instance.state.settings
    db = mongo_client.db
    
    try:
        logger.info("telegram_reconnect_initiated", message="Initiating Telegram reconnection...")
        
        # Disconnect client
        await telegram_client.disconnect()
        
        # Connect client using configuration settings
        await telegram_client.connect(settings)
        
        # Restart the background worker task if the connection succeeded and database is ready
        if telegram_client.is_connected and db is not None:
            # 1. Cancel existing worker task
            old_task = getattr(app_instance.state, "worker_task", None)
            if old_task and not old_task.done():
                old_task.cancel()
                await asyncio.gather(old_task, return_exceptions=True)
            
            # 2. Start a fresh task
            from forward_bot.tasks import run_telegram_worker
            new_worker_task = asyncio.create_task(run_telegram_worker(settings, db))
            app_instance.state.worker_task = new_worker_task
            logger.info("telegram_reconnect_success", message="Telegram client reconnected and worker restarted successfully")
        else:
            logger.error("telegram_reconnect_failed", error="Telegram client disconnected or DB not initialized after connect attempt")
    except Exception as e:
        logger.error(
            "telegram_reconnect_failed",
            error=str(e),
            message=f"Error encountered during Telegram client reconnection: {e}"
        )


@router.post(
    "/reconnect",
    response_model=AdminReconnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger a Telegram client reconnect attempt."
)
async def reconnect(
    request: Request,
    _: str = Depends(get_current_operator),
) -> AdminReconnectResponse:
    """Triggers an asynchronous Telegram reconnection and worker restart.

    Runs in the background (fire-and-forget). Returns immediately.
    """
    # Fire and forget reconnect background task with strong reference to prevent GC
    task = asyncio.create_task(perform_reconnect(request.app))
    
    # Store reference in app state to prevent garbage collection
    if not hasattr(request.app.state, "background_tasks"):
        request.app.state.background_tasks = set()
    request.app.state.background_tasks.add(task)
    task.add_done_callback(request.app.state.background_tasks.discard)
    
    return AdminReconnectResponse(ok=True)


@router.post(
    "/cache/refresh",
    response_model=CacheRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger immediate in-memory RuleCache rebuild.",
)
async def refresh_cache(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: str = Depends(get_current_operator),
) -> CacheRefreshResponse:
    """Triggers an immediate rebuild of the RuleCache snapshot from MongoDB."""
    cache = await trigger_cache_rebuild(db)
    return CacheRefreshResponse(
        version=cache.version,
        rule_count=len(cache.rules),
        source_count=len(cache.sources),
        refreshed_at=cache.refreshed_at,
    )

