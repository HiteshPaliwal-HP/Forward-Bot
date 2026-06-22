"""Unit tests for Telegram message delivery."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError

from forward_bot.config import Settings
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.infrastructure.telegram.delivery import deliver_message


@pytest.fixture
def mock_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.delivery_max_retries = 3
    settings.delivery_backoff_factor = 2.0
    settings.delivery_base_delay = 1.0
    return settings


@pytest.fixture
def mock_context() -> PipelineContext:
    rule = MagicMock(spec=ForwardingRule)
    rule.id = "rule_1"
    rule.destination_channel = "-10012345678"  # numeric ID string
    source = MagicMock(spec=Source)
    source.telegram_id = 12345
    return PipelineContext(
        text="Hello world",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr_id_123",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_deliver_message_success(mock_context, mock_settings) -> None:
    """Test standard successful text-only delivery."""
    mock_client = MagicMock(spec=TelegramClient)
    mock_msg = MagicMock()
    mock_msg.id = 98765
    mock_msg.chat_id = -10012345678
    mock_client.send_message = AsyncMock(return_value=mock_msg)

    msg_id, chat_id = await deliver_message(mock_client, mock_context, mock_settings)

    assert msg_id == 98765
    assert chat_id == -10012345678
    # Assert destination resolved to int
    mock_client.send_message.assert_called_once_with(
        -10012345678,
        message="Hello world",
        reply_to=None
    )


@pytest.mark.asyncio
async def test_deliver_message_with_media_success(mock_context, mock_settings) -> None:
    """Test delivery of messages with media (caption and file conversion)."""
    mock_context.media = "path/to/image.jpg"
    mock_context.caption = "This is a caption"

    mock_client = MagicMock(spec=TelegramClient)
    mock_msg = MagicMock()
    mock_msg.id = 11111
    mock_msg.chat_id = -10012345678
    mock_client.send_message = AsyncMock(return_value=mock_msg)

    msg_id, chat_id = await deliver_message(mock_client, mock_context, mock_settings)

    assert msg_id == 11111
    assert chat_id == -10012345678
    mock_client.send_message.assert_called_once_with(
        -10012345678,
        message="This is a caption",
        file="path/to/image.jpg",
        reply_to=None
    )


@pytest.mark.asyncio
async def test_deliver_message_reply_to(mock_context, mock_settings) -> None:
    """Test delivery with a reply destination ID."""
    mock_context.reply_target_destination_id = 55555

    mock_client = MagicMock(spec=TelegramClient)
    mock_msg = MagicMock()
    mock_msg.id = 22222
    mock_msg.chat_id = -10012345678
    mock_client.send_message = AsyncMock(return_value=mock_msg)

    msg_id, chat_id = await deliver_message(mock_client, mock_context, mock_settings)

    assert msg_id == 22222
    assert chat_id == -10012345678
    mock_client.send_message.assert_called_once_with(
        -10012345678,
        message="Hello world",
        reply_to=55555
    )


@pytest.mark.asyncio
async def test_deliver_message_flood_wait_handling(mock_context, mock_settings) -> None:
    """Test that FloodWaitError logs a warning, sleeps, and retries successfully without decrementing retry budget."""
    mock_client = MagicMock(spec=TelegramClient)
    mock_msg = MagicMock()
    mock_msg.id = 999
    mock_msg.chat_id = -10012345678

    # Raise FloodWaitError once, then return success message
    mock_client.send_message = AsyncMock(side_effect=[FloodWaitError(MagicMock(), 42), mock_msg])

    with patch("forward_bot.infrastructure.telegram.delivery.logger") as mock_logger, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        msg_id, chat_id = await deliver_message(mock_client, mock_context, mock_settings)

        assert msg_id == 999
        assert chat_id == -10012345678
        # verify sleep was called with e.seconds
        mock_sleep.assert_called_once_with(42)
        # verify warning log event was emitted
        mock_logger.warning.assert_any_call(
            "flood_wait",
            wait_seconds=42,
            rule_id="rule_1",
            correlation_id="corr_id_123",
            message="Telegram flood wait triggered. Must wait 42 seconds."
        )


@pytest.mark.asyncio
async def test_deliver_message_flood_wait_too_long(mock_context, mock_settings) -> None:
    """Test that FloodWaitError above threshold (300s) aborts the delivery immediately without sleeping."""
    mock_client = MagicMock(spec=TelegramClient)
    mock_client.send_message = AsyncMock(side_effect=FloodWaitError(MagicMock(), 301))

    with patch("forward_bot.infrastructure.telegram.delivery.logger") as mock_logger, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        with pytest.raises(FloodWaitError):
            await deliver_message(mock_client, mock_context, mock_settings)

        # Ensure no sleep took place
        mock_sleep.assert_not_called()
        # Verify warning log and error log was emitted
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_called_once_with(
            "forward_failed",
            rule_id="rule_1",
            correlation_id="corr_id_123",
            error="FloodWait too long: 301s (max 300s)",
            message="Flood wait duration exceeds threshold. Aborting delivery."
        )


@pytest.mark.asyncio
async def test_deliver_message_transient_error_backoff_and_exhaustion(mock_context, mock_settings) -> None:
    """Test transient connection error retry loop, log warning on attempts, and eventual exhaustion log & exception propagation."""
    mock_client = MagicMock(spec=TelegramClient)
    # Fail 4 times (which exceeds default 3 retries, total 4 attempts)
    mock_client.send_message = AsyncMock(side_effect=ConnectionError("Server disconnected"))

    with patch("forward_bot.infrastructure.telegram.delivery.logger") as mock_logger, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        with pytest.raises(ConnectionError):
            await deliver_message(mock_client, mock_context, mock_settings)

        # Total retries is 3. The 4th attempt raises ConnectionError which we propagate.
        # So sleep should be called 3 times with exponential backoff:
        # attempt 1: delay = 1.0 * (2.0 ** 0) = 1.0
        # attempt 2: delay = 1.0 * (2.0 ** 1) = 2.0
        # attempt 3: delay = 1.0 * (2.0 ** 2) = 4.0
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

        # Check transient error warnings
        assert mock_logger.warning.call_count == 3
        # Check final error log on exhaustion
        mock_logger.error.assert_called_once_with(
            "forward_failed",
            rule_id="rule_1",
            correlation_id="corr_id_123",
            error="Server disconnected",
            message="Forwarding failed after 3 retries due to transient error."
        )


@pytest.mark.asyncio
async def test_deliver_message_transient_error_eventual_success(mock_context, mock_settings) -> None:
    """Test that transient errors are retried and eventually succeed if within budget."""
    mock_client = MagicMock(spec=TelegramClient)
    mock_msg = MagicMock()
    mock_msg.id = 456
    mock_msg.chat_id = -10012345678

    # Fail twice, then succeed
    mock_client.send_message = AsyncMock(side_effect=[
        asyncio.TimeoutError("Timeout"),
        RPCError(MagicMock(), "Temporary RPC issue"),
        mock_msg
    ])

    with patch("forward_bot.infrastructure.telegram.delivery.logger") as mock_logger, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        msg_id, chat_id = await deliver_message(mock_client, mock_context, mock_settings)

        assert msg_id == 456
        assert chat_id == -10012345678
        # Sleep called twice: 1.0 and 2.0
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)
        # 2 warning logs
        assert mock_logger.warning.call_count == 2
        # No error log
        mock_logger.error.assert_not_called()
