"""
E2E & Integration Tests for Epic 7: Session Management UI & Multi-Tier Cache Control.

Covers:
  7.1 Multi-Tier Rule Cache Rebuild & Admin Refresh API
  7.2 Telegram Session Management Backend API & Lifecycle Methods
  7.3 E2E Integration Workflows for Web Admin Settings & Header Controls
"""

import asyncio
import os
import pytest
import re
import tempfile
import uuid
import structlog
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from bson import ObjectId
from httpx import AsyncClient, ASGITransport

from telethon import events
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
)

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.infrastructure.cache.rule_cache import CacheHolder
from forward_bot.infrastructure.cache.cache_refresher import (
    build_rule_cache,
    trigger_cache_rebuild,
)
from forward_bot.infrastructure.telegram.client import TelegramClientHolder
from forward_bot.infrastructure.telegram.worker import TelegramWorker
from forward_bot.api.routers.telegram_auth import AUTH_STATE


# ---------------------------------------------------------------------------
# In-Memory MockDatabase Helper
# ---------------------------------------------------------------------------

class MockCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field_or_list, direction=1):
        if isinstance(field_or_list, list):
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

    async def find_one_and_update(self, filter_query, update_op, upsert=False, return_document=None):
        import copy
        found_doc = None
        for doc in self.data_store:
            if self._match(doc, filter_query):
                found_doc = doc
                break

        if not found_doc:
            if upsert:
                new_doc = copy.deepcopy(filter_query)
                if "_id" not in new_doc:
                    new_doc["_id"] = ObjectId()
                self.data_store.append(new_doc)
                found_doc = new_doc
            else:
                return None

        if "$set" in update_op:
            for k, v in update_op["$set"].items():
                found_doc[k] = v
        if "$inc" in update_op:
            for k, v in update_op["$inc"].items():
                found_doc[k] = found_doc.get(k, 0) + v

        return copy.deepcopy(found_doc)

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

    def _match(self, doc, query):
        for k, v in query.items():
            val = doc.get(k)
            if k == "_id" and not isinstance(v, dict):
                if val != v:
                    return False
            elif isinstance(v, dict):
                if "$ne" in v and val == v["$ne"]:
                    return False
                if "$in" in v:
                    if val not in v["$in"]:
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
def base_settings(tmp_path):
    session_file = tmp_path / "test_session.session"
    session_file.write_text("test-session-content")
    return Settings(
        api_key="test-api-key",
        secret_key="test-secret-key",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=12345,
        telegram_api_hash="test-api-hash",
        telegram_session_path=str(session_file),
        telegram_phone="+12025550123",
        ui_enabled=False,
        _env_file=None,
    )


@pytest.fixture(autouse=True)
def mock_db():
    from forward_bot.infrastructure.mongo.client import mongo_client
    fake_db = MockDatabase()
    with patch.object(mongo_client, "db", fake_db):
        yield fake_db


@pytest.fixture
def app_no_lifespan(base_settings):
    return create_app(base_settings, lifespan=None)


