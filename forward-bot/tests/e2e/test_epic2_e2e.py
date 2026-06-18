"""
E2E & Integration Tests for Epic 2: Source Catalog & Folder Organization.

Covers:
  2.1 Source Registration and Retrieval
  2.2 Source Listing and Updates
  2.3 Folder CRUD
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId
from telethon.tl.types import Channel, Chat

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.entities.source import Source
from forward_bot.api.dependencies.providers import get_folder_repository, get_source_repository


# ---------------------------------------------------------------------------
# In-Memory MongoDB Mock for E2E routing verification
# ---------------------------------------------------------------------------

class MockCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field, direction=1):
        rev = (direction == -1)
        self.items.sort(
            key=lambda x: x.get(field) or datetime.min if not isinstance(x.get(field), str) else x.get(field).lower(),
            reverse=rev
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
        self.global_db = None

    async def create_index(self, *args, **kwargs):
        return None

    async def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.data_store.append(doc)
        res = MagicMock()
        res.inserted_id = doc["_id"]
        return res

    async def find_one(self, query):
        for doc in self.data_store:
            if self._match(doc, query):
                return doc
        return None

    def find(self, query):
        matched = [doc for doc in self.data_store if self._match(doc, query)]
        return MockCursor(matched)

    async def count_documents(self, query):
        return sum(1 for doc in self.data_store if self._match(doc, query))

    async def replace_one(self, filter_query, replacement):
        for i, doc in enumerate(self.data_store):
            if self._match(doc, filter_query):
                if "_id" not in replacement and "_id" in doc:
                    replacement["_id"] = doc["_id"]
                self.data_store[i] = replacement
                res = MagicMock()
                res.modified_count = 1
                return res
        res = MagicMock()
        res.modified_count = 0
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

    def aggregate(self, pipeline):
        matched = list(self.data_store)
        if pipeline and "$match" in pipeline[0]:
            match_query = pipeline[0]["$match"]
            matched = [doc for doc in matched if self._match(doc, match_query)]
        
        results = []
        for doc in matched:
            folder_id = doc["_id"]
            sources_store = self.global_db.get("sources", [])
            source_count = sum(1 for s in sources_store if s.get("folder_id") == folder_id)
            results.append({
                "_id": folder_id,
                "name": doc["name"],
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
                "source_count": source_count
            })
        
        results.sort(key=lambda x: x["name"].lower())
        return MockCursor(results)

    def _match(self, doc, query):
        for k, v in query.items():
            val = doc.get(k)
            if k == "_id" and not isinstance(v, dict):
                if val != v:
                    return False
            elif isinstance(v, dict):
                if "$ne" in v:
                    if val == v["$ne"]:
                        return False
                if "$regex" in v:
                    import re
                    pattern = v["$regex"]
                    options = v.get("$options", "")
                    flags = re.IGNORECASE if "i" in options else 0
                    cleaned_pat = pattern.replace("\\ ", " ").replace("^", "").replace("$", "")
                    val_str = str(val)
                    if "i" in options:
                        if cleaned_pat.lower() != val_str.lower():
                            return False
                    else:
                        if cleaned_pat != val_str:
                            return False
            else:
                if val != v:
                    return False
        return True


class MockDatabase:
    def __init__(self):
        self.stores = {
            "source_folders": [],
            "sources": [],
            "forwarding_rules": []
        }
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            coll = MockCollection(self.stores.setdefault(name, []))
            coll.global_db = self.stores
            self.collections[name] = coll
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


@pytest.fixture
def mock_telegram():
    from forward_bot.infrastructure.telegram import telegram_client
    
    original_client = telegram_client.client
    original_status = telegram_client.status
    
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)
    
    def get_entity_side_effect(ref):
        if ref == "@crypto_alerts" or ref == "crypto_alerts":
            channel = MagicMock(spec=Channel)
            channel.id = 1000000002
            channel.username = "crypto_alerts"
            channel.megagroup = False
            return channel
        elif ref == 123456789 or ref == "123456789":
            chat = MagicMock(spec=Chat)
            chat.id = 123456789
            chat.username = None
            return chat
        else:
            raise ValueError("Cannot find entity")
            
    mock_client.get_entity.side_effect = get_entity_side_effect
    telegram_client.client = mock_client
    telegram_client.status = "disconnected"
    
    yield telegram_client
    
    telegram_client.client = original_client
    telegram_client.status = original_status


# ---------------------------------------------------------------------------
# E2E Workflow Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic2_e2e_workflow(app_no_lifespan, mock_telegram):
    """
    Validates the entire Epic 2 workflow end-to-end:
      - Initial checks (empty folders/sources list)
      - Auth gate enforcement
      - Folder CRUD (creation, name validation, duplicate checks)
      - Source registration & resolution with connected/disconnected Telegram Client
      - Source listing, retrieve, details, updates, patching
      - Folder detailed view (include=sources) and source counts
      - Folder renaming validation (conflict vs self-rename)
      - Folder deletion and disassociation check (sources remain intact, folder_id -> None)
    """
    headers = {"X-API-Key": "test-api-key"}
    
    async with AsyncClient(transport=ASGITransport(app=app_no_lifespan), base_url="http://test") as ac:
        # 1. Verify initially empty lists
        res = await ac.get("/api/v1/folders", headers=headers)
        assert res.status_code == 200
        assert res.json() == []

        res = await ac.get("/api/v1/sources", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["items"] == []

        # 2. Auth gate checks
        res = await ac.get("/api/v1/folders")
        assert res.status_code == 401
        res = await ac.get("/api/v1/sources")
        assert res.status_code == 401

        # 3. Create folders
        # Create folder 1
        res = await ac.post("/api/v1/folders", json={"name": "Crypto Signals"}, headers=headers)
        assert res.status_code == 201
        folder1 = res.json()
        assert folder1["name"] == "Crypto Signals"
        assert len(folder1["id"]) == 24
        
        # Try duplicate folder name (case-insensitive)
        res = await ac.post("/api/v1/folders", json={"name": "crypto signals"}, headers=headers)
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "folder_name_in_use"

        # Create folder 2
        res = await ac.post("/api/v1/folders", json={"name": "Stock Market"}, headers=headers)
        assert res.status_code == 201
        folder2 = res.json()
        assert folder2["name"] == "Stock Market"

        # Check alphabetical sorting in folder listing
        res = await ac.get("/api/v1/folders", headers=headers)
        assert res.status_code == 200
        folders = res.json()
        assert len(folders) == 2
        assert folders[0]["name"] == "Crypto Signals"
        assert folders[1]["name"] == "Stock Market"

        # Verify folder name availability check route: GET /api/v1/folders?name={name}
        res = await ac.get("/api/v1/folders?name=crypto signals", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "Crypto Signals"

        res = await ac.get("/api/v1/folders?name=Available Folder", headers=headers)
        assert res.status_code == 200
        assert res.json() == []

        # 4. Source registration (Telegram Client Mock)
        # Try registration while disconnected
        mock_telegram.status = "disconnected"
        res = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "crypto_alerts", "display_name": "Crypto Alerts"},
            headers=headers
        )
        assert res.status_code == 503
        assert res.json()["error"]["code"] == "telegram_unavailable"

        # Connect Telegram
        mock_telegram.status = "connected"
        # Register channel
        res = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "@crypto_alerts", "display_name": "Crypto Alerts"},
            headers=headers
        )
        assert res.status_code == 201
        source1 = res.json()
        assert source1["telegram_id"] == 1000000002
        assert source1["telegram_username"] == "crypto_alerts"
        assert source1["type"] == "channel"
        assert source1["folder_id"] is None

        # Register group
        res = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "123456789", "display_name": "Operator Group"},
            headers=headers
        )
        assert res.status_code == 201
        source2 = res.json()
        assert source2["telegram_id"] == 123456789
        assert source2["type"] == "group"

        # Try duplicate registration check
        res = await ac.post(
            "/api/v1/sources",
            json={"telegram_reference": "crypto_alerts", "display_name": "Duplicate"},
            headers=headers
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "source_already_exists"

        # 5. List sources and check filters/pagination
        res = await ac.get("/api/v1/sources", headers=headers)
        assert res.status_code == 200
        sources_list = res.json()
        assert sources_list["total"] == 2
        assert len(sources_list["items"]) == 2

        # 6. Retrieve source details by ID
        res = await ac.get(f"/api/v1/sources/{source1['id']}", headers=headers)
        assert res.status_code == 200
        assert res.json()["telegram_username"] == "crypto_alerts"

        # 7. Update source: assign to a folder
        # Check folder_not_found error
        res = await ac.put(
            f"/api/v1/sources/{source1['id']}",
            json={
                "display_name": "Updated Crypto Alerts",
                "type": "channel",
                "folder_id": "65c52c6f1f2e3d4a5b6c7d8f", # missing folder
                "telegram_username": "crypto_alerts"
            },
            headers=headers
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "folder_not_found"

        # Successfully assign to folder1
        res = await ac.put(
            f"/api/v1/sources/{source1['id']}",
            json={
                "display_name": "Crypto Alerts",
                "type": "channel",
                "folder_id": folder1["id"],
                "telegram_username": "crypto_alerts"
            },
            headers=headers
        )
        assert res.status_code == 200
        assert res.json()["folder_id"] == folder1["id"]

        # Patch test
        res = await ac.patch(
            f"/api/v1/sources/{source2['id']}",
            json={"folder_id": folder2["id"]},
            headers=headers
        )
        assert res.status_code == 200
        assert res.json()["folder_id"] == folder2["id"]

        # 8. Check source counts in folder listing
        res = await ac.get("/api/v1/folders", headers=headers)
        assert res.status_code == 200
        folders = res.json()
        assert folders[0]["name"] == "Crypto Signals"
        assert folders[0]["source_count"] == 1
        assert folders[1]["name"] == "Stock Market"
        assert folders[1]["source_count"] == 1

        # 9. GET folder details with options
        res = await ac.get(f"/api/v1/folders/{folder1['id']}", headers=headers)
        assert res.status_code == 200
        f_details = res.json()
        assert f_details["source_count"] == 1
        assert f_details["sources"] is None

        # Include sources
        res = await ac.get(f"/api/v1/folders/{folder1['id']}?include=sources", headers=headers)
        assert res.status_code == 200
        f_details_sources = res.json()
        assert f_details_sources["source_count"] == 1
        assert len(f_details_sources["sources"]) == 1
        assert f_details_sources["sources"][0]["id"] == source1["id"]

        # 10. Folder renaming logic
        # Rename to already in use name
        res = await ac.put(f"/api/v1/folders/{folder2['id']}", json={"name": "Crypto Signals"}, headers=headers)
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "folder_name_in_use"

        # Rename to own name (self-rename allowed)
        res = await ac.put(f"/api/v1/folders/{folder2['id']}", json={"name": "Stock Market"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Stock Market"

        # Successful rename
        res = await ac.put(f"/api/v1/folders/{folder2['id']}", json={"name": "Stock Options"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Stock Options"

        # 11. Folder deletion & disassociation
        res = await ac.delete(f"/api/v1/folders/{folder1['id']}", headers=headers)
        assert res.status_code == 204

        # Verify folder is gone
        res = await ac.get(f"/api/v1/folders/{folder1['id']}", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "folder_not_found"

        # Verify source1 is still there but folder_id is null/None
        res = await ac.get(f"/api/v1/sources/{source1['id']}", headers=headers)
        assert res.status_code == 200
        assert res.json()["folder_id"] is None
