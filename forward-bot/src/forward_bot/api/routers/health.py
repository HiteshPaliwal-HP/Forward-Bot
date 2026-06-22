"""Health check routers for liveness, readiness, and telegram connectivity."""
from typing import Any
from fastapi import APIRouter, Response, status
from forward_bot.infrastructure.mongo import mongo_client
from forward_bot.infrastructure.telegram import telegram_client
from forward_bot.infrastructure.logging import logger

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    """Liveness probe. Returns HTTP 200 OK when application shell is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check(response: Response) -> dict[str, str]:
    """Readiness probe. Checks MongoDB connectivity to confirm app is ready to serve traffic."""
    try:
        if mongo_client.db is not None:
            # Ping database to verify connection is active and reachable
            await mongo_client.db.command("ping")
            return {"mongodb": "up"}
        else:
            logger.error("mongodb_ready_check_failed", error="Database connection not initialized")
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"mongodb": "down"}
    except Exception as e:
        logger.exception("mongodb_ready_check_failed", error=str(e))
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"mongodb": "down"}


@router.get("/telegram")
async def telegram_status(response: Response) -> dict[str, Any]:
    """Telegram connection status."""
    status_str = telegram_client.status
    if status_str != "connected":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "telegram": status_str,
        "last_event": telegram_client.last_event
    }
