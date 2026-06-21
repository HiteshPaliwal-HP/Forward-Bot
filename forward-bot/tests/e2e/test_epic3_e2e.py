"""
E2E & Integration Tests for Epic 3: Forwarding Rule Configuration.

Covers:
  3.1 Forwarding Rule CRUD API
  3.2 Replacement Rule CRUD API
  3.3 Atomic Rule Cache & Cache Refresher

The E2E test uses an in-memory MockDatabase (same pattern as test_epic2_e2e.py)
to exercise full HTTP request → use-case → repository → response cycles without a
real MongoDB instance.  The cache-related tests are unit-level (mocked repos) to
avoid async complexity while still validating the cache layer end-to-end.
"""
import asyncio
import pytest
import re
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    SamplingConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
)
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
from forward_bot.api.dependencies.providers import (
    get_rule_repository,
    get_source_repository,
    get_replacement_repository,
)


# ---------------------------------------------------------------------------
# In-Memory MockDatabase (mirrors test_epic2_e2e.py pattern)
# Supports: insert_one, find_one, find, count_documents, replace_one,
#           delete_one, delete_many, update_one, update_many, aggregate,
#           create_index
# ---------------------------------------------------------------------------

class MockCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field_or_list, direction=1):
        """Accept both single (field, direction) and Motor multi-sort [(field, dir), ...] style."""
        if isinstance(field_or_list, list):
            # Multi-sort: apply in reverse order so first key has highest priority
            for field, direction in reversed(field_or_list):
                rev = direction == -1
                self.items.sort(
                    key=lambda x, f=field: (x.get(f) or "")
                    if isinstance(x.get(f), str)
                    else (x.get(f) or datetime.min),
                    reverse=rev,
                )
        else:
            field = field_or_list
            rev = direction == -1
            self.items.sort(
                key=lambda x: (x.get(field) or datetime.min)
                if not isinstance(x.get(field), str)
                else x.get(field).lower(),
                reverse=rev,
            )
        return self

    def skip(self, n):
        self.items = self.items[n:]
        return self

    def limit(self, n):
        self.items = self.items[:n]
        return self

    async def to_list(self, length=None):
        if length is not None:
            return self.items[:length]
        return self.items


class MockCollection:
    def __init__(self, data_store):
        self.data_store = data_store

    async def create_index(self, *args, **kwargs):
        return None

    async def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        # Deep-copy to avoid mutation issues
        import copy
        self.data_store.append(copy.deepcopy(doc))
        res = MagicMock()
        res.inserted_id = doc["_id"]
        return res

    async def find_one(self, query):
        for doc in self.data_store:
            if self._match(doc, query):
                return doc
        return None

    def find(self, query=None):
        query = query or {}
        matched = [doc for doc in self.data_store if self._match(doc, query)]
        return MockCursor(matched)

    async def count_documents(self, query):
        return sum(1 for doc in self.data_store if self._match(doc, query))

    async def replace_one(self, filter_query, replacement):
        import copy
        for i, doc in enumerate(self.data_store):
            if self._match(doc, filter_query):
                new_doc = copy.deepcopy(replacement)
                if "_id" not in new_doc and "_id" in doc:
                    new_doc["_id"] = doc["_id"]
                self.data_store[i] = new_doc
                res = MagicMock()
                res.modified_count = 1
                return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def update_one(self, filter_query, update_op):
        set_op = update_op.get("$set", {})
        for doc in self.data_store:
            if self._match(doc, filter_query):
                for k, v in set_op.items():
                    doc[k] = v
                res = MagicMock()
                res.modified_count = 1
                return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def update_many(self, filter_query, update_op):
        count = 0
        set_op = update_op.get("$set", {})
        for doc in self.data_store:
            if self._match(doc, filter_query):
                for k, v in set_op.items():
                    doc[k] = v
                count += 1
        res = MagicMock()
        res.modified_count = count
        return res

    async def delete_one(self, filter_query):
        for i, doc in enumerate(self.data_store):
            if self._match(doc, filter_query):
                self.data_store.pop(i)
                res = MagicMock()
                res.deleted_count = 1
                return res
        res = MagicMock()
        res.deleted_count = 0
        return res

    async def delete_many(self, filter_query):
        original_len = len(self.data_store)
        self.data_store[:] = [
            doc for doc in self.data_store if not self._match(doc, filter_query)
        ]
        deleted = original_len - len(self.data_store)
        res = MagicMock()
        res.deleted_count = deleted
        return res

    def aggregate(self, pipeline):
        """Minimal aggregate: supports $match + $lookup (unused) — returns all docs."""
        matched = list(self.data_store)
        if pipeline and "$match" in pipeline[0]:
            matched = [doc for doc in matched if self._match(doc, pipeline[0]["$match"])]
        return MockCursor(matched)

    def _match(self, doc, query):  # noqa: C901
        for k, v in query.items():
            val = doc.get(k)
            if k == "_id" and not isinstance(v, dict):
                if val != v:
                    return False
            elif isinstance(v, dict):
                if "$ne" in v and val == v["$ne"]:
                    return False
                if "$in" in v and val not in v["$in"]:
                    return False
                if "$regex" in v:
                    pattern = v["$regex"]
                    options = v.get("$options", "")
                    flags = re.IGNORECASE if "i" in options else 0
                    cleaned = (
                        pattern.replace("\\ ", " ").replace("^", "").replace("$", "")
                    )
                    val_str = str(val)
                    if "i" in options:
                        if cleaned.lower() != val_str.lower():
                            return False
                    else:
                        if cleaned != val_str:
                            return False
            else:
                if val != v:
                    return False
        return True


