"""
E2E & Integration Tests for Epic 4: Core Message Forwarding Engine.

Covers:
  4.1 Pipeline Infrastructure (Context, Protocol, Engine, PersistMapping)
  4.2 Filter Pipeline Steps (TimeWindow, Sampling, MediaType, Keywords, Empty)
  4.3 Transform & Media Steps (MediaDecision, ReplyLookup, SourceRefReplace, TextReplacement, Removals, Attribution, MediaReplacement)
  4.4 Telegram Delivery & Reliability (FloodWait, Retries, Per-Rule Isolation)
  4.5 Telegram Worker (Reload loop, process event, in-memory sampling counters)
"""
import asyncio
import pytest
import re
from datetime import datetime, timezone, time
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from bson import ObjectId
import zoneinfo

from telethon import events
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, Message
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    SamplingConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
    TimeWindowConfig,
)
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder
from forward_bot.infrastructure.telegram.worker import TelegramWorker
from forward_bot.infrastructure.telegram.delivery import deliver_message


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
        sampling_persist=False,
        delivery_max_retries=2,
        delivery_backoff_factor=1.1,
        delivery_base_delay=0.01,
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
    mock_client.run_until_disconnected = AsyncMock()
    
    telegram_client.client = mock_client
    telegram_client.status = "connected"
    
    yield telegram_client
    
    telegram_client.client = original_client
    telegram_client.status = original_status


