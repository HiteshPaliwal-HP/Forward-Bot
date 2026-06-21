"""Unit tests for MediaTypeFilterStep."""
import pytest
from unittest.mock import MagicMock

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.media_type_filter import MediaTypeFilterStep


# Helper mock classes for Telethon media structure
class MockAttribute:
    def __init__(self, class_name: str, voice: bool = False) -> None:
        self.__class__.__name__ = class_name
        self.voice = voice


class MockDocument:
    def __init__(self, attributes: list, mime_type: str = "") -> None:
        self.attributes = attributes
        self.mime_type = mime_type


class MockMedia:
    def __init__(self, class_name: str, document: MockDocument | None = None, type_name: str | None = None) -> None:
        self.__class__.__name__ = class_name
        self.document = document
        if type_name is not None:
            self.type_name = type_name


def make_context(media, allowlist: list[str] | None = None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        media_type_filter=allowlist
    )
    source = MagicMock(spec=Source)
    source.telegram_id = 123
    source.display_name = "Src"
    return PipelineContext(
        text="Hello",
        caption=None,
        media=media,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_media_type_filter_text() -> None:
    step = MediaTypeFilterStep()

    # None maps to "text". Default allowlist includes ["text", "photo"].
    ctx_pass = make_context(None, allowlist=["text", "photo"])
    res_pass = await step.apply(ctx_pass)
    assert isinstance(res_pass, PipelineContext)

    # If "text" is not in allowlist -> Blocked
    ctx_block = make_context(None, allowlist=["photo"])
    res_block = await step.apply(ctx_block)
    assert isinstance(res_block, BlockedOutcome)
    assert res_block.reason == "media_type_filtered"


@pytest.mark.asyncio
async def test_media_type_filter_photo() -> None:
    step = MediaTypeFilterStep()

    photo_media = MockMedia("MessageMediaPhoto")
    ctx_pass = make_context(photo_media, allowlist=["photo"])
    res_pass = await step.apply(ctx_pass)
    assert isinstance(res_pass, PipelineContext)


@pytest.mark.asyncio
async def test_media_type_filter_type_name_stub() -> None:
    step = MediaTypeFilterStep()

    # Pre-stubbed type_name in mock
    stub_media = MockMedia("SomeUnrecognizedClass", type_name="custom_media")
    ctx = make_context(stub_media, allowlist=["custom_media"])
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_media_type_filter_document_attributes() -> None:
    step = MediaTypeFilterStep()

    # Sticker
    sticker_media = MockMedia(
        "MessageMediaDocument",
        document=MockDocument([MockAttribute("DocumentAttributeSticker")])
    )
    ctx = make_context(sticker_media, allowlist=["sticker"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # GIF (Animated)
    gif_media = MockMedia(
        "MessageMediaDocument",
        document=MockDocument([MockAttribute("DocumentAttributeAnimated")])
    )
    ctx = make_context(gif_media, allowlist=["gif"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # Video
    video_media = MockMedia(
        "MessageMediaDocument",
        document=MockDocument([MockAttribute("DocumentAttributeVideo")])
    )
    ctx = make_context(video_media, allowlist=["video"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # Voice
    voice_media = MockMedia(
        "MessageMediaDocument",
        document=MockDocument([MockAttribute("DocumentAttributeAudio", voice=True)])
    )
    ctx = make_context(voice_media, allowlist=["voice"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # Audio
    audio_media = MockMedia(
        "MessageMediaDocument",
        document=MockDocument([MockAttribute("DocumentAttributeAudio", voice=False)])
    )
    ctx = make_context(audio_media, allowlist=["audio"])
    assert isinstance(await step.apply(ctx), PipelineContext)


@pytest.mark.asyncio
async def test_media_type_filter_mime_type_fallbacks() -> None:
    step = MediaTypeFilterStep()

    # Video mime type
    video_media = MockMedia("MessageMediaDocument", document=MockDocument([], mime_type="video/mp4"))
    ctx = make_context(video_media, allowlist=["video"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # Audio mime type
    audio_media = MockMedia("MessageMediaDocument", document=MockDocument([], mime_type="audio/mpeg"))
    ctx = make_context(audio_media, allowlist=["audio"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # General Document
    doc_media = MockMedia("MessageMediaDocument", document=MockDocument([], mime_type="application/pdf"))
    ctx = make_context(doc_media, allowlist=["document"])
    assert isinstance(await step.apply(ctx), PipelineContext)


@pytest.mark.asyncio
async def test_media_type_filter_other_telethon_types() -> None:
    step = MediaTypeFilterStep()

    # Dice
    dice_media = MockMedia("MessageMediaDice")
    ctx = make_context(dice_media, allowlist=["dice"])
    assert isinstance(await step.apply(ctx), PipelineContext)

    # Unrecognized maps to "other"
    unknown_media = MockMedia("MessageMediaUnsupportedUnknown")
    ctx = make_context(unknown_media, allowlist=["other"])
    assert isinstance(await step.apply(ctx), PipelineContext)
