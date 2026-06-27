# Test Automation Summary — Forward Bot

**Framework:** pytest 9.0.3 + pytest-asyncio 1.4.0 (Python 3.13.3) | Vitest 4.1.9 + @testing-library/react (Node / React 19)  
**Test Suites:**
- Backend E2E Tests: [`tests/e2e/test_epic1_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic1_e2e.py), [`tests/e2e/test_epic2_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic2_e2e.py), [`tests/e2e/test_epic3_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic3_e2e.py)
- Backend API Tests: [`tests/api/test_rules.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_rules.py), [`tests/api/test_replacement_rules.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_replacement_rules.py), [`tests/api/test_folders.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_folders.py), [`tests/api/test_sources.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py), [`tests/api/test_health.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_health.py)
- Backend Repository & Client Tests: [`tests/infrastructure/mongo/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/), [`tests/infrastructure/cache/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/cache/)
- **Frontend (Epic 6) Tests:** [`web/src/hooks/useSseLog.test.ts`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/hooks/useSseLog.test.ts), [`web/src/components/shared/LogRow.test.tsx`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/shared/LogRow.test.tsx), [`web/src/components/FirstRunWizard.test.tsx`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/FirstRunWizard.test.tsx), [`web/src/pages/Logs.test.tsx`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/Logs.test.tsx), [`web/src/pages/Dashboard.test.tsx`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/Dashboard.test.tsx)

---

## Generated Tests

### Epic 1 — Project Foundation & Telegram Connectivity

#### Story 1.1 — Project Scaffold & Directory Structure
- `test_source_package_importable`: All top-level `forward_bot` modules import without error.
- `test_project_files_exist`: Critical scaffold files (`pyproject.toml`, `__init__.py`, `tests/`) exist.

#### Story 1.2 — Application Settings & MongoDB Client
- `TestSettingsValidation`: Pydantic settings loading, required fields validation, defaults (`telegram_session_path`, `media_replacement_base_dir`), and helper object conversions.
- `TestValidateSettingsHelper`: Obfuscation, whitespace validation, placeholder verification.
- `TestMongoClientHolder`: connect/close database clients lifecycle, default database name fallback.

#### Story 1.3 — FastAPI Shell, Health Endpoints & Background Tasks
- `TestHealthEndpoints`: `/health` (Liveness), `/health/telegram` (Telegram status), `/health/ready` (Readiness check with ping timeouts), Swagger `/docs`, and ReDoc `/redoc`.
- `TestBackgroundTaskStubs`: Clean cancellation/unwinding of `run_cache_refresher`, `run_mapping_sweeper`, and `run_telegram_worker`.
- `TestLifespanIntegration`: Lifespan startup failure paths, clean shutdowns canceling background tasks and closing connections.

#### Story 1.4 — Telegram Authentication & Session Management
- `TestTelegramClientHolder`: Connection states (`connected`, `disconnected`, `connecting`), user authentication invalidations, error handling (`AuthKeyUnregisteredError`, `UserDeactivatedError`, `SessionExpiredError`).
- `TestTelegramHealthEndpoint`: `/health/telegram` reflection of connected/reconnecting status.

---

### Epic 2 — Source Catalog & Folder Organization

#### E2E Workflow Test (`test_epic2_e2e_workflow`)
- Initial state verification (empty listings).
- Auth gate verification (API key and cookie validation).
- Folder CRUD flow (unique constraints, case-insensitive collision checks, debounced name availability, listing sorted alphabetically).
- Source registration flow (handling disconnected/connected Telegram client states, channel/group resolution via Telethon entity, duplicate username/id collision checks).
- Source grouping and updating (assigning to folders, validating folder existence).
- Folder details retrieval with/without embedded sources (mapping `?include=sources`).
- Self-renaming check (allowed) and conflicting renaming checks (rejected).
- Folder deletion disassociation verification (sources are detached, updating `folder_id` to `null` while preserving the source documents).

#### API Router Tests

