"""Source reference auto-replacement step of the forwarding pipeline."""
import re
from typing import Optional
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class SourceRefReplaceStep:
    """Case-insensitively replaces source references with destination references (FR-13)."""
    name: str = "SourceRefReplaceStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        config = getattr(rule, "auto_replace_source_refs", None)
        if not config or not config.enabled:
            return ctx

        source_username = ctx.source.telegram_username
        display_name = ctx.source.display_name

        dest_val = config.replacement or rule.destination_channel
        dest_val_clean = dest_val.lstrip("@")

        def replace_text(text: Optional[str]) -> Optional[str]:
            if not text:
                return text

            # 1. Username-based references (case-insensitive)
            if source_username:
                # Escape the username in regex
                username_escaped = re.escape(source_username)
                
                # Replace https://t.me/username
                text = re.sub(
                    rf"https://t\.me/{username_escaped}",
                    f"https://t.me/{dest_val_clean}",
                    text,
                    flags=re.IGNORECASE
                )
                # Replace t.me/username
                text = re.sub(
                    rf"t\.me/{username_escaped}",
                    f"t.me/{dest_val_clean}",
                    text,
                    flags=re.IGNORECASE
                )
                # Replace @username
                text = re.sub(
                    rf"@{username_escaped}",
                    f"@{dest_val_clean}",
                    text,
                    flags=re.IGNORECASE
                )

            # 2. Display name-based references (case-sensitive)
            if config.replace_display_name and display_name:
                text = text.replace(display_name, dest_val)

            return text

        if ctx.text:
            ctx.text = replace_text(ctx.text)
        if ctx.caption:
            ctx.caption = replace_text(ctx.caption)

        return ctx
