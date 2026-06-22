"""Background task for periodically sweeping expired message mappings from MongoDB."""
import asyncio
from forward_bot.infrastructure.logging import logger
from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository


async def run_mapping_sweeper(settings=None, db=None) -> None:
    """Hourly background task loop that deletes expired mappings older than retention days."""
    if settings is None or db is None:
        # Stub mode (keeps existing E2E/lifespan startup logic working safely)
        logger.info("mapping_sweeper_started", status="stub-no-settings")
        try:
            await asyncio.sleep(float("inf"))
        except asyncio.CancelledError:
            logger.info("mapping_sweeper_stopped")
            raise
        return

    logger.info("mapping_sweeper_started", status="active")
    repo = MappingRepository(db)

    try:
        while True:
            try:
                retention_days = settings.mapping_retention_days
                deleted_count = await repo.delete_expired_mappings(retention_days)
                logger.info(
                    "mapping_sweep_completed",
                    deleted_count=deleted_count
                )
            except Exception as e:
                logger.error("mapping_sweeper_error", error=str(e))

            # Sleep for 1 hour (3600 seconds)
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("mapping_sweeper_stopped")
        raise
