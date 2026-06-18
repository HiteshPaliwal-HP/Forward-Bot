"""Repository for Folder documents in MongoDB."""
import re
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.api.schemas.base import SOURCE_FOLDERS, SOURCES
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository


class FolderRepository(BaseRepository):
    """Provides methods for SourceFolder specific database persistence."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, SOURCE_FOLDERS)

    def _to_entity(self, doc: dict[str, Any]) -> SourceFolder:
        """Map a MongoDB dictionary document to a SourceFolder domain entity."""
        return SourceFolder(
            id=str(doc["_id"]),
            name=doc["name"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    def _to_document(self, entity: SourceFolder) -> dict[str, Any]:
        """Map a SourceFolder domain entity to a MongoDB dictionary document."""
        doc: dict[str, Any] = {
            "name": entity.name,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at
        }
        if entity.id:
            doc["_id"] = ObjectId(entity.id)
        return doc

    async def get_folder_by_id(self, id: str) -> SourceFolder | None:
        """Fetch a SourceFolder by its database ID."""
        if not ObjectId.is_valid(id):
            return None
        doc = await self.get_by_id(id)
        return self._to_entity(doc) if doc else None

    async def get_folder_by_name(self, name: str, exclude_id: str | None = None) -> SourceFolder | None:
        """Fetch a SourceFolder by its name (case-insensitive), optionally excluding an ID."""
        escaped_name = re.escape(name)
        query: dict[str, Any] = {"name": {"$regex": f"^{escaped_name}$", "$options": "i"}}
        if exclude_id and ObjectId.is_valid(exclude_id):
            query["_id"] = {"$ne": ObjectId(exclude_id)}
        doc = await self.collection.find_one(query)
        return self._to_entity(doc) if doc else None

    async def add_folder(self, folder: SourceFolder) -> str:
        """Insert a new SourceFolder domain entity into the database and update its ID."""
        doc = self._to_document(folder)
        inserted_id = await self.insert(doc)
        folder.id = inserted_id
        return inserted_id

    async def update_folder(self, folder: SourceFolder) -> bool:
        """Update/Replace an existing SourceFolder in the database."""
        doc = self._to_document(folder)
        return await self.update(folder.id, doc)

    async def delete_folder(self, id: str) -> bool:
        """Permanently delete a Folder from the database and disassociate its sources."""
        if not ObjectId.is_valid(id):
            return False
        deleted = await self.delete(id)
        if deleted:
            # Update all sources referencing this folder to have folder_id set to None
            await self.db[SOURCES].update_many(
                {"folder_id": ObjectId(id)},
                {"$set": {"folder_id": None}}
            )
        return deleted

    async def list_folders_with_source_count(self, name_filter: str | None = None) -> list[dict[str, Any]]:
        """List folders with their source counts using a single aggregate query."""
        pipeline: list[dict[str, Any]] = []

        if name_filter:
            escaped_name = re.escape(name_filter)
            pipeline.append({
                "$match": {
                    "name": {"$regex": f"^{escaped_name}$", "$options": "i"}
                }
            })

        pipeline.extend([
            {
                "$lookup": {
                    "from": SOURCES,
                    "localField": "_id",
                    "foreignField": "folder_id",
                    "as": "sources"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "source_count": {"$size": "$sources"}
                }
            },
            {
                "$sort": {
                    "name": 1
                }
            }
        ])

        cursor = self.collection.aggregate(pipeline)
        docs = await cursor.to_list(length=None)

        results = []
        for doc in docs:
            doc["id"] = str(doc["_id"])
            results.append(doc)
        return results
