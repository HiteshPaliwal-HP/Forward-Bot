"""Repository for Source documents in MongoDB."""
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from forward_bot.domain.entities.source import Source
from forward_bot.api.schemas.base import SOURCES
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository


class SourceRepository(BaseRepository):
    """Provides methods for Source specific database persistence."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, SOURCES)

    def _to_entity(self, doc: dict[str, Any]) -> Source:
        """Map a MongoDB dictionary document to a Source domain entity."""
        folder_id = doc.get("folder_id")
        return Source(
            id=str(doc["_id"]),
            telegram_id=doc["telegram_id"],
            telegram_username=doc.get("telegram_username"),
            display_name=doc["display_name"],
            type=doc["type"],
            folder_id=str(folder_id) if folder_id is not None else None,
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    def _to_document(self, entity: Source) -> dict[str, Any]:
        """Map a Source domain entity to a MongoDB dictionary document."""
        doc: dict[str, Any] = {
            "telegram_id": entity.telegram_id,
            "telegram_username": entity.telegram_username,
            "display_name": entity.display_name,
            "type": entity.type,
            "folder_id": ObjectId(entity.folder_id) if entity.folder_id else None,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at
        }
        if entity.id:
            doc["_id"] = ObjectId(entity.id)
        return doc

    async def get_source_by_id(self, id: str) -> Source | None:
        """Fetch a Source by its database ID."""
        doc = await self.get_by_id(id)
        return self._to_entity(doc) if doc else None

    async def get_source_by_telegram_id(self, telegram_id: int) -> Source | None:
        """Fetch a Source by its Telegram ID."""
        doc = await self.collection.find_one({"telegram_id": telegram_id})
        return self._to_entity(doc) if doc else None

    async def get_source_by_username(self, username: str) -> Source | None:
        """Fetch a Source by its normalized username (without @)."""
        normalized = username.lstrip("@").strip()
        doc = await self.collection.find_one({"telegram_username": normalized})
        return self._to_entity(doc) if doc else None

    async def add_source(self, source: Source) -> str:
        """Insert a new Source domain entity into the database and update its ID."""
        doc = self._to_document(source)
        inserted_id = await self.insert(doc)
        source.id = inserted_id
        return inserted_id

    async def delete_source(self, id: str) -> bool:
        """Permanently delete a Source from the database."""
        return await self.delete(id)

    async def get_referencing_rules_count(self, source_id: str) -> int:
        """Count the forwarding rules referencing this source."""
        if not ObjectId.is_valid(source_id):
            return 0
        from forward_bot.api.schemas.base import FORWARDING_RULES
        count = await self.db[FORWARDING_RULES].count_documents({"source_id": ObjectId(source_id)})
        return count
