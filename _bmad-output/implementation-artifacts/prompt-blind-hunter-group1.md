You are the Blind Hunter. Review the following code for logic flaws, bugs, security issues, performance problems, and code smells. You have no project context or spec.

## DIFF CONTENT (Group 1)

**forward-bot/src/forward_bot/application/pipeline/steps/__init__.py**
(Added exports for TimeWindowStep, SamplingStep, MediaTypeFilterStep, BlockKeywordStep, AllowKeywordStep)

**forward-bot/src/forward_bot/application/pipeline/steps/allow_keyword.py**
```python
"""Allow Keyword filter step."""
import re

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import CacheHolder


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
                pattern = None
                if compiled and idx < len(compiled.allow_patterns):
                    pattern = compiled.allow_patterns[idx]

                if pattern is None:
                    try:
                        pattern = re.compile(kw, re.IGNORECASE)
                    except Exception:
                        continue

                if (text_to_check and pattern.search(text_to_check)) or (
                    caption_to_check and pattern.search(caption_to_check)
                ):
                    matched_any = True
                    break
        else:
            # Literal mode (case-insensitive substring search)
            for kw in rule.allow_keywords:
                kw_lower = kw.lower()
                if (text_to_check and (kw_lower in text_to_check.lower())) or (
                    caption_to_check and (kw_lower in caption_to_check.lower())
                ):
                    matched_any = True
                    break

        if not matched_any:
            return BlockedOutcome(reason="no_allow_keyword_matched")

        return ctx
```

**forward-bot/src/forward_bot/application/pipeline/steps/block_keyword.py**
```python
"""Block Keyword filter step."""
import re

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.cache.rule_cache import CacheHolder


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
                pattern = None
                if compiled and idx < len(compiled.block_patterns):
                    pattern = compiled.block_patterns[idx]

                if pattern is None:
                    try:
                        pattern = re.compile(kw, re.IGNORECASE)
                    except Exception:
                        continue

                # Check text and caption
                if (text_to_check and pattern.search(text_to_check)) or (
                    caption_to_check and pattern.search(caption_to_check)
                ):
                    return BlockedOutcome(reason="blocked_keyword", matched_keyword=kw)
        else:
            # Literal mode (case-insensitive substring search)
            for kw in rule.block_keywords:
                kw_lower = kw.lower()
                if (text_to_check and (kw_lower in text_to_check.lower())) or (
                    caption_to_check and (kw_lower in caption_to_check.lower())
                ):
                    return BlockedOutcome(reason="blocked_keyword", matched_keyword=kw)

        return ctx
```

**forward-bot/src/forward_bot/application/pipeline/steps/media_type_filter.py**
```python
"""Media Type filter step."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


def resolve_media_type(media) -> str:
    """Map the Telethon media object or test mock to a string category."""
    if media is None:
        return "text"

    # Check type_name override (useful for mock objects in unit tests)
    type_name = getattr(media, "type_name", None)
    if type_name is not None:
        return type_name

    class_name = media.__class__.__name__

    if class_name == "MessageMediaPhoto":
        return "photo"

    if class_name == "MessageMediaDocument":
        doc = getattr(media, "document", None)
        if doc:
            mime_type = getattr(doc, "mime_type", "") or ""
            attrs = getattr(doc, "attributes", []) or []
            attr_class_names = {a.__class__.__name__ for a in attrs}

            if "DocumentAttributeSticker" in attr_class_names:
                return "sticker"
            if "DocumentAttributeAnimated" in attr_class_names:
                return "gif"
            if "DocumentAttributeVideo" in attr_class_names:
                return "video"
            if "DocumentAttributeAudio" in attr_class_names:
                for a in attrs:
                    if a.__class__.__name__ == "DocumentAttributeAudio" and getattr(a, "voice", False):
                        return "voice"
                return "audio"

            # Fallbacks based on mime_type
            if mime_type.startswith("video/"):
                return "video"
            if mime_type.startswith("audio/"):
                return "audio"

        return "document"

    if class_name == "MessageMediaPoll":
        return "poll"
    if class_name == "MessageMediaContact":
        return "contact"
    if class_name in ("MessageMediaGeo", "MessageMediaGeoLive", "MessageMediaVenue"):
        return "location"
    if class_name == "MessageMediaDice":
        return "dice"
    if class_name == "MessageMediaGame":
        return "game"
    if class_name == "MessageMediaInvoice":
        return "invoice"

    return "other"


class MediaTypeFilterStep:
    name: str = "MediaTypeFilterStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        allowlist = rule.media_type_filter if rule.media_type_filter is not None else ["text", "photo"]

        resolved_type = resolve_media_type(ctx.media)
        if resolved_type not in allowlist:
            return BlockedOutcome(reason="media_type_filtered")

        return ctx
```

**forward-bot/src/forward_bot/application/pipeline/steps/sampling.py**
```python
"""Sampling filter step."""
from forward_bot.config import Settings
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class SamplingStep:
    name: str = "SamplingStep"

    def __init__(self, sampling_repository=None) -> None:
        self.sampling_repository = sampling_repository
        self._fallback_counters = {}

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        if not rule.sampling or rule.sampling.n <= 1:
            return ctx

        # Check if sampling persistence is enabled
        try:
            settings = Settings()
            persist = settings.sampling_persist
        except Exception:
            persist = False

        if persist and self.sampling_repository is not None:
            counter = await self.sampling_repository.increment_counter(rule.id)
        else:
            # InMemory counters
            counters = ctx.metadata.get("sampling_counters") if isinstance(ctx.metadata, dict) else None
            if counters is None or not isinstance(counters, dict):
                counters = self._fallback_counters
            
            current_val = counters.get(rule.id, 0)
            new_val = current_val + 1
            counters[rule.id] = new_val
            counter = new_val

        if counter % rule.sampling.n != 0:
            return BlockedOutcome(reason="sampled_out")

        return ctx
```

**forward-bot/src/forward_bot/application/pipeline/steps/time_window.py**
```python
"""Time Window filter step."""
from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.logging import logger


class TimeWindowStep:
    name: str = "TimeWindowStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        if not rule.time_window:
            return ctx

        try:
            # Extract date
            dt = ctx.metadata.get("date")
            if not isinstance(dt, datetime):
                dt = datetime.now(timezone.utc)
            elif dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Resolve timezone
            tz = ZoneInfo(rule.time_window.timezone)
            local_dt = dt.astimezone(tz)
            local_t = local_dt.time()

            # Parse start and end times
            sh, sm = map(int, rule.time_window.start_time.split(":"))
            eh, em = map(int, rule.time_window.end_time.split(":"))
            start_t = time(hour=sh, minute=sm)
            end_t = time(hour=eh, minute=em)

            in_window = False
            active_day_dt = local_dt

            if end_t < start_t:
                # Cross-midnight window
                if local_t >= start_t or local_t <= end_t:
                    in_window = True
                    if local_t <= end_t:
                        active_day_dt = local_dt - timedelta(days=1)
            else:
                # Regular window
                if start_t <= local_t <= end_t:
                    in_window = True

            if not in_window:
                return BlockedOutcome(reason="outside_time_window")

            # Check days of week
            active_day_str = active_day_dt.strftime("%a").upper()
            if active_day_str not in rule.time_window.days_of_week:
                return BlockedOutcome(reason="outside_time_window")

            return ctx

        except Exception as e:
            logger.warning(
                "time_window_eval_error",
                rule_id=rule.id,
                error=str(e),
                message="Error evaluating time window filter. Failing open.",
            )
            return ctx
```
