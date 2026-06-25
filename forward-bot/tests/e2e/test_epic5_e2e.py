"""
E2E & Integration Tests for Epic 5: Edit/Delete Propagation, Full Observability & Stats API.

Covers:
  5.1 Edit & Delete Propagation + Mapping Sweeper
  5.2 Full Structlog Chain, Ring Buffer & Complete Event Catalog
  5.3 SSE Log Broadcaster & Stats/Log API Endpoints
"""
import asyncio
import pytest
import re
import uuid
import structlog
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from bson import ObjectId
from httpx import AsyncClient, ASGITransport

from telethon import events
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, Message
from telethon.errors import FloodWaitError, MessageNotModifiedError

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.infrastructure.logging.ring_buffer import (
    init_ring_buffer,
    append_to_ring_buffer,
    get_recent_logs,
)
from forward_bot.infrastructure.logging.sse_broadcaster import (
    broadcast_log,
    register_subscriber,
    unregister_subscriber,
)
from forward_bot.infrastructure.logging.setup import setup_logging
from forward_bot.infrastructure.telegram.worker import TelegramWorker
from forward_bot.infrastructure.mongo.mapping_sweeper import run_mapping_sweeper


# ---------------------------------------------------------------------------
# In-Memory MockDatabase
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
                    # Support list matching
                    in_list = v["$in"]
                    if val not in in_list:
                        return False
                if "$lt" in v:
                    if not (val < v["$lt"]):
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
        sampling_persist=False,
        delivery_max_retries=2,
        delivery_backoff_factor=1.1,
        delivery_base_delay=0.01,
        mapping_retention_days=30,
        log_ring_buffer_hours=1.0,
        _env_file=None,
    )


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
    
    mock_client = MagicMock()
    mock_client.is_connected = MagicMock(return_value=True)
    mock_client.send_message = AsyncMock()
    mock_client.edit_message = AsyncMock()
    mock_client.delete_messages = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.connect = AsyncMock()
    
    telegram_client.client = mock_client
    telegram_client.status = "connected"
    
    yield telegram_client
    
    telegram_client.client = original_client
    telegram_client.status = original_status


@pytest.fixture
def app_no_lifespan(base_settings):
    return create_app(base_settings, lifespan=None)


