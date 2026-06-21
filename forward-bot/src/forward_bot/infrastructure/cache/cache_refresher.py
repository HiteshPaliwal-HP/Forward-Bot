"""Background cache refresher for the forwarding rule pipeline.

Provides two public coroutines:

  - ``build_rule_cache(db, version)``  — fetches all four MongoDB collections,
    compiles regex patterns, and returns a frozen ``RuleCache`` snapshot.
  - ``run_cache_refresher(settings, db)`` — long-running background loop that
    calls ``build_rule_cache`` every ``HOT_RELOAD_INTERVAL`` seconds and
    atomically replaces ``CacheHolder.current``.

Design decisions
----------------
* **Sleep-first pattern**: the refresher sleeps *before* the first build so
  that the MongoDB connection pool and all startup tasks are fully established
  before the initial fetch.  The pipeline starts with the empty
  ``RuleCache()`` (version=0) until the first refresh completes — Epic 4
  workers tolerate an empty ``rules`` list at startup.
* **Atomic swap**: ``CacheHolder.current = new_cache`` is a single Python
  reference assignment, which is atomic under the CPython GIL and the asyncio
  event loop.  No locking primitives are needed.
* **Retain last snapshot on failure**: if MongoDB is temporarily unreachable
  the ``WARNING`` is logged and ``CacheHolder.current`` is left unchanged so
  the pipeline continues with the last known-good snapshot.
* **Invalid regex — skip and log**: a ``re.error`` during pattern compilation
  logs an ``ERROR`` for the offending rule/pattern and skips that pattern.
  The rest of the refresh completes normally (AC-3).
* **O(1) DB queries**: the refresh performs exactly 4 MongoDB round-trips
  (sources, folders, rules, all-replacements-in-one-``$in``-query),
  regardless of rule count. Previously replacement rules were fetched in an
  O(N) per-rule loop — this is fixed as of the Epic 3 retrospective.
"""
import asyncio
import re
from datetime import datetime, timezone

from forward_bot.infrastructure.logging import logger
from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository
from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository


async def build_rule_cache(db, version: int) -> RuleCache:
    """Fetch all four collections from MongoDB and build an atomic RuleCache snapshot.

    Steps
    -----
    1. Fetch all Sources → ``dict[id, Source]``
    2. Fetch all Folders → ``dict[id, SourceFolder]``
    3. Fetch **active** ForwardingRules → ``list[ForwardingRule]``
    4. Fetch ALL ReplacementRules for all active rules in one ``$in`` query →
       ``dict[rule_id, list[ReplacementRule]]``  (O(1) DB round-trips)
    5. Compile regex patterns for each rule
       (``block_keywords``, ``allow_keywords``, replacement ``search_text``)
    6. Return a frozen ``RuleCache`` with the supplied ``version`` number.

    Args:
        db:      Motor ``AsyncIOMotorDatabase`` instance.
        version: Version number to stamp on the returned cache snapshot.

    Returns:
        A frozen ``RuleCache`` snapshot ready to be atomically assigned to
        ``CacheHolder.current``.

    Raises:
        Any exception raised by MongoDB (network failures, etc.) — callers
        should catch these and retain the last valid snapshot.
    """
    source_repo = SourceRepository(db)
    folder_repo = FolderRepository(db)
    rule_repo = ForwardingRuleRepository(db)
    replacement_repo = ReplacementRuleRepository(db)

    # 1. Fetch all sources (not just active) — page_size=10000 effectively fetches all
    #    (NFR-Scale target is 100 active sources, so this is well above the expected ceiling)
    all_sources_list, _ = await source_repo.list_sources(page_size=10000)
    sources = {s.id: s for s in all_sources_list if s.id}

    # 2. Fetch all folders
    all_folders = await folder_repo.list_folders()
    folders = {f.id: f for f in all_folders if f.id}

    # 3. Fetch only active forwarding rules
    #    source_repo=None is fine here because we are not filtering by folder_id
    active_rules, _ = await rule_repo.list_rules(
        source_repo=None,
        is_active=True,
        page_size=10000,
    )

    # 4. Fetch ALL replacement rules for all active rules in ONE MongoDB query.
    #    ``list_all_replacements_for_rules`` uses a ``$in`` filter, reducing DB
    #    round-trips from O(N) per-rule to a fixed O(1) regardless of rule count.
    #    All replacement rules are loaded (not filtered by is_active) so that the
    #    pipeline TextReplacementStep can skip is_active=False at runtime —
    #    consistent with FR-7 and the Epic 4 design notes.
    rule_ids = [r.id for r in active_rules if r.id]
    replacements: dict[str, list] = await replacement_repo.list_all_replacements_for_rules(rule_ids)

    # 5. Compile regex patterns for each active rule.
    #    Invalid patterns are logged as ERROR and skipped (no-op) for the
    #    lifetime of this snapshot — the refresh continues normally (AC-3).
    compiled_patterns: dict[str, CompiledPatterns] = {}
    for rule in active_rules:
        if not rule.id:
            continue

        patterns = CompiledPatterns()

        if rule.keyword_match_mode == "regex":
            # Compile block_keywords
            for kw in rule.block_keywords:
                try:
                    patterns.block_patterns.append(re.compile(kw, re.IGNORECASE))
                except re.error as e:
                    logger.error(
                        "cache_pattern_compile_failed",
                        rule_id=rule.id,
                        pattern=kw,
                        field="block_keywords",
                        error=str(e),
                    )
                    # Skip this pattern — no-op for this snapshot's lifetime

            # Compile allow_keywords
            for kw in rule.allow_keywords:
                try:
                    patterns.allow_patterns.append(re.compile(kw, re.IGNORECASE))
                except re.error as e:
                    logger.error(
                        "cache_pattern_compile_failed",
                        rule_id=rule.id,
                        pattern=kw,
                        field="allow_keywords",
                        error=str(e),
                    )
                    # Skip this pattern — no-op for this snapshot's lifetime

        # Compile replacement rule search_text patterns (regex mode only)
        for rr in replacements.get(rule.id, []):
            if rr.match_mode == "regex" and rr.id:
                try:
                    patterns.replacement_patterns[rr.id] = re.compile(
                        rr.search_text, re.IGNORECASE
                    )
                except re.error as e:
                    logger.error(
                        "cache_pattern_compile_failed",
                        rule_id=rule.id,
                        replacement_rule_id=rr.id,
                        pattern=rr.search_text,
                        field="replacement_search_text",
                        error=str(e),
                    )
                    # Skip this pattern — no-op for this snapshot's lifetime

        compiled_patterns[rule.id] = patterns

    return RuleCache(
        sources=sources,
        folders=folders,
        rules=active_rules,
        replacements=replacements,
        compiled_patterns=compiled_patterns,
        version=version,
        refreshed_at=datetime.now(timezone.utc),
    )