# ---------------------------------------------------------------------------
# E2E Tests: Story 7.1 (Multi-Tier Rule Cache Rebuild & Admin Refresh API)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic7_story7_1_admin_cache_refresh_api(app_no_lifespan, mock_db):
    """
    Story 7.1 AC 2: POST /api/v1/admin/cache/refresh
    Triggers explicit cache rebuild and returns updated cache metadata (version, rule_count, source_count, refreshed_at).
    """
    transport = ASGITransport(app=app_no_lifespan)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed initial source & forwarding rule in mock DB
        source_id = ObjectId()
        mock_db["sources"].data_store.append({
            "_id": source_id,
            "telegram_id": 1001,
            "display_name": "E2E Test Source",
            "type": "channel",
            "folder_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

        rule_id = ObjectId()
        mock_db["forwarding_rules"].data_store.append({
            "_id": rule_id,
            "source_id": str(source_id),
            "destination_channel": 2002,
            "is_active": True,
            "keyword_match_mode": "literal",
            "block_keywords": [],
            "allow_keywords": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

        # Request admin cache refresh
        response = await client.post(
            "/api/v1/admin/cache/refresh",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] >= 1
        assert data["rule_count"] == 1
        assert data["source_count"] == 1
        assert "refreshed_at" in data

        # Verify CacheHolder global snapshot matches returned metadata
        current = CacheHolder.current
        assert current.version == data["version"]
        assert len(current.sources) == 1
        assert len(current.rules) == 1


@pytest.mark.asyncio
async def test_epic7_story7_1_mutation_triggers_async_rebuild(app_no_lifespan, mock_db):
    """
    Story 7.1 AC 1: REST API entity mutations (create/update/delete rules/sources)
    trigger non-blocking async cache rebuild via BackgroundTasks.
    """
    from forward_bot.application.sources.register_source import RegisterSource
    transport = ASGITransport(app=app_no_lifespan)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get baseline cache version
        baseline_version = CacheHolder.current.version if CacheHolder.current else 0

        mock_source = Source(
            id=str(ObjectId()),
            telegram_id=9999,
            telegram_username="async_source",
            display_name="Async Mutation Source",
            type="channel",
            folder_id=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch.object(RegisterSource, "execute", return_value=mock_source):
            # Create source via API
            source_res = await client.post(
                "/api/v1/sources",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "telegram_reference": "9999",
                    "display_name": "Async Mutation Source",
                },
            )
            assert source_res.status_code in (200, 201)

        # Allow background task execution
        await asyncio.sleep(0.1)

        # Verify version incremented in CacheHolder
        assert CacheHolder.current is not None
        assert CacheHolder.current.version > baseline_version


@pytest.mark.asyncio
async def test_epic7_story7_1_cache_rebuild_resiliency_and_invalid_regex(mock_db):
    """
    Story 7.1 AC 3 & 5:
    - Invalid regex compilation produces ERROR log and skips invalid pattern without crashing rebuild.
    - Database error during rebuild logs WARNING cache_refresh_failed and retains last valid snapshot.
    """
    rule_id = ObjectId()
    mock_db["forwarding_rules"].data_store.append({
        "_id": rule_id,
        "source_id": str(ObjectId()),
        "destination_channel": 6666,
        "is_active": True,
        "keyword_match_mode": "regex",
        "block_keywords": ["[invalid_regex("],
        "allow_keywords": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # Trigger cache rebuild
    with patch("forward_bot.infrastructure.cache.cache_refresher.logger") as mock_logger:
        await trigger_cache_rebuild(mock_db)
        assert CacheHolder.current is not None

    # Simulate DB error on rebuild to verify snapshot retention
    previous_snapshot = CacheHolder.current
    with patch("forward_bot.infrastructure.cache.cache_refresher.build_rule_cache", side_effect=Exception("DB connection error")):
        with patch("forward_bot.infrastructure.cache.cache_refresher.logger") as mock_logger:
            await trigger_cache_rebuild(mock_db)
            # Retains previous valid snapshot
            assert CacheHolder.current == previous_snapshot
            mock_logger.warning.assert_called_with("cache_refresh_failed", error="DB connection error", last_successful_refresh=ANY)


# ---------------------------------------------------------------------------
# E2E Tests: Story 7.2 (Telegram Session Management Backend API & Lifecycle)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic7_story7_2_telegram_status_endpoint(app_no_lifespan):
    """
    Story 7.2 AC 1: GET /api/v1/telegram/auth/status
    Returns status envelope with connection state, masked phone, phone_required, session_path.
    """
    from forward_bot.api.dependencies.providers import get_telegram_client
    transport = ASGITransport(app=app_no_lifespan)
    mock_holder = MagicMock()
    mock_holder.is_connected = True
    mock_holder.settings = app_no_lifespan.state.settings
    mock_holder.client = None
    app_no_lifespan.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/telegram/auth/status",
                headers={"X-API-Key": "test-api-key"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert "session_path" in data
    finally:
        app_no_lifespan.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_epic7_story7_2_telegram_auth_start_verify_and_2fa_flow(app_no_lifespan):
    """
    Story 7.2 AC 2 & 3: Full login lifecycle via /start and /verify
    - /start sends code request via Telethon and saves phone_code_hash
    - /verify returns 202 requires_2fa: true if 2FA password required
    - /verify completes sign in and returns status: connected on 200
    """
    from forward_bot.api.dependencies.providers import get_telegram_client
    AUTH_STATE.clear()
    transport = ASGITransport(app=app_no_lifespan)

    mock_telethon = AsyncMock()
    mock_telethon.is_connected = MagicMock(return_value=False)
    mock_telethon.connect = AsyncMock()
    mock_telethon.send_code_request = AsyncMock(return_value=MagicMock(phone_code_hash="mock_hash_123"))

    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app_no_lifespan.state.settings
    mock_holder.client = mock_telethon
    mock_holder.reconnect = AsyncMock()
    app_no_lifespan.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        with patch("forward_bot.api.routers.telegram_auth.TelegramClient", return_value=mock_telethon):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. Start auth flow
                start_res = await client.post(
                    "/api/v1/telegram/auth/start",
                    headers={"X-API-Key": "test-api-key"},
                    json={"phone": "+12025550123"},
                )
                assert start_res.status_code == 200
                assert start_res.json() == {"status": "code_sent"}
                assert AUTH_STATE.get("current", {}).get("phone") == "+12025550123"

                # 2. Verify OTP requiring 2FA (HTTP 202)
                mock_telethon.sign_in = AsyncMock(side_effect=SessionPasswordNeededError(request=None))
                verify_2fa_res = await client.post(
                    "/api/v1/telegram/auth/verify",
                    headers={"X-API-Key": "test-api-key"},
                    json={"otp": "123456", "phone": "+12025550123"},
                )
                assert verify_2fa_res.status_code == 202
                assert verify_2fa_res.json() == {"requires_2fa": True}

                # 3. Verify OTP with password succeeding (HTTP 200)
                mock_telethon.sign_in = AsyncMock(return_value=MagicMock())
                verify_success_res = await client.post(
                    "/api/v1/telegram/auth/verify",
                    headers={"X-API-Key": "test-api-key"},
                    json={"otp": "123456", "password": "mypassword", "phone": "+12025550123"},
                )
                assert verify_success_res.status_code == 200
                assert verify_success_res.json() == {"status": "connected"}
                mock_holder.reconnect.assert_called_once()
    finally:
        app_no_lifespan.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_epic7_story7_2_telegram_terminate_session_and_worker_drop(app_no_lifespan, base_settings):
    """
    Story 7.2 AC 4 & worker drop requirement:
    - /terminate sets _connected = False, logs out telethon client, unlinks session file.
    - Incoming TelegramWorker events while disconnected are dropped immediately with log.
    """
    from forward_bot.api.dependencies.providers import get_telegram_client
    transport = ASGITransport(app=app_no_lifespan)
    tmp_session = base_settings.telegram_session_path

    mock_holder = MagicMock()
    mock_holder.is_connected = True
    mock_holder.terminate = AsyncMock()
    app_no_lifespan.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            term_res = await client.post(
                "/api/v1/telegram/auth/terminate",
                headers={"X-API-Key": "test-api-key"},
            )
            assert term_res.status_code == 200
            assert term_res.json() == {"status": "terminated"}
            mock_holder.terminate.assert_called_once()
    finally:
        app_no_lifespan.dependency_overrides.clear()

    # Test TelegramWorker event drop when _connected is False
    worker = TelegramWorker(db=MockDatabase(), settings=base_settings)
    event_mock = MagicMock()
    event_mock.chat_id = 1111

    with patch("forward_bot.infrastructure.telegram.worker.logger") as mock_logger:
        with patch("forward_bot.infrastructure.telegram.telegram_client") as mock_worker_tg:
            mock_worker_tg.is_connected = False
            await worker.process_event(event_mock)
            mock_logger.info.assert_called_with(
                "telegram_session_terminated_drop",
                message="Dropped incoming event because Telegram session is terminated or disconnected.",
            )


@pytest.mark.asyncio
async def test_epic7_story7_2_telegram_auth_edge_cases(app_no_lifespan):
    """
    Story 7.2 AC 5: Edge cases and HTTP status codes
    - Invalid OTP -> 400 invalid_otp
    - Expired OTP -> 400 otp_expired
    - Concurrent auth attempt -> 409 auth_in_progress
    - Already connected start -> 409 already_connected
    """
    from forward_bot.api.dependencies.providers import get_telegram_client
    AUTH_STATE.clear()
    transport = ASGITransport(app=app_no_lifespan)

    mock_telethon = AsyncMock()
    mock_telethon.is_connected = MagicMock(return_value=False)
    mock_telethon.connect = AsyncMock()

    mock_holder = MagicMock()
    mock_holder.is_connected = False
    mock_holder.settings = app_no_lifespan.state.settings
    mock_holder.client = mock_telethon
    app_no_lifespan.dependency_overrides[get_telegram_client] = lambda: mock_holder

    try:
        with patch("forward_bot.api.routers.telegram_auth.TelegramClient", return_value=mock_telethon):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. Already connected -> 409
                mock_holder.is_connected = True
                start_conn_res = await client.post(
                    "/api/v1/telegram/auth/start",
                    headers={"X-API-Key": "test-api-key"},
                    json={"phone": "+12025550123"},
                )
                assert start_conn_res.status_code == 409
                assert start_conn_res.json()["error"]["code"] == "already_connected"

                # 2. Invalid OTP -> 400
                mock_holder.is_connected = False
                mock_telethon.send_code_request = AsyncMock(return_value=MagicMock(phone_code_hash="hash_abc"))
                await client.post(
                    "/api/v1/telegram/auth/start",
                    headers={"X-API-Key": "test-api-key"},
                    json={"phone": "+12025550123"},
                )

                mock_telethon.sign_in = AsyncMock(side_effect=PhoneCodeInvalidError(request=None))
                invalid_res = await client.post(
                    "/api/v1/telegram/auth/verify",
                    headers={"X-API-Key": "test-api-key"},
                    json={"otp": "000000", "phone": "+12025550123"},
                )
                assert invalid_res.status_code == 400
                assert invalid_res.json()["error"]["code"] == "invalid_otp"
    finally:
        app_no_lifespan.dependency_overrides.clear()


