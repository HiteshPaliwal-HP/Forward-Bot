"""Unit tests for BlockKeywordStep."""
import pytest
import re
from unittest.mock import MagicMock

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.block_keyword import BlockKeywordStep
from forward_bot.infrastructure.cache.rule_cache import CacheHolder, RuleCache, CompiledPatterns


def make_context(
    block_keywords: list[str],
    match_mode: str = "literal",
    text: str = "Hello",
    caption: str | None = None
) -> PipelineContext:
    rule = ForwardingRule(
        id="rule_1",
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        keyword_match_mode=match_mode,
        block_keywords=block_keywords
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
async def test_block_keyword_step_no_keywords() -> None:
    step = BlockKeywordStep()
    ctx = make_context([])
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_block_keyword_step_literal_match() -> None:
    step = BlockKeywordStep()

    # Block match on text (case-insensitive substring)
    ctx = make_context(["spam", "test"], match_mode="literal", text="This is a test message")
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "blocked_keyword"
    assert res.matched_keyword == "test"

    # Block match on caption
    ctx_cap = make_context(["spam"], match_mode="literal", text="hello", caption="Check out the SPAM here")
    res_cap = await step.apply(ctx_cap)
    assert isinstance(res_cap, BlockedOutcome)
    assert res_cap.reason == "blocked_keyword"
    assert res_cap.matched_keyword == "spam"

    # No match
    ctx_ok = make_context(["spam"], match_mode="literal", text="This is fine", caption="Nothing bad here")
    res_ok = await step.apply(ctx_ok)
    assert isinstance(res_ok, PipelineContext)


@pytest.mark.asyncio
async def test_block_keyword_step_regex_match_from_cache() -> None:
    step = BlockKeywordStep()

    # Pre-populate RuleCache
    pattern = re.compile(r"s.am", re.IGNORECASE)
    compiled = CompiledPatterns(block_patterns=[pattern])
    
    # Store in CacheHolder
    CacheHolder.current = RuleCache(
        compiled_patterns={"rule_1": compiled}
    )

    # Context setup
    ctx = make_context(["spam"], match_mode="regex", text="Here is some sPaM")
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "blocked_keyword"
    assert res.matched_keyword == "spam"


@pytest.mark.asyncio
async def test_block_keyword_step_regex_match_dynamic_fallback() -> None:
    step = BlockKeywordStep()

    # Cache is empty, should fall back to compiling dynamically
    ctx = make_context([r"\b[0-9]{3}\b"], match_mode="regex", text="The code is 123 today")
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "blocked_keyword"
    assert res.matched_keyword == r"\b[0-9]{3}\b"

    # Non-matching
    ctx_ok = make_context([r"\b[0-9]{3}\b"], match_mode="regex", text="The code is 1234 today")
    res_ok = await step.apply(ctx_ok)
    assert isinstance(res_ok, PipelineContext)


@pytest.mark.asyncio
async def test_block_keyword_step_regex_invalid_pattern_ignored() -> None:
    step = BlockKeywordStep()

    # Invalid regex "[invalid" should not crash the filter
    ctx = make_context(["[invalid", "valid"], match_mode="regex", text="This is valid text")
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "blocked_keyword"
    assert res.matched_keyword == "valid"
