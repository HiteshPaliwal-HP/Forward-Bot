---
baseline_commit: NO_VCS
---

# Story 7.1: Multi-Tier Rule Cache Rebuild & Admin Refresh API

Status: done

## Story

As a Channel Operator,
I want rule changes made via the API to take effect in the forwarding pipeline instantly (<1s) and have a manual refresh endpoint as well as a background safety net,
so that configuration changes take effect immediately without needing service restarts or periodic delays.

## Acceptance Criteria

1. **Given** active Forwarding Rules and Replacement Rules exist in MongoDB,
   **When** any REST API operation mutates rules, replacement rules, sources, or folders (Create, Update, Delete, Enable, Disable),
   **Then** the system immediately triggers an asynchronous in-memory rebuild of `RuleCache` and atomically swaps `CacheHolder.current` in <1 second without blocking the API HTTP response (FR-12a).

2. **Given** the operator wants to force a cache refresh out-of-band or via the admin API,
   **When** `POST /api/v1/admin/cache/refresh` (or `/api/v1/cache/refresh`) is called,
   **Then** HTTP 200 is returned with cache metadata (`version`, `rule_count`, `source_count`, `refreshed_at` timestamp) after triggering an immediate `build_rule_cache()` call (FR-12b).

3. **Given** MongoDB is temporarily unreachable during a refresh attempt,
   **When** the periodic background refresher runs (`HOT_RELOAD_INTERVAL` default 30s),
   **Then** `CacheHolder.current` retains the last valid snapshot, logs a WARNING `cache_refresh_failed`, and retries on the next interval without crashing (FR-12c).

4. **Given** `trigger_cache_rebuild()` is executed,
   **When** an asynchronous cache rebuild finishes,
   **Then** `CacheHolder.current` is updated with `version = CacheHolder.current.version + 1` and `refreshed_at` timestamp set to current UTC datetime.

5. **Given** invalid regex patterns during cache rebuild,
   **When** pattern compilation fails,
   **Then** an ERROR `cache_pattern_compile_failed` is logged with `rule_id`, `pattern`, `field`, and `error`, skipping the invalid pattern while completing the rest of the cache rebuild normally.

## Tasks / Subtasks

- [x] Task 1: Implement `trigger_cache_rebuild()` helper in `infrastructure/cache/cache_refresher.py`
  - [x] Implement an awaitable `trigger_cache_rebuild(db)` function that fetches all collections via `build_rule_cache()` and updates `CacheHolder.current`.
  - [x] Protect the rebuild execution using a module-level `asyncio.Lock()` to serialize concurrent rebuilds, preventing duplicate versions and redundant DB reads.
  - [x] Catch any exceptions during the rebuild, log a WARNING `cache_refresh_failed`, and retain the existing snapshot to avoid crashing the background task.
  - [x] Ensure version correctly increments (`CacheHolder.current.version + 1`).

- [x] Task 2: Implement Admin Cache Refresh API Endpoint in `api/routers/admin.py`
  - [x] Define Pydantic response schema `CacheRefreshResponse` containing `version: int`, `rule_count: int`, `source_count: int`, `refreshed_at: datetime`.
  - [x] Implement `POST /api/v1/admin/cache/refresh` guarded by `Depends(get_current_operator)`.
  - [x] `await trigger_cache_rebuild(db)` inside the endpoint to execute the synchronous rebuild.
  - [x] Return the newly updated `CacheHolder.current` metadata in the response.

- [x] Task 3: Wire Cache Refresh Hooks into REST API Mutation Endpoints
  - [x] Inject FastAPI `BackgroundTasks` into all rule, replacement rule, source, and folder mutation endpoints.
  - [x] Enqueue the rebuild using `background_tasks.add_task(trigger_cache_rebuild, db)` to ensure the HTTP response completes <1s before DB hits occur. DO NOT use `asyncio.create_task()`.

- [x] Task 4: Validate Resiliency and Fault Tolerance
  - [x] Verify background periodic refresher catches exceptions and logs WARNING `cache_refresh_failed`.
  - [x] Write tests verifying regex pattern compile errors (which are *already implemented* in `build_rule_cache()`) produce `cache_pattern_compile_failed` logs without crashing the cache refresh. Do not re-implement this logic.

- [x] Task 5: Automated Testing & Verification
  - [x] Write unit tests for `trigger_cache_rebuild()` and concurrency lock in `tests/infrastructure/cache/test_cache_refresher.py`.
  - [x] Write integration test for `POST /api/v1/admin/cache/refresh` endpoint in `tests/api/routers/test_admin.py`.
  - [x] Test event-driven cache rebuilds via `BackgroundTasks` triggered by mutations via test client requests.

