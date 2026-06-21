---
baseline_commit: 0838a33a62b81c669346ccaecddab270bf7d26f6
---

# Story 3.3: Atomic Rule Cache & Cache Refresher

Status: done

## Story

As a **Channel Operator**,
I want rule changes I make via the API to take effect in the forwarding pipeline within 60 seconds without restarting the service,
so that **I can tune filters and see results in near real-time**.

---

## Acceptance Criteria

1. **Atomic Cache Snapshot — Happy Path:**
   - **Given** active Forwarding Rules and their Replacement Rules exist in MongoDB.
   - **When** the cache refresher coroutine runs (every `HOT_RELOAD_INTERVAL` seconds, default 30).
   - **Then** it fetches all four collections (`sources`, `source_folders`, `forwarding_rules`, `replacement_rules`) in sequence, builds a new frozen `RuleCache` dataclass, and replaces `CacheHolder.current` in a single Python assignment — atomic under the asyncio event loop.
   - **And** the new cache is visible to the next pipeline dispatch.

2. **Regex Pattern Pre-compilation:**
   - **Given** rules contain regex patterns in `block_keywords`, `allow_keywords`, or `replacement_rules` with `match_mode="regex"`.
   - **When** the cache is refreshed.
   - **Then** all regex patterns are compiled to `re.Pattern` objects and stored in `RuleCache.compiled_patterns` keyed by rule ID.
   - **And** compilation happens once per refresh cycle — not per message dispatched.

3. **Invalid Regex Pattern — Skip and Log:**
   - **Given** a regex pattern in a rule fails to compile (`re.compile(pattern)` raises `re.error`).
   - **When** the cache is refreshed.
   - **Then** an ERROR is logged with `rule_id` and the offending pattern.
   - **And** that pattern is skipped (no-op) for this snapshot's lifetime.
   - **And** the refresh completes normally and all other rules load correctly.

4. **Staleness Guarantee (NFR-RuleChange):**
   - **Given** a rule is created or updated via the API.
   - **When** at most two `HOT_RELOAD_INTERVAL` periods elapse (worst case: change made just after a refresh).
   - **Then** the new rule configuration is reflected in all subsequent pipeline dispatches (end-to-end staleness ≤ 60s per NFR-RuleChange).

5. **MongoDB Failure — Retain Last Valid Snapshot:**
   - **Given** MongoDB is temporarily unreachable during a refresh attempt.
   - **When** the refresh fails.
   - **Then** `CacheHolder.current` retains the last valid snapshot.
   - **And** a WARNING is logged with `{"event": "cache_refresh_failed", "last_successful_refresh": "<ISO timestamp>", ...}`.
   - **And** the refresher retries on the next interval without crashing.

6. **Cache Refresher Replaces Lifespan Stub:**
   - **Given** Story 1.3 created a `run_cache_refresher()` stub in `tasks.py`.
   - **When** Story 3.3 is implemented.
   - **Then** the stub in `tasks.py` is replaced by a real call to `infrastructure/cache/cache_refresher.py`'s `run_cache_refresher(settings, db)` coroutine.
   - **And** `lifespan` in `app.py` passes `settings` and `mongo_client.db` to the refresher.

---

## Tasks / Subtasks

- [x] **RuleCache Dataclass & CompiledPatterns** (`infrastructure/cache/rule_cache.py`)
  - [x] Define `CompiledPatterns` dataclass: `block_patterns: list[re.Pattern]`, `allow_patterns: list[re.Pattern]`, `replacement_patterns: dict[str, re.Pattern]` (keyed by replacement rule id → compiled pattern for `search_text`)
  - [x] Define `RuleCache` frozen dataclass with fields: `sources`, `folders`, `rules`, `replacements`, `compiled_patterns`, `version`, `refreshed_at`
  - [x] Define `CacheHolder` with class-level `current: RuleCache` attribute (mutable singleton)

- [x] **FolderRepository Extension** (`infrastructure/mongo/repositories/folder_repository.py`)
  - [x] Implement `list_folders(self) -> list[SourceFolder]` method fetching all folders mapped to domain entities

