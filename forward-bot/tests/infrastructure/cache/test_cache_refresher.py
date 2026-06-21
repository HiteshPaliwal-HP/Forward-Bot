import asyncio
import contextlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.infrastructure.cache.rule_cache import CacheHolder, CompiledPatterns, RuleCache


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_source(id_: str = "src1") -> Source:
    return Source(
        id=id_,
        telegram_id=1001,
        telegram_username="test_chan",
        display_name="Test Chan",
        type="channel",
        folder_id=None,
        created_at=_now(),
        updated_at=_now(),
    )


def make_folder(id_: str = "fol1") -> SourceFolder:
    return SourceFolder(id=id_, name="Test Folder", created_at=_now(), updated_at=_now())


def make_rule(
    id_: str = "rule1",
    match_mode: str = "literal",
    block: list[str] | None = None,
    allow: list[str] | None = None,
    active: bool = True,
) -> ForwardingRule:
    return ForwardingRule(
        id=id_,
        source_id="src1",
        destination_channel="@dest",
        is_active=active,
        keyword_match_mode=match_mode,
        block_keywords=block or [],
        allow_keywords=allow or [],
    )


def make_replacement(
    id_: str = "rr1",
    search: str = "old",
    mode: str = "literal",
    rule_id: str = "rule1",
) -> ReplacementRule:
    return ReplacementRule(
        id=id_,
        forwarding_rule_id=rule_id,
        search_text=search,
        replacement_text="new",
        match_mode=mode,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )


def _make_mock_repos(
    sources=None,
    folders=None,
    rules=None,
    replacements=None,
):
    """Return a dict of pre-configured mock repositories.

    ``replacements`` should be a ``dict[rule_id, list[ReplacementRule]]``.
    The mock wires up ``list_all_replacements_for_rules`` (the O(1) batch method
    used by ``build_rule_cache``) to return the dict keyed by the requested IDs.
    The per-rule ``list_replacements_for_rule`` is NOT called by the cache refresher.
    """
    mock_source_repo = MagicMock()
    mock_source_repo.list_sources = AsyncMock(
        return_value=(sources or [], len(sources) if sources else 0)
    )

    mock_folder_repo = MagicMock()
    mock_folder_repo.list_folders = AsyncMock(return_value=folders or [])

    mock_rule_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(
        return_value=(rules or [], len(rules) if rules else 0)
    )

    mock_replacement_repo = MagicMock()
    _replacements = replacements or {}

    async def batch_list(rule_ids):
        """Simulate list_all_replacements_for_rules: pre-seed every requested id."""
        return {rid: _replacements.get(rid, []) for rid in rule_ids}

    mock_replacement_repo.list_all_replacements_for_rules = batch_list

    return mock_source_repo, mock_folder_repo, mock_rule_repo, mock_replacement_repo


@contextlib.contextmanager
def _patch_repos(source_repo, folder_repo, rule_repo, replacement_repo):
    """Context manager that patches all four repository classes simultaneously."""
    with (
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.SourceRepository",
            return_value=source_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.FolderRepository",
            return_value=folder_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository",
            return_value=rule_repo,
        ),
        patch(
            "forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository",
            return_value=replacement_repo,
        ),
    ):
        yield



# ---------------------------------------------------------------------------
# build_rule_cache — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_rule_cache_happy_path():
    """build_rule_cache fetches 4 collections and builds a valid RuleCache snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    source = make_source()
    folder = make_folder()
    rule = make_rule()
    replacement = make_replacement()

    sr, fr, rr, rep = _make_mock_repos(
        sources=[source],
        folders=[folder],
        rules=[rule],
        replacements={"rule1": [replacement]},
    )

    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    assert isinstance(cache, RuleCache)
    assert cache.version == 1
    assert "src1" in cache.sources
    assert "fol1" in cache.folders
    assert len(cache.rules) == 1
    assert "rule1" in cache.replacements
    assert len(cache.replacements["rule1"]) == 1
    assert cache.refreshed_at is not None


@pytest.mark.asyncio
async def test_build_rule_cache_version_stamped_correctly():
    """build_rule_cache stamps the provided version number into the snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    sr, fr, rr, rep = _make_mock_repos()
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=7)

    assert cache.version == 7


@pytest.mark.asyncio
async def test_build_rule_cache_refreshed_at_is_utc():
    """build_rule_cache sets refreshed_at to UTC datetime."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    sr, fr, rr, rep = _make_mock_repos()
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    assert cache.refreshed_at is not None
    assert cache.refreshed_at.tzinfo is not None  # timezone-aware


@pytest.mark.asyncio
async def test_build_rule_cache_empty_db():
    """build_rule_cache with empty collections returns an empty but valid snapshot."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    sr, fr, rr, rep = _make_mock_repos()
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    assert cache.sources == {}
    assert cache.folders == {}
    assert cache.rules == []
    assert cache.replacements == {}
    assert cache.compiled_patterns == {}