##### Folders Router (`tests/api/test_folders.py`)
- `test_folders_endpoints_require_authentication`: Endpoints fail with 401 when no credentials are provided.
- `test_create_folder_success`: Folder creation returns 201 with generated fields.
- `test_create_folder_duplicate_rejection`: Duplicate folder name fails with 422 `folder_name_in_use`.
- `test_list_folders_success`: Retrieval returns folders sorted alphabetically with pre-calculated `source_count`.
- `test_get_folder_details_success`: Retrieves details without embedded sources.
- `test_get_folder_details_with_sources`: Retrieves folder details and embedded sources list.
- `test_get_folder_not_found`: Return 404 for invalid hex ID format or non-existent folders.
- `test_rename_folder_success` / `test_rename_folder_conflict`: Self-rename and renaming conflict checks.
- `test_delete_folder_success`: Deleting folder deletes the document and disassociates sources.

##### Sources Router (`tests/api/test_sources.py`)
- `test_sources_endpoints_require_authentication`: Checks API key auth.
- `test_get_source_success` / `test_get_source_not_found`: Retrieves registered source.
- `test_register_source_telegram_disconnected`: Fails with 503 if Telethon client is offline.
- `test_register_source_success_channel` / `test_register_source_success_group`: Registers channel/group and saves mappings.
- `test_register_source_duplicate_check`: Triggers 422 if username or Telegram ID is registered.
- `test_register_source_resolve_failed`: Triggers 422 if Telegram cannot locate the reference.
- `test_delete_source_success` / `test_delete_source_in_use_rejection`: Safe deletions, blocked with 409 if source is referenced by forwarding rules.
- `test_list_sources_success` / `test_list_sources_page_size_cap`: Pagination and maximum page limit caps (200).
- `test_list_sources_filtering`: Filter items by type (`channel`/`group`) and `folder_id` (including `"null"` for uncategorized sources).
- `test_update_source_success` / `test_patch_source_success`: Verify full PUT and partial PATCH updates.

---

### Epic 3 — Forwarding Rule Configuration

#### E2E Workflow Test (`test_epic3_e2e_workflow`)
Single comprehensive test exercising the full HTTP → use-case → MockDatabase cycle:

**Story 3.1 — Forwarding Rule CRUD:**
- Auth gate enforcement (401 without API key).
- Create rule returns 201 with all 14 default fields verified.
- Duplicate `(source_id, destination_channel)` pairs permitted (no uniqueness constraint).
- Non-existent `source_id` → 422 `source_not_found`.
- Self-referential rule by username → 422 `self_referential_rule`.
- Self-referential rule by Telegram ID string → 422 `self_referential_rule`.
- Invalid regex in `block_keywords` → 422 `invalid_regex`.
- Invalid regex in `allow_keywords` → 422 `invalid_regex`.
- Cross-midnight time window (`end_time < start_time`) accepted → 201.
- Invalid IANA timezone → 422 `invalid_timezone`.
- `media_replacement.enabled=true` + `null` path → 422 `media_replacement_path_required`.
- Get single rule 200 / not-found 404 `rule_not_found`.
- Enable rule → 200 `{ok: true}`; `is_active` becomes `true`.
- Disable rule → 200 `{ok: true}`; enable/disable on non-existent → 404.
- List rules with pagination (total, page, page_size).
- Filter by `source_id`, `is_active`, `destination_channel`.
- `page_size` capped at 200.
- PUT update with all validation rules (invalid source, invalid regex, invalid timezone, not-found).
- DELETE returns 204; cascade to replacement_rules; delete non-existent → 404.

**Story 3.2 — Replacement Rule CRUD:**
- POST to non-existent parent rule → 404 `rule_not_found`.
- Create replacement rule → 201 with all fields including `is_active=true` default.
- Invalid regex in `search_text` → 422 `invalid_regex`.
- List returns ordered by `created_at` ASC (pipeline order).
- List for non-existent parent → 404 `rule_not_found`.
- PUT update refreshes fields; invalid regex → 422; not-found → 404 `replacement_rule_not_found`.
- DELETE → 204; verify removal from listing; delete non-existent → 404.
- Auth gate for replacement-rules endpoints (401 without API key).
- Cascade delete: deleting parent rule removes all child replacement rules.

#### Story 3.3 — Atomic Rule Cache & Cache Refresher

