"""Unit tests for MentionRemovalStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.mention_removal import MentionRemovalStep


def make_context(remove_mentions: bool, text: str, caption: str | None = None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        remove_mentions=remove_mentions
    )
    source = MagicMock(spec=Source)
    return PipelineContext(
        text=text,
        caption=caption,
        media="photo",
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_mention_removal_disabled() -> None:
    step = MentionRemovalStep()
    ctx = make_context(False, "Check @user and @admin")
    res = await step.apply(ctx)
    assert res.text == "Check @user and @admin"


@pytest.mark.asyncio
async def test_mention_removal_enabled() -> None:
    step = MentionRemovalStep()
    ctx = make_context(True, "Check @user and @admin", "Important @info")
    res = await step.apply(ctx)
    assert res.text == "Check  and "
    assert res.caption == "Important "