### Review Findings

- [x] [Review][Patch] Move asyncio.Lock() instantiation inside coroutine (or use a getter) to prevent `RuntimeError: There is no current event loop in thread` upon startup in Python 3.10+ [cache_refresher.py:173]
- [x] [Review][Patch] Fix `valid_source` missing fixture by mocking the source repo directly in the test [test_rules.py:819]
- [x] [Review][Patch] Replace undefined `make_rule_entity()` function with `make_rule()` [test_rules.py:825]
- [x] [Review][Patch] Change `mock_rule_repo.create_rule` mock to `mock_rule_repo.add_rule` to match the actual use case call in `test_rule_mutation_triggers_cache_rebuild` [test_rules.py:825]

## Dev Notes

### Architectural & Technical Requirements

- **Existing Architecture Integration**:
  - `build_rule_cache()` logic (including regex compile error handling) is already completed.
  - Only introduce `trigger_cache_rebuild(db)` and an `asyncio.Lock()` in `cache_refresher.py`.
- **Multi-Tier Caching Refresh Model**:
  - **Tier 1 (Event-Driven Instant Rebuild)**: Triggered immediately when REST API mutates entities. Enqueue via FastAPI `BackgroundTasks` (do not use `asyncio.create_task`) for non-blocking HTTP completion.
  - **Tier 2 (Manual Refresh Endpoint)**: `POST /api/v1/admin/cache/refresh`. `await` the `trigger_cache_rebuild` explicitly and return the updated cache details.
  - **Tier 3 (Periodic Fallback Coroutine)**: `run_cache_refresher()` already runs in the background. Ensure it is undisturbed.
- **Concurrency & Resiliency**:
  - `trigger_cache_rebuild` MUST catch and log its own exceptions. If a `BackgroundTask` raises, it fails silently and incorrectly.
  - Rapid successive mutations (e.g., bulk actions) must be serialized by the `asyncio.Lock()`.

### Files to UPDATE

- [forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py):
  - Add `async def trigger_cache_rebuild(db)` with an `asyncio.Lock()`.
- [forward-bot/src/forward_bot/api/routers/admin.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/admin.py):
  - Add `POST /api/v1/admin/cache/refresh` route awaiting `trigger_cache_rebuild(db)`.
- [forward-bot/src/forward_bot/api/routers/rules.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/rules.py):
  - Inject `BackgroundTasks` and use `background_tasks.add_task(trigger_cache_rebuild, db)` for rule and replacement mutations.
- [forward-bot/src/forward_bot/api/routers/sources.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py):
  - Inject `BackgroundTasks` and enqueue cache rebuild after source mutations.
- [forward-bot/src/forward_bot/api/routers/folders.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py):
  - Inject `BackgroundTasks` and enqueue cache rebuild after folder mutations.

### References

- [Epics & Stories: Epic 7 Story 7.1](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L1277-L1300)
- [Architecture: Rule Cache Management & Multi-Tier Refresh](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/architecture.md)
- [rule_cache.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py)
- [cache_refresher.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py)
- [admin.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/admin.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.6 Flash (High)

### Debug Log References

None.

### Completion Notes List

- Implemented awaitable `trigger_cache_rebuild(db)` helper guarded by module-level `asyncio.Lock()` in `cache_refresher.py`.
- Added `POST /api/v1/admin/cache/refresh` endpoint and `CacheRefreshResponse` schema in `admin.py`.
- Injected `BackgroundTasks` across all mutation routes in `rules.py`, `sources.py`, and `folders.py` to trigger non-blocking `trigger_cache_rebuild`.
- Added unit and integration tests verifying cache rebuild lock serialization, exception retention, admin refresh API endpoint, and background task enqueuing.

### File List

- [forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py)
- [forward-bot/src/forward_bot/api/routers/admin.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/admin.py)
- [forward-bot/src/forward_bot/api/routers/rules.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/rules.py)
- [forward-bot/src/forward_bot/api/routers/sources.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py)
- [forward-bot/src/forward_bot/api/routers/folders.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py)
- [forward-bot/tests/infrastructure/cache/test_cache_refresher.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/tests/infrastructure/cache/test_cache_refresher.py)
- [forward-bot/tests/api/test_admin.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/tests/api/test_admin.py)
- [forward-bot/tests/api/test_rules.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/tests/api/test_rules.py)

### Change Log

- Complete implementation of Story 7.1: Multi-Tier Rule Cache Rebuild & Admin Refresh API (Date: 2026-09-07)

