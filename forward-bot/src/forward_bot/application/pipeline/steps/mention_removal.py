"""Mention removal step of the forwarding pipeline."""
import re
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class MentionRemovalStep:
    """Removes mentions from message text and caption (FR-8)."""
    name: str = "MentionRemovalStep"
    PATTERN = re.compile(r"@\w+")

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        if getattr(ctx.rule, "remove_mentions", False):
            if ctx.text:
                ctx.text = self.PATTERN.sub("", ctx.text)
            if ctx.caption:
                ctx.caption = self.PATTERN.sub("", ctx.caption)
        return ctx
