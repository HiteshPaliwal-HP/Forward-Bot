"""Unit tests for AllowKeywordStep."""
import pytest
import re
from unittest.mock import MagicMock

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.allow_keyword import AllowKeywordStep
from forward_bot.infrastructure.cache.rule_cache import CacheHolder, RuleCache, CompiledPatterns


def make_context(
    allow_keywords: list[str],
    match_mode: str = "literal",
    text: str = "Hello",
    caption: str | None = None
) -> PipelineContext:
    rule = ForwardingRule(
        id="rule_1",
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        keyword_match_mode=match_mode,
        allow_keywords=allow_keywords
    )
    source = MagicMock(spec=Source)
    source.telegram_id = 123
    source.display_name = "Src"
    return PipelineContext(
        text=text,
        caption=caption,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.fixture(autouse=True)
def reset_cache_holder():
    CacheHolder.current = RuleCache()
    yield
    CacheHolder.current = RuleCache()


@pytest.mark.asyncio
async def test_allow_keyword_step_empty_passes() -> None:
    step = AllowKeywordStep()
    ctx = make_context([])
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_allow_keyword_step_literal_matching() -> None:
    step = AllowKeywordStep()

    # Matches text
    ctx = make_context(["alert", "info"], match_mode="literal", text="This is an urgent ALERT")
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)

    # Matches caption
    ctx_cap = make_context(["photo"], match_mode="literal", text="hello", caption="Beautify PHOTO here")
    res_cap = await step.apply(ctx_cap)
    assert isinstance(res_cap, PipelineContext)

    # Blocked (no match)
    ctx_block = make_context(["secret"], match_mode="literal", text="normal conversation", caption="nothing to see")
    res_block = await step.apply(ctx_block)
    assert isinstance(res_block, BlockedOutcome)
    assert res_block.reason == "no_allow_keyword_matched"


@pytest.mark.asyncio
async def test_allow_keyword_step_regex_matching_cache() -> None:
    step = AllowKeywordStep()

    # Cache pre-compilation
    pattern = re.compile(r"ur.ent", re.IGNORECASE)
    compiled = CompiledPatterns(allow_patterns=[pattern])
    CacheHolder.current = RuleCache(compiled_patterns={"rule_1": compiled})

    # Regex matches
    ctx = make_context(["urgent"], match_mode="regex", text="This is a very urgent message")
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)

    # Regex doesn't match -> Blocked
    ctx_block = make_context(["urgent"], match_mode="regex", text="normal work")
    res_block = await step.apply(ctx_block)
    assert isinstance(res_block, BlockedOutcome)
    assert res_block.reason == "no_allow_keyword_matched"


@pytest.mark.asyncio
async def test_allow_keyword_step_regex_matching_dynamic_fallback() -> None:
    step = AllowKeywordStep()

    # Cache is empty, compile dynamically
    ctx = make_context([r"^match_this.*$"], match_mode="regex", text="match_this string")
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)

    ctx_block = make_context([r"^match_this.*$"], match_mode="regex", text="do not match this")
    res_block = await step.apply(ctx_block)
    assert isinstance(res_block, BlockedOutcome)
    assert res_block.reason == "no_allow_keyword_matched"
