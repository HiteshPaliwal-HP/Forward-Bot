"""Use case for registering a new Telegram source."""
from datetime import datetime, timezone
from typing import Any
from telethon.tl.types import Channel, Chat

from forward_bot.domain.entities.source import Source
from forward_bot.domain.exceptions import (
    TelegramUnavailableException,
    TelegramResolveFailedException,
    SourceAlreadyExistsException,
)
from forward_bot.infrastructure.logging import logger
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository
from forward_bot.infrastructure.telegram.client import TelegramClientHolder


class RegisterSource:
    """Orchestrates source registration and entity resolution via Telegram."""

    def __init__(self, source_repo: SourceRepository, tg_client: TelegramClientHolder) -> None:
        self.source_repo = source_repo
        self.tg_client = tg_client

    async def execute(self, telegram_reference: str | int, display_name: str) -> Source:
        """Resolve a Telegram reference and register it as a Source."""
        # 1. Telegram Connection Gate
        if not self.tg_client.is_connected:
            raise TelegramUnavailableException(
                "Telegram client is not connected. Cannot resolve source reference."
            )

        # 2. Reference normalisation / parsing
        entity_ref: str | int = telegram_reference
        if isinstance(telegram_reference, str):
            ref_str = telegram_reference.strip()
            # If it's a numeric ID (e.g. -100123456 or 123456), convert to int
            if not ref_str.startswith("@"):
                try:
                    # Support negative IDs
                    entity_ref = int(ref_str)
                except ValueError:
                    pass

        # 3. Resolve Telegram Entity
        entity: Any = None
        try:
            entity = await self.tg_client.client.get_entity(entity_ref)
        except Exception as e:
            logger.error(
                "telegram_resolve_failed",
                error=str(e),
                message=f"Failed to resolve Telegram reference: {telegram_reference}"
            )
            raise TelegramResolveFailedException(str(e))

        # 4. Map Entity Type
        if isinstance(entity, Channel):
            if getattr(entity, "megagroup", False):
                entity_type = "group"
            else:
                entity_type = "channel"
        elif isinstance(entity, Chat):
            entity_type = "group"
        else:
            raise TelegramResolveFailedException(
                f"Resolved entity of type {type(entity).__name__} is neither a Channel nor a Group."
            )

        # Extract normalized username
        username = getattr(entity, "username", None)
        if username:
            username = username.lstrip("@").strip()
            if not username:
                username = None
        else:
            username = None

        logger.info(
            "source_resolved",
            telegram_id=entity.id,
            telegram_username=username,
            type=entity_type,
            message="Telegram entity successfully resolved"
        )

        # 5. Duplicate Registration Check
        # Check by telegram_id
        existing = await self.source_repo.get_source_by_telegram_id(entity.id)
        if existing:
            logger.warning(
                "source_already_exists",
                telegram_id=entity.id,
                message="Source already exists in database (by Telegram ID)"
            )
            raise SourceAlreadyExistsException(entity.id)

        # Check by username if present
        if username:
            existing_by_username = await self.source_repo.get_source_by_username(username)
            if existing_by_username:
                logger.warning(
                    "source_already_exists",
                    telegram_username=username,
                    message="Source already exists in database (by username)"
                )
                raise SourceAlreadyExistsException(entity.id)

        # 6. Save to Database
        now = datetime.now(timezone.utc)
        source = Source(
            id=None,
            telegram_id=entity.id,
            telegram_username=username,
            display_name=display_name,
            type=entity_type,
            folder_id=None,
            created_at=now,
            updated_at=now,
        )

        inserted_id = await self.source_repo.add_source(source)

        logger.info(
            "source_registered",
            source_id=inserted_id,
            telegram_id=entity.id,
            telegram_username=username,
            display_name=display_name,
            type=entity_type,
            message="Source registered successfully in database"
        )

        return source