# ---------------------------------------------------------------------------
# E2E Test Cases: Epic 4
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_epic4_happy_path_forwarding(base_settings, mock_db, mock_telegram):
    """
    Story 4.1 & 4.5: Happy Path Forwarding E2E
    Verifies that a message from a registered source channel processed by the worker's
    NewMessage event handler runs the 18-step pipeline, delivers it, and stores the mapping.
    """
    source_id = str(ObjectId())
    rule_id = str(ObjectId())

    source = Source(
        id=source_id,
        telegram_id=11111,
        telegram_username="source_chan",
        display_name="Source Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    rule = ForwardingRule(
        id=rule_id,
        source_id=source_id,
        destination_channel="-10099999",
        is_active=True,
        keyword_match_mode="literal",
        block_keywords=[],
        allow_keywords=[],
        media_type_filter=["text", "photo"],
        remove_links=False,
        remove_hashtags=False,
        remove_mentions=False,
        forward_media="forward",
    )

    # Set up cache snapshot
    cache = RuleCache(
        sources={source_id: source},
        rules=[rule],
        version=1,
    )
    CacheHolder.current = cache

    # Setup worker
    worker = TelegramWorker(base_settings, mock_db)

    # Setup mocked sent message return
    sent_msg = MagicMock()
    sent_msg.id = 9001
    sent_msg.chat_id = -10099999
    mock_telegram.client.send_message = AsyncMock(return_value=sent_msg)

    # Simulate message event
    mock_event = MagicMock(spec=events.NewMessage.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 123
    mock_event.message.peer_id = PeerChannel(channel_id=11111)
    mock_event.message.message = "Forward me!"
    mock_event.message.media = None
    mock_event.message.reply_to = None

    await worker.process_event(mock_event)

    # Verifications
    mock_telegram.client.send_message.assert_called_once_with(
        -10099999,
        message="Forward me!",
        reply_to=None,
    )

    # Verify message mapping created in DB
    mappings = mock_db["message_mappings"].data_store
    assert len(mappings) == 1
    m = mappings[0]
    assert str(m["forwarding_rule_id"]) == rule_id
    assert m["source_channel_id"] == 11111
    assert m["source_message_id"] == 123
    assert m["destination_channel_id"] == -10099999
    assert m["destination_message_id"] == 9001


@pytest.mark.asyncio
async def test_epic4_pipeline_filter_steps(base_settings, mock_db, mock_telegram, monkeypatch):
    """
    Story 4.2: Tests TimeWindow, Sampling, MediaType, Keywords, and Empty result filters.
    """
    source_id = str(ObjectId())
    rule_id = str(ObjectId())
    source = Source(
        id=source_id,
        telegram_id=22222,
        telegram_username="filter_chan",
        display_name="Filter Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Configure rule with complex keywords, sampling, and media filter
    rule = ForwardingRule(
        id=rule_id,
        source_id=source_id,
        destination_channel="-10099999",
        is_active=True,
        keyword_match_mode="regex",
        block_keywords=["scam.*", "dump[s]?"],
        allow_keywords=["BTC", "ETH|ADA"],
        media_type_filter=["text"],  # text only, photo is blocked
        sampling=SamplingConfig(n=1),  # Set n=1 initially so it does not block by sampling
    )

    cache = RuleCache(
        sources={source_id: source},
        rules=[rule],
        version=1,
    )
    # Pre-populate compiled patterns in cache
    compiled_patterns = MagicMock()
    compiled_patterns.block_patterns = [re.compile("scam.*", re.I), re.compile("dump[s]?", re.I)]
    compiled_patterns.allow_patterns = [re.compile("BTC", re.I), re.compile("ETH|ADA", re.I)]
    cache.compiled_patterns[rule_id] = compiled_patterns
    CacheHolder.current = cache

    worker = TelegramWorker(base_settings, mock_db)
    
    # 1. Test MediaType Filter: Photo should block because filter only allows ["text"]
    mock_event_photo = MagicMock(spec=events.NewMessage.Event)
    mock_event_photo.message = MagicMock(spec=Message)
    mock_event_photo.message.id = 201
    mock_event_photo.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_photo.message.message = "BTC analysis"
    mock_event_photo.message.media = MagicMock()  # mock presence of photo/media
    mock_event_photo.message.media.type_name = "photo"
    mock_event_photo.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_photo)
        logger_mock.info.assert_any_call(
            "pipeline_blocked",
            reason="media_type_filtered",
            rule_id=rule_id,
            correlation_id=ANY,
        )

    # 2. Test Block Keyword Filter
    mock_event_block = MagicMock(spec=events.NewMessage.Event)
    mock_event_block.message = MagicMock(spec=Message)
    mock_event_block.message.id = 202
    mock_event_block.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_block.message.message = "BTC price is a scammer strategy!"
    mock_event_block.message.media = None
    mock_event_block.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_block)
        logger_mock.info.assert_any_call(
            "pipeline_blocked",
            reason="blocked_keyword",
            rule_id=rule_id,
            correlation_id=ANY,
        )

    # 3. Test Allow Keyword Filter
    mock_event_no_allow = MagicMock(spec=events.NewMessage.Event)
    mock_event_no_allow.message = MagicMock(spec=Message)
    mock_event_no_allow.message.id = 203
    mock_event_no_allow.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_no_allow.message.message = "Buy DOGE now!"
    mock_event_no_allow.message.media = None
    mock_event_no_allow.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_no_allow)
        logger_mock.info.assert_any_call(
            "pipeline_blocked",
            reason="no_allow_keyword_matched",
            rule_id=rule_id,
            correlation_id=ANY,
        )

    # 4. Test Sampling Filter (n=3)
    rule.sampling = SamplingConfig(n=3)
    worker.sampling_counters = {}
    
    # Message 1 matching allows:
    mock_event_allow1 = MagicMock(spec=events.NewMessage.Event)
    mock_event_allow1.message = MagicMock(spec=Message)
    mock_event_allow1.message.id = 204
    mock_event_allow1.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_allow1.message.message = "Buy BTC"
    mock_event_allow1.message.media = None
    mock_event_allow1.message.reply_to = None

    # Reset delivery mock count
    mock_telegram.client.send_message.reset_mock()

    # 1st matching message -> gets sampled out (counter=1)
    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_allow1)
        logger_mock.info.assert_any_call("pipeline_blocked", reason="sampled_out", rule_id=rule_id, correlation_id=ANY)

    # 2nd matching message -> gets sampled out (counter=2)
    mock_event_allow2 = MagicMock(spec=events.NewMessage.Event)
    mock_event_allow2.message = MagicMock(spec=Message)
    mock_event_allow2.message.id = 205
    mock_event_allow2.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_allow2.message.message = "Buy ETH"
    mock_event_allow2.message.media = None
    mock_event_allow2.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_allow2)
        logger_mock.info.assert_any_call("pipeline_blocked", reason="sampled_out", rule_id=rule_id, correlation_id=ANY)

    # 3rd matching message -> passes sampling and gets forwarded (counter=3)
    mock_event_allow3 = MagicMock(spec=events.NewMessage.Event)
    mock_event_allow3.message = MagicMock(spec=Message)
    mock_event_allow3.message.id = 206
    mock_event_allow3.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_allow3.message.message = "Buy ADA"
    mock_event_allow3.message.media = None
    mock_event_allow3.message.reply_to = None

    sent_msg = MagicMock()
    sent_msg.id = 9002
    sent_msg.chat_id = -10099999
    mock_telegram.client.send_message = AsyncMock(return_value=sent_msg)

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_allow3)
        logger_mock.info.assert_any_call("forward_succeeded", rule_id=rule_id, source_message_id=206, destination_message_id=9002, correlation_id=ANY)

    # 5. Database-Backed Sampling Test (SAMPLING_PERSIST=True)
    monkeypatch.setenv("SAMPLING_PERSIST", "true")
    base_settings.sampling_persist = True
    rule.sampling = SamplingConfig(n=2)  # n=2
    # Reset in-memory counters
    worker.sampling_counters = {}

    mock_event_persist1 = MagicMock(spec=events.NewMessage.Event)
    mock_event_persist1.message = MagicMock(spec=Message)
    mock_event_persist1.message.id = 207
    mock_event_persist1.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_persist1.message.message = "Buy BTC"
    mock_event_persist1.message.media = None
    mock_event_persist1.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_persist1)
        # Verify it writes to sampling_counters collection
        assert len(mock_db["sampling_counters"].data_store) == 1
        assert mock_db["sampling_counters"].data_store[0]["counter"] == 1
        logger_mock.info.assert_any_call("pipeline_blocked", reason="sampled_out", rule_id=rule_id, correlation_id=ANY)

    mock_event_persist2 = MagicMock(spec=events.NewMessage.Event)
    mock_event_persist2.message = MagicMock(spec=Message)
    mock_event_persist2.message.id = 208
    mock_event_persist2.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_persist2.message.message = "Buy BTC"
    mock_event_persist2.message.media = None
    mock_event_persist2.message.reply_to = None

    with patch("structlog.get_logger") as mock_log:
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_persist2)
        # Verify db updated to 2 (n=2, so it forwards)
        assert mock_db["sampling_counters"].data_store[0]["counter"] == 2
        logger_mock.info.assert_any_call("forward_succeeded", rule_id=rule_id, source_message_id=208, destination_message_id=9002, correlation_id=ANY)

    # 6. Test TimeWindow restriction (outside window)
    rule.time_window = TimeWindowConfig(
        timezone="America/New_York",
        days_of_week=["MON"],
        start_time="09:00",
        end_time="17:00",
    )
    
    mock_event_time = MagicMock(spec=events.NewMessage.Event)
    mock_event_time.message = MagicMock(spec=Message)
    mock_event_time.message.id = 209
    mock_event_time.message.peer_id = PeerChannel(channel_id=22222)
    mock_event_time.message.message = "Buy BTC"
    mock_event_time.message.media = None
    mock_event_time.message.reply_to = None

    # Simulate message arriving on a Sunday (outside Monday window)
    sunday_dt = datetime(2026, 6, 21, 12, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
    # Patch datetime inside time_window.py to return sunday_dt
    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            dt = sunday_dt
            if tz is not None:
                dt = dt.astimezone(tz)
            return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)

    with patch("structlog.get_logger") as mock_log, \
         patch("forward_bot.application.pipeline.steps.time_window.datetime", MockDatetime):
        logger_mock = MagicMock()
        mock_log.return_value = logger_mock
        await worker.process_event(mock_event_time)
        logger_mock.info.assert_any_call("pipeline_blocked", reason="outside_time_window", rule_id=rule_id, correlation_id=ANY)


