"""Media decision step of the forwarding pipeline."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class MediaDecisionStep:
    """Evaluates rule-specific media handling configuration (FR-11)."""
    name: str = "MediaDecisionStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        forward_media = getattr(rule, "forward_media", "forward")
        if forward_media == "ignore":
            ctx.media = None
            ctx.caption = None
        elif forward_media == "caption_only":
            if ctx.media is not None:
                ctx.media = None
            
            # Promote caption text to main text if main text is empty and caption is populated
            if not ctx.text and ctx.caption:
                ctx.text = ctx.caption
                ctx.caption = None

        # if forward_media == "forward" (default), do nothing to media and caption
        return ctx
