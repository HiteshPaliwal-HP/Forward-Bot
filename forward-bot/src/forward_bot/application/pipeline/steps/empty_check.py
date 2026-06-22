"""Empty result check step of the forwarding pipeline."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class EmptyCheckStep:
    """Verifies that the message is not empty after filtering and transforming (FR-11)."""
    name: str = "EmptyCheckStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        # Check if text, caption, and media are all empty/None
        if not ctx.text and not ctx.caption and ctx.media is None:
            return BlockedOutcome(reason="empty_after_processing")
        return ctx
