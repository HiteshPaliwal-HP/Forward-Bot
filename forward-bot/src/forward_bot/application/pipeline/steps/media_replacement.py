"""Media replacement step of the forwarding pipeline."""
import asyncio
from pathlib import Path
from forward_bot.config import Settings
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.logging import logger


class MediaReplacementStep:
    """Replaces forwarded media with a configured static replacement image (FR-15)."""
    name: str = "MediaReplacementStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        config = getattr(rule, "media_replacement", None)
        if not config or not config.enabled:
            return ctx

        # Step only runs if the context actually has media (e.g. photo)
        if ctx.media is None:
            return ctx

        replacement_path = config.replacement_image_path
        if not replacement_path:
            logger.warning(
                "media_replacement_failed",
                rule_id=getattr(rule, "id", None),
                reason="missing_replacement_image_path"
            )
            return ctx

        try:
            settings = Settings()
            base_dir = Path(settings.media_replacement_base_dir).resolve()
            candidate = (base_dir / replacement_path).resolve()

            # Enforce path containment to prevent directory traversal
            if not candidate.is_relative_to(base_dir):
                logger.warning(
                    "media_replacement_path_traversal_attempt",
                    rule_id=getattr(rule, "id", None),
                    path=replacement_path,
                    base_dir=str(base_dir)
                )
                # Fall back to original photo
                return ctx

            # Non-blocking check for file existence
            exists = await asyncio.to_thread(candidate.exists)
            if not exists:
                logger.warning(
                    "media_replacement_failed",
                    rule_id=getattr(rule, "id", None),
                    path=str(candidate),
                    reason="file_does_not_exist"
                )
                # Fall back to original photo
                return ctx

            # Assign resolved Path object directly to save memory
            ctx.media = candidate

            # Adjust caption based on replacement_caption_mode
            caption_mode = config.replacement_caption_mode
            if caption_mode == "none":
                ctx.caption = None
            elif caption_mode == "use_replacement":
                # Since there is no custom replacement caption field, set to None
                ctx.caption = None
            # If "use_source", do nothing (keep processed caption)

        except Exception as e:
            logger.warning(
                "media_replacement_failed",
                rule_id=getattr(rule, "id", None),
                error=str(e),
                reason="unexpected_error"
            )
            # Fall back to original photo on error
            return ctx

        return ctx