##### RuleCache Unit Tests (`tests/e2e/test_epic3_e2e.py` + `tests/infrastructure/cache/test_rule_cache.py`)
- `test_rule_cache_is_frozen`: Mutation of frozen RuleCache raises `AttributeError`/`TypeError`.
- `test_rule_cache_empty_defaults`: `RuleCache()` with no args is version=0, all fields empty.
- `test_cache_holder_starts_with_empty_cache`: `CacheHolder.current` is empty at startup.
- `test_cache_holder_atomic_swap`: Assigning `CacheHolder.current` atomically replaces the snapshot.
- `test_compiled_patterns_empty_defaults`: `CompiledPatterns` defaults to empty lists/dict.
- `test_compiled_patterns_with_real_patterns`: `re.Pattern` objects stored and retrievable.

##### Cache Refresher Tests (`tests/e2e/test_epic3_e2e.py` + `tests/infrastructure/cache/test_cache_refresher.py`)
- `test_build_rule_cache_happy_path`: Fetches all 4 collections, builds valid `RuleCache` with correct version.
- `test_build_rule_cache_compiles_regex_patterns`: Block/allow/replacement regex patterns are pre-compiled into `CompiledPatterns`.
- `test_build_rule_cache_skips_invalid_regex`: Invalid regex skipped — `block_patterns` empty; refresh completes; version is set.
- `test_cache_refresher_retains_snapshot_on_mongodb_failure`: MongoDB failure → `CacheHolder.current` retains last valid snapshot (version unchanged).

#### API Integration Tests

##### Rules Router (`tests/api/test_rules.py`)
All 14 ACs from Story 3.1 covered with 25 tests including: happy path create with defaults, duplicate pair permitted, source not found (422), self-referential (username + telegram_id), invalid regex (block + allow), cross-midnight time window, invalid timezone, media_replacement path required, enable/disable (success + not-found), list (pagination + 4 filters), get (200 + 404), PUT (success + validations + not-found), DELETE cascade (204 + 404), auth gate.

##### Replacement Rules Router (`tests/api/test_replacement_rules.py`)
All 8 ACs from Story 3.2 covered with 10 tests including: happy path create, invalid regex rejection (POST + PUT), parent rule not found (POST + GET), list ordered ASC, update refreshes `updated_at`, delete 204, auth gate, cascade delete.

---

### Epic 6 — Web Admin Dashboard (Frontend Tests)

**Test Framework:** Vitest 4.1.9 + @testing-library/react + jsdom  
**Run command:** `npm test` (in `web/`)

#### Story 6-6 — `useSseLog` Hook (`web/src/hooks/useSseLog.test.ts`)

| Test | AC | Description |
|------|----|-------------|
| opens EventSource when enabled=true | AC6 | Connects to `/api/v1/logs/stream` |
| does NOT open EventSource when enabled=false | AC6 | EventSource gating |
| returns initial state: entries=[], isConnected=false, isError=false | AC6 | Initial state |
| sets isConnected=true and isError=false on onopen | AC6 | Connection open event |
| sets isConnected=false and isError=true on onerror | AC2/AC6 | Error state detection |
| clears isError when connection re-opens after error | AC2/AC6 | Auto-reconnect recovery |
| appends incoming SSE entries to the buffer | AC6 | Entry accumulation |
| filters out entries with timestamps <= startAfterTimestamp | AC6 | Dedup via cutoff |
| updates cutoff so replay duplicates are rejected | AC1/AC6 | Anti-duplicate on reconnect |
| ignores malformed SSE data (no crash) | AC6 | Error resilience |
| closes EventSource on unmount | AC6 | Memory leak prevention |
| sets isConnected=false when enabled becomes false | AC6 | Dynamic enabled toggle |
| opens EventSource with withCredentials=true | AC6 | Cookie auth on SSE |

**Total: 13 tests ✅**

#### Story 6-2/6-6 — `LogRow` Component (`web/src/components/shared/LogRow.test.tsx`)

