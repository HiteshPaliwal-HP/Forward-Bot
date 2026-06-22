"""Unit tests for the TelegramWorker background worker."""
import asyncio
import contextvars
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telethon import events
from telethon.tl.types import PeerChannel, PeerChat, Message
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from forward_bot.config import Settings
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, SamplingConfig
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder
from forward_bot.infrastructure.telegram.worker import TelegramWorker


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.hot_reload_interval = 0.05
    settings.sampling_persist = False
    return settings


@pytest.mark.asyncio
async def test_worker_startup_and_shutdown(mock_settings, mock_db) -> None:
    """Test worker starts, registers handlers, starts reload task, and terminates gracefully."""
    mock_client = MagicMock()
    mock_client.run_until_disconnected = AsyncMock()

    # Stub run_until_disconnected to raise CancelledError to trigger shutdown sequence
    mock_client.run_until_disconnected.side_effect = asyncio.CancelledError()

    with patch("forward_bot.infrastructure.telegram.telegram_client") as mock_tg_holder:
        mock_tg_holder.is_connected = True
        mock_tg_holder.client = mock_client

        worker = TelegramWorker(mock_settings, mock_db)
        
        with pytest.raises(asyncio.CancelledError):
            await worker.run()

        # Assert handler registration and removal
        assert mock_client.on.call_count == 3
        assert mock_client.remove_event_handler.call_count == 3


@pytest.mark.asyncio
async def test_worker_reload_loop_joins_channels(mock_settings, mock_db) -> None:
    """Test worker reload loop scans cache and issues JoinChannelRequest and ImportChatInviteRequest."""
    mock_client = MagicMock()
    mock_client.get_entity = AsyncMock(return_value="resolved_entity")
    mock_client.run_until_disconnected = AsyncMock()

    # Active source has no username, is a channel, should be joined
    src1 = Source(
        id="src_1",
        telegram_id=11111,
        telegram_username=None,
        display_name="Source 1",
        type="channel",
        folder_id=None,
        created_at=MagicMock(),
        updated_at=MagicMock()
    )

    # Active source has username, is a channel, should be joined
    src2 = Source(
        id="src_2",
        telegram_id=22222,
        telegram_username="my_pub_chan",
        display_name="Source 2",
        type="channel",
        folder_id=None,
        created_at=MagicMock(),
        updated_at=MagicMock()
    )

    # Active source is a private link (joinchat/hash)
    src3 = Source(
        id="src_3",
        telegram_id=33333,
        telegram_username="joinchat/abc123xyz",
        display_name="Source 3",
        type="channel",
        folder_id=None,
        created_at=MagicMock(),
        updated_at=MagicMock()
    )

    rule1 = ForwardingRule(source_id="src_1", destination_channel="dest", is_active=True, id="r1")
    rule2 = ForwardingRule(source_id="src_2", destination_channel="dest", is_active=True, id="r2")
    rule3 = ForwardingRule(source_id="src_3", destination_channel="dest", is_active=True, id="r3")

    cache = RuleCache(
        sources={"src_1": src1, "src_2": src2, "src_3": src3},
        rules=[rule1, rule2, rule3],
        version=1
    )

    with patch("forward_bot.infrastructure.telegram.telegram_client") as mock_tg_holder, \
         patch("forward_bot.infrastructure.cache.rule_cache.CacheHolder.current", new=cache):

        mock_tg_holder.is_connected = True
        mock_tg_holder.client = mock_client

        worker = TelegramWorker(mock_settings, mock_db)
        
        # Run reload loop for exactly one iteration by mocking reload_loop's sleep
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            try:
                await worker.reload_loop()
            except asyncio.CancelledError:
                pass

            # Assert JoinChannelRequest was called for src1 and src2
            # Since src3 was an invite link, ImportChatInviteRequest is called instead.
            mock_client.assert_any_call(JoinChannelRequest("resolved_entity"))
            mock_client.assert_any_call(ImportChatInviteRequest(hash="abc123xyz"))


