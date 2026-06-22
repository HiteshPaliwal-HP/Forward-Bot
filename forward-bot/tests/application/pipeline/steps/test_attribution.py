"""Unit tests for AttributionStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, AttributionConfig
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.attribution import AttributionStep


def make_context(
    enabled: bool,
    position: str,
    fmt: str,
    source_name: str,
    source_username: str | None,
    media,
    text: str,
    caption: str | None = None
) -> PipelineContext:
    config = AttributionConfig(
        enabled=enabled,
        position=position,
        format=fmt
    )
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        attribution=config
    )
    source = MagicMock(spec=Source)
    source.display_name = source_name
    source.telegram_username = source_username
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
async def test_attribution_disabled() -> None:
    step = AttributionStep()
    ctx = make_context(False, "suffix", "From {source_name}", "MySource", "src_user", None, "Hello")
    res = await step.apply(ctx)
    assert res.text == "Hello"


@pytest.mark.asyncio
async def test_attribution_prefix_no_media() -> None:
    step = AttributionStep()
    ctx = make_context(True, "prefix", "From {source_name} (@{source_username})", "MySource", "src_user", None, "Hello")
    res = await step.apply(ctx)
    assert res.text == "From MySource (@src_user)\nHello"


@pytest.mark.asyncio
async def test_attribution_suffix_no_media() -> None:
    step = AttributionStep()
    ctx = make_context(True, "suffix", "From {source_name}", "MySource", "src_user", None, "Hello")
    res = await step.apply(ctx)
    assert res.text == "Hello\nFrom MySource"


@pytest.mark.asyncio
async def test_attribution_username_fallback() -> None:
    # If username is None, fall back to display name in {source_username}
    step = AttributionStep()
    ctx = make_context(True, "prefix", "Author: {source_username}", "MySource", None, None, "Hello")
    res = await step.apply(ctx)
    assert res.text == "Author: MySource\nHello"


@pytest.mark.asyncio
async def test_attribution_with_media_prefix() -> None:
    step = AttributionStep()
    ctx = make_context(True, "prefix", "Credits: {source_name}", "MySource", "src_user", "photo_obj", "Hello", caption="My Caption")
    res = await step.apply(ctx)
    # Applies to caption, text is untouched
    assert res.text == "Hello"
    assert res.caption == "Credits: MySource\nMy Caption"


@pytest.mark.asyncio
async def test_attribution_with_media_empty_caption() -> None:
    step = AttributionStep()
    ctx = make_context(True, "suffix", "Credits: {source_name}", "MySource", "src_user", "photo_obj", "Hello", caption=None)
    res = await step.apply(ctx)
    assert res.text == "Hello"
    assert res.caption == "Credits: MySource"