@pytest.mark.asyncio
async def test_build_rule_cache_multiple_sources_and_rules():
    """build_rule_cache correctly indexes multiple sources and rules."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    sources = [make_source(id_=f"src{i}") for i in range(3)]
    rules = [make_rule(id_=f"rule{i}") for i in range(2)]

    sr, fr, rr, rep = _make_mock_repos(sources=sources, rules=rules)
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    assert len(cache.sources) == 3
    assert len(cache.rules) == 2
    assert all(f"src{i}" in cache.sources for i in range(3))


# ---------------------------------------------------------------------------
# build_rule_cache — regex pattern compilation (AC-2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_rule_cache_compiles_block_and_allow_regex():
    """Regex block_keywords and allow_keywords are compiled into CompiledPatterns (AC-2)."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["BTC|ETH"])

    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    assert "rule1" in cache.compiled_patterns
    cp = cache.compiled_patterns["rule1"]
    assert len(cp.block_patterns) == 1
    assert cp.block_patterns[0].pattern == "pump.*"
    assert len(cp.allow_patterns) == 1
    assert cp.allow_patterns[0].pattern == "BTC|ETH"


@pytest.mark.asyncio
async def test_build_rule_cache_compiles_replacement_regex():
    """Regex replacement search_text is compiled into CompiledPatterns.replacement_patterns."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="literal")  # keyword mode doesn't matter for replacement regex
    replacement = make_replacement(search="old.+new", mode="regex")

    sr, fr, rr, rep = _make_mock_repos(
        rules=[rule],
        replacements={"rule1": [replacement]},
    )
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    assert "rule1" in cache.compiled_patterns
    cp = cache.compiled_patterns["rule1"]
    assert "rr1" in cp.replacement_patterns
    assert cp.replacement_patterns["rr1"].pattern == "old.+new"


@pytest.mark.asyncio
async def test_build_rule_cache_literal_keywords_not_compiled():
    """Literal-mode keywords do NOT populate block_patterns or allow_patterns."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="literal", block=["pump"], allow=["btc"])

    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    cp = cache.compiled_patterns["rule1"]
    # Literal mode — no compiled patterns for block/allow
    assert cp.block_patterns == []
    assert cp.allow_patterns == []


@pytest.mark.asyncio
async def test_build_rule_cache_literal_replacement_not_compiled():
    """Literal-mode replacement rules do NOT populate replacement_patterns."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule()
    replacement = make_replacement(search="old", mode="literal")

    sr, fr, rr, rep = _make_mock_repos(
        rules=[rule],
        replacements={"rule1": [replacement]},
    )
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    cp = cache.compiled_patterns["rule1"]
    assert cp.replacement_patterns == {}


@pytest.mark.asyncio
async def test_build_rule_cache_patterns_compiled_with_ignorecase():
    """Compiled patterns use re.IGNORECASE flag (FR-36, FR-8 compliance)."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
    import re

    rule = make_rule(match_mode="regex", block=["TestPATTERN"])

    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    cp = cache.compiled_patterns["rule1"]
    assert cp.block_patterns[0].flags & re.IGNORECASE


# ---------------------------------------------------------------------------
# build_rule_cache — invalid regex skip and log (AC-3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_rule_cache_skips_invalid_block_regex(caplog):
    """Invalid block_keywords regex is skipped and logged as ERROR — refresh completes (AC-3)."""
    import logging
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="regex", block=["[invalid("])  # invalid regex

    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
    with _patch_repos(sr, fr, rr, rep):
        with caplog.at_level(logging.ERROR):
            cache = await build_rule_cache(MagicMock(), version=1)

    # Refresh completes — version stamped correctly
    assert cache.version == 1
    # Invalid pattern skipped — CompiledPatterns exists but block_patterns is empty
    assert "rule1" in cache.compiled_patterns
    assert cache.compiled_patterns["rule1"].block_patterns == []


@pytest.mark.asyncio
async def test_build_rule_cache_skips_invalid_allow_regex():
    """Invalid allow_keywords regex is skipped — other valid patterns still compile."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["[bad("])

    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    cp = cache.compiled_patterns["rule1"]
    # Valid block pattern compiled; invalid allow pattern skipped
    assert len(cp.block_patterns) == 1
    assert cp.allow_patterns == []


@pytest.mark.asyncio
async def test_build_rule_cache_skips_invalid_replacement_regex():
    """Invalid replacement search_text regex is skipped — refresh completes (AC-3)."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule()
    bad_replacement = make_replacement(search="[invalid(", mode="regex")

    sr, fr, rr, rep = _make_mock_repos(
        rules=[rule],
        replacements={"rule1": [bad_replacement]},
    )
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    # Refresh completes; invalid replacement pattern absent from compiled_patterns
    assert cache.version == 1
    assert cache.compiled_patterns["rule1"].replacement_patterns == {}


