"""Repository for ForwardingRule documents in MongoDB."""
from typing import Any
from bson import ObjectId
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    TimeWindowConfig,
    SamplingConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
)
from forward_bot.api.schemas.base import FORWARDING_RULES, REPLACEMENT_RULES
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository


class ForwardingRuleRepository(BaseRepository):
    """Provides methods for ForwardingRule document persistence in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, FORWARDING_RULES)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, doc: dict[str, Any]) -> ForwardingRule:
        """Map a MongoDB document to a ForwardingRule domain entity."""
        time_window = None
        if doc.get("time_window"):
            tw = doc["time_window"]
            time_window = TimeWindowConfig(
                timezone=tw["timezone"],
                days_of_week=tw["days_of_week"],
                start_time=tw["start_time"],
                end_time=tw["end_time"],
            )

        sampling_data = doc.get("sampling", {"n": 1})
        sampling = SamplingConfig(n=sampling_data.get("n", 1))

        attribution_data = doc.get("attribution", {})
        attribution = AttributionConfig(
            enabled=attribution_data.get("enabled", False),
            position=attribution_data.get("position", "prefix"),
            format=attribution_data.get("format", "From {source_name}"),
        )

        auto_replace_data = doc.get("auto_replace_source_refs", {})
        auto_replace = AutoReplaceSourceRefsConfig(
            enabled=auto_replace_data.get("enabled", False),
            replacement=auto_replace_data.get("replacement"),
            replace_display_name=auto_replace_data.get("replace_display_name", False),
        )

        media_replacement_data = doc.get("media_replacement", {})
        media_replacement = MediaReplacementConfig(
            enabled=media_replacement_data.get("enabled", False),
            replacement_image_path=media_replacement_data.get("replacement_image_path"),
            replacement_caption_mode=media_replacement_data.get("replacement_caption_mode", "use_source"),
        )

        return ForwardingRule(
            id=str(doc["_id"]),
            source_id=str(doc["source_id"]),  # BSON ObjectId → hex string
            destination_channel=doc["destination_channel"],
            is_active=doc.get("is_active", False),
            keyword_match_mode=doc.get("keyword_match_mode", "literal"),
            block_keywords=doc.get("block_keywords", []),
            allow_keywords=doc.get("allow_keywords", []),
            media_type_filter=doc.get("media_type_filter", ["text", "photo"]),
            remove_links=doc.get("remove_links", False),
            remove_hashtags=doc.get("remove_hashtags", False),
            remove_mentions=doc.get("remove_mentions", False),
            forward_media=doc.get("forward_media", "forward"),
            sampling=sampling,
            time_window=time_window,
            attribution=attribution,
            auto_replace_source_refs=auto_replace,
            media_replacement=media_replacement,
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    def _to_document(self, entity: ForwardingRule) -> dict[str, Any]:
        """Map a ForwardingRule domain entity to a MongoDB document."""
        doc: dict[str, Any] = {
            # Store source_id as BSON ObjectId — required by SourceRepository.get_referencing_rules_count()
            "source_id": ObjectId(entity.source_id),
            "destination_channel": entity.destination_channel,
            "is_active": entity.is_active,
            "keyword_match_mode": entity.keyword_match_mode,
            "block_keywords": entity.block_keywords,
            "allow_keywords": entity.allow_keywords,
            "media_type_filter": entity.media_type_filter,
            "remove_links": entity.remove_links,
            "remove_hashtags": entity.remove_hashtags,
            "remove_mentions": entity.remove_mentions,
            "forward_media": entity.forward_media,
            "sampling": {"n": entity.sampling.n},
            "time_window": (
                {
                    "timezone": entity.time_window.timezone,
                    "days_of_week": entity.time_window.days_of_week,
                    "start_time": entity.time_window.start_time,
                    "end_time": entity.time_window.end_time,
                }
                if entity.time_window
                else None
            ),
            "attribution": {
                "enabled": entity.attribution.enabled,
                "position": entity.attribution.position,
                "format": entity.attribution.format,
            },
            "auto_replace_source_refs": {
                "enabled": entity.auto_replace_source_refs.enabled,
                "replacement": entity.auto_replace_source_refs.replacement,
                "replace_display_name": entity.auto_replace_source_refs.replace_display_name,
            },
            "media_replacement": {
                "enabled": entity.media_replacement.enabled,
                "replacement_image_path": entity.media_replacement.replacement_image_path,
                "replacement_caption_mode": entity.media_replacement.replacement_caption_mode,
            },
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }
        if entity.id:
            doc["_id"] = ObjectId(entity.id)
        return doc

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def get_rule_by_id(self, id: str) -> ForwardingRule | None:
        """Fetch a ForwardingRule by its database ID. Returns None for invalid/missing IDs."""
        doc = await self.get_by_id(id)
        return self._to_entity(doc) if doc else None

    async def add_rule(self, rule: ForwardingRule) -> str:
        """Insert a new ForwardingRule into the database and return the inserted ID string."""
        doc = self._to_document(rule)
        inserted_id = await self.insert(doc)
        rule.id = inserted_id
        return inserted_id

    async def update_rule(self, id: str, rule: ForwardingRule) -> bool:
        """Full replacement update for a ForwardingRule. Returns True if document was modified."""
        doc = self._to_document(rule)
        return await self.update(id, doc)

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a ForwardingRule and cascade-delete all child ReplacementRules.

        Mirrors FolderRepository.delete_folder() cross-collection pattern.
        replacement_rules.forwarding_rule_id is stored as plain string (not ObjectId).
        """
        # 1. Cascade-delete child replacement rules (forwarding_rule_id stored as string)
        await self.db[REPLACEMENT_RULES].delete_many({"forwarding_rule_id": rule_id})
        # 2. Delete the rule itself
        return await self.delete(rule_id)

    async def enable_rule(self, rule_id: str) -> bool:
        """Set is_active=True. Returns True if document was modified; False if not found."""
        if not ObjectId.is_valid(rule_id):
            return False
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": ObjectId(rule_id)},
            {"$set": {"is_active": True, "updated_at": now}}
        )
        return res.modified_count > 0

    async def disable_rule(self, rule_id: str) -> bool:
        """Set is_active=False. Returns True if document was modified; False if not found."""
        if not ObjectId.is_valid(rule_id):
            return False
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": ObjectId(rule_id)},
            {"$set": {"is_active": False, "updated_at": now}}
        )
        return res.modified_count > 0

    async def list_rules(
        self,
        source_repo=None,
        source_id: str | None = None,
        destination_channel: str | None = None,
        is_active: bool | None = None,
        folder_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ForwardingRule], int]:
        """List ForwardingRules with optional filters and pagination sorted by created_at DESC.

        Args:
            source_repo: SourceRepository instance (required when folder_id filter is provided).
            source_id: Filter by source ObjectId hex string.
            destination_channel: Filter by destination channel string.
            is_active: Filter by is_active boolean.
            folder_id: Filter rules whose source has this folder_id (two-step join).
            page: 1-indexed page number.
            page_size: Maximum items per page (capped at 200 by router).
        """
        query: dict[str, Any] = {}

        if source_id is not None:
            if not ObjectId.is_valid(source_id):
                raise ValueError("Invalid source_id format")
            query["source_id"] = ObjectId(source_id)

        if destination_channel is not None:
            query["destination_channel"] = destination_channel

        if is_active is not None:
            query["is_active"] = is_active

        if folder_id is not None:
            if not ObjectId.is_valid(folder_id):
                raise ValueError("Invalid folder_id format")
            if source_repo is not None:
                # Two-step join: fetch all sources in the folder, then filter rules by source_ids
                sources = await source_repo.get_sources_by_folder_id(folder_id)
                source_ids = [ObjectId(s.id) for s in sources]
                query["source_id"] = {"$in": source_ids}

        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        docs = await cursor.to_list(length=page_size)
        rules = [self._to_entity(doc) for doc in docs]
        return rules, total
