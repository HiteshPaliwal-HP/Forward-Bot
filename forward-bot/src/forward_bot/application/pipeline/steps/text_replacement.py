"""Text replacement rules step of the forwarding pipeline."""
import re
from datetime import datetime, timezone

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import CacheHolder
from forward_bot.infrastructure.logging import logger


class TextReplacementStep:
    """Applies active child ReplacementRules in order of created_at ASC (FR-7)."""
    name: str = "TextReplacementStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        cache = CacheHolder.current
        
        # Get rules from cache or default to empty list if cache is not initialized
        replacements = cache.replacements.get(rule.id, []) if cache and cache.replacements else []
        active_rr = [rr for rr in replacements if rr.is_active]
        if not active_rr:
            return ctx

        # Ensure sorted in ascending order of created_at
        active_rr.sort(key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc))

        for rr in active_rr:
            if rr.match_mode == "regex":
                # Find pre-compiled pattern in CacheHolder compiled_patterns
                pattern = None
                if cache and cache.compiled_patterns:
                    compiled = cache.compiled_patterns.get(rule.id)
                    if compiled and rr.id in compiled.replacement_patterns:
                        pattern = compiled.replacement_patterns[rr.id]

                if pattern is None:
                    try:
                        pattern = re.compile(rr.search_text, re.IGNORECASE)
                    except Exception as e:
                        logger.warning(
                            "regex_compile_error",
                            rule_id=rule.id,
                            replacement_rule_id=rr.id,
                            pattern=rr.search_text,
                            error=str(e),
                            message="Failed to compile replacement regex. Skipping."
                        )
                        continue

                # Apply re.sub supporting capture-group backreferences (e.g. \1, \2)
                if ctx.text:
                    ctx.text = pattern.sub(rr.replacement_text, ctx.text)
                if ctx.caption:
                    ctx.caption = pattern.sub(rr.replacement_text, ctx.caption)

            else:
                # match_mode == "literal" (case-insensitive substring replacement)
                try:
                    pattern = re.compile(re.escape(rr.search_text), re.IGNORECASE)
                except Exception as e:
                    logger.warning(
                        "literal_compile_error",
                        rule_id=rule.id,
                        replacement_rule_id=rr.id,
                        pattern=rr.search_text,
                        error=str(e),
                        message="Failed to compile literal replacement pattern. Skipping."
                    )
                    continue

                # Using lambda treats replacement_text literally, preventing backslash backref parsing
                if ctx.text:
                    ctx.text = pattern.sub(lambda m: rr.replacement_text, ctx.text)
                if ctx.caption:
                    ctx.caption = pattern.sub(lambda m: rr.replacement_text, ctx.caption)

        return ctx