@pytest.mark.asyncio
async def test_build_rule_cache_valid_patterns_survive_invalid_one():
    """When one of multiple patterns is invalid, valid patterns still compile."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule = make_rule(match_mode="regex", block=["pump.*", "[invalid(", "dump.*"])

    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    cp = cache.compiled_patterns["rule1"]
    # 2 valid patterns compiled; 1 invalid skipped
    assert len(cp.block_patterns) == 2
    compiled_texts = {p.pattern for p in cp.block_patterns}
    assert "pump.*" in compiled_texts
    assert "dump.*" in compiled_texts


@pytest.mark.asyncio
async def test_build_rule_cache_invalid_regex_other_rules_unaffected():
    """An invalid pattern in one rule does not affect compilation of other rules."""
    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache

    rule_bad = make_rule(id_="rule_bad", match_mode="regex", block=["[invalid("])
    rule_good = make_rule(id_="rule_good", match_mode="regex", block=["pump.*"])

    sr, fr, rr, rep = _make_mock_repos(rules=[rule_bad, rule_good])
    with _patch_repos(sr, fr, rr, rep):
        cache = await build_rule_cache(MagicMock(), version=1)

    # Bad rule: empty block_patterns
    assert cache.compiled_patterns["rule_bad"].block_patterns == []
    # Good rule: compiled correctly
    assert len(cache.compiled_patterns["rule_good"].block_patterns) == 1


# ---------------------------------------------------------------------------
# run_cache_refresher — MongoDB failure retains last snapshot (AC-5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_cache_refresher_retains_snapshot_on_mongodb_failure():
    """On MongoDB error, CacheHolder.current retains the last valid snapshot (AC-5)."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    initial_cache = RuleCache(version=99)
    saved = CacheHolder.current
    CacheHolder.current = initial_cache

    mock_settings = MagicMock()
    mock_settings.hot_reload_interval = 0.01  # very short for test speed

    async def mock_build(db, version):
        raise Exception("MongoDB connection lost")

    with patch(
        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
        side_effect=mock_build,
    ):
        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
        await asyncio.sleep(0.05)  # Let it fail at least once
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Snapshot retained — not reset to empty
    assert CacheHolder.current.version == 99
    CacheHolder.current = saved


@pytest.mark.asyncio
async def test_run_cache_refresher_continues_after_failure():
    """After a MongoDB failure the refresher continues on the next interval (AC-5)."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    saved = CacheHolder.current
    CacheHolder.current = RuleCache(version=0)

    call_count = 0

    async def mock_build(db, version):
        nonlocal call_count
        call_count += 1
        raise Exception("transient error")

    mock_settings = MagicMock()
    mock_settings.hot_reload_interval = 0.01

    with patch(
        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
        side_effect=mock_build,
    ):
        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
        await asyncio.sleep(0.08)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Refresher looped multiple times despite repeated failures
    assert call_count >= 2
    CacheHolder.current = saved


@pytest.mark.asyncio
async def test_run_cache_refresher_version_increments_on_success():
    """Version counter increments by 1 on each successful cache build."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    saved = CacheHolder.current
    version_log: list[int] = []

    async def mock_build(db, version):
        version_log.append(version)
        return RuleCache(version=version, refreshed_at=datetime.now(timezone.utc))

    mock_settings = MagicMock()
    mock_settings.hot_reload_interval = 0.01

    with patch(
        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
        side_effect=mock_build,
    ):
        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
        await asyncio.sleep(0.08)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Versions should be sequential starting at 1
    assert version_log[0] == 1
    for i in range(1, len(version_log)):
        assert version_log[i] == version_log[i - 1] + 1

    CacheHolder.current = saved


@pytest.mark.asyncio
async def test_run_cache_refresher_swaps_cache_on_success():
    """run_cache_refresher atomically replaces CacheHolder.current on a successful build."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    saved = CacheHolder.current
    CacheHolder.current = RuleCache(version=0)

    built_cache = RuleCache(version=1, refreshed_at=datetime.now(timezone.utc))

    async def mock_build(db, version):
        return built_cache

    mock_settings = MagicMock()
    mock_settings.hot_reload_interval = 0.01

    with patch(
        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
        side_effect=mock_build,
    ):
        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # CacheHolder.current was replaced
    assert CacheHolder.current.refreshed_at is not None

    CacheHolder.current = saved


@pytest.mark.asyncio
async def test_run_cache_refresher_cancelled_error_propagates():
    """run_cache_refresher re-raises CancelledError for clean shutdown."""
    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher

    mock_settings = MagicMock()
    mock_settings.hot_reload_interval = 10.0  # long sleep

    task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
