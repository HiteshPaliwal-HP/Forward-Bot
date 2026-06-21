"""Repository for MessageMapping documents in MongoDB."""
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.api.schemas.base import MESSAGE_MAPPINGS
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository


class MappingRepository(BaseRepository):
    """Provides methods for MessageMapping specific database persistence."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, MESSAGE_MAPPINGS)

    def _to_entity(self, doc: dict[str, Any]) -> MessageMapping:
        """Map a MongoDB dictionary document to a MessageMapping domain entity."""
        return MessageMapping(
            id=str(doc["_id"]),
            forwarding_rule_id=str(doc["forwarding_rule_id"]),
            source_channel_id=doc["source_channel_id"],
            source_message_id=doc["source_message_id"],
            destination_channel_id=doc["destination_channel_id"],
            destination_message_id=doc["destination_message_id"],
            forwarded_at=doc["forwarded_at"],
        )

    def _to_document(self, entity: MessageMapping) -> dict[str, Any]:
        """Map a MessageMapping domain entity to a MongoDB dictionary document."""
        doc: dict[str, Any] = {
            "forwarding_rule_id": ObjectId(entity.forwarding_rule_id),
            "source_channel_id": entity.source_channel_id,
            "source_message_id": entity.source_message_id,
            "destination_channel_id": entity.destination_channel_id,
            "destination_message_id": entity.destination_message_id,
            "forwarded_at": entity.forwarded_at,
        }
        if entity.id:
            doc["_id"] = ObjectId(entity.id)
        return doc

    async def add_mapping(self, mapping: MessageMapping) -> str:
        """Insert a new MessageMapping domain entity into the database and update its ID."""
        doc = self._to_document(mapping)
        inserted_id = await self.insert(doc)
        mapping.id = inserted_id
        return inserted_id

    async def get_by_source_message(
        self,
        source_channel_id: int,
        source_message_id: int,
        forwarding_rule_id: str
    ) -> MessageMapping | None:
        """Look up parent mapping. Returns MessageMapping entity or None if no mapping exists."""
        if not ObjectId.is_valid(forwarding_rule_id):
            return None
        doc = await self.collection.find_one({
            "source_channel_id": source_channel_id,
            "source_message_id": source_message_id,
            "forwarding_rule_id": ObjectId(forwarding_rule_id)
        })
        return self._to_entity(doc) if doc else None