| Test | Description |
|------|-------------|
| renders event label in title case | `forward_succeeded` → "Forward Succeeded" |
| renders event label for multi-word events | `pipeline_blocked` → "Pipeline Blocked" |
| renders formatted timestamp (HH:MM:SS) | `toLocaleTimeString` output |
| expands detail panel on click | Panel opens with action buttons |
| collapses detail panel on second click (state toggles) | Toggle isOpen |
| expands on Enter key press | Keyboard accessibility |
| expands on Space key press | Keyboard accessibility |
| does NOT expand on unrelated key press | Tab key ignored |
| shows Copy Correlation ID when correlation_id present | Copy button present |
| does NOT show Copy button when correlation_id absent | Conditional render |
| calls onFilterByCorrelationId with id on Filter click | AC4 — filter callback |
| does NOT show Filter button without callback | Optional prop behavior |
| shows Jump to rule link when rule_id present | AC4 — rule navigation |
| does NOT show Jump to rule when rule_id absent | Conditional render |
| renders payload preview text for entries with extra data | Inline payload preview |
| applies success border stripe for forward_succeeded | Variant CSS class |
| applies muted border stripe for pipeline_blocked | Variant CSS class |
| applies error border stripe for forward_failed | Variant CSS class |
| applies warning border stripe for flood_wait | Variant CSS class |
| applies default border stripe for unknown events | Default fallback |

**Total: 20 tests ✅**

#### Story 6-6 — `FirstRunWizard` Component (`web/src/components/FirstRunWizard.test.tsx`)

| Test | AC | Description |
|------|----|-------------|
| renders wizard dialog when open=true | AC5/AC7 | Dialog visible |
| does NOT render wizard content when open=false | AC7 | Conditional render |
| shows step 1: Register a Source on initial render | AC5 | Step 1 content |
| shows all 3 step indicators | AC5 | Step indicator UI |
| Back button is disabled on step 1 | AC5 | Navigation constraint |
| Next button advances to step 2 | AC5 | Step navigation |
| Back button from step 2 goes back to step 1 | AC5 | Back navigation |
| Next from step 2 advances to step 3 | AC5 | Step 3 content |
| shows Finish button on last step (not Next) | AC5 | Last step UI |
| "Go to Sources" navigates to /sources/new | AC5 | Step action routing |
| "Go to Forwards" navigates to /forwards/new | AC5 | Step action routing |
| "Go to Logs" navigates to /logs | AC5 | Step action routing |
| "Skip setup" calls onDismiss | AC5 | Dismiss behavior |
| "Skip setup" sets localStorage fb-first-run-dismissed=true | AC5 | Persistent dismissal |
| "Finish" on last step calls onDismiss | AC5 | Finish dismiss |
| "Finish" sets localStorage fb-first-run-dismissed=true | AC5 | Persistent dismissal |
| shows "Welcome to Forward Bot" subtitle text | AC5/AC7 | Branding text |

**Total: 17 tests ✅**

#### Story 6-6 — `Logs` Page (`web/src/pages/Logs.test.tsx`)

| Test | AC | Description |
|------|----|-------------|
| renders the System Logs heading | AC1 | Page renders |
| calls logsApi.fetchRecent(200) on mount | AC1 | Historical batch API call |
| shows "Live Feed" badge when SSE is connected | AC1 | Connection status |
| shows "Disconnected" badge when SSE is not connected | AC1/AC2 | Disconnect state |
| renders historical log entries as LogRow components | AC1 | Historical data display |
| renders SSE (live) entries merged with historical | AC1 | Merge logic |
| shows loading spinner while data is loading | AC1 | Loading state |
| shows error state when historical batch fails | AC1 | Error handling |
| shows empty state when no entries and no filters | AC1 | Empty state |
| renders "Pause Scroll" button when entries present | AC1 | Auto-scroll control |
| toggles auto-scroll: Pause → Auto Scroll on click | AC1 | Toggle functionality |
| shows "Tail Mode Enabled" when auto-scroll is active | AC1 | Footer label |
| shows DegradedBanner when SSE isError=true | AC2 | Error banner |
| does NOT show DegradedBanner when isError=false | AC2 | Conditional banner |
| renders all 4 severity filter chips | AC3 | Filter UI |
| renders Trace ID input field | AC3/AC4 | Correlation filter UI |
| filters entries by severity chip (error only) | AC3 | Client-side filter |
| shows "Clear active filters" when filter active | AC3 | Clear button UI |
| clearing filters resets visible entries | AC3 | Filter reset |
| shows "No Logs Found" with filter-specific message | AC3 | Empty filtered state |
| pre-selects severity filter from URL query param | AC3 | URL state persistence |
| shows entry count when filters active | AC3 | Count indicator |
| filters by correlation_id when typed in Trace ID input | AC4 | Correlation ID filter |
| shows clear (×) button inside Trace ID input | AC4 | Input clear UX |
| shows "Jump to forwarding rule →" link | AC4 | Rule navigation in filter bar |
| pre-selects correlation_id filter from URL | AC3/AC4 | URL state persistence |
| shows "Buffer limit: 1000 items" in footer | AC1/AC6 | Buffer info |

