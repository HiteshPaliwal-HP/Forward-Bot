"""Link removal step of the forwarding pipeline."""
import re
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class LinkRemovalStep:
    """Removes links from message text and caption (FR-8)."""
    name: str = "LinkRemovalStep"
    
    # Matches URLs starting with http://, https://, tg://, t.me/, telegram.me/
    # excluding trailing punctuation (like dots/commas) that aren't part of the URL.
    PATTERN = re.compile(
        r"(https?://|tg://|t\.me/|telegram\.me/)(?:\S*[^.,?!;:\s])?",
        re.IGNORECASE
    )

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        if getattr(ctx.rule, "remove_links", False):
            if ctx.text:
                ctx.text = self.PATTERN.sub("", ctx.text)
            if ctx.caption:
                ctx.caption = self.PATTERN.sub("", ctx.caption)
        return ctx