# ---------------------------------------------------------------------------
# E2E Tests: Epic 5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic5_edit_propagation_happy_path(base_settings, mock_db, mock_telegram):
    """
    Story 5.1: Edit Propagation Happy Path
    Verifies that worker handles MessageEdited events, resolves mapped destination messages,
    propagates the edit using Telethon, and logs 'edit_propagated'.
    """
    rule_id = str(ObjectId())
    
    # Save mapping in DB
    mapping_doc = {
        "forwarding_rule_id": ObjectId(rule_id),
        "source_channel_id": 11111,
        "source_message_id": 100,
        "destination_channel_id": -10099999,
        "destination_message_id": 5000,
        "forwarded_at": datetime.now(timezone.utc),
    }
    await mock_db["message_mappings"].insert_one(mapping_doc)

    worker = TelegramWorker(base_settings, mock_db)

    # Setup mocked edit response
    mock_telegram.client.edit_message = AsyncMock()

    # Simulate message edited event
    mock_event = MagicMock(spec=events.MessageEdited.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 100
    mock_event.message.peer_id = PeerChannel(channel_id=11111)
    mock_event.message.message = "Updated text!"
    mock_event.message.media = None
    mock_event.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_edit_event(mock_event)
        
        # Verify logger logs edit_propagated
        logger_mock.info.assert_any_call(
            "edit_propagated",
            rule_id=rule_id,
            source_message_id=100,
            destination_message_id=5000,
            correlation_id=ANY,
        )

    # Verify edit_message called correctly
    mock_telegram.client.edit_message.assert_called_once_with(
        entity=-10099999,
        message=5000,
        text="Updated text!"
    )


@pytest.mark.asyncio
async def test_epic5_edit_propagation_failures_and_ignores(base_settings, mock_db, mock_telegram):
    """
    Story 5.1: Edit Propagation Edge Cases
    1. Verify edit ignored silently if no mappings exist.
    2. Verify warning log and non-crashing behavior when propagate_edit fails.
    """
    worker = TelegramWorker(base_settings, mock_db)

    # 1. No mapping exists -> silently ignore
    mock_event = MagicMock(spec=events.MessageEdited.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 999
    mock_event.message.peer_id = PeerChannel(channel_id=11111)
    mock_event.message.message = "Not mapped edit"
    mock_event.message.media = None

    await worker.process_edit_event(mock_event)
    mock_telegram.client.edit_message.assert_not_called()

    # 2. Mapping exists, but propagate_edit fails
    rule_id = str(ObjectId())
    mapping_doc = {
        "forwarding_rule_id": ObjectId(rule_id),
        "source_channel_id": 11111,
        "source_message_id": 200,
        "destination_channel_id": -10099999,
        "destination_message_id": 5002,
        "forwarded_at": datetime.now(timezone.utc),
    }
    await mock_db["message_mappings"].insert_one(mapping_doc)

    # Make edit_message raise RPCError
    mock_telegram.client.edit_message.side_effect = RuntimeError("Telegram side error")

    # Reset retry settings to avoid waiting in tests
    base_settings.delivery_max_retries = 0

    mock_event_fail = MagicMock(spec=events.MessageEdited.Event)
    mock_event_fail.message = MagicMock(spec=Message)
    mock_event_fail.message.id = 200
    mock_event_fail.message.peer_id = PeerChannel(channel_id=11111)
    mock_event_fail.message.message = "Edit that fails"
    mock_event_fail.message.media = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        # Should not crash
        await worker.process_edit_event(mock_event_fail)

        logger_mock.warning.assert_any_call(
            "edit_propagation_failed",
            rule_id=rule_id,
            source_message_id=200,
            destination_message_id=5002,
            correlation_id=ANY,
            error=ANY,
            message="Edit propagation failed"
        )


@pytest.mark.asyncio
async def test_epic5_delete_propagation_happy_path(base_settings, mock_db, mock_telegram):
    """
    Story 5.1: Delete Propagation Batch Deletes
    Verifies that worker handles MessageDeleted events, resolves mapped destination messages,
    groups them by destination, deletes them in chunks using Telethon, and logs 'delete_propagated'.
    """
    rule_id_1 = str(ObjectId())
    rule_id_2 = str(ObjectId())
    
    # Save mappings in DB
    mappings = [
        {
            "forwarding_rule_id": ObjectId(rule_id_1),
            "source_channel_id": 11111,
            "source_message_id": 300,
            "destination_channel_id": -10099999,
            "destination_message_id": 6000,
            "forwarded_at": datetime.now(timezone.utc),
        },
        {
            "forwarding_rule_id": ObjectId(rule_id_2),
            "source_channel_id": 11111,
            "source_message_id": 301,
            "destination_channel_id": -10099999,
            "destination_message_id": 6001,
            "forwarded_at": datetime.now(timezone.utc),
        }
    ]
    for m in mappings:
        await mock_db["message_mappings"].insert_one(m)

    worker = TelegramWorker(base_settings, mock_db)

    # Setup mocked delete response
    mock_telegram.client.delete_messages = AsyncMock()

    # Simulate message deleted event
    mock_event = MagicMock(spec=events.MessageDeleted.Event)
    mock_event.chat_id = 11111
    mock_event.deleted_ids = [300, 301, 302]  # 302 has no mapping

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_delete_event(mock_event)
        
        # Verify logger logs delete_propagated for mapped events
        logger_mock.info.assert_any_call(
            "delete_propagated",
            rule_id=rule_id_1,
            source_message_id=300,
            destination_message_id=6000,
            correlation_id=ANY,
        )
        logger_mock.info.assert_any_call(
            "delete_propagated",
            rule_id=rule_id_2,
            source_message_id=301,
            destination_message_id=6001,
            correlation_id=ANY,
        )

    # Verify delete_messages called for the batch in the correct channel
    mock_telegram.client.delete_messages.assert_called_once_with(
        entity=-10099999,
        message_ids=[6000, 6001]
    )


@pytest.mark.asyncio
async def test_epic5_delete_propagation_failures(base_settings, mock_db, mock_telegram):
    """
    Story 5.1: Delete Propagation Edge Cases
    Verify warning log and non-crashing behavior when propagate_delete fails.
    """
    rule_id = str(ObjectId())
    mapping_doc = {
        "forwarding_rule_id": ObjectId(rule_id),
        "source_channel_id": 11111,
        "source_message_id": 400,
        "destination_channel_id": -10099999,
        "destination_message_id": 7000,
        "forwarded_at": datetime.now(timezone.utc),
    }
    await mock_db["message_mappings"].insert_one(mapping_doc)

    worker = TelegramWorker(base_settings, mock_db)

    # Make delete_messages raise an exception
    mock_telegram.client.delete_messages.side_effect = RuntimeError("Delete error")
    base_settings.delivery_max_retries = 0

    mock_event = MagicMock(spec=events.MessageDeleted.Event)
    mock_event.chat_id = 11111
    mock_event.deleted_ids = [400]

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        # Should not crash
        await worker.process_delete_event(mock_event)

        logger_mock.warning.assert_any_call(
            "delete_propagation_failed",
            correlation_id=ANY,
            error=ANY,
            message="Delete propagation failed for destination channel -10099999"
        )


@pytest.mark.asyncio
async def test_epic5_mapping_sweeper(base_settings, mock_db):
    """
    Story 5.1: Mapping Sweeper Task
    Verifies that the mapping sweeper hourly coroutine deletes mappings older than retention days.
    """
    # Seed mappings
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(days=35)
    fresh_time = now - timedelta(days=5)

    expired_mapping = {
        "forwarding_rule_id": ObjectId(),
        "source_channel_id": 11111,
        "source_message_id": 500,
        "destination_channel_id": -10099999,
        "destination_message_id": 8000,
        "forwarded_at": expired_time,
    }
    fresh_mapping = {
        "forwarding_rule_id": ObjectId(),
        "source_channel_id": 11111,
        "source_message_id": 501,
        "destination_channel_id": -10099999,
        "destination_message_id": 8001,
        "forwarded_at": fresh_time,
    }

    await mock_db["message_mappings"].insert_one(expired_mapping)
    await mock_db["message_mappings"].insert_one(fresh_mapping)

    assert len(mock_db["message_mappings"].data_store) == 2

    # Patch asyncio.sleep to exit immediately after one iteration
    with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await run_mapping_sweeper(base_settings, mock_db)

    # Verify only fresh mapping remains
    store = mock_db["message_mappings"].data_store
    assert len(store) == 1
    assert store[0]["source_message_id"] == 501


@pytest.mark.asyncio
async def test_epic5_logging_ring_buffer_and_redaction(base_settings):
    """
    Story 5.2: Structlog ring buffer eviction and secret redacting.
    """
    # Resetup/initialize logging
    base_settings.log_ring_buffer_hours = 0.0003  # ~1.08 seconds buffer size, sets to min 1000 maxlen
    setup_logging(base_settings)
    
    # 1. Verify secrets are redacted
    logger = structlog.get_logger()
    logger.info("user_authenticated", api_key="test-api-key", secret_key="test-secret-key", msg="My api_key is test-api-key")
    
    logs = get_recent_logs()
    assert len(logs) > 0
    latest_log = logs[-1]
    
    # Assert values are redacted
    assert latest_log.get("api_key") == "[REDACTED]"
    assert latest_log.get("secret_key") == "[REDACTED]"
    assert "test-api-key" not in latest_log.get("msg", "")
    assert "[REDACTED]" in latest_log.get("msg", "")

    # 2. Test Ring Buffer eviction
    # Directly set maxlen lower for ring buffer to test eviction easily without inserting 1000 items
    import forward_bot.infrastructure.logging.ring_buffer as rb
    from collections import deque
    rb._ring_buffer = deque(maxlen=5)

    for i in range(10):
        logger.info("bulk_log", index=i)

    recent_logs = get_recent_logs()
    assert len(recent_logs) == 5
    assert recent_logs[0]["index"] == 5
    assert recent_logs[-1]["index"] == 9


# ---------------------------------------------------------------------------
# API Routing Tests: Epic 5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic5_logs_api_endpoints(app_no_lifespan, base_settings):
    """
    Story 5.3: REST and SSE endpoints for log access and search.
    """
    headers = {"X-API-Key": base_settings.api_key}

    # Seed logs into ring buffer
    import forward_bot.infrastructure.logging.ring_buffer as rb
    from collections import deque
    rb._ring_buffer = deque(maxlen=100)
    
    now = datetime.now(timezone.utc)
    log1 = {"event": "forward_succeeded", "level": "info", "timestamp": (now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"), "correlation_id": "c1"}
    log2 = {"event": "pipeline_blocked", "level": "info", "timestamp": now.isoformat().replace("+00:00", "Z"), "correlation_id": "c2"}
    log3 = {"event": "edit_propagation_failed", "level": "warning", "timestamp": now.isoformat().replace("+00:00", "Z"), "correlation_id": "c1"}
    
    rb._ring_buffer.append(log1)
    rb._ring_buffer.append(log2)
    rb._ring_buffer.append(log3)

    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan), base_url="http://test"
    ) as ac:

        # ── Auth Gate Check ──────────────────────────────────────────────────
        assert (await ac.get("/api/v1/logs/recent")).status_code == 401
        assert (await ac.get("/api/v1/logs/search?correlation_id=c1")).status_code == 401

        # ── GET /recent ──────────────────────────────────────────────────────
        res = await ac.get("/api/v1/logs/recent?limit=2", headers=headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert items[0]["correlation_id"] == "c2"
        assert items[1]["correlation_id"] == "c1"

        # GET /recent with event filter
        res = await ac.get("/api/v1/logs/recent?event=forward_succeeded", headers=headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["event"] == "forward_succeeded"

        # ── GET /search ──────────────────────────────────────────────────────
        res = await ac.get("/api/v1/logs/search?correlation_id=c1", headers=headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert all(item["correlation_id"] == "c1" for item in items)

        # ── GET /stream (SSE) ────────────────────────────────────────────────
        # Test historical replay and live logs streaming via SSE
        async with ac.stream("GET", "/api/v1/logs/stream", headers=headers) as response:
            assert response.status_code == 200
            
            # Read first line (should contain historical replay of log1)
            line1 = await response.aread(1000)
            line_str = line1.decode("utf-8")
            assert "data: {" in line_str
            assert "forward_succeeded" in line_str

            # Stream a new event in the background
            loop = asyncio.get_running_loop()
            loop.call_soon(broadcast_log, {"event": "new_live_log", "level": "info", "timestamp": now.isoformat().replace("+00:00", "Z"), "correlation_id": "c3"})
            
            # Read streaming output
            live_line = await response.aread(1000)
            live_str = live_line.decode("utf-8")
            assert "new_live_log" in live_str


@pytest.mark.asyncio
async def test_epic5_stats_endpoint(app_no_lifespan, base_settings):
    """
    Story 5.3: Stats API Summary Endpoint
    """
    headers = {"X-API-Key": base_settings.api_key}

    # Seed logs into ring buffer
    import forward_bot.infrastructure.logging.ring_buffer as rb
    from collections import deque
    rb._ring_buffer = deque(maxlen=100)
    
    now = datetime.now(timezone.utc)
    rb._ring_buffer.append({"event": "forward_succeeded", "level": "info", "timestamp": now.isoformat().replace("+00:00", "Z")})
    rb._ring_buffer.append({"event": "pipeline_blocked", "level": "info", "timestamp": now.isoformat().replace("+00:00", "Z")})
    rb._ring_buffer.append({"event": "edit_propagation_failed", "level": "warning", "timestamp": now.isoformat().replace("+00:00", "Z")})
    rb._ring_buffer.append({"event": "forward_failed", "level": "error", "timestamp": now.isoformat().replace("+00:00", "Z")})
    
    # Old log (more than 24h ago) -> should not count
    old_ts = (now - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    rb._ring_buffer.append({"event": "forward_succeeded", "level": "info", "timestamp": old_ts})

    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan), base_url="http://test"
    ) as ac:
        
        # Auth Check
        assert (await ac.get("/api/v1/stats/summary")).status_code == 401

        res = await ac.get("/api/v1/stats/summary", headers=headers)
        assert res.status_code == 200
        stats = res.json()
        
        assert stats["forwarded_24h"] == 1
        assert stats["blocked_24h"] == 1
        # failed_24h counts error level + events containing 'failed' or 'error'
        # edit_propagation_failed (warning level but 'failed' in name) -> counts
        # forward_failed (error level and 'failed' in name) -> counts
        assert stats["failed_24h"] == 2


@pytest.mark.asyncio
async def test_epic5_admin_reconnect_endpoint(app_no_lifespan, base_settings, mock_telegram):
    """
    Story 5.3: Admin Reconnect Endpoint
    Verifies that calling the endpoint schedules the Telegram reconnect task.
    """
    headers = {"X-API-Key": base_settings.api_key}

    # Setup mocks for reconnection sequence
    mock_telegram.disconnect = AsyncMock()
    mock_telegram.connect = AsyncMock()

    # Mock the fastapi app instance state settings/worker_task
    app_no_lifespan.state.settings = base_settings
    app_no_lifespan.state.worker_task = MagicMock()
    app_no_lifespan.state.worker_task.done = MagicMock(return_value=False)
    app_no_lifespan.state.worker_task.cancel = MagicMock()

    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan), base_url="http://test"
    ) as ac:
        
        # Auth Check
        assert (await ac.post("/api/v1/admin/reconnect")).status_code == 401

        with patch("forward_bot.infrastructure.telegram.telegram_client.disconnect", new_callable=AsyncMock) as mock_disc, \
             patch("forward_bot.infrastructure.telegram.telegram_client.connect", new_callable=AsyncMock) as mock_conn, \
             patch("forward_bot.tasks.run_telegram_worker", new_callable=AsyncMock) as mock_run:

            res = await ac.post("/api/v1/admin/reconnect", headers=headers)
            assert res.status_code == 200
            assert res.json() == {"ok": True}

            # Await background task execution
            await asyncio.sleep(0.1)

            mock_disc.assert_called_once()
            mock_conn.assert_called_once_with(base_settings)