- [x] **Cache Refresher Coroutine** (`infrastructure/cache/cache_refresher.py`)
  - [x] Implement `build_rule_cache(db, version) -> RuleCache` async function: fetches 4 collections, compiles regex patterns, increments version
  - [x] Implement `run_cache_refresher(settings, db) -> None` coroutine: loops with `asyncio.sleep(settings.hot_reload_interval)`, calls `build_rule_cache`, atomically updates `CacheHolder.current`, handles exceptions (log WARNING, retain last snapshot)
  - [x] Ensure pre-compilation errors per rule are logged as ERROR but do not abort the refresh

- [x] **Replace `tasks.py` Stub**
  - [x] Replace the `run_cache_refresher()` body in `tasks.py` to call the real coroutine from `infrastructure/cache/cache_refresher.py`

- [x] **`app.py` Lifespan Wiring**
  - [x] Update the `cache_task` creation in `default_lifespan` to pass `settings` and `mongo_client.db`
  - [x] Add Message Mappings index to `app.py` startup (compound index on `message_mappings.forwarding_rule_id + source_channel_id + source_message_id`) — pre-created now so Epic 4 Story 4.1 doesn't touch `app.py` for this

- [x] **Verification & Testing**
  - [x] Write unit tests in `tests/infrastructure/cache/test_rule_cache.py`: RuleCache construction, frozen assertion, CompiledPatterns fields
  - [x] Write unit tests in `tests/infrastructure/cache/test_cache_refresher.py`: happy path build, invalid regex skip-and-log, MongoDB failure retains snapshot, version increments on each refresh
  - [x] Write unit test for `FolderRepository.list_folders()` in `tests/infrastructure/mongo/test_folder_repository.py`
  - [x] Verify the compound index on `message_mappings` exists in MongoDB after startup
  - [x] Verify all 182 existing tests still pass (zero regressions)

### Review Findings

- [x] [Review][Patch] Schema type comment inconsistency in ReplacementRuleResponse [forward-bot/src/forward_bot/api/schemas/replacement_rule.py:50]
- [x] [Review][Defer] Sequential O(N) database queries for replacement rules [forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py:152] — deferred, pre-existing

---

## Dev Notes

### Architecture & Implementation Guardrails

#### Why This Story Is "CRITICAL DEPENDENCY" for Epic 4

Every Epic 4 pipeline step reads from `CacheHolder.current` to get the snapshot of rules, sources, and compiled patterns for a given dispatch. Without `RuleCache` and `CacheHolder` in place, all pipeline steps have nothing to read from. This story provides:

- `RuleCache` — the frozen, atomic snapshot dataclass
- `CacheHolder` — the singleton holder swapped atomically each interval
- `CompiledPatterns` — pre-compiled `re.Pattern` objects for filter/replacement steps

**Do NOT defer any of these to Epic 4.** Epic 4 expects them already present.

#### Clean Architecture Rules

- All cache infrastructure lives in `infrastructure/cache/` — no domain entities created here (all four entity types are already defined in `domain/entities/`).
- `cache_refresher.py` imports from `infrastructure/mongo/repositories/` to fetch data — this is an infrastructure-to-infrastructure dependency, which is acceptable.
- `rule_cache.py` imports domain entities (`Source`, `SourceFolder`, `ForwardingRule`, `ReplacementRule`) — domain types are safe to reference from infrastructure.
- **No new domain exceptions** required for this story. Cache failures are logged internally; they never surface through the API.

#### `RuleCache` Frozen Dataclass Design