async def run_cache_refresher(settings, db) -> None:
    """Background coroutine: refreshes ``RuleCache`` every ``HOT_RELOAD_INTERVAL`` seconds.

    Behaviour
    ---------
    * **Sleep-first**: waits one interval before the first build so that the
      rest of the application (MongoDB pool, Telegram client) has time to
      initialise.  The pipeline starts with the empty ``RuleCache()``
      (version=0, ``rules=[]``) until the first refresh completes.
    * **On success**: atomically replaces ``CacheHolder.current``; logs INFO
      with version, rule_count, source_count, folder_count.
    * **On failure**: logs WARNING with ``last_successful_refresh`` ISO
      timestamp; retains the current ``CacheHolder.current`` (last known-good
      snapshot); continues the loop on the next interval (AC-5).
    * **Graceful shutdown**: re-raises ``asyncio.CancelledError`` after logging
      so that the task can be awaited cleanly by the lifespan handler.

    The ``version`` counter starts at 1 on the first successful build
    (``CacheHolder`` starts at version=0, the empty initial cache).

    Args:
        settings: Application ``Settings`` instance with ``hot_reload_interval``.
        db:       Motor ``AsyncIOMotorDatabase`` instance.
    """
    version = 1
    last_successful_refresh: datetime | None = None
    logger.info("cache_refresher_started", hot_reload_interval=settings.hot_reload_interval)

    while True:
        try:
            # Sleep first — ensures MongoDB is ready before the initial fetch
            await asyncio.sleep(settings.hot_reload_interval)

            new_cache = await build_rule_cache(db, version)
            CacheHolder.current = new_cache          # ← atomic under asyncio event loop
            last_successful_refresh = new_cache.refreshed_at
            version += 1

            logger.info(
                "cache_refreshed",
                version=new_cache.version,
                rule_count=len(new_cache.rules),
                source_count=len(new_cache.sources),
                folder_count=len(new_cache.folders),
            )

        except asyncio.CancelledError:
            logger.info("cache_refresher_stopped")
            raise

        except Exception as e:
            logger.warning(
                "cache_refresh_failed",
                error=str(e),
                last_successful_refresh=(
                    last_successful_refresh.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if last_successful_refresh
                    else None
                ),
            )
            # Retain CacheHolder.current (last valid snapshot) — do NOT clear it.
            # The loop continues on the next interval (AC-5).
