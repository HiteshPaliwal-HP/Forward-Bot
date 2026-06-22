"""Attribution prefix/suffix step of the forwarding pipeline."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class AttributionStep:
    """Formats and prepends/appends source attribution information (FR-14)."""
    name: str = "AttributionStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        config = getattr(rule, "attribution", None)
        if not config or not config.enabled:
            return ctx

        # Determine replacement values
        source_name = ctx.source.display_name or ""
        source_username = ctx.source.telegram_username or source_name

        # Format the template
        template = config.format or "From {source_name}"
        attr_text = template.replace("{source_name}", source_name).replace("{source_username}", source_username)

        position = config.position or "prefix"

        if ctx.media is not None:
            # Apply to ctx.caption (initialize to "" if None)
            caption = ctx.caption or ""
            if position == "prefix":
                ctx.caption = f"{attr_text}\n{caption}" if caption else attr_text
            else:  # suffix
                ctx.caption = f"{caption}\n{attr_text}" if caption else attr_text
        else:
            # Apply to ctx.text
            text = ctx.text or ""
            if position == "prefix":
                ctx.text = f"{attr_text}\n{text}" if text else attr_text
            else:  # suffix
                ctx.text = f"{text}\n{attr_text}" if text else attr_text

        return ctx
