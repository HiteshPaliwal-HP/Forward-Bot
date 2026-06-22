"""Unit tests for MediaReplacementStep."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, MediaReplacementConfig
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.media_replacement import MediaReplacementStep


def make_context(
    enabled: bool,
    path: str | None,
    mode: str,
    media="original_photo",
    caption="Original Caption"
) -> PipelineContext:
    config = MediaReplacementConfig(
        enabled=enabled,
        replacement_image_path=path,
        replacement_caption_mode=mode
    )
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        media_replacement=config
    )
    rule.id = "rule_1"
    source = MagicMock(spec=Source)
    return PipelineContext(
        text="Hello",
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
async def test_media_replacement_disabled() -> None:
    step = MediaReplacementStep()
    ctx = make_context(False, "image.png", "use_source")
    res = await step.apply(ctx)
    assert res.media == "original_photo"


@pytest.mark.asyncio
async def test_media_replacement_no_media_in_ctx() -> None:
    step = MediaReplacementStep()
    ctx = make_context(True, "image.png", "use_source", media=None)
    res = await step.apply(ctx)
    assert res.media is None


@pytest.mark.asyncio
async def test_media_replacement_missing_image_path() -> None:
    step = MediaReplacementStep()
    ctx = make_context(True, None, "use_source")
    res = await step.apply(ctx)
    assert res.media == "original_photo"


@pytest.mark.asyncio
async def test_media_replacement_success(tmp_path) -> None:
    base_dir = tmp_path / "replacement-images"
    base_dir.mkdir()
    repl_file = base_dir / "logo.png"
    repl_file.write_text("dummy image")

    step = MediaReplacementStep()
    ctx = make_context(True, "logo.png", "use_source")

    mock_settings = MagicMock()
    mock_settings.media_replacement_base_dir = str(base_dir)

    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
        res = await step.apply(ctx)

    assert isinstance(res.media, Path)
    assert res.media.resolve() == repl_file.resolve()
    assert res.caption == "Original Caption"


@pytest.mark.asyncio
async def test_media_replacement_caption_modes(tmp_path) -> None:
    base_dir = tmp_path / "replacement-images"
    base_dir.mkdir()
    repl_file = base_dir / "logo.png"
    repl_file.write_text("dummy image")

    mock_settings = MagicMock()
    mock_settings.media_replacement_base_dir = str(base_dir)

    # 1. Mode: none -> caption set to None
    step = MediaReplacementStep()
    ctx1 = make_context(True, "logo.png", "none", caption="Original Caption")
    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
        res1 = await step.apply(ctx1)
    assert res1.caption is None

    # 2. Mode: use_replacement -> caption set to None
    ctx2 = make_context(True, "logo.png", "use_replacement", caption="Original Caption")
    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
        res2 = await step.apply(ctx2)
    assert res2.caption is None


@pytest.mark.asyncio
async def test_media_replacement_path_traversal(tmp_path) -> None:
    base_dir = tmp_path / "replacement-images"
    base_dir.mkdir()

    step = MediaReplacementStep()
    ctx = make_context(True, "../traversal.png", "use_source")

    mock_settings = MagicMock()
    mock_settings.media_replacement_base_dir = str(base_dir)

    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
        res = await step.apply(ctx)

    # Should fall back to the original photo
    assert res.media == "original_photo"


@pytest.mark.asyncio
async def test_media_replacement_file_not_found(tmp_path) -> None:
    base_dir = tmp_path / "replacement-images"
    base_dir.mkdir()

    step = MediaReplacementStep()
    ctx = make_context(True, "nonexistent.png", "use_source")

    mock_settings = MagicMock()
    mock_settings.media_replacement_base_dir = str(base_dir)

    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
        res = await step.apply(ctx)

    # Should fall back to the original photo
    assert res.media == "original_photo"
