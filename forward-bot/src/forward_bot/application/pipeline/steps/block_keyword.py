"""Block Keyword filter step."""
import re

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import CacheHolder
from forward_bot.infrastructure.logging import logger


class BlockKeywordStep:
    name: str = "BlockKeywordStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        if not rule.block_keywords:
            return ctx

        text_to_check = ctx.text or ""
        caption_to_check = ctx.caption or ""

        if rule.keyword_match_mode == "regex":
            cache = CacheHolder.current
            compiled = cache.compiled_patterns.get(rule.id) if cache else None

            for idx, kw in enumerate(rule.block_keywords):
                if not kw:
                    continue
                
                pattern = None
                if compiled and idx < len(compiled.block_patterns):
                    pattern = compiled.block_patterns[idx]

                if pattern is None:
                    try:
                        pattern = re.compile(kw, re.IGNORECASE)
                    except Exception as e:
                        logger.warning(
                            "regex_compile_error",
                            rule_id=rule.id,
                            keyword=kw,
                            error=str(e),
                            message="Failed to compile block keyword regex. Skipping."
                        )
                        continue

                # Check text and caption
                if (text_to_check and pattern.search(text_to_check)) or (
                    caption_to_check and pattern.search(caption_to_check)
                ):
                    return BlockedOutcome(reason="blocked_keyword", matched_keyword=kw)
        else:
            # Literal mode (case-insensitive substring search)
            for kw in rule.block_keywords:
                if not kw:
                    continue
                kw_lower = kw.lower()
                if (text_to_check and (kw_lower in text_to_check.lower())) or (
                    caption_to_check and (kw_lower in caption_to_check.lower())
                ):
                    return BlockedOutcome(reason="blocked_keyword", matched_keyword=kw)

        return ctx
