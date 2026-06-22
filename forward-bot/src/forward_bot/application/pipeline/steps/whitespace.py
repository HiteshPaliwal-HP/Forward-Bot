"""Whitespace normalization step of the forwarding pipeline."""
import re
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class WhitespaceStep:
    """Collapses consecutive spaces, tabs, and newlines (FR-14)."""
    name: str = "WhitespaceStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        def clean_whitespace(text: str | None) -> str | None:
            if not text:
                return text
            # Collapse multiple consecutive spaces and tabs to a single space
            text = re.sub(r"[ \t]+", " ", text)
            # Remove horizontal spaces surrounding newlines
            text = re.sub(r" ?\n ?", "\n", text)
            # Collapse multiple consecutive newlines to a single newline
            text = re.sub(r"\n+", "\n", text)
            return text.strip()

        if ctx.text:
            ctx.text = clean_whitespace(ctx.text)
        if ctx.caption:
            ctx.caption = clean_whitespace(ctx.caption)

        return ctx