@pytest.mark.asyncio
async def test_epic4_pipeline_transform_steps(base_settings, mock_db, mock_telegram):
    """
    Story 4.3: Tests MediaDecision, ReplyLookup, SourceRefReplace, TextReplacement,
    Link/Hashtag/Mention Removal, Whitespace Normalization, and Attribution.
    """
    source_id = str(ObjectId())
    rule_id = str(ObjectId())
    source = Source(
        id=source_id,
        telegram_id=33333,
        telegram_username="source_ref",
        display_name="Source Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    rule = ForwardingRule(
        id=rule_id,
        source_id=source_id,
        destination_channel="-10099999",
        is_active=True,
        remove_links=True,
        remove_hashtags=True,
        remove_mentions=True,
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(
            enabled=True,
            replacement="@my_target",
            replace_display_name=True,
        ),
        attribution=AttributionConfig(
            enabled=True,
            position="prefix",
            format="From {source_name} - {source_username}",
        ),
        media_replacement=MediaReplacementConfig(
            enabled=True,
            replacement_image_path="test_image.jpg",
        ),
        forward_media="forward",
    )

    # Replacement rule
    rr = ReplacementRule(
        id=str(ObjectId()),
        forwarding_rule_id=rule_id,
        search_text="scam",
        replacement_text="legit project",
        match_mode="literal",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    cache = RuleCache(
        sources={source_id: source},
        rules=[rule],
        version=1,
    )
    cache.replacements[rule_id] = [rr]
    CacheHolder.current = cache

    # Setup worker
    worker = TelegramWorker(base_settings, mock_db)

    # Seed mapping database with parent mapping to test ReplyLookup
    parent_mapping = {
        "forwarding_rule_id": ObjectId(rule_id),
        "source_channel_id": 33333,
        "source_message_id": 100,
        "destination_channel_id": -10099999,
        "destination_message_id": 5000,
        "forwarded_at": datetime.now(timezone.utc),
    }
    await mock_db["message_mappings"].insert_one(parent_mapping)

    # Setup mock send response
    sent_msg = MagicMock()
    sent_msg.id = 5001
    sent_msg.chat_id = -10099999
    mock_telegram.client.send_message = AsyncMock(return_value=sent_msg)

    # 1. Test full transform pipeline with reply message and photo
    mock_event = MagicMock(spec=events.NewMessage.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 101
    mock_event.message.peer_id = PeerChannel(channel_id=33333)
    mock_event.message.message = "Check out @source_ref. It is a scam. See https://competitor.com/link. #tag"
    mock_event.message.media = MagicMock()  # Simulates photo message
    mock_event.message.media.type_name = "photo"
    
    # Reply to parent message 100
    mock_reply = MagicMock()
    mock_reply.reply_to_msg_id = 100
    mock_event.message.reply_to = mock_reply

    # Stub file reading in MediaReplacementStep
    with patch("pathlib.Path.exists", return_value=True), \
         patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        
        mock_thread.return_value = True
        await worker.process_event(mock_event)

    # Verifications of transformations:
    # Original message text: "Check out @source_ref. It is a scam. See https://competitor.com/link. #tag"
    # Auto ref replaced -> "Check out @my_target. It is a scam. See https://competitor.com/link. #tag"
    # Text Replacement (scam -> legit project) -> "Check out @my_target. It is a legit project. See https://competitor.com/link. #tag"
    # Link, hashtag, mention stripped:
    # Link: "See https://competitor.com/link." -> "See"
    # Mention: "@my_target" -> stripped (mention removal strips "@name" tokens)
    # Hashtag: "#tag" -> stripped
    # Resulting base text: "Check out . It is a legit project. See"
    # Whitespace Normalized: "Check out . It is a legit project. See" -> "Check out. It is a legit project. See"
    # Attribution Prefix formatting: "From Source Channel - @source_ref\n\nCheck out..."
    
    # Check that send_message was called with formatting and correct reply ID
    called_args, called_kwargs = mock_telegram.client.send_message.call_args
    assert called_kwargs["reply_to"] == 5000
    assert called_kwargs["file"] is not None  # photo was forwarded (replacement image path)
    
    caption_text = called_kwargs["message"]
    assert "From Source Channel - source_ref" in caption_text
    assert "legit project" in caption_text
    assert "https://competitor.com" not in caption_text
    assert "#tag" not in caption_text

    # 2. Test Media Replacement Path Traversal Block
    rule.media_replacement.replacement_image_path = "../../etc/passwd"
    mock_telegram.client.send_message.reset_mock()
    
    with patch("forward_bot.application.pipeline.steps.media_replacement.logger") as logger_mock:
        await worker.process_event(mock_event)
        # Should warning log traversal and fallback
        logger_mock.warning.assert_any_call(
            "media_replacement_path_traversal_attempt",
            rule_id=rule_id,
            path="../../etc/passwd",
            base_dir=ANY,
        )


@pytest.mark.asyncio
async def test_epic4_delivery_reliability_and_isolation(base_settings, mock_db, mock_telegram):
    """
    Story 4.4: Tests FloodWaitError retry logic, backoff exhaustion, and rule-level failure isolation.
    """
    source_id = str(ObjectId())
    rule_id_1 = str(ObjectId())
    rule_id_2 = str(ObjectId())

    source = Source(
        id=source_id,
        telegram_id=44444,
        telegram_username="reliable_chan",
        display_name="Reliable Source",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Rule 1: Fails/rate-limited
    rule1 = ForwardingRule(
        id=rule_id_1,
        source_id=source_id,
        destination_channel="-10088888",
        is_active=True,
    )

    # Rule 2: Succeeds
    rule2 = ForwardingRule(
        id=rule_id_2,
        source_id=source_id,
        destination_channel="-10099999",
        is_active=True,
    )

    cache = RuleCache(
        sources={source_id: source},
        rules=[rule1, rule2],
        version=1,
    )
    CacheHolder.current = cache

    worker = TelegramWorker(base_settings, mock_db)

    # 1. Test Rule-level isolation & FloodWaitError retry
    # Rule 1 raises FloodWaitError once, then succeeds. Rule 2 succeeds immediately.
    call_counts = {"rule1": 0, "rule2": 0}
    sent_msg = MagicMock()
    sent_msg.id = 1234
    sent_msg.chat_id = -10099999

    async def mock_send(dest, message, reply_to=None, file=None):
        if dest == -10088888:
            call_counts["rule1"] += 1
            if call_counts["rule1"] == 1:
                raise FloodWaitError(MagicMock(), 1)  # sleep 1s
            return sent_msg
        elif dest == -10099999:
            call_counts["rule2"] += 1
            return sent_msg

    mock_telegram.client.send_message.side_effect = mock_send

    mock_event = MagicMock(spec=events.NewMessage.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 301
    mock_event.message.peer_id = PeerChannel(channel_id=44444)
    mock_event.message.message = "Reliability Test"
    mock_event.message.media = None
    mock_event.message.reply_to = None

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await worker.process_event(mock_event)
        
        # Verify FloodWait sleep was called once for 1s
        mock_sleep.assert_called_once_with(1)
        # Verify both rules successfully finished (Rule 1 retried)
        assert call_counts["rule1"] == 2
        assert call_counts["rule2"] == 1

    # 2. Test backoff exhaustion
    # Reset mocks
    mock_telegram.client.send_message.reset_mock()
    # Always raise ConnectionError to trigger transient failure retry
    mock_telegram.client.send_message.side_effect = ConnectionError("Disconnected")

    base_settings.delivery_max_retries = 3
    base_settings.delivery_base_delay = 0.01

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("forward_bot.application.pipeline.steps.deliver.get_settings", return_value=base_settings), \
         patch("forward_bot.infrastructure.telegram.delivery.logger") as logger_mock:
        await worker.process_event(mock_event)
        
        # Verify sleep called 6 times (2 rules * 3 retries)
        assert mock_sleep.call_count == 6
        # Verify error event logged
        logger_mock.error.assert_any_call(
            "forward_failed",
            rule_id=rule_id_1,
            correlation_id=ANY,
            error="Disconnected",
            message="Forwarding failed after 3 retries due to transient error."
        )


@pytest.mark.asyncio
async def test_epic4_worker_shutdown_and_reload(base_settings, mock_db, mock_telegram):
    """
    Story 4.4 & 4.5: Tests reload_loop subscription behavior and graceful shutdown handling.
    """
    source_id = str(ObjectId())
    
    # Public channel source
    source1 = Source(
        id=source_id,
        telegram_id=55555,
        telegram_username="public_chan",
        display_name="Public Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Private invite link source
    source2 = Source(
        id=str(ObjectId()),
        telegram_id=66666,
        telegram_username="joinchat/abc123xyz",
        display_name="Private Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    rule1 = ForwardingRule(source_id=source_id, destination_channel="dest", is_active=True, id="r1")
    rule2 = ForwardingRule(source_id=source2.id, destination_channel="dest", is_active=True, id="r2")

    cache = RuleCache(
        sources={source_id: source1, source2.id: source2},
        rules=[rule1, rule2],
        version=1,
    )
    CacheHolder.current = cache

    mock_telegram.client.get_entity = AsyncMock(return_value="resolved_entity")

    # Instantiate worker
    worker = TelegramWorker(base_settings, mock_db)

    # 1. Test reload loop joins channels via correct requests
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Loop once then cancel reload
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        try:
            await worker.reload_loop()
        except asyncio.CancelledError:
            pass

        # Verify JoinChannelRequest for public channel
        mock_telegram.client.assert_any_call(JoinChannelRequest("resolved_entity"))
        # Verify ImportChatInviteRequest for private invite link hash
        mock_telegram.client.assert_any_call(ImportChatInviteRequest(hash="abc123xyz"))

    # 2. Test worker startup & graceful shutdown
    # Stub run_until_disconnected to raise CancelledError
    mock_telegram.client.run_until_disconnected = AsyncMock(side_effect=asyncio.CancelledError())

    # Start worker run in task and cancel it immediately
    worker_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.01)
    
    with pytest.raises(asyncio.CancelledError):
        await worker_task

    # Verify event handler registered then cleaned up
    mock_telegram.client.on.assert_called_once()
    mock_telegram.client.remove_event_handler.assert_called_once()