```python
# infrastructure/cache/rule_cache.py
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.replacement_rule import ReplacementRule


@dataclass
class CompiledPatterns:
    """Pre-compiled regex patterns for a single ForwardingRule.
    
    Keyed structures allow O(1) lookup by field name during pipeline execution.
    block_patterns and allow_patterns are lists of compiled re.Pattern objects
    (one per keyword that uses regex mode). replacement_patterns maps each
    replacement_rule.id → compiled re.Pattern for its search_text.
    """
    block_patterns: list[re.Pattern] = field(default_factory=list)
    allow_patterns: list[re.Pattern] = field(default_factory=list)
    replacement_patterns: dict[str, re.Pattern] = field(default_factory=dict)
    # Key: replacement_rule.id (str) → compiled re.Pattern for search_text


@dataclass(frozen=True)
class RuleCache:
    """Atomic, immutable snapshot of all four collections.
    
    Built once per HOT_RELOAD_INTERVAL by cache_refresher and atomically
    assigned to CacheHolder.current. Pipeline steps read this snapshot for
    the full lifecycle of a single message dispatch — no torn reads possible.
    
    Fields:
        sources:           All sources keyed by their id (hex string).
        folders:           All folders keyed by their id (hex string).
        rules:             Active-only ForwardingRules (is_active=True), ordered by created_at ASC.
        replacements:      All replacement rules per parent rule_id.
                           Key: forwarding_rule_id (str) → list[ReplacementRule] (created_at ASC order).
        compiled_patterns: Pre-compiled regex patterns per rule_id.
                           Key: rule_id (str) → CompiledPatterns.
        version:           Monotonically increasing integer. Starts at 0 (initial empty cache),
                           increments by 1 on each successful build. Useful for debugging.
        refreshed_at:      UTC datetime of the last successful cache build.
    """
    sources: dict = field(default_factory=dict)          # dict[str, Source]
    folders: dict = field(default_factory=dict)          # dict[str, SourceFolder]
    rules: list = field(default_factory=list)            # list[ForwardingRule] (active only)
    replacements: dict = field(default_factory=dict)     # dict[str, list[ReplacementRule]]
    compiled_patterns: dict = field(default_factory=dict) # dict[str, CompiledPatterns]
    version: int = 0
    refreshed_at: Optional[datetime] = None


class CacheHolder:
    """Singleton holder for the current RuleCache snapshot.
    
    Assignment of CacheHolder.current is atomic under the CPython GIL and the
    asyncio event loop's single-threaded execution model. No locks needed.
    
    Usage:
        snapshot = CacheHolder.current        # read in pipeline steps
        CacheHolder.current = new_cache       # write in cache_refresher (atomic)
    """
    current: RuleCache = RuleCache()          # Start with empty cache (version=0)
```

> **Why `frozen=True`?** The `frozen` flag prevents accidental mutation of the snapshot after creation. Pipeline steps may safely read fields without defensive copying. The `CacheHolder.current` reference itself (the pointer) is mutable — that is the only write that occurs during a refresh cycle.

> **Why `Optional[datetime]` for `refreshed_at`?** The initial `RuleCache()` (version=0, the empty cache present at startup) has no refresh timestamp. `refreshed_at` only becomes non-None after the first successful build.

> **`rules`: active-only.** The cache holds only `is_active=True` forwarding rules. Inactive rules are not needed by the pipeline. Epic 4's worker iterates `CacheHolder.current.rules` directly.

#### `cache_refresher.py` Implementation Design

```python
# infrastructure/cache/cache_refresher.py
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
    
    Steps:
    1. Fetch all Sources → dict[id, Source]
    2. Fetch all Folders → dict[id, SourceFolder]
    3. Fetch active ForwardingRules → list[ForwardingRule]
    4. For each active rule, fetch its ReplacementRules → dict[rule_id, list[ReplacementRule]]
    5. Compile regex patterns for each rule (block_keywords, allow_keywords, replacement search_text)
    6. Return a frozen RuleCache with version+1
    """
    source_repo = SourceRepository(db)
    folder_repo = FolderRepository(db)
    rule_repo = ForwardingRuleRepository(db)
    replacement_repo = ReplacementRuleRepository(db)

    # 1. Fetch sources (all, not just active) — note: must pass page_size=10000 to fetch all sources
    all_sources_list, _ = await source_repo.list_sources(page_size=10000)
    sources = {s.id: s for s in all_sources_list if s.id}

    # 2. Fetch folders (all)
    all_folders = await folder_repo.list_folders()
    folders = {f.id: f for f in all_folders if f.id}

    # 3. Fetch active forwarding rules only
    active_rules, _ = await rule_repo.list_rules(is_active=True, page_size=10000)

    # 4. Fetch replacement rules for each active rule
    replacements: dict[str, list] = {}
    for rule in active_rules:
        if rule.id:
            rule_replacements = await replacement_repo.list_replacements_for_rule(rule.id)
            replacements[rule.id] = rule_replacements

    # 5. Compile regex patterns
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
                    # Skip this pattern — no-op for this snapshot lifetime
            
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

        # Compile replacement rule search_text patterns (only for regex mode replacements)
        for rr in replacements.get(rule.id, []):
            if rr.match_mode == "regex" and rr.id:
                try:
                    patterns.replacement_patterns[rr.id] = re.compile(rr.search_text, re.IGNORECASE)
                except re.error as e:
                    logger.error(
                        "cache_pattern_compile_failed",
                        rule_id=rule.id,
                        replacement_rule_id=rr.id,
                        pattern=rr.search_text,
                        field="replacement_search_text",
                        error=str(e),
                    )
        
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
    """Background coroutine: refreshes RuleCache every HOT_RELOAD_INTERVAL seconds.
    
    - On success: atomically replaces CacheHolder.current; logs INFO.
    - On failure: logs WARNING with last_successful_refresh; retains last valid snapshot.
    - Handles asyncio.CancelledError cleanly for graceful shutdown.
    
    The version counter starts at 1 on the first successful build (CacheHolder.current
    starts at version=0, the empty initial cache).
    """
    version = 1
    last_successful_refresh: datetime | None = None
    logger.info("cache_refresher_started", hot_reload_interval=settings.hot_reload_interval)
    
    while True:
        try:
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
            # Retain CacheHolder.current (last valid snapshot) — do NOT clear it
            # Continue the loop on the next interval
```