**Total: 27 tests ✅**

#### Story 6-6 — `Dashboard` First-Run Wizard Integration (`web/src/pages/Dashboard.test.tsx`)

| Test | AC | Description |
|------|----|-------------|
| opens First-Run Wizard when rules total=0 and localStorage not set | AC5 | Auto-open condition |
| does NOT open wizard when localStorage is "true" | AC5 | Dismissed state |
| does NOT open wizard when at least 1 rule exists | AC5 | Rules exist condition |
| calls fetchRules with page_size=1 to detect first-run | AC5 | Efficient API check |
| renders Dashboard header content | — | Basic render |

**Total: 5 tests ✅**

---

## Suite Summary & Coverage

### Backend Tests (Python / pytest)

| Test Suite | Total Passed | Description |
|------------|--------------|-------------|
| `test_epic1_e2e.py` | 52 | E2E foundation client tests |
| `test_epic2_e2e.py` | 1 | E2E complete Epic 2 workflow |
| `test_epic3_e2e.py` | 11 | E2E Epic 3 workflow + cache unit/integration |
| `test_rules.py` | 25 | Forwarding Rules HTTP API integration tests |
| `test_replacement_rules.py` | 10 | Replacement Rules HTTP API integration tests |
| `test_folders.py` | 10 | Folders HTTP API integration tests |
| `test_sources.py` | 19 | Sources HTTP API integration tests |
| `test_health.py` | 5 | Health endpoints unit tests |
| `test_client.py` | 2 | MongoClientHolder unit tests |
| `test_folder_repository.py` | 6 | Folder repository + `list_folders` tests |
| `test_source_repository.py` | 3 | Source repository database mapper tests |
| `test_rule_repository.py` | 8 | Rule repository (cascade delete, filters, join) |
| `test_replacement_repository.py` | 14 | Replacement repository mapper + edge cases |
| `test_rule_cache.py` | 10 | RuleCache / CacheHolder / CompiledPatterns |
| `test_cache_refresher.py` | 11 | build_rule_cache + run_cache_refresher |
| `test_telegram_client.py` | 5 | Telegram connection unit tests |
| `test_config.py` | 7 | Settings validation unit tests |
| **Subtotal** | **199** | |

### Frontend Tests (Vitest / React Testing Library)

| Test Suite | Total Passed | Description |
|------------|--------------|-------------|
| `useSseLog.test.ts` | 13 | SSE hook lifecycle, state, dedup, buffer |
| `LogRow.test.tsx` | 20 | Component render, expand/collapse, variant CSS, callbacks |
| `FirstRunWizard.test.tsx` | 17 | 3-step wizard, navigation, localStorage, dismiss |
| `Logs.test.tsx` | 27 | Logs page: historical+SSE merge, filters, URL state, AC1-4 |
| `Dashboard.test.tsx` | 5 | First-Run Wizard auto-open integration |
| **Subtotal** | **82** | |

---

## Total Passing Tests

| Layer | Count |
|-------|-------|
| Backend (Python/pytest) | 199 |
| Frontend (Vitest/React) | 82 |
| **Grand Total** | **281** |

---

## Test Run Results

### Backend
```
====================== 230 passed, 4 warnings in 12.27s =======================
```

### Frontend (Epic 6)
```
 ✓ src/hooks/useSseLog.test.ts (13 tests) 97ms
 ✓ src/components/shared/LogRow.test.tsx (20 tests) 981ms
 ✓ src/components/FirstRunWizard.test.tsx (17 tests) 846ms
 ✓ src/pages/Dashboard.test.tsx (5 tests) 204ms
 ✓ src/pages/Logs.test.tsx (27 tests) 1377ms

 Test Files  5 passed (5)
      Tests  82 passed (82)
   Duration  12.35s
```

---

## Next Steps

- Add Playwright E2E browser tests for full cross-browser user journey testing (login → dashboard → logs → first-run wizard).
- Run frontend tests in CI pipeline alongside backend pytest tests.
- Consider adding tests for remaining Epic 6 screens: ForwardsList, ForwardEdit, SourcesList, SourceEdit pages.