class MockDatabase:
    def __init__(self):
        self.stores: dict[str, list] = {}
        self.collections: dict[str, MockCollection] = {}

    def __getitem__(self, name):
        if name not in self.collections:
            store = self.stores.setdefault(name, [])
            self.collections[name] = MockCollection(store)
        return self.collections[name]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_settings():
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=12345,
        telegram_api_hash="test-api-hash",
        ui_enabled=False,
        _env_file=None,
    )


@pytest.fixture
def app_no_lifespan(base_settings):
    return create_app(base_settings, lifespan=None)


@pytest.fixture(autouse=True)
def mock_db():
    from forward_bot.infrastructure.mongo.client import mongo_client
    fake_db = MockDatabase()
    with patch.object(mongo_client, "db", fake_db):
        yield fake_db


# Pre-seed a source into the mock DB so rules can reference it.
@pytest.fixture
def seeded_source(mock_db):
    source_id = ObjectId()
    doc = {
        "_id": source_id,
        "telegram_id": 1000000001,
        "telegram_username": "news_channel",
        "display_name": "News Channel",
        "type": "channel",
        "folder_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mock_db["sources"].data_store.append(doc)
    return str(source_id)


# ---------------------------------------------------------------------------
# E2E Workflow Test: Stories 3.1 + 3.2
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic3_e2e_workflow(app_no_lifespan, seeded_source):
    """
    Validates the entire Epic 3 workflow end-to-end:
      Story 3.1 — Forwarding Rule CRUD
        - Auth gate enforcement
        - Create rule (201 with all default fields)
        - Reject non-existent source_id (422 source_not_found)
        - Reject self-referential rule (422 self_referential_rule)
        - Reject invalid regex keywords (422 invalid_regex)
        - Reject invalid IANA timezone (422 invalid_timezone)
        - Reject media_replacement enabled + null path (422 media_replacement_path_required)
        - Accept cross-midnight time window (201)
        - Enable rule (200 {ok: true}) and verify is_active in list
        - Disable rule (200 {ok: true})
        - Get single rule (200) and not-found (404)
        - List rules with filter by source_id, is_active, destination_channel
        - Update rule via PUT (200 with updated fields + same validations)
        - Delete rule cascade (204), verify replacement_rules also removed (Story 3.2 cascade)
        - Delete non-existent rule (404)

      Story 3.2 — Replacement Rule CRUD
        - Create replacement rule under forwarding rule (201)
        - Reject invalid regex in search_text (422)
        - Reject creation for non-existent parent rule (404)
        - List replacement rules ordered by created_at ASC
        - Update replacement rule (200, updated_at refreshed)
        - Update not-found replacement rule (404)
        - Delete replacement rule (204)
        - Auth gate for replacement-rule endpoints (401)
        - Cascade: deleting parent rule removes its replacement rules
    """
    headers = {"X-API-Key": "test-api-key"}
    source_id = seeded_source

    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan), base_url="http://test"
    ) as ac:

        # ── AUTH GATE ────────────────────────────────────────────────────────
        # AC14: Rules endpoints require authentication
        assert (await ac.get("/api/v1/rules")).status_code == 401
        assert (await ac.post("/api/v1/rules", json={})).status_code == 401

        # ── CREATE RULE — HAPPY PATH ─────────────────────────────────────────
        # AC1: POST /api/v1/rules returns 201 with all defaults
        payload = {
            "source_id": source_id,
            "destination_channel": "@target_news",
        }
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        rule1 = res.json()
        rule1_id = rule1["id"]
        assert len(rule1_id) == 24
        assert rule1["source_id"] == source_id
        assert rule1["destination_channel"] == "@target_news"
        assert rule1["is_active"] is False
        assert rule1["keyword_match_mode"] == "literal"
        assert rule1["block_keywords"] == []
        assert rule1["allow_keywords"] == []
        assert rule1["media_type_filter"] == ["text", "photo"]
        assert rule1["remove_links"] is False
        assert rule1["remove_hashtags"] is False
        assert rule1["remove_mentions"] is False
        assert rule1["forward_media"] == "forward"
        assert rule1["sampling"] == {"n": 1}
        assert rule1["time_window"] is None
        assert rule1["attribution"] == {
            "enabled": False,
            "position": "prefix",
            "format": "From {source_name}",
        }
        assert rule1["auto_replace_source_refs"] == {
            "enabled": False,
            "replacement": None,
            "replace_display_name": False,
        }
        assert rule1["media_replacement"] == {
            "enabled": False,
            "replacement_image_path": None,
            "replacement_caption_mode": "use_source",
        }

        # AC1: Duplicate (source_id, destination_channel) pairs ARE permitted
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)
        assert res.status_code == 201, "Duplicate rule pair must be allowed"
        dup_rule_id = res.json()["id"]
        # Clean up duplicate
        await ac.delete(f"/api/v1/rules/{dup_rule_id}", headers=headers)

        # ── VALIDATION REJECTIONS ────────────────────────────────────────────

        # AC2: Non-existent source_id → 422 source_not_found
        bad_source = "65c52c6f1f2e3d4a5b6c0000"
        res = await ac.post(
            "/api/v1/rules",
            json={"source_id": bad_source, "destination_channel": "@target"},
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "source_not_found"

        # AC3: Self-referential rule → 422 self_referential_rule
        res = await ac.post(
            "/api/v1/rules",
            json={"source_id": source_id, "destination_channel": "@news_channel"},
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "self_referential_rule"

        # AC3: Self-referential by telegram_id string
        res = await ac.post(
            "/api/v1/rules",
            json={"source_id": source_id, "destination_channel": "1000000001"},
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "self_referential_rule"

        # AC4: Invalid regex in block_keywords → 422 invalid_regex
        res = await ac.post(
            "/api/v1/rules",
            json={
                "source_id": source_id,
                "destination_channel": "@target_news",
                "keyword_match_mode": "regex",
                "block_keywords": ["[invalid("],
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "invalid_regex"
        assert "[invalid(" in res.json()["error"]["message"]

        # AC4: Invalid regex in allow_keywords → 422 invalid_regex
        res = await ac.post(
            "/api/v1/rules",
            json={
                "source_id": source_id,
                "destination_channel": "@target_news",
                "keyword_match_mode": "regex",
                "allow_keywords": ["**bad**"],
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "invalid_regex"

        # AC5: Cross-midnight time window accepted → 201
        res = await ac.post(
            "/api/v1/rules",
            json={
                "source_id": source_id,
                "destination_channel": "@target_news",
                "time_window": {
                    "timezone": "UTC",
                    "days_of_week": ["MON", "FRI"],
                    "start_time": "22:00",
                    "end_time": "06:00",  # cross-midnight
                },
            },
            headers=headers,
        )
        assert res.status_code == 201, "Cross-midnight time windows must be accepted"
        cross_midnight_rule_id = res.json()["id"]
        # Clean up
        await ac.delete(f"/api/v1/rules/{cross_midnight_rule_id}", headers=headers)

        # AC6: Invalid IANA timezone → 422 invalid_timezone
        res = await ac.post(
            "/api/v1/rules",
            json={
                "source_id": source_id,
                "destination_channel": "@target_news",
                "time_window": {
                    "timezone": "Not/AZone",
                    "days_of_week": ["MON"],
                    "start_time": "09:00",
                    "end_time": "17:00",
                },
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "invalid_timezone"

        # AC7: media_replacement enabled + null path → 422
        res = await ac.post(
            "/api/v1/rules",
            json={
                "source_id": source_id,
                "destination_channel": "@target_news",
                "media_replacement": {
                    "enabled": True,
                    "replacement_image_path": None,
                    "replacement_caption_mode": "use_source",
                },
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "media_replacement_path_required"

        # ── GET SINGLE RULE ───────────────────────────────────────────────────
        # AC11: 200 for existing rule
        res = await ac.get(f"/api/v1/rules/{rule1_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["id"] == rule1_id

        # AC11: 404 for non-existent rule
        fake_id = "65c52c6f1f2e3d4a5b6c9999"
        res = await ac.get(f"/api/v1/rules/{fake_id}", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # ── ENABLE / DISABLE ─────────────────────────────────────────────────
        # AC8: Enable rule → 200 {ok: true}
        res = await ac.post(f"/api/v1/rules/{rule1_id}/enable", headers=headers)
        assert res.status_code == 200
        assert res.json() == {"ok": True}

        # Verify is_active is now true
        res = await ac.get(f"/api/v1/rules/{rule1_id}", headers=headers)
        assert res.json()["is_active"] is True

        # AC9: Disable rule → 200 {ok: true}
        res = await ac.post(f"/api/v1/rules/{rule1_id}/disable", headers=headers)
        assert res.status_code == 200
        assert res.json() == {"ok": True}

        # AC8: Enable non-existent rule → 404
        res = await ac.post(f"/api/v1/rules/{fake_id}/enable", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # AC9: Disable non-existent rule → 404
        res = await ac.post(f"/api/v1/rules/{fake_id}/disable", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # ── LIST RULES ────────────────────────────────────────────────────────
        # Create a second rule for listing tests
        res = await ac.post(
            "/api/v1/rules",
            json={"source_id": source_id, "destination_channel": "@second_target"},
            headers=headers,
        )
        assert res.status_code == 201
        rule2_id = res.json()["id"]

        # AC10: List returns paginated response
        res = await ac.get("/api/v1/rules", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert len(data["items"]) >= 2

        # AC10: Filter by source_id
        res = await ac.get(f"/api/v1/rules?source_id={source_id}", headers=headers)
        assert res.status_code == 200
        assert all(item["source_id"] == source_id for item in res.json()["items"])

        # AC10: Filter by is_active=false (both rules are disabled)
        res = await ac.get("/api/v1/rules?is_active=false", headers=headers)
        assert res.status_code == 200
        assert all(item["is_active"] is False for item in res.json()["items"])

        # AC10: Filter by destination_channel
        res = await ac.get(
            "/api/v1/rules?destination_channel=%40target_news", headers=headers
        )
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["destination_channel"] == "@target_news"

        # AC10: page_size capped at 200
        res = await ac.get("/api/v1/rules?page_size=500", headers=headers)
        assert res.status_code == 200
        assert res.json()["page_size"] == 200

        # ── UPDATE RULE (PUT) ─────────────────────────────────────────────────
        # AC12: Full PUT update
        update_payload = {
            "source_id": source_id,
            "destination_channel": "@updated_target",
            "is_active": True,
            "remove_links": True,
            "remove_hashtags": True,
        }
        res = await ac.put(f"/api/v1/rules/{rule1_id}", json=update_payload, headers=headers)
        assert res.status_code == 200
        updated = res.json()
        assert updated["destination_channel"] == "@updated_target"
        assert updated["is_active"] is True
        assert updated["remove_links"] is True
        assert updated["remove_hashtags"] is True

        # AC12: PUT re-validates source_id → 422 if source doesn't exist
        res = await ac.put(
            f"/api/v1/rules/{rule1_id}",
            json={"source_id": bad_source, "destination_channel": "@target_news"},
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "source_not_found"

        # AC12: PUT validates invalid regex → 422
        res = await ac.put(
            f"/api/v1/rules/{rule1_id}",
            json={
                "source_id": source_id,
                "destination_channel": "@updated_target",
                "keyword_match_mode": "regex",
                "block_keywords": ["[bad"],
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "invalid_regex"

        # AC12: PUT not-found → 404
        res = await ac.put(
            f"/api/v1/rules/{fake_id}",
            json={"source_id": source_id, "destination_channel": "@target"},
            headers=headers,
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # ── STORY 3.2: REPLACEMENT RULE CRUD ────────────────────────────────

        # AC3/3.2: POST to non-existent parent rule → 404 rule_not_found
        res = await ac.post(
            f"/api/v1/rules/{fake_id}/replacement-rules",
            json={"search_text": "foo", "replacement_text": "bar", "match_mode": "literal"},
            headers=headers,
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # AC1/3.2: Create replacement rule (happy path) → 201
        res = await ac.post(
            f"/api/v1/rules/{rule1_id}/replacement-rules",
            json={"search_text": "competitor", "replacement_text": "us", "match_mode": "literal"},
            headers=headers,
        )
        assert res.status_code == 201, res.text
        rr1 = res.json()
        rr1_id = rr1["id"]
        assert len(rr1_id) == 24
        assert rr1["search_text"] == "competitor"
        assert rr1["replacement_text"] == "us"
        assert rr1["match_mode"] == "literal"
        assert rr1["is_active"] is True  # default True per FR-7
        assert rr1["forwarding_rule_id"] == rule1_id

        # Create a second replacement rule (to verify ordering)
        res = await ac.post(
            f"/api/v1/rules/{rule1_id}/replacement-rules",
            json={
                "search_text": "old.+product",
                "replacement_text": "new product",
                "match_mode": "regex",
            },
            headers=headers,
        )
        assert res.status_code == 201
        rr2 = res.json()
        rr2_id = rr2["id"]
        assert rr2["match_mode"] == "regex"

        # AC2/3.2: Invalid regex in search_text → 422 invalid_regex
        res = await ac.post(
            f"/api/v1/rules/{rule1_id}/replacement-rules",
            json={"search_text": "[invalid(", "replacement_text": "x", "match_mode": "regex"},
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "invalid_regex"

        # AC4/3.2: List replacement rules → 200 items ordered by created_at ASC
        res = await ac.get(
            f"/api/v1/rules/{rule1_id}/replacement-rules", headers=headers
        )
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert items[0]["search_text"] == "competitor"  # first created — ASC order
        assert items[1]["search_text"] == "old.+product"

        # AC4/3.2: List for non-existent parent rule → 404
        res = await ac.get(
            f"/api/v1/rules/{fake_id}/replacement-rules", headers=headers
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # AC5/3.2: Update replacement rule → 200, updated_at refreshed
        res = await ac.put(
            f"/api/v1/rules/{rule1_id}/replacement-rules/{rr1_id}",
            json={
                "search_text": "competitor_brand",
                "replacement_text": "us",
                "match_mode": "literal",
                "is_active": True,
            },
            headers=headers,
        )
        assert res.status_code == 200
        updated_rr = res.json()
        assert updated_rr["search_text"] == "competitor_brand"

        # AC5/3.2: PUT with invalid regex → 422
        res = await ac.put(
            f"/api/v1/rules/{rule1_id}/replacement-rules/{rr2_id}",
            json={
                "search_text": "[bad",
                "replacement_text": "x",
                "match_mode": "regex",
                "is_active": True,
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "invalid_regex"

        # AC5/3.2: PUT non-existent replacement → 404
        fake_rr_id = "65c52c6f1f2e3d4a5b6c8888"
        res = await ac.put(
            f"/api/v1/rules/{rule1_id}/replacement-rules/{fake_rr_id}",
            json={
                "search_text": "x",
                "replacement_text": "y",
                "match_mode": "literal",
                "is_active": True,
            },
            headers=headers,
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "replacement_rule_not_found"

        # AC6/3.2: Delete replacement rule → 204
        res = await ac.delete(
            f"/api/v1/rules/{rule1_id}/replacement-rules/{rr2_id}", headers=headers
        )
        assert res.status_code == 204

        # Verify rr2 is gone from listing
        res = await ac.get(
            f"/api/v1/rules/{rule1_id}/replacement-rules", headers=headers
        )
        assert res.status_code == 200
        remaining = res.json()["items"]
        assert len(remaining) == 1
        assert remaining[0]["id"] == rr1_id

        # AC6/3.2: Delete non-existent replacement → 404
        res = await ac.delete(
            f"/api/v1/rules/{rule1_id}/replacement-rules/{fake_rr_id}", headers=headers
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "replacement_rule_not_found"

        # AC8/3.2: Auth gate for replacement-rules endpoints → 401 without key
        res = await ac.get(f"/api/v1/rules/{rule1_id}/replacement-rules")
        assert res.status_code == 401
        res = await ac.post(
            f"/api/v1/rules/{rule1_id}/replacement-rules",
            json={"search_text": "x", "replacement_text": "y", "match_mode": "literal"},
        )
        assert res.status_code == 401

        # ── CASCADE DELETE ────────────────────────────────────────────────────
        # AC7/3.2 + AC13/3.1: Deleting parent rule cascades to replacement_rules
        # Ensure rr1 (the remaining replacement rule) is in DB
        res = await ac.get(
            f"/api/v1/rules/{rule1_id}/replacement-rules", headers=headers
        )
        assert len(res.json()["items"]) == 1, "rr1 must still exist before cascade delete"

        # Delete the parent rule
        res = await ac.delete(f"/api/v1/rules/{rule1_id}", headers=headers)
        assert res.status_code == 204

        # Parent rule is gone
        res = await ac.get(f"/api/v1/rules/{rule1_id}", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # Cascade: listing replacement-rules for deleted parent → 404 (rule not found)
        res = await ac.get(
            f"/api/v1/rules/{rule1_id}/replacement-rules", headers=headers
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # AC13/3.1: DELETE non-existent rule → 404
        res = await ac.delete(f"/api/v1/rules/{rule1_id}", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "rule_not_found"

        # Clean up rule2 as well
        res = await ac.delete(f"/api/v1/rules/{rule2_id}", headers=headers)
        assert res.status_code == 204

        # List is now empty
        res = await ac.get("/api/v1/rules", headers=headers)
        assert res.json()["total"] == 0


# ---------------------------------------------------------------------------
# Story 3.3: RuleCache & CacheHolder Unit Tests
# (These are focused unit tests; the refresher itself is well-covered in
#  tests/infrastructure/cache/test_cache_refresher.py — we validate the
#  essential cache integration properties here.)
# ---------------------------------------------------------------------------

def test_rule_cache_is_frozen():
    """AC: RuleCache is frozen — attributes cannot be mutated after creation."""
    cache = RuleCache(version=1)
    with pytest.raises((AttributeError, TypeError)):
        cache.version = 2  # type: ignore[misc]


def test_rule_cache_empty_defaults():
    """AC: RuleCache() with no args is a valid empty snapshot (version=0)."""
    cache = RuleCache()
    assert cache.sources == {}
    assert cache.folders == {}
    assert cache.rules == []
    assert cache.replacements == {}
    assert cache.compiled_patterns == {}
    assert cache.version == 0
    assert cache.refreshed_at is None


def test_cache_holder_starts_with_empty_cache():
    """AC: CacheHolder.current starts as an empty RuleCache (version=0)."""
    CacheHolder.current = RuleCache()  # reset to known state
    assert CacheHolder.current.version == 0
    assert CacheHolder.current.rules == []


def test_cache_holder_atomic_swap():
    """AC: Assigning CacheHolder.current atomically replaces the snapshot."""
    original = CacheHolder.current
    try:
        new_cache = RuleCache(version=42)
        CacheHolder.current = new_cache
        assert CacheHolder.current.version == 42
    finally:
        CacheHolder.current = original


def test_compiled_patterns_empty_defaults():
    """AC: CompiledPatterns has correct empty defaults."""
    p = CompiledPatterns()
    assert p.block_patterns == []
    assert p.allow_patterns == []
    assert p.replacement_patterns == {}


def test_compiled_patterns_with_real_patterns():
    """AC: CompiledPatterns stores compiled re.Pattern objects correctly."""
    block = [re.compile("pump", re.IGNORECASE)]
    allow = [re.compile("btc", re.IGNORECASE)]
    repl = {"rr-id-1": re.compile("old", re.IGNORECASE)}
    p = CompiledPatterns(block_patterns=block, allow_patterns=allow, replacement_patterns=repl)
    assert len(p.block_patterns) == 1
    assert p.block_patterns[0].pattern == "pump"
    assert "rr-id-1" in p.replacement_patterns


# ---------------------------------------------------------------------------
# Story 3.3: Cache Refresher — build_rule_cache integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_rule_cache_happy_path():
    """AC1/3.3: build_rule_cache fetches 4 collections and builds a valid snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    now = datetime.now(timezone.utc)
    source = Source(
        id="src1",
        telegram_id=1001,
        telegram_username="test_chan",
        display_name="Test",
        type="channel",
        folder_id=None,
        created_at=now,
        updated_at=now,
    )
    rule = ForwardingRule(
        id="rule1",
        source_id="src1",
        destination_channel="@dest",
        is_active=True,
        keyword_match_mode="literal",
        block_keywords=[],
        allow_keywords=[],
        media_type_filter=["text"],
        remove_links=False,
        remove_hashtags=False,
        remove_mentions=False,
        forward_media="forward",
        sampling=SamplingConfig(),
        attribution=AttributionConfig(),
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(),
        media_replacement=MediaReplacementConfig(),
        created_at=now,
        updated_at=now,
    )
    replacement = ReplacementRule(
        id="rr1",
        forwarding_rule_id="rule1",
        search_text="old",
        replacement_text="new",
        match_mode="literal",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(return_value=([source], 1))
    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=[])
    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([rule], 1))
    mock_replacement_repo = MagicMock()
    async def _batch_happy(rule_ids):
        return {rid: ([replacement] if rid == "rule1" else []) for rid in rule_ids}
    mock_replacement_repo.list_all_replacements_for_rules = _batch_happy
    mock_db = MagicMock()

    with (
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.SourceRepository",
            return_value=mock_source_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.FolderRepository",
            return_value=mock_folder_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository",
            return_value=mock_rule_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository",
            return_value=mock_replacement_repo,
        ),
    ):
        cache = await build_rule_cache(mock_db, version=1)

    assert cache.version == 1
    assert "src1" in cache.sources
    assert len(cache.rules) == 1
    assert "rule1" in cache.replacements
    assert len(cache.replacements["rule1"]) == 1
    assert cache.refreshed_at is not None
    assert isinstance(cache, RuleCache)


@pytest.mark.asyncio
async def test_build_rule_cache_compiles_regex_patterns():
    """AC2/3.3: Regex patterns are pre-compiled into CompiledPatterns."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    now = datetime.now(timezone.utc)
    rule = ForwardingRule(
        id="rule_rx",
        source_id="src1",
        destination_channel="@dest",
        is_active=True,
        keyword_match_mode="regex",
        block_keywords=["pump.*"],
        allow_keywords=["BTC|ETH"],
        media_type_filter=["text"],
        remove_links=False,
        remove_hashtags=False,
        remove_mentions=False,
        forward_media="forward",
        sampling=SamplingConfig(),
        attribution=AttributionConfig(),
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(),
        media_replacement=MediaReplacementConfig(),
        created_at=now,
        updated_at=now,
    )
    replacement = ReplacementRule(
        id="rr_rx",
        forwarding_rule_id="rule_rx",
        search_text="old.+new",
        replacement_text="new",
        match_mode="regex",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(return_value=([], 0))
    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=[])
    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([rule], 1))
    mock_replacement_repo = MagicMock()
    async def _batch_regex(rule_ids):
        return {rid: ([replacement] if rid == "rule_rx" else []) for rid in rule_ids}
    mock_replacement_repo.list_all_replacements_for_rules = _batch_regex
    mock_db = MagicMock()

    with (
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.SourceRepository",
            return_value=mock_source_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.FolderRepository",
            return_value=mock_folder_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository",
            return_value=mock_rule_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository",
            return_value=mock_replacement_repo,
        ),
    ):
        cache = await build_rule_cache(mock_db, version=1)

    assert "rule_rx" in cache.compiled_patterns
    cp = cache.compiled_patterns["rule_rx"]
    assert len(cp.block_patterns) == 1
    assert cp.block_patterns[0].pattern == "pump.*"
    assert len(cp.allow_patterns) == 1
    assert "rr_rx" in cp.replacement_patterns


@pytest.mark.asyncio
async def test_build_rule_cache_skips_invalid_regex():
    """AC3/3.3: Invalid regex patterns are skipped and logged; refresh still completes."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    now = datetime.now(timezone.utc)
    rule = ForwardingRule(
        id="rule_bad_rx",
        source_id="src1",
        destination_channel="@dest",
        is_active=True,
        keyword_match_mode="regex",
        block_keywords=["[invalid("],  # bad regex
        allow_keywords=[],
        media_type_filter=["text"],
        remove_links=False,
        remove_hashtags=False,
        remove_mentions=False,
        forward_media="forward",
        sampling=SamplingConfig(),
        attribution=AttributionConfig(),
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(),
        media_replacement=MediaReplacementConfig(),
        created_at=now,
        updated_at=now,
    )

    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(return_value=([], 0))
    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=[])
    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([rule], 1))
    mock_replacement_repo = MagicMock()
    async def _batch_empty(rule_ids):
        return {rid: [] for rid in rule_ids}
    mock_replacement_repo.list_all_replacements_for_rules = _batch_empty
    mock_db = MagicMock()

    with (
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.SourceRepository",
            return_value=mock_source_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.FolderRepository",
            return_value=mock_folder_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository",
            return_value=mock_rule_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository",
            return_value=mock_replacement_repo,
        ),
    ):
        cache = await build_rule_cache(mock_db, version=1)

    # Refresh completes — version is set
    assert cache.version == 1
    # Invalid pattern skipped — block_patterns is empty for this rule
    assert "rule_bad_rx" in cache.compiled_patterns
    assert cache.compiled_patterns["rule_bad_rx"].block_patterns == []


@pytest.mark.asyncio
async def test_cache_refresher_retains_snapshot_on_mongodb_failure():
    """AC5/3.3: On MongoDB failure, CacheHolder retains the last valid snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    initial_cache = RuleCache(version=77)
    CacheHolder.current = initial_cache

    try:
        mock_settings = MagicMock()
        mock_settings.hot_reload_interval = 0.01

        async def mock_build_fail(db, version):
            raise Exception("MongoDB connection lost")

        with patch(
            "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
            side_effect=mock_build_fail,
        ):
            task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Snapshot retained — NOT reset to empty
        assert CacheHolder.current.version == 77
    finally:
        CacheHolder.current = RuleCache()  # restore