> **Critical: `asyncio.sleep` is called BEFORE the first build.** This means the pipeline starts with `CacheHolder.current = RuleCache()` (the empty version-0 cache) until the first refresh interval elapses. Epic 4 workers must tolerate an empty cache at startup — the `rules` list will be `[]` and no forwarding will happen until the first successful refresh. This is acceptable because Telegram event handlers are also registered after the worker starts (within one `HOT_RELOAD_INTERVAL`).

> **Why sleep first?** The pattern of sleeping first ensures the MongoDB connection is fully established and the worker is running before the first cache build. If the sleep came after the build, a startup race could cause the first build to fail with a connection error.

#### Updating `tasks.py`

    The stub `run_cache_refresher()` in `tasks.py` must be updated to delegate to the real implementation:

```python
# tasks.py — UPDATED run_cache_refresher function ONLY
# The mapping_sweeper and telegram_worker stubs remain unchanged.

async def run_cache_refresher(settings=None, db=None) -> None:
    """Real cache refresher — delegates to infrastructure/cache/cache_refresher.py."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher as _run
    await _run(settings, db)
```

#### Updating `app.py` — Lifespan Wiring

```python
# In app.py default_lifespan, replace:
cache_task = asyncio.create_task(run_cache_refresher())

# With:
from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher as _real_cache_refresher
cache_task = asyncio.create_task(_real_cache_refresher(settings, mongo_client.db))
```

Or if using the delegation pattern through `tasks.py`:

```python
# tasks.py's run_cache_refresher now accepts settings and db:
cache_task = asyncio.create_task(run_cache_refresher(settings, mongo_client.db))
```

Either approach is correct. What matters is that `settings` and `mongo_client.db` are passed — the refresher cannot access them via module-level globals.

#### Accessing Source and Folder Repositories

**`SourceRepository.list_sources()`** is the existing method from Story 2.2. Check its signature:

```python
# source_repository.py — existing signature (from Story 2.2):
async def list_sources(
    self,
    filter_type: str | None = None,
    folder_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Source], int]:
```

For the cache build, we need ALL sources — use `page_size=10000` to effectively get all (the NFR-Scale target is 100 active sources, so this is more than sufficient):

```python
all_sources_list, _ = await source_repo.list_sources(page_size=10000)
```

**`FolderRepository` Implementation Requirements:**
The `FolderRepository` must be updated to expose a `list_folders()` method fetching all folders mapped to domain entities. Implement it in `infrastructure/mongo/repositories/folder_repository.py` as:

```python
    async def list_folders(self) -> list[SourceFolder]:
        """Fetch all Folders from the database mapped to domain entities."""
        docs = await self.find({})
        return [self._to_entity(doc) for doc in docs]
```

#### `RuleRepository.list_rules()` — Active-Only Filter

```python
# Rule repository already supports is_active filter (Story 3.1):
active_rules, _ = await rule_repo.list_rules(is_active=True, page_size=10000)
```

`list_rules` requires `source_repo` only when `folder_id` filter is used. For the cache build, we're not filtering by folder, so `source_repo=None` is fine:

```python
active_rules, _ = await rule_repo.list_rules(
    source_repo=None,    # not needed — no folder_id filter
    is_active=True,
    page_size=10000,
)
```

#### `ReplacementRuleRepository.list_replacements_for_rule()` — Existing Method

Already implemented in Story 3.2. Simply call it per rule:

