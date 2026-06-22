"""Unit tests for WhitespaceStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.whitespace import WhitespaceStep


def make_context(text: str, caption: str | None = None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan"
    )
    source = MagicMock(spec=Source)
    return PipelineContext(
        text=text,
        caption=caption,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_whitespace_normalization() -> None:
    step = WhitespaceStep()
    ctx = make_context(
        text="   Hello    World!  \n\n\n  Next   Line.   ",
        caption="\tCaption\t\tWith\tTabs\n\nAnd   Newlines\t"
    )
    res = await step.apply(ctx)
    assert res.text == "Hello World!\nNext Line."
    assert res.caption == "Caption With Tabs\nAnd Newlines"
