"""Generic base repository for MongoDB operations using Motor."""
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class BaseRepository:
    """Encapsulates common async MongoDB operations."""

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.db = db
        self.collection = db[collection_name]

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        """Fetch a document by its 24-character hexadecimal ObjectId."""
        if not ObjectId.is_valid(id):
            return None
        return await self.collection.find_one({"_id": ObjectId(id)})

    async def insert(self, document: dict[str, Any]) -> str:
        """Insert a single document into MongoDB and return its hex string ID."""
        res = await self.collection.insert_one(document)
        return str(res.inserted_id)

    async def update(self, id: str, document: dict[str, Any]) -> bool:
        """Replace an existing document by its ID. Returns True if modified."""
        if not ObjectId.is_valid(id):
            return False
        doc_copy = document.copy()
        doc_copy.pop("_id", None)
        doc_copy.pop("id", None)
        res = await self.collection.replace_one({"_id": ObjectId(id)}, doc_copy)
        return res.modified_count > 0

    async def delete(self, id: str) -> bool:
        """Delete a document by ID. Returns True if deleted."""
        if not ObjectId.is_valid(id):
            return False
        res = await self.collection.delete_one({"_id": ObjectId(id)})
        return res.deleted_count > 0

    async def find(self, filter_query: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch multiple documents matching a filter query."""
        cursor = self.collection.find(filter_query)
        return await cursor.to_list(length=None)
