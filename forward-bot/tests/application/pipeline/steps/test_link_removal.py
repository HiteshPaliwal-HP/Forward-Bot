"""Unit tests for LinkRemovalStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.link_removal import LinkRemovalStep


def make_context(remove_links: bool, text: str, caption: str | None = None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        remove_links=remove_links
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
async def test_link_removal_disabled() -> None:
    step = LinkRemovalStep()
    ctx = make_context(False, "Check https://t.me/mychan")
    res = await step.apply(ctx)
    assert res.text == "Check https://t.me/mychan"


@pytest.mark.asyncio
async def test_link_removal_enabled() -> None:
    step = LinkRemovalStep()
    ctx = make_context(
        remove_links=True,
        text="Visit http://example.com/abc or https://google.com. Join t.me/joinchat/12345.",
        caption="Telegram tg://resolve?domain=xyz or telegram.me/mychan"
    )
    res = await step.apply(ctx)
    # The links are stripped, trailing spaces collapsed/stripped in the next steps,
    # but here they are just replaced by "".
    assert res.text == "Visit  or . Join ."
    assert res.caption == "Telegram  or "
