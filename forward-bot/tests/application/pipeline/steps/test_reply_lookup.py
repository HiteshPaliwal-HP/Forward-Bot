"""Unit tests for ReplyLookupStep."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.application.pipeline.steps.reply_lookup import ReplyLookupStep


def make_context(reply_to_msg_id: int | None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan"
    )
    rule.id = "rule_1"
    source = MagicMock(spec=Source)
    source.telegram_id = 98765
    metadata = {}
    if reply_to_msg_id is not None:
        metadata["reply_to_msg_id"] = reply_to_msg_id
    return PipelineContext(
        text="Hello",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata=metadata
    )


@pytest.mark.asyncio
async def test_reply_lookup_no_reply_id() -> None:
    step = ReplyLookupStep(MagicMock())
    ctx = make_context(None)
    res = await step.apply(ctx)
    assert res.reply_target_destination_id is None


@pytest.mark.asyncio
async def test_reply_lookup_no_repo() -> None:
    step = ReplyLookupStep(None)
    ctx = make_context(123)
    res = await step.apply(ctx)
    assert res.reply_target_destination_id is None


@pytest.mark.asyncio
async def test_reply_lookup_parent_found() -> None:
    mock_repo = MagicMock()
    mock_mapping = MagicMock(spec=MessageMapping)
    mock_mapping.destination_message_id = 45678
    mock_repo.get_by_source_message = AsyncMock(return_value=mock_mapping)

    step = ReplyLookupStep(mock_repo)
    ctx = make_context(123)
    res = await step.apply(ctx)

    assert res.reply_target_destination_id == 45678
    mock_repo.get_by_source_message.assert_called_once_with(
        source_channel_id=98765,
        source_message_id=123,
        forwarding_rule_id="rule_1"
    )


@pytest.mark.asyncio
async def test_reply_lookup_parent_not_found() -> None:
    mock_repo = MagicMock()
    mock_repo.get_by_source_message = AsyncMock(return_value=None)

    step = ReplyLookupStep(mock_repo)
    ctx = make_context(123)
    res = await step.apply(ctx)

    assert res.reply_target_destination_id is None
    mock_repo.get_by_source_message.assert_called_once_with(
        source_channel_id=98765,
        source_message_id=123,
        forwarding_rule_id="rule_1"
    )
