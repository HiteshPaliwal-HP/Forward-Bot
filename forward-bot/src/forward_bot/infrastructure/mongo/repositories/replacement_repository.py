"""MongoDB repository for ReplacementRule entities."""
from forward_bot.api.schemas.base import REPLACEMENT_RULES
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository
from forward_bot.domain.entities.replacement_rule import ReplacementRule


class ReplacementRuleRepository(BaseRepository):
    """Repository for CRUD operations on the replacement_rules MongoDB collection.

    Extends BaseRepository following the same pattern as ForwardingRuleRepository.
    All CRUD methods are async and use motor (Motor AsyncIO).

    Key design decision: `forwarding_rule_id` is stored as a plain hex string (NOT BSON ObjectId),
    consistent with the existing cascade delete in ForwardingRuleRepository.delete_rule().
    """

    def __init__(self, db):
        super().__init__(db, REPLACEMENT_RULES)

    def _to_entity(self, doc: dict) -> ReplacementRule:
        """Map a MongoDB document dict to a ReplacementRule domain entity."""
        return ReplacementRule(
            id=str(doc["_id"]),
            forwarding_rule_id=doc["forwarding_rule_id"],  # already stored as string
            search_text=doc["search_text"],
            replacement_text=doc["replacement_text"],
            match_mode=doc["match_mode"],
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    def _to_document(self, entity: ReplacementRule) -> dict:
        """Map a ReplacementRule domain entity to a MongoDB document dict."""
        doc = {
            "forwarding_rule_id": entity.forwarding_rule_id,  # store as plain string
            "search_text": entity.search_text,
            "replacement_text": entity.replacement_text,
            "match_mode": entity.match_mode,
            "is_active": entity.is_active,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }
        if entity.id:
            from bson import ObjectId
            doc["_id"] = ObjectId(entity.id)
        return doc

    async def get_replacement_by_id(self, id: str) -> ReplacementRule | None:
        """Fetch a single replacement rule by its ObjectId hex string. Returns None if not found."""
        doc = await self.get_by_id(id)
        return self._to_entity(doc) if doc else None

    async def add_replacement(self, replacement: ReplacementRule) -> str:
        """Insert a new replacement rule. Sets replacement.id to the inserted ObjectId string."""
        doc = self._to_document(replacement)
        inserted_id = await self.insert(doc)
        replacement.id = inserted_id
        return inserted_id

    async def update_replacement(self, id: str, replacement: ReplacementRule) -> bool:
        """Replace all fields of an existing replacement rule. Returns True if modified."""
        doc = self._to_document(replacement)
        return await self.update(id, doc)

    async def delete_replacement(self, id: str) -> bool:
        """Delete a replacement rule by ObjectId. Returns True if deleted."""
        return await self.delete(id)

    async def list_all_replacements_for_rules(
        self, rule_ids: list[str]
    ) -> dict[str, list[ReplacementRule]]:
        """Fetch ALL replacement rules for a set of forwarding rule IDs in ONE query.

        Uses a ``$in`` filter to fetch all matching documents in a single MongoDB
        round-trip, then groups results in-memory by ``forwarding_rule_id``.
        Within each group the order is ``created_at ASC, _id ASC`` (pipeline order, FR-7).

        This is the O(1) replacement for the O(N) per-rule sequential loop previously
        used in ``build_rule_cache``. At NFR-Scale (100 active rules) this reduces cache
        refresh DB round-trips from 101 to 4 (sources, folders, rules, replacements).

        Args:
            rule_ids: List of forwarding rule ID hex strings whose replacement rules to fetch.

        Returns:
            ``dict[forwarding_rule_id, list[ReplacementRule]]`` — every requested rule_id
            appears as a key; missing ones map to ``[]``.
        """
        if not rule_ids:
            return {}

        cursor = (
            self.collection.find({"forwarding_rule_id": {"$in": rule_ids}})
            .sort([("created_at", 1), ("_id", 1)])  # pipeline application order (FR-7)
        )
        docs = await cursor.to_list(length=None)

        # Group in-memory; pre-seed all requested IDs so callers get [] for rules with no replacements
        grouped: dict[str, list[ReplacementRule]] = {rid: [] for rid in rule_ids}
        for doc in docs:
            entity = self._to_entity(doc)
            grouped.setdefault(entity.forwarding_rule_id, []).append(entity)
        return grouped

    async def list_replacements_for_rule(self, rule_id: str) -> list[ReplacementRule]:
        """List all replacement rules for a parent forwarding rule, ordered by created_at ASC.

        Order is ascending (oldest first) because this is the pipeline application order (FR-7).
        Uses to_list(length=None) since replacement rules per rule are bounded in practice.
        """
        cursor = (
            self.collection.find({"forwarding_rule_id": rule_id})
            .sort([("created_at", 1), ("_id", 1)])  # ASC with secondary _id sort to prevent collision
        )
        docs = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in docs]
