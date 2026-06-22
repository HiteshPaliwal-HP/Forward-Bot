"""Unit tests for DeliverStep."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.deliver import DeliverStep


@pytest.fixture
def mock_context() -> PipelineContext:
    rule = MagicMock(spec=ForwardingRule)
    rule.id = "rule_1"
    rule.destination_channel = "dest_chan"
    source = MagicMock(spec=Source)
    source.telegram_id = 12345
    return PipelineContext(
        text="Hello",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="xyz12345",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_deliver_step_success(mock_context) -> None:
    """Test that DeliverStep delegates to deliver_message and records metadata on success."""
    step = DeliverStep()
    with patch("forward_bot.application.pipeline.steps.deliver.deliver_message", new_callable=AsyncMock) as mock_deliver:
        mock_deliver.return_value = (11111, 22222)

        result = await step.apply(mock_context)

        assert isinstance(result, PipelineContext)
        assert result.metadata["destination_message_id"] == 11111
        assert result.metadata["destination_channel_id"] == 22222
        mock_deliver.assert_called_once()


@pytest.mark.asyncio
async def test_deliver_step_failure(mock_context) -> None:
    """Test that DeliverStep handles exceptions gracefully by returning step_error."""
    step = DeliverStep()
    with patch("forward_bot.application.pipeline.steps.deliver.deliver_message", new_callable=AsyncMock) as mock_deliver:
        mock_deliver.side_effect = RuntimeError("Telegram connection failed")

        result = await step.apply(mock_context)

        assert isinstance(result, BlockedOutcome)
        assert result.reason == "step_error"
        assert "Telegram connection failed" in result.details
