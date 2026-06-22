"""Unit and integration tests for edit/delete propagation and mapping sweeper."""
import asyncio
import contextvars
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from telethon import events
from telethon.errors import FloodWaitError, RPCError, MessageNotModifiedError
from telethon.tl.types import PeerChannel, Message

from forward_bot.config import Settings
from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository
from forward_bot.infrastructure.telegram.delivery import propagate_edit, propagate_delete
from forward_bot.infrastructure.telegram.worker import TelegramWorker
from forward_bot.infrastructure.mongo.mapping_sweeper import run_mapping_sweeper


@pytest.fixture
def mock_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.delivery_max_retries = 3
    settings.delivery_backoff_factor = 2.0
    settings.delivery_base_delay = 0.01  # small delay for tests
    settings.mapping_retention_days = 30
    return settings


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    # collection is a MagicMock because find() is synchronous in Motor/Pymongo
    collection = MagicMock()
    db.__getitem__.return_value = collection
    return db


@pytest.mark.asyncio
async def test_mapping_repository_extensions(mock_db) -> None:
    """Test get_by_source, get_by_source_messages, and delete_expired_mappings in MappingRepository."""
    repo = MappingRepository(mock_db)
    collection = repo.collection

    # 1. Test get_by_source
    mock_docs = [
        {
            "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d81"),
            "forwarding_rule_id": ObjectId("65c52c6f1f2e3d4a5b6c7d82"),
            "source_channel_id": 12345,
            "source_message_id": 999,
            "destination_channel_id": 54321,
            "destination_message_id": 888,
            "forwarded_at": datetime.now(timezone.utc),
        }
    ]
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_docs)
    collection.find.return_value = mock_cursor

    mappings = await repo.get_by_source(12345, 999)
    assert len(mappings) == 1
    assert mappings[0].id == "65c52c6f1f2e3d4a5b6c7d81"
    collection.find.assert_called_with({
        "source_channel_id": 12345,
        "source_message_id": 999
    })

    # 2. Test get_by_source_messages
    mappings_batch = await repo.get_by_source_messages(12345, [999, 1000])
    assert len(mappings_batch) == 1
    collection.find.assert_called_with({
        "source_channel_id": 12345,
        "source_message_id": {"$in": [999, 1000]}
    })

    # 3. Test delete_expired_mappings
    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 5
    collection.delete_many = AsyncMock(return_value=mock_delete_result)

    deleted = await repo.delete_expired_mappings(30)
    assert deleted == 5
    collection.delete_many.assert_called_once()
    query = collection.delete_many.call_args[0][0]
    assert "forwarded_at" in query
    assert "$lt" in query["forwarded_at"]


@pytest.mark.asyncio
async def test_propagate_edit_success(mock_settings) -> None:
    """Test successful propagate_edit execution."""
    mock_client = MagicMock()
    mock_client.edit_message = AsyncMock()

    await propagate_edit(
        client=mock_client,
        destination_channel_id=54321,
        destination_message_id=888,
        text="Updated Text",
        caption=None,
        media=None,
        rule_id="r1",
        correlation_id="c1",
        settings=mock_settings
    )
    mock_client.edit_message.assert_called_once_with(
        entity=54321,
        message=888,
        text="Updated Text"
    )


@pytest.mark.asyncio
async def test_propagate_edit_not_modified(mock_settings) -> None:
    """Test propagate_edit catches MessageNotModifiedError and treats it as success."""
    mock_client = MagicMock()
    mock_client.edit_message = AsyncMock(side_effect=MessageNotModifiedError(MagicMock()))

    # Should not raise an error
    await propagate_edit(
        client=mock_client,
        destination_channel_id=54321,
        destination_message_id=888,
        text="Updated Text",
        caption=None,
        media=None,
        rule_id="r1",
        correlation_id="c1",
        settings=mock_settings
    )
    mock_client.edit_message.assert_called_once()