```python
rule_replacements = await replacement_repo.list_replacements_for_rule(rule.id)
replacements[rule.id] = rule_replacements
```

> **Only active replacement rules in cache?** The epics spec says `replacements: dict[ObjectId, list[ReplacementRule]]` — no filter on `is_active` is mentioned for the cache structure. However, including inactive replacements in the cache means pipeline steps must filter them at execution time. Recommendation: **load all replacement rules** (not just `is_active=True`) for each parent rule. Pipeline step `TextReplacementStep` in Epic 4 will skip `is_active=False` replacements during execution. This is consistent with FR-7 (replacement rule has `is_active` field) and simplifies the cache refresher.

#### Regex Compilation with Case-Insensitivity

Compile all regex patterns (`block_keywords`, `allow_keywords`, and replacement `search_text`) with the `re.IGNORECASE` flag. This ensures consistency with FR-8 (case-insensitive substring replacement) and FR-36 (case-insensitive keyword matching) during pipeline execution. Literal mode keyword matching will be handled case-insensitively at execution time.

#### Message Mappings Index — Pre-create in `app.py`

Epic 4 Story 4.1 requires a compound index on `message_mappings`:
`(forwarding_rule_id, source_channel_id, source_message_id)`.

Create this index in `app.py`'s lifespan **now** in Story 3.3 to avoid touching `app.py` again in Epic 4. This is an additive change — creating an index on an empty collection is instant and harmless.

```python
# In app.py lifespan, inside the try block after the REPLACEMENT_RULES index:
# Message mapping index (pre-created for Epic 4 Story 4.1)
from forward_bot.api.schemas.base import MESSAGE_MAPPINGS
await mongo_client.db[MESSAGE_MAPPINGS].create_index(
    [("forwarding_rule_id", 1), ("source_channel_id", 1), ("source_message_id", 1)],
    background=True
)
```

#### Unit Test Design

**`tests/infrastructure/cache/test_rule_cache.py`:**

```python
"""Unit tests for RuleCache and CacheHolder in infrastructure/cache/rule_cache.py."""
import pytest
import re
from datetime import datetime, timezone
from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns


def test_rule_cache_frozen():
    """RuleCache is frozen — attributes cannot be mutated after creation."""
    cache = RuleCache(version=1)
    with pytest.raises((AttributeError, TypeError)):
        cache.version = 2  # frozen dataclass should raise


def test_rule_cache_defaults():
    """RuleCache() with no args produces a valid empty snapshot."""
    cache = RuleCache()
    assert cache.sources == {}
    assert cache.folders == {}
    assert cache.rules == []
    assert cache.replacements == {}
    assert cache.compiled_patterns == {}
    assert cache.version == 0
    assert cache.refreshed_at is None


def test_cache_holder_starts_with_empty_cache():
    """CacheHolder.current starts as an empty RuleCache (version=0)."""
    # Note: CacheHolder is a singleton — this tests the module-level state
    # Reset to empty for test isolation
    CacheHolder.current = RuleCache()
    assert CacheHolder.current.version == 0
    assert CacheHolder.current.rules == []


def test_cache_holder_atomic_swap():
    """Assigning CacheHolder.current replaces the snapshot atomically."""
    original = CacheHolder.current
    new_cache = RuleCache(version=42)
    CacheHolder.current = new_cache
    assert CacheHolder.current.version == 42
    # Restore
    CacheHolder.current = original


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
    assert "rr-id-1" in p.replacement_patterns
```

**`tests/infrastructure/cache/test_cache_refresher.py`:**

