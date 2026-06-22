"""Unit tests for MediaDecisionStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.media_decision import MediaDecisionStep


def make_context(forward_media: str, media, text: str, caption: str | None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        forward_media=forward_media
    )
    source = MagicMock(spec=Source)
    return PipelineContext(
        text=text,
        caption=caption,
        media=media,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_media_decision_forward() -> None:
    step = MediaDecisionStep()
    ctx = make_context("forward", "photo_object", "Hello", "Caption Text")
    res = await step.apply(ctx)
    assert res.media == "photo_object"
    assert res.caption == "Caption Text"


@pytest.mark.asyncio
async def test_media_decision_ignore() -> None:
    step = MediaDecisionStep()
    ctx = make_context("ignore", "photo_object", "Hello", "Caption Text")
    res = await step.apply(ctx)
    assert res.media is None
    assert res.caption is None


@pytest.mark.asyncio
async def test_media_decision_caption_only_with_text() -> None:
    step = MediaDecisionStep()
    # If text is present, caption is retained as caption
    ctx = make_context("caption_only", "photo_object", "Hello", "Caption Text")
    res = await step.apply(ctx)
    assert res.media is None
    assert res.caption == "Caption Text"
    assert res.text == "Hello"


@pytest.mark.asyncio
async def test_media_decision_caption_only_no_text() -> None:
    step = MediaDecisionStep()
    # If text is empty/None, caption is promoted to text
    ctx = make_context("caption_only", "photo_object", "", "Caption Text")
    res = await step.apply(ctx)
    assert res.media is None
    assert res.caption is None
    assert res.text == "Caption Text"
