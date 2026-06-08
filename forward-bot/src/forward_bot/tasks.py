"""Async background tasks for Forward Bot."""
import asyncio
from forward_bot.infrastructure.logging import logger

async def run_cache_refresher() -> None:
    """Stub for cache refresher task."""
    logger.info("cache_refresher_started", status="stub")
    try:
        await asyncio.sleep(float('inf'))
    except asyncio.CancelledError:
        logger.info("cache_refresher_stopped")
        raise

async def run_mapping_sweeper() -> None:
    """Stub for mapping sweeper task."""
    logger.info("mapping_sweeper_started", status="stub")
    try:
        await asyncio.sleep(float('inf'))
    except asyncio.CancelledError:
        logger.info("mapping_sweeper_stopped")
        raise

async def run_telegram_worker() -> None:
    """Stub for telegram worker task."""
    logger.info("telegram_worker_started", status="stub")
    try:
        await asyncio.sleep(float('inf'))
    except asyncio.CancelledError:
        logger.info("telegram_worker_stopped")
        raise
