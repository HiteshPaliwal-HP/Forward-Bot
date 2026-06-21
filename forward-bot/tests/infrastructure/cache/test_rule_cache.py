"""Unit tests for RuleCache, CacheHolder, and CompiledPatterns.

Tests the construction, frozen behaviour, and atomic swap semantics of the
cache types defined in ``infrastructure/cache/rule_cache.py``.
"""
import re
from datetime import datetime, timezone

import pytest

from forward_bot.infrastructure.cache.rule_cache import CacheHolder, CompiledPatterns, RuleCache


# ---------------------------------------------------------------------------
# RuleCache — construction and frozen semantics
# ---------------------------------------------------------------------------


def test_rule_cache_defaults():
    """RuleCache() with no args produces a valid empty snapshot (version=0)."""
    cache = RuleCache()
    assert cache.sources == {}
    assert cache.folders == {}
    assert cache.rules == []
    assert cache.replacements == {}
    assert cache.compiled_patterns == {}
    assert cache.version == 0
    assert cache.refreshed_at is None


def test_rule_cache_with_version():
    """RuleCache stores the supplied version number."""
    cache = RuleCache(version=5)
    assert cache.version == 5


def test_rule_cache_with_refreshed_at():
    """RuleCache stores a non-None refreshed_at when explicitly supplied."""
    ts = datetime.now(timezone.utc)
    cache = RuleCache(version=1, refreshed_at=ts)
    assert cache.refreshed_at == ts


def test_rule_cache_frozen():
    """RuleCache is a frozen dataclass — attributes cannot be mutated after creation."""
    cache = RuleCache(version=1)
    with pytest.raises((AttributeError, TypeError)):
        cache.version = 2  # type: ignore[misc]


def test_rule_cache_frozen_sources():
    """RuleCache.sources dict is NOT replaced after creation (frozen reference)."""
    cache = RuleCache(version=1, sources={"s1": object()})
    with pytest.raises((AttributeError, TypeError)):
        cache.sources = {}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CacheHolder — singleton and atomic swap
# ---------------------------------------------------------------------------


def test_cache_holder_starts_with_empty_cache():
    """CacheHolder.current starts as an empty RuleCache (version=0).

    Note: CacheHolder is module-level state — we reset it before asserting to
    ensure isolation from other tests that mutate it.
    """
    CacheHolder.current = RuleCache()
    assert CacheHolder.current.version == 0
    assert CacheHolder.current.rules == []
    assert CacheHolder.current.refreshed_at is None


def test_cache_holder_atomic_swap():
    """Assigning CacheHolder.current replaces the snapshot reference atomically."""
    original = CacheHolder.current
    new_cache = RuleCache(version=42)
    CacheHolder.current = new_cache
    assert CacheHolder.current.version == 42
    # Restore to keep other tests clean
    CacheHolder.current = original


def test_cache_holder_multiple_swaps():
    """Multiple successive swaps always expose the latest cache."""
    saved = CacheHolder.current
    for v in range(1, 6):
        CacheHolder.current = RuleCache(version=v)
        assert CacheHolder.current.version == v
    CacheHolder.current = saved


def test_cache_holder_local_snapshot_not_affected_by_swap():
    """A local reference to the old snapshot is not changed by a later swap."""
    saved = CacheHolder.current
    snapshot_before = CacheHolder.current      # capture reference
    CacheHolder.current = RuleCache(version=99)
    # The local variable still points to the old snapshot
    assert snapshot_before is not CacheHolder.current
    CacheHolder.current = saved


# ---------------------------------------------------------------------------
# CompiledPatterns
# ---------------------------------------------------------------------------


def test_compiled_patterns_defaults():
    """CompiledPatterns has correct empty defaults."""
    p = CompiledPatterns()
    assert p.block_patterns == []
    assert p.allow_patterns == []
    assert p.replacement_patterns == {}


def test_compiled_patterns_with_real_patterns():
    """CompiledPatterns stores compiled re.Pattern objects correctly."""
    block = [re.compile("pump", re.IGNORECASE)]
    allow = [re.compile("btc", re.IGNORECASE)]
    repl = {"rr-id-1": re.compile("old", re.IGNORECASE)}
    p = CompiledPatterns(block_patterns=block, allow_patterns=allow, replacement_patterns=repl)
    assert len(p.block_patterns) == 1
    assert p.block_patterns[0].pattern == "pump"
    assert len(p.allow_patterns) == 1
    assert p.allow_patterns[0].pattern == "btc"
    assert "rr-id-1" in p.replacement_patterns
    assert p.replacement_patterns["rr-id-1"].pattern == "old"


def test_compiled_patterns_multiple_block_patterns():
    """CompiledPatterns can hold multiple block and allow patterns."""
    block = [re.compile(p, re.IGNORECASE) for p in ["pump.*", "dump.*", "scam"]]
    p = CompiledPatterns(block_patterns=block)
    assert len(p.block_patterns) == 3
    assert {pat.pattern for pat in p.block_patterns} == {"pump.*", "dump.*", "scam"}


def test_compiled_patterns_ignorecase_flag():
    """CompiledPatterns correctly stores patterns compiled with IGNORECASE."""
    pattern = re.compile("TestPattern", re.IGNORECASE)
    p = CompiledPatterns(block_patterns=[pattern])
    assert p.block_patterns[0].flags & re.IGNORECASE
