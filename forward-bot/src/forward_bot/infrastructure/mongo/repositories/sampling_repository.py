"""Repository for sampling counter documents in MongoDB."""
from bson import ObjectId
from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorDatabase

from forward_bot.api.schemas.base import SAMPLING_COUNTERS
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository


class SamplingRepository(BaseRepository):
    """Provides methods for sampling counter persistence in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, SAMPLING_COUNTERS)

    async def get_counter(self, rule_id: str) -> int:
        """Retrieve the current counter value for a forwarding rule.

        Returns 0 if no counter document exists.
        """
        query_id = ObjectId(rule_id) if ObjectId.is_valid(rule_id) else rule_id
        doc = await self.collection.find_one({"_id": query_id})
        if not doc:
            return 0
        return doc.get("counter", 0)

    async def increment_counter(self, rule_id: str) -> int:
        """Atomically increment the counter for a forwarding rule.

        Returns the new incremented value.
        """
        query_id = ObjectId(rule_id) if ObjectId.is_valid(rule_id) else rule_id
        doc = await self.collection.find_one_and_update(
            {"_id": query_id},
            {"$inc": {"counter": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return 1
        return doc.get("counter", 1)