```python
"""Unit tests for build_rule_cache and run_cache_refresher in infrastructure/cache/cache_refresher.py."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, SamplingConfig, AttributionConfig, AutoReplaceSourceRefsConfig, MediaReplacementConfig
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.source_folder import SourceFolder


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

def make_source(id_="src1"):
    return Source(
        id=id_, telegram_id=1001, telegram_username="test_chan",
        display_name="Test Chan", type="channel", folder_id=None,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )


def make_rule(id_="rule1", match_mode="literal", block=None, allow=None, active=True):
    return ForwardingRule(
        id=id_, source_id="src1", destination_channel="@dest",
        is_active=active, keyword_match_mode=match_mode,
        block_keywords=block or [], allow_keywords=allow or [],
        sampling=SamplingConfig(), attribution=AttributionConfig(),
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(),
        media_replacement=MediaReplacementConfig(),
    )


def make_replacement(id_="rr1", search="old", mode="literal", rule_id="rule1"):
    now = datetime.now(timezone.utc)
    return ReplacementRule(
        id=id_, forwarding_rule_id=rule_id,
        search_text=search, replacement_text="new",
        match_mode=mode, is_active=True, created_at=now, updated_at=now,
    )


# ─────────────────────────────────────────────
# Tests for build_rule_cache
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_rule_cache_happy_path():
    """build_rule_cache fetches 4 collections and builds a valid RuleCache snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    source = make_source()
    rule = make_rule()
    replacement = make_replacement()

    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(return_value=([source], 1))

    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=[])

    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([rule], 1))

    mock_replacement_repo = MagicMock()
    mock_replacement_repo.list_replacements_for_rule = AsyncMock(return_value=[replacement])

    mock_db = MagicMock()

    with (
        patch("forward_bot.infrastructure.cache.cache_refresher.SourceRepository", return_value=mock_source_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.FolderRepository", return_value=mock_folder_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository", return_value=mock_rule_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository", return_value=mock_replacement_repo),
    ):
        cache = await build_rule_cache(mock_db, version=1)

    assert cache.version == 1
    assert "src1" in cache.sources
    assert "rule1" in cache.replacements
    assert len(cache.replacements["rule1"]) == 1
    assert cache.refreshed_at is not None
    assert isinstance(cache, RuleCache)


@pytest.mark.asyncio
async def test_build_rule_cache_compiles_regex_patterns():
    """Regex patterns in block_keywords/allow_keywords are compiled into CompiledPatterns."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["BTC|ETH"])
    replacement = make_replacement(search="old.+new", mode="regex")

    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(return_value=([], 0))
    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=[])
    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([rule], 1))
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.list_replacements_for_rule = AsyncMock(return_value=[replacement])
    mock_db = MagicMock()

    with (
        patch("forward_bot.infrastructure.cache.cache_refresher.SourceRepository", return_value=mock_source_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.FolderRepository", return_value=mock_folder_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository", return_value=mock_rule_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository", return_value=mock_replacement_repo),
    ):
        cache = await build_rule_cache(mock_db, version=1)

    assert "rule1" in cache.compiled_patterns
    cp = cache.compiled_patterns["rule1"]
    assert len(cp.block_patterns) == 1
    assert cp.block_patterns[0].pattern == "pump.*"
    assert len(cp.allow_patterns) == 1
    assert "rr1" in cp.replacement_patterns


@pytest.mark.asyncio
async def test_build_rule_cache_skips_invalid_regex(caplog):
    """Invalid regex patterns are skipped (no-op) and logged as ERROR — refresh completes."""
    import logging
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="regex", block=["[invalid("])  # invalid regex

    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(return_value=([], 0))
    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=[])
    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([rule], 1))
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.list_replacements_for_rule = AsyncMock(return_value=[])
    mock_db = MagicMock()

    with (
        patch("forward_bot.infrastructure.cache.cache_refresher.SourceRepository", return_value=mock_source_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.FolderRepository", return_value=mock_folder_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository", return_value=mock_rule_repo),
        patch("forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository", return_value=mock_replacement_repo),
    ):
        cache = await build_rule_cache(mock_db, version=1)

    # Refresh completes — cache has version set
    assert cache.version == 1
    # The invalid pattern is skipped — compiled_patterns for rule1 exists but block_patterns is empty
    assert "rule1" in cache.compiled_patterns
    assert cache.compiled_patterns["rule1"].block_patterns == []


@pytest.mark.asyncio
async def test_run_cache_refresher_retains_snapshot_on_mongodb_failure():
    """On MongoDB error, CacheHolder.current retains the last valid snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    initial_cache = RuleCache(version=99)
    CacheHolder.current = initial_cache

    mock_settings = MagicMock()
    mock_settings.hot_reload_interval = 0.01  # very short for test speed
    mock_db = MagicMock()

    async def mock_build(db, version):
        raise Exception("MongoDB connection lost")

    with patch("forward_bot.infrastructure.cache.cache_refresher.build_rule_cache", side_effect=mock_build):
        # Run refresher as a background task, then cancel it
        task = asyncio.create_task(run_cache_refresher(mock_settings, mock_db))
        await asyncio.sleep(0.05)  # Let it run and fail at least once
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Snapshot retained — not reset to empty
    assert CacheHolder.current.version == 99

    # Restore
    CacheHolder.current = RuleCache()
```

