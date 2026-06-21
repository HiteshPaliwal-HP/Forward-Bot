"""Atomic cache snapshot types for the forwarding rule pipeline.

This module defines the three types consumed by Epic 4 pipeline steps:

  - CompiledPatterns  — pre-compiled re.Pattern objects for a single ForwardingRule.
  - RuleCache         — frozen, immutable snapshot of all four MongoDB collections.
  - CacheHolder       — mutable singleton whose `.current` attribute is atomically
                        replaced by the cache refresher on each interval.

Assignment of ``CacheHolder.current`` is a single Python reference swap, which is
atomic under both the CPython GIL and the asyncio event loop's single-threaded
execution model.  No locking primitives are required.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CompiledPatterns:
    """Pre-compiled regex patterns for a single ForwardingRule.

    Keyed structures allow O(1) lookup by field name during pipeline execution.
    ``block_patterns`` and ``allow_patterns`` are lists of compiled ``re.Pattern``
    objects (one per keyword that uses regex mode).
    ``replacement_patterns`` maps each ``replacement_rule.id`` →
    compiled ``re.Pattern`` for its ``search_text``.
    """

    block_patterns: list[re.Pattern] = field(default_factory=list)
    allow_patterns: list[re.Pattern] = field(default_factory=list)
    replacement_patterns: dict[str, re.Pattern] = field(default_factory=dict)
    # Key: replacement_rule.id (str) → compiled re.Pattern for search_text


@dataclass(frozen=True)
class RuleCache:
    """Atomic, immutable snapshot of all four MongoDB collections.

    Built once per ``HOT_RELOAD_INTERVAL`` by the cache refresher and atomically
    assigned to ``CacheHolder.current``.  Pipeline steps read this snapshot for
    the full lifecycle of a single message dispatch — no torn reads possible.

    Fields:
        sources:           All sources keyed by their id (hex string).
        folders:           All folders keyed by their id (hex string).
        rules:             Active-only ForwardingRules (``is_active=True``),
                           fetched with ``page_size=10000`` (all active rules).
        replacements:      All replacement rules per parent rule_id.
                           Key: ``forwarding_rule_id`` (str) →
                           ``list[ReplacementRule]`` (``created_at`` ASC order).
        compiled_patterns: Pre-compiled regex patterns per rule_id.
                           Key: ``rule_id`` (str) → ``CompiledPatterns``.
        version:           Monotonically increasing integer.  Starts at 0
                           (initial empty cache), increments by 1 on each
                           successful build.  Useful for debugging staleness.
        refreshed_at:      UTC datetime of the last successful cache build.
                           ``None`` for the initial empty cache (version=0).
    """

    sources: dict = field(default_factory=dict)           # dict[str, Source]
    folders: dict = field(default_factory=dict)           # dict[str, SourceFolder]
    rules: list = field(default_factory=list)             # list[ForwardingRule] (active only)
    replacements: dict = field(default_factory=dict)      # dict[str, list[ReplacementRule]]
    compiled_patterns: dict = field(default_factory=dict)  # dict[str, CompiledPatterns]
    version: int = 0
    refreshed_at: Optional[datetime] = None


class CacheHolder:
    """Singleton holder for the current ``RuleCache`` snapshot.

    ``CacheHolder.current`` is the only write path for the cache refresher.
    All reads come from pipeline steps (Epic 4) which consume a local reference
    to the snapshot at the start of each dispatch.

    Usage::

        # Read in pipeline steps (capture once per dispatch):
        snapshot = CacheHolder.current

        # Write in cache_refresher only (atomic reference swap):
        CacheHolder.current = new_cache
    """

    current: RuleCache = RuleCache()  # Start with empty cache (version=0)
