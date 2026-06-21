"""Allow Keyword filter step."""
import re

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import CacheHolder
from forward_bot.infrastructure.logging import logger


class AllowKeywordStep:
    name: str = "AllowKeywordStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        if not rule.allow_keywords:
            return ctx

        text_to_check = ctx.text or ""
        caption_to_check = ctx.caption or ""

        matched_any = False

        if rule.keyword_match_mode == "regex":
            cache = CacheHolder.current
            compiled = cache.compiled_patterns.get(rule.id) if cache else None

            for idx, kw in enumerate(rule.allow_keywords):
                if not kw:
                    continue
                
                pattern = None
                if compiled and idx < len(compiled.allow_patterns):
                    pattern = compiled.allow_patterns[idx]

                if pattern is None:
                    try:
                        pattern = re.compile(kw, re.IGNORECASE)
                    except Exception as e:
                        logger.warning(
                            "regex_compile_error",
                            rule_id=rule.id,
                            keyword=kw,
                            error=str(e),
                            message="Failed to compile allow keyword regex. Skipping."
                        )
                        continue

                if (text_to_check and pattern.search(text_to_check)) or (
                    caption_to_check and pattern.search(caption_to_check)
                ):
                    matched_any = True
                    break
        else:
            # Literal mode (case-insensitive substring search)
            for kw in rule.allow_keywords:
                if not kw:
                    continue
                kw_lower = kw.lower()
                if (text_to_check and (kw_lower in text_to_check.lower())) or (
                    caption_to_check and (kw_lower in caption_to_check.lower())
                ):
                    matched_any = True
                    break

        if not matched_any:
            return BlockedOutcome(reason="no_allow_keyword_matched")

        return ctx