@pytest.mark.asyncio
async def test_propagate_edit_flood_wait_retry(mock_settings) -> None:
    """Test propagate_edit sleep-and-retry on FloodWaitError."""
    mock_client = MagicMock()
    mock_client.edit_message = AsyncMock(side_effect=[FloodWaitError(MagicMock(), 2), None])

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await propagate_edit(
            client=mock_client,
            destination_channel_id=54321,
            destination_message_id=888,
            text="Updated Text",
            caption=None,
            media=None,
            rule_id="r1",
            correlation_id="c1",
            settings=mock_settings
        )
        mock_sleep.assert_called_once_with(2)
        assert mock_client.edit_message.call_count == 2


@pytest.mark.asyncio
async def test_propagate_delete_success(mock_settings) -> None:
    """Test successful propagate_delete execution."""
    mock_client = MagicMock()
    mock_client.delete_messages = AsyncMock()

    await propagate_delete(
        client=mock_client,
        destination_channel_id=54321,
        destination_message_ids=[888, 889],
        settings=mock_settings,
        rule_ids=["r1"],
        correlation_id="c1"
    )
    mock_client.delete_messages.assert_called_once_with(
        entity=54321,
        message_ids=[888, 889]
    )


@pytest.mark.asyncio
async def test_worker_process_edit_event_success(mock_settings, mock_db) -> None:
    """Test worker handles MessageEdited event, looks up mappings, dispatches in context vars."""
    worker = TelegramWorker(mock_settings, mock_db)

    # Mock mappings
    mapping = MessageMapping(
        id="m1",
        forwarding_rule_id="r1",
        source_channel_id=12345,
        source_message_id=999,
        destination_channel_id=54321,
        destination_message_id=888,
        forwarded_at=datetime.now(timezone.utc)
    )
    worker.mapping_repo.get_by_source = AsyncMock(return_value=[mapping])

    # Mock Telethon event
    mock_event = MagicMock(spec=events.MessageEdited.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 999
    mock_event.message.peer_id = PeerChannel(channel_id=12345)
    mock_event.message.media = None
    mock_event.message.message = "New Edit Text"
    mock_event.chat_id = 12345

    # Mock propagate_edit
    with patch("forward_bot.infrastructure.telegram.delivery.propagate_edit", new_callable=AsyncMock) as mock_prop, \
         patch("forward_bot.infrastructure.telegram.telegram_client") as mock_tg_holder:
        mock_client = MagicMock()
        mock_tg_holder.client = mock_client

        await worker.process_edit_event(mock_event)

        worker.mapping_repo.get_by_source.assert_called_once_with(
            source_channel_id=12345,
            source_message_id=999
        )
        mock_prop.assert_called_once()
        args = mock_prop.call_args[1]
        assert args["destination_channel_id"] == 54321
        assert args["destination_message_id"] == 888
        assert args["text"] == "New Edit Text"


@pytest.mark.asyncio
async def test_worker_process_delete_event_success(mock_settings, mock_db) -> None:
    """Test worker handles MessageDeleted event, groups deletions, dispatches batched delete."""
    worker = TelegramWorker(mock_settings, mock_db)

    # Mock mappings for multiple deleted messages to the same destination
    mapping1 = MessageMapping(
        id="m1",
        forwarding_rule_id="r1",
        source_channel_id=12345,
        source_message_id=999,
        destination_channel_id=54321,
        destination_message_id=888,
        forwarded_at=datetime.now(timezone.utc)
    )
    mapping2 = MessageMapping(
        id="m2",
        forwarding_rule_id="r1",
        source_channel_id=12345,
        source_message_id=1000,
        destination_channel_id=54321,
        destination_message_id=889,
        forwarded_at=datetime.now(timezone.utc)
    )
    worker.mapping_repo.get_by_source_messages = AsyncMock(return_value=[mapping1, mapping2])

    # Mock Telethon event
    mock_event = MagicMock(spec=events.MessageDeleted.Event)
    mock_event.deleted_ids = [999, 1000]
    mock_event.chat_id = 12345

    # Mock propagate_delete
    with patch("forward_bot.infrastructure.telegram.delivery.propagate_delete", new_callable=AsyncMock) as mock_prop, \
         patch("forward_bot.infrastructure.telegram.telegram_client") as mock_tg_holder:
        mock_client = MagicMock()
        mock_tg_holder.client = mock_client

        await worker.process_delete_event(mock_event)

        worker.mapping_repo.get_by_source_messages.assert_called_once_with(
            source_channel_id=12345,
            source_message_ids=[999, 1000]
        )
        mock_prop.assert_called_once()
        args = mock_prop.call_args[1]
        assert args["destination_channel_id"] == 54321
        assert args["destination_message_ids"] == [888, 889]


@pytest.mark.asyncio
async def test_worker_propagation_unmapped_ignored(mock_settings, mock_db) -> None:
    """Test that event is silently ignored if no mappings exist."""
    worker = TelegramWorker(mock_settings, mock_db)
    worker.mapping_repo.get_by_source = AsyncMock(return_value=[])
    worker.mapping_repo.get_by_source_messages = AsyncMock(return_value=[])

    mock_edit_event = MagicMock(spec=events.MessageEdited.Event)
    mock_edit_event.message = MagicMock(spec=Message)
    mock_edit_event.message.id = 999
    mock_edit_event.message.peer_id = PeerChannel(channel_id=12345)
    mock_edit_event.chat_id = 12345

    mock_delete_event = MagicMock(spec=events.MessageDeleted.Event)
    mock_delete_event.deleted_ids = [999]
    mock_delete_event.chat_id = 12345

    with patch("forward_bot.infrastructure.telegram.delivery.propagate_edit") as mock_edit_prop, \
         patch("forward_bot.infrastructure.telegram.delivery.propagate_delete") as mock_delete_prop:
        
        await worker.process_edit_event(mock_edit_event)
        await worker.process_delete_event(mock_delete_event)

        mock_edit_prop.assert_not_called()
        mock_delete_prop.assert_not_called()


@pytest.mark.asyncio
async def test_worker_propagation_error_isolation(mock_settings, mock_db) -> None:
    """Test that edit propagation failure in one destination does not affect other destinations."""
    worker = TelegramWorker(mock_settings, mock_db)

    # 2 mappings to different destinations
    mapping1 = MessageMapping(
        id="m1", forwarding_rule_id="r1", source_channel_id=12345, source_message_id=999,
        destination_channel_id=54321, destination_message_id=888, forwarded_at=datetime.now(timezone.utc)
    )
    mapping2 = MessageMapping(
        id="m2", forwarding_rule_id="r2", source_channel_id=12345, source_message_id=999,
        destination_channel_id=54322, destination_message_id=889, forwarded_at=datetime.now(timezone.utc)
    )
    worker.mapping_repo.get_by_source = AsyncMock(return_value=[mapping1, mapping2])

    mock_event = MagicMock(spec=events.MessageEdited.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 999
    mock_event.message.peer_id = PeerChannel(channel_id=12345)
    mock_event.message.media = None
    mock_event.message.message = "Some text to edit"
    mock_event.chat_id = 12345

    # propagate_edit fails for destination 54321, succeeds for 54322
    async def side_effect(*args, **kwargs):
        if kwargs.get("destination_channel_id") == 54321:
            raise RuntimeError("Telegram write failed")
        return None

    with patch("forward_bot.infrastructure.telegram.delivery.propagate_edit", side_effect=side_effect) as mock_prop, \
         patch("forward_bot.infrastructure.telegram.telegram_client") as mock_tg_holder:
        mock_tg_holder.client = MagicMock()

        # Should run without raising exception
        await worker.process_edit_event(mock_event)

        # Both dispatches should be called
        assert mock_prop.call_count == 2


@pytest.mark.asyncio
async def test_run_mapping_sweeper_loop(mock_settings, mock_db) -> None:
    """Test run_mapping_sweeper background task runs and terminates on CancelledError."""
    # We will patch sleep to raise CancelledError on first sleep to terminate
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.side_effect = [asyncio.CancelledError()]
        
        repo = MappingRepository(mock_db)
        repo.delete_expired_mappings = AsyncMock(return_value=12)
        
        with patch("forward_bot.infrastructure.mongo.mapping_sweeper.MappingRepository", return_value=repo):
            with pytest.raises(asyncio.CancelledError):
                await run_mapping_sweeper(mock_settings, mock_db)
                
            repo.delete_expired_mappings.assert_called_once_with(30)
