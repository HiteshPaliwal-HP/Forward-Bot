"""FastAPI router for live Telegram client operations."""
from fastapi import APIRouter, Depends, status
from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import get_telegram_client
from forward_bot.infrastructure.telegram.client import TelegramClientHolder
from forward_bot.infrastructure.logging import logger

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


@router.get("/dialogs")
async def list_telegram_dialogs(
    tg_client: TelegramClientHolder = Depends(get_telegram_client),
    _: str = Depends(get_current_operator),
) -> dict:
    """Fetch channels and groups from the live connected Telegram account dialogs list."""
    if not tg_client.is_connected or tg_client.client is None:
        return {
            "connected": False,
            "dialogs": []
        }

    dialogs = []
    try:
        # Fetch the active dialogues (capped at 250 items for rapid lookup)
        async for dialog in tg_client.client.iter_dialogs(limit=250):
            if dialog.is_channel or dialog.is_group:
                entity = dialog.entity
                username = getattr(entity, "username", None)
                dialogs.append({
                    "id": str(dialog.id),
                    "name": dialog.name or "Unnamed Dialog",
                    "username": username,
                    "is_channel": dialog.is_channel,
                    "is_group": dialog.is_group
                })
    except Exception as e:
        logger.error("failed_to_fetch_telegram_dialogs", error=str(e))
        return {
            "connected": True,
            "error": "Failed to retrieve dialogs from Telegram.",
            "dialogs": []
        }

    return {
        "connected": True,
        "dialogs": dialogs
    }