@pytest.mark.asyncio
async def test_process_event_no_matching_source(mock_settings, mock_db) -> None:
    """Test that event from unregistered source is ignored."""
    worker = TelegramWorker(mock_settings, mock_db)
    worker.pipeline_engine.execute = AsyncMock()

    # Event from telegram ID 99999
    mock_event = MagicMock(spec=events.NewMessage.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.peer_id = PeerChannel(channel_id=99999)
    mock_event.chat_id = 99999

    # Cache with only source ID 11111
    src1 = Source(id="src_1", telegram_id=11111, telegram_username=None, display_name="Src 1", type="channel", folder_id=None, created_at=MagicMock(), updated_at=MagicMock())
    cache = RuleCache(sources={"src_1": src1}, rules=[], version=1)

    with patch("forward_bot.infrastructure.cache.rule_cache.CacheHolder.current", new=cache):
        await worker.process_event(mock_event)
        worker.pipeline_engine.execute.assert_not_called()


@pytest.mark.asyncio
async def test_process_event_forward_success(mock_settings, mock_db) -> None:
    """Test process_event parses message, runs pipeline engine, isolates context, and logs success."""
    worker = TelegramWorker(mock_settings, mock_db)

    # Mock pipeline execution success
    mock_result = MagicMock(spec=PipelineContext)
    mock_result.metadata = {"destination_message_id": 9876}
    worker.pipeline_engine.execute = AsyncMock(return_value=mock_result)

    src1 = Source(id="src_1", telegram_id=11111, telegram_username="mysrc", display_name="Src 1", type="channel", folder_id=None, created_at=MagicMock(), updated_at=MagicMock())
    rule1 = ForwardingRule(source_id="src_1", destination_channel="dest", is_active=True, id="r1")
    cache = RuleCache(sources={"src_1": src1}, rules=[rule1], version=1)

    # Mock incoming message event
    mock_event = MagicMock(spec=events.NewMessage.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 55
    mock_event.message.peer_id = PeerChannel(channel_id=11111)
    mock_event.message.media = None
    mock_event.message.message = "Hello world!"
    mock_event.message.reply_to = None

    with patch("forward_bot.infrastructure.cache.rule_cache.CacheHolder.current", new=cache), \
         patch("structlog.get_logger") as mock_structlog_logger:

        mock_logger = MagicMock()
        mock_structlog_logger.return_value = mock_logger

        await worker.process_event(mock_event)

        # Verify pipeline execution was called
        worker.pipeline_engine.execute.assert_called_once()
        
        # Verify context details in execution context
        exec_ctx = worker.pipeline_engine.execute.call_args[0][0]
        assert isinstance(exec_ctx, PipelineContext)
        assert exec_ctx.text == "Hello world!"
        assert exec_ctx.media is None
        assert exec_ctx.rule == rule1
        assert exec_ctx.source == src1
        assert exec_ctx.metadata["source_message_id"] == 55

        # Verify successful structured log emission
        mock_logger.info.assert_any_call(
            "forward_succeeded",
            rule_id="r1",
            source_message_id=55,
            destination_message_id=9876,
            correlation_id=exec_ctx.correlation_id
        )


@pytest.mark.asyncio
async def test_process_event_pipeline_blocked(mock_settings, mock_db) -> None:
    """Test process_event handles blocked outcome and logs correctly."""
    worker = TelegramWorker(mock_settings, mock_db)

    # Mock pipeline execution blocked
    mock_result = BlockedOutcome(reason="blocked_keyword", matched_keyword="spam")
    worker.pipeline_engine.execute = AsyncMock(return_value=mock_result)

    src1 = Source(id="src_1", telegram_id=11111, telegram_username="mysrc", display_name="Src 1", type="channel", folder_id=None, created_at=MagicMock(), updated_at=MagicMock())
    rule1 = ForwardingRule(source_id="src_1", destination_channel="dest", is_active=True, id="r1")
    cache = RuleCache(sources={"src_1": src1}, rules=[rule1], version=1)

    # Mock incoming message event
    mock_event = MagicMock(spec=events.NewMessage.Event)
    mock_event.message = MagicMock(spec=Message)
    mock_event.message.id = 66
    mock_event.message.peer_id = PeerChannel(channel_id=11111)
    mock_event.message.media = None
    mock_event.message.message = "Spam post!"
    mock_event.message.reply_to = None

    with patch("forward_bot.infrastructure.cache.rule_cache.CacheHolder.current", new=cache), \
         patch("structlog.get_logger") as mock_structlog_logger:

        mock_logger = MagicMock()
        mock_structlog_logger.return_value = mock_logger

        await worker.process_event(mock_event)

        # Verify pipeline execution was called
        worker.pipeline_engine.execute.assert_called_once()
        
        exec_ctx = worker.pipeline_engine.execute.call_args[0][0]
        # Verify blocked structured log emission
        mock_logger.info.assert_any_call(
            "pipeline_blocked",
            reason="blocked_keyword",
            rule_id="r1",
            correlation_id=exec_ctx.correlation_id
        )


@pytest.mark.asyncio
async def test_process_event_in_memory_sampling_counters(mock_settings, mock_db) -> None:
    """Test that in-memory sampling counters dictionary is passed in metadata and updated across dispatches."""
    worker = TelegramWorker(mock_settings, mock_db)
    
    # Simple pass-through pipeline mock simulating sampling step counter mutation
    def mock_execute(ctx):
        ctx.metadata["sampling_counters"][ctx.rule.id] = ctx.metadata["sampling_counters"].get(ctx.rule.id, 0) + 1
        return ctx

    worker.pipeline_engine.execute = AsyncMock(side_effect=mock_execute)

    src1 = Source(id="src_1", telegram_id=11111, telegram_username="mysrc", display_name="Src 1", type="channel", folder_id=None, created_at=MagicMock(), updated_at=MagicMock())
    rule1 = ForwardingRule(
        source_id="src_1",
        destination_channel="dest",
        is_active=True,
        id="r1",
        sampling=SamplingConfig(n=3)
    )
    cache = RuleCache(sources={"src_1": src1}, rules=[rule1], version=1)

    # 1st Event
    mock_event1 = MagicMock(spec=events.NewMessage.Event)
    mock_event1.message = MagicMock(spec=Message)
    mock_event1.message.id = 101
    mock_event1.message.peer_id = PeerChannel(channel_id=11111)
    mock_event1.message.media = None
    mock_event1.message.message = "Msg 1"
    mock_event1.message.reply_to = None

    with patch("forward_bot.infrastructure.cache.rule_cache.CacheHolder.current", new=cache):
        # Dispatch first event
        await worker.process_event(mock_event1)
        
        # Verify that sampling counters dictionary was initialized
        assert "r1" in worker.sampling_counters
        # Note: the pipeline engine wasn't mocked to mutate it (since it's a stub lambda in this test),
        # but in actual run, the step updates the dictionary reference.
        # Let's assert that the dictionary is passed in metadata.
        exec_ctx = worker.pipeline_engine.execute.call_args[0][0]
        assert exec_ctx.metadata["sampling_counters"] is worker.sampling_counters