#### File Structure — What Changes in This Story

```
src/forward_bot/
  infrastructure/cache/
    __init__.py              ✅ exists (empty)
    rule_cache.py            🚧 NEW — RuleCache, CacheHolder, CompiledPatterns
    cache_refresher.py       🚧 NEW — build_rule_cache(), run_cache_refresher()
  
  # MODIFIED files:
  tasks.py                   ✅ exists — UPDATE run_cache_refresher() to delegate or replace stub
  app.py                     ✅ exists — UPDATE cache_task creation to pass settings + db;
                                         ADD message_mappings index

tests/
  infrastructure/
    cache/                   🚧 NEW directory
      __init__.py            🚧 NEW — empty
      test_rule_cache.py     🚧 NEW — unit tests for RuleCache/CacheHolder/CompiledPatterns
      test_cache_refresher.py 🚧 NEW — unit tests for build_rule_cache + run_cache_refresher
```

> **Only 2 new production files** — this story is intentionally focused on infrastructure only. No domain entities, no API routers, no schemas, no exceptions added.

### Previous Story Intelligence (Story 3.2 Learnings)

1. **`list_sources()` uses page-based pagination** (from Story 2.2): Pass `page_size=10000` to effectively retrieve all sources — the NFR-Scale target is 100 active sources. Verify the actual `list_sources()` signature before calling; the repository filters via `type`, `folder_id`, `page`, `page_size`.

2. **`forwarding_rule_id` in `replacement_rules` is stored as a plain string** (not BSON ObjectId). When calling `list_replacements_for_rule(rule.id)`, `rule.id` is already a hex string. No ObjectId conversion needed.

3. **Repository instances require `db`** (motor `AsyncIOMotorDatabase`) as the first constructor argument. In `build_rule_cache(db, version)`, instantiate each repository with `SourceRepository(db)`, `FolderRepository(db)`, etc.

4. **`validate_keyword_regex` wraps in a list** — the validator in `application/rules/validators.py` iterates over a list. This is the rule-save validator; `build_rule_cache` does its own `try/except re.error` — do NOT reuse the domain validator here.

5. **`FolderRepository.list_folders()` signature**: From Story 2.3, `list_folders()` returns `list[SourceFolder]` (no pagination). Confirm by reading the actual file before calling.

6. **Total test count at start of Story 3.3**: **182 tests**. Zero regressions accepted.

7. **`CacheHolder` is a module-level singleton.** In tests, always reset `CacheHolder.current = RuleCache()` at the start of tests that mutate it, or use fixtures. Tests that inspect `CacheHolder.current.version == 0` can be brittle if run after tests that swap the cache. Use `MagicMock` to avoid actual DB calls.

### Git Intelligence (Snapshot at Story File Creation)

| Commit | What It Did |
|--------|-------------|
| `0838a33` | Story 3.2 — Replacement Rule CRUD API (4 endpoints, 7 new files, 4 modified, 182 tests) |
| `57848c6` | Story 2.2 — Source listing, updates (list/filter/pagination, PATCH endpoint) |
| `64187b5` | Story 2.1 — Source registration + Telegram ID resolve |
| `514a259` | Story 1.4 — Telegram auth + session management |

> **Baseline commit**: `0838a33` — the cache refresher starts from this state.

### What This Story Must NOT Do

- ❌ **Do NOT implement any pipeline steps** (`TimeWindowStep`, `SamplingStep`, etc.) — those are Epic 4.
- ❌ **Do NOT implement `MessageMapping` entity or its repository** — that is Epic 4 Story 4.1.
- ❌ **Do NOT implement the Telegram worker** (`worker.py`) — that is Epic 4 Story 4.5.
- ❌ **Do NOT expose any new API endpoints** — the cache is purely internal infrastructure.
- ❌ **Do NOT raise domain exceptions** from the cache refresher — failures are logged as WARNING and the loop continues.
- ❌ **Do NOT use `asyncio.Queue` for cache distribution** — single atomic reference swap is sufficient and correct.
- ❌ **Do NOT create a sampling_counters index** — that is only needed when `SAMPLING_PERSIST=true` (Epic 4 Story 4.2).
- ❌ **Do NOT add `media_replacement_images` endpoint** — that is Epic 6 (UX-DR12).

