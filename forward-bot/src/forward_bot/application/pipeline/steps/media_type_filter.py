"""Media Type filter step."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


def resolve_media_type(media) -> str:
    """Map the Telethon media object or test mock to a string category."""
    if media is None:
        return "text"

    # Check type_name override (useful for mock objects in unit tests)
    type_name = getattr(media, "type_name", None)
    if type_name is not None:
        return type_name

    class_name = media.__class__.__name__

    if class_name == "MessageMediaPhoto":
        return "photo"

    if class_name == "MessageMediaDocument":
        doc = getattr(media, "document", None)
        if doc:
            mime_type = getattr(doc, "mime_type", "") or ""
            attrs = getattr(doc, "attributes", []) or []
            attr_class_names = {a.__class__.__name__ for a in attrs}

            if "DocumentAttributeSticker" in attr_class_names:
                return "sticker"
            if "DocumentAttributeAnimated" in attr_class_names:
                return "gif"
            if "DocumentAttributeVideo" in attr_class_names:
                return "video"
            if "DocumentAttributeAudio" in attr_class_names:
                for a in attrs:
                    if a.__class__.__name__ == "DocumentAttributeAudio" and getattr(a, "voice", False):
                        return "voice"
                return "audio"

            # Fallbacks based on mime_type
            if mime_type.startswith("video/"):
                return "video"
            if mime_type.startswith("audio/"):
                return "audio"

        return "document"

    if class_name == "MessageMediaPoll":
        return "poll"
    if class_name == "MessageMediaContact":
        return "contact"
    if class_name in ("MessageMediaGeo", "MessageMediaGeoLive", "MessageMediaVenue"):
        return "location"
    if class_name == "MessageMediaDice":
        return "dice"
    if class_name == "MessageMediaGame":
        return "game"
    if class_name == "MessageMediaInvoice":
        return "invoice"

    return "other"


class MediaTypeFilterStep:
    name: str = "MediaTypeFilterStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        allowlist = rule.media_type_filter if rule.media_type_filter is not None else ["text", "photo"]

        resolved_type = resolve_media_type(ctx.media)
        if resolved_type not in allowlist:
            return BlockedOutcome(reason="media_type_filtered")

        return ctx
