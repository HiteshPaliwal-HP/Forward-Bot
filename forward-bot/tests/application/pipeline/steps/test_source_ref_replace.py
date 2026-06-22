"""Unit tests for SourceRefReplaceStep."""
import pytest
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, AutoReplaceSourceRefsConfig
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.source_ref_replace import SourceRefReplaceStep


def make_context(
    enabled: bool,
    replacement: str | None,
    replace_display_name: bool,
    source_username: str | None,
    display_name: str,
    text: str,
    caption: str | None = None
) -> PipelineContext:
    config = AutoReplaceSourceRefsConfig(
        enabled=enabled,
        replacement=replacement,
        replace_display_name=replace_display_name
    )
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        auto_replace_source_refs=config
    )
    source = MagicMock(spec=Source)
    source.telegram_username = source_username
    source.display_name = display_name
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
async def test_source_ref_replace_disabled() -> None:
    step = SourceRefReplaceStep()
    ctx = make_context(False, None, False, "src_user", "MySource", "Post @src_user")
    res = await step.apply(ctx)
    assert res.text == "Post @src_user"


@pytest.mark.asyncio
async def test_source_ref_replace_username_default() -> None:
    step = SourceRefReplaceStep()
    ctx = make_context(
        enabled=True,
        replacement=None,
        replace_display_name=False,
        source_username="src_user",
        display_name="MySource",
        text="Visit https://t.me/src_user or check t.me/Src_User or mention @src_user",
        caption="From @SRC_USER"
    )
    res = await step.apply(ctx)
    assert res.text == "Visit https://t.me/dest_chan or check t.me/dest_chan or mention @dest_chan"
    assert res.caption == "From @dest_chan"


@pytest.mark.asyncio
async def test_source_ref_replace_username_custom() -> None:
    step = SourceRefReplaceStep()
    ctx = make_context(
        enabled=True,
        replacement="@custom_repl",
        replace_display_name=False,
        source_username="src_user",
        display_name="MySource",
        text="Check @src_user",
    )
    res = await step.apply(ctx)
    assert res.text == "Check @custom_repl"


@pytest.mark.asyncio
async def test_source_ref_replace_display_name() -> None:
    step = SourceRefReplaceStep()
    # Case-sensitive replace display_name.
    # Note: Text contains "MySource" (exact match) and "mysource" (lower, should not replace display name).
    ctx = make_context(
        enabled=True,
        replacement="@custom_repl",
        replace_display_name=True,
        source_username=None,
        display_name="MySource",
        text="From MySource (not mysource)",
    )
    res = await step.apply(ctx)
    assert res.text == "From @custom_repl (not mysource)"