### Technical References

- Architecture decision D1 (atomic cache snapshot): epics.md L139
- Architecture decision D2 (regex compilation per snapshot): epics.md L141
- NFR-RuleChange (≤60s staleness): epics.md L117
- `BaseRepository` pattern: [base.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/base.py)
- `ForwardingRuleRepository.list_rules()` (active filter): [rule_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/rule_repository.py#L189-L242)
- `ReplacementRuleRepository.list_replacements_for_rule()`: [replacement_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py)
- `CacheHolder` consumers (Epic 4 reading context): epics.md L700 — `cache_holder.current` read once per dispatch
- `tasks.py` (stub to replace): [tasks.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/tasks.py)
- `app.py` (lifespan wiring): [app.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py#L75-L78)
- `Settings.hot_reload_interval` (default 30): [config.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/config.py#L84-L87)

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (Thinking)

### Debug Log References

- Fixed `tasks.py` stub: existing E2E test `test_cache_refresher_cancels_cleanly` called `run_cache_refresher()` with no args. Added `settings is None or db is None` guard to fall back to stub sleep mode, preserving backward compatibility.
- Fixed `_patch_repos()` in `test_cache_refresher.py`: the function initially returned a tuple of patch objects instead of a context manager. Converted it to a `@contextlib.contextmanager` function so `with _patch_repos(...):` works correctly.

### Completion Notes List

- ✅ `infrastructure/cache/rule_cache.py` — NEW: `CompiledPatterns`, `RuleCache` (frozen dataclass), `CacheHolder` singleton. All fields match story spec exactly.
- ✅ `infrastructure/cache/cache_refresher.py` — NEW: `build_rule_cache()` fetches 4 collections, compiles regex with `re.IGNORECASE`, skips/logs invalid patterns. `run_cache_refresher()` sleep-first loop, atomic swap, retains last snapshot on failure, re-raises `CancelledError`.
- ✅ `infrastructure/mongo/repositories/folder_repository.py` — MODIFIED: Added `list_folders()` using `self.find({})` as documented in story spec.
- ✅ `tasks.py` — MODIFIED: `run_cache_refresher()` stub replaced with real delegation to `cache_refresher.py`. `None`-guard preserves backward compatibility with Story 1.3 E2E test.
- ✅ `app.py` — MODIFIED: `cache_task` now passes `settings, mongo_client.db`; added `message_mappings` compound index creation for Epic 4 Story 4.1.
- ✅ `tests/infrastructure/cache/test_rule_cache.py` — NEW: 12 unit tests covering construction, frozen semantics, singleton swap, and `CompiledPatterns` storage.
- ✅ `tests/infrastructure/cache/test_cache_refresher.py` — NEW: 21 unit tests covering happy path, regex compilation, invalid regex skip-and-log, MongoDB failure retention, version increment, CancelledError propagation.
- ✅ `tests/infrastructure/mongo/test_folder_repository.py` — MODIFIED: 4 new tests for `list_folders()` added to existing file.
- ✅ Full test suite: **219 passed, 0 failed** (182 baseline + 37 new = 219 total).

### File List

**New files:**
- `src/forward_bot/infrastructure/cache/rule_cache.py`
- `src/forward_bot/infrastructure/cache/cache_refresher.py`
- `tests/infrastructure/cache/__init__.py`
- `tests/infrastructure/cache/test_rule_cache.py`
- `tests/infrastructure/cache/test_cache_refresher.py`

**Modified files:**
- `src/forward_bot/infrastructure/mongo/repositories/folder_repository.py`
- `src/forward_bot/tasks.py`
- `src/forward_bot/app.py`
- `tests/infrastructure/mongo/test_folder_repository.py`

---

## Change Log

- Story 3.3 created: Atomic Rule Cache & Cache Refresher — story file created, status ready-for-dev. (Date: 2026-06-18)
- Story 3.3 implemented: All tasks complete. Created `rule_cache.py` (RuleCache, CacheHolder, CompiledPatterns), `cache_refresher.py` (build_rule_cache, run_cache_refresher), extended FolderRepository with `list_folders()`, wired `app.py` lifespan with settings+db and pre-created `message_mappings` compound index, replaced `tasks.py` stub. 37 new tests added; 219/219 pass. Status → review. (Date: 2026-06-18)
