"""Unit tests for TextReplacementStep."""
import pytest
import re
from datetime import datetime
from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.entities.source import Source
from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
from forward_bot.application.pipeline.steps.text_replacement import TextReplacementStep


def make_context(text: str, caption: str | None = None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan"
    )
    rule.id = "rule_1"
    source = MagicMock(spec=Source)
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


@pytest.mark.asyncio
async def test_text_replacement_no_replacements() -> None:
    CacheHolder.current = RuleCache()  # Empty cache
    step = TextReplacementStep()
    ctx = make_context("Hello World")
    res = await step.apply(ctx)
    assert res.text == "Hello World"


@pytest.mark.asyncio
async def test_text_replacement_literal_and_regex_ordered() -> None:
    # Set up some rules:
    # Rule 1: Literal, replace "apple" with "banana", created at T1
    # Rule 2: Regex, replace "ba(na){2}" with "cherry", created at T2
    # Rule 3: Inactive, replace "cherry" with "nothing", created at T3
    r1 = ReplacementRule(
        forwarding_rule_id="rule_1",
        search_text="apple",
        replacement_text="banana",
        match_mode="literal",
        is_active=True,
        id="r1",
        created_at=datetime(2026, 6, 1, 12, 0)
    )
    r2 = ReplacementRule(
        forwarding_rule_id="rule_1",
        search_text=r"ba(na){2}",
        replacement_text="cherry",
        match_mode="regex",
        is_active=True,
        id="r2",
        created_at=datetime(2026, 6, 1, 13, 0)
    )
    r3 = ReplacementRule(
        forwarding_rule_id="rule_1",
        search_text="cherry",
        replacement_text="nothing",
        match_mode="literal",
        is_active=False,
        id="r3",
        created_at=datetime(2026, 6, 1, 14, 0)
    )

    # Compile regex pattern for Rule 2 in CompiledPatterns
    compiled_patterns = CompiledPatterns(
        replacement_patterns={"r2": re.compile(r"ba(na){2}", re.IGNORECASE)}
    )

    # Populate cache
    cache = RuleCache(
        replacements={"rule_1": [r2, r3, r1]},  # Out of order to test sorting
        compiled_patterns={"rule_1": compiled_patterns}
    )
    CacheHolder.current = cache

    step = TextReplacementStep()
    
    # "Apple" (literal, case-insensitive) becomes "banana" (first rule applied)
    # Then "banana" matches "ba(na){2}" (regex) and becomes "cherry"
    # Rule 3 is inactive, so "cherry" remains "cherry"
    ctx = make_context("I love Apple pie.")
    res = await step.apply(ctx)
    assert res.text == "I love cherry pie."


@pytest.mark.asyncio
async def test_text_replacement_regex_dynamic_fallback() -> None:
    # If compiled pattern is missing from CompiledPatterns, dynamically compile it.
    r1 = ReplacementRule(
        forwarding_rule_id="rule_1",
        search_text=r"\d+",
        replacement_text="NUM",
        match_mode="regex",
        is_active=True,
        id="r1",
        created_at=datetime(2026, 6, 1, 12, 0)
    )
    
    cache = RuleCache(
        replacements={"rule_1": [r1]},
        compiled_patterns={}  # Missing compiled patterns
    )
    CacheHolder.current = cache

    step = TextReplacementStep()
    ctx = make_context("Code 123 and 456")
    res = await step.apply(ctx)
    assert res.text == "Code NUM and NUM"
