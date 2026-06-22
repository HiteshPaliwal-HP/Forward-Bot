"""Unit tests for EmptyCheckStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.empty_check import EmptyCheckStep


def make_context(text: str, caption: str | None, media) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan"
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
async def test_empty_check_all_empty() -> None:
    step = EmptyCheckStep()
    ctx = make_context("", None, None)
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "empty_after_processing"


@pytest.mark.asyncio
async def test_empty_check_has_text() -> None:
    step = EmptyCheckStep()
    ctx = make_context("Hello", None, None)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_empty_check_has_caption() -> None:
    step = EmptyCheckStep()
    ctx = make_context("", "My Caption", None)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_empty_check_has_media() -> None:
    step = EmptyCheckStep()
    ctx = make_context("", None, "photo_object")
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)
