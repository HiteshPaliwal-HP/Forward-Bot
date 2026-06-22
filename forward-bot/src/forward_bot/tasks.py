"""Async background tasks for Forward Bot."""
import asyncio
from forward_bot.infrastructure.logging import logger

async def run_cache_refresher(settings=None, db=None) -> None:
    """Real cache refresher — delegates to infrastructure/cache/cache_refresher.py.

    When called without arguments (legacy / test scenarios) the function falls
    back to an infinite sleep so that task cancellation still works cleanly —
    preserving backward compatibility with existing E2E tests from Story 1.3.

    Args:
        settings: Application ``Settings`` instance with ``hot_reload_interval``.
                  When ``None`` the function sleeps indefinitely (stub mode).
        db:       Motor ``AsyncIOMotorDatabase`` instance.
                  When ``None`` the function sleeps indefinitely (stub mode).
    """
    if settings is None or db is None:
        # Stub mode: sleep until cancelled (preserves cancellation semantics)
        logger.info("cache_refresher_started", status="stub-no-settings")
        try:
            await asyncio.sleep(float("inf"))
        except asyncio.CancelledError:
            logger.info("cache_refresher_stopped")
            raise
        return

    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher as _run
    await _run(settings, db)


async def run_mapping_sweeper() -> None:
    """Stub for mapping sweeper task."""
    logger.info("mapping_sweeper_started", status="stub")
    try:
        await asyncio.sleep(float('inf'))
    except asyncio.CancelledError:
        logger.info("mapping_sweeper_stopped")
        raise

async def run_telegram_worker(settings=None, db=None) -> None:
    """Real telegram worker task runner."""
    if settings is None or db is None:
        # Stub mode: sleep until cancelled (preserves cancellation semantics)
        logger.info("telegram_worker_started", status="stub-no-settings")
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            logger.info("telegram_worker_stopped")
            raise
        return

    from forward_bot.infrastructure.telegram.worker import TelegramWorker
    worker = TelegramWorker(settings, db)
    await worker.run()
