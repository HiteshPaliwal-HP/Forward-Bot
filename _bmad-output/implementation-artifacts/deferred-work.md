# Deferred Work

This file tracks technical debt and deferred items from code reviews and implementations.

## Deferred from: code review of 1-1-initialize-project-scaffold-directory-structure (2026-06-06)

- **Default MongoDB URI Warn/Error in Production**: Add a check that prevents running with localhost MongoDB URI when in a production environment (to be addressed in Story 1.2 during database setup).
- **UI Enabled Flag verification for static files directory**: When `ui_enabled` settings is true, check if the UI's static build folder exists on start (to be addressed in Story 1.3 during web server shell setup).
- **Logging Ring-Buffer Size Default Configuration**: Evaluate logging ring buffer size constraints for high-traffic environments to prevent early log eviction (to be addressed in Story 5.2 during structured logging implementation).

## Deferred from: code review of 1-2-configure-application-settings-database-client (2026-06-06)

- **SecretRedactor risk of over-scrubbing**: If `API_KEY` or `SECRET_KEY` are very short, `SecretRedactor` might redact safe data in logs. Pre-existing risk but deferred since keys are typically long hashes.

## Deferred from: code review of 1-4-telegram-authentication-session-management (2026-06-08)

- **Session file path detection logic is duplicated**: The logic that appends `.session` if the path doesn't already end with it is copy-pasted in both `TelegramClientHolder.connect()` and `main_auth()`. Refactor into a shared helper function when touching this area again.
- **`/health/telegram` returns HTTP 200 when Telegram is disconnected**: The health endpoint always returns 200 regardless of Telegram status. For proper readiness/liveness probes, it should return 503 when disconnected. Address in the observability epic (Story 5.x).
- **`TelegramClientHolder.connect()` doesn't guard against reconnect when already connected**: If called twice concurrently, the lock protects against overlap, but sequential calls after a successful connect would re-initialize the client. Add a short-circuit guard (`if self.status == "connected": return`) when retry/reconnect logic is introduced in Epic 4.

## Pre-start notes for Epic 2 (from Epic 1 retrospective — 2026-06-09)

### Story 2.1: MongoDB Index Creation in Lifespan
The epic spec says "unique index on `telegram_id` and sparse unique index on `telegram_username` created at startup." This must be wired into the FastAPI lifespan (`app.py: default_lifespan`) before the app begins accepting source-registration requests. The dev agent for Story 2.1 must:
- Add an `ensure_indexes()` call to `default_lifespan` after MongoDB connects
- Create `sources` collection indexes: `{"telegram_id": 1}` (unique) + `{"telegram_username": 1}` (sparse unique)
- Create `source_folders` collection index: `{"name": 1}` (unique) — needed for Story 2.3 but safe to create here
- Indexes must be `background=True` to avoid blocking startup

### Story 2.1: Missing Acceptance Criterion — Telegram Disconnected During Source Registration
The epic spec does not cover what happens when `POST /api/v1/sources` is called while the Telegram client is disconnected. Story 2.1 must include this AC:

> **Given** Telegram is disconnected (status != "connected")
> **When** `POST /api/v1/sources` is called with any valid payload
> **Then** HTTP 503 is returned with `{"error": {"code": "telegram_unavailable", "message": "Telegram client is not connected. Cannot resolve source reference."}}` and no MongoDB write occurs.

### Telethon `get_entity()` Usage Notes
- Use `await client.get_entity(reference)` where reference is a username string (`"@handle"`) or integer Telegram ID
- Returns a `Channel` or `Chat` object — check `isinstance(entity, Channel)` vs `Chat` for type detection
- Raises `ValueError` for unknown references; `ChannelPrivateError` for private channels; `UsernameNotOccupiedError` for non-existent usernames — all should map to `telegram_resolve_failed` (HTTP 422)
- Rate limiting: Telegram allows ~30 resolve calls/second; safe for typical operator usage but document in dev notes

## Deferred from: code review of 3-3-atomic-rule-cache-cache-refresher.md (2026-06-18)

- ~~**Sequential O(N) database queries for replacement rules**~~: **RESOLVED** (2026-06-19, Epic 3 Retro)
  Added `ReplacementRuleRepository.list_all_replacements_for_rules(rule_ids)` — a single `$in` query that fetches all replacement rules for all active rules in one MongoDB round-trip, then groups in-memory. `build_rule_cache` now performs exactly 4 DB queries regardless of rule count (was 4+N). `cache_refresher.py` updated; tests updated in `test_cache_refresher.py`.

## Resolved during: Epic 3 Retrospective (2026-06-19)

- **`_id`/`id` Pydantic v2 serialization-alias pattern documented**: `MongoBaseModel` docstring in `api/schemas/base.py` now contains the definitive two-pattern guide (Pattern A: alias-only subclass; Pattern B: subclass with extra `@field_validator`). Common mistakes listed. Prevents recurrence of the duplicate-validator Pydantic error in Epic 6 schemas.

## Deferred from: code review of 4-1-pipeline-infrastructure-context-protocol-engine-message-mapping (2026-06-19)

- **Pagination missing in `list_sources` and `list_rules` during cache refresh**: Fetching uses a hardcoded `page_size=10000`. If limits exceed this, silent truncation occurs. (Deferred, pre-existing).
- **BSON limit risk for `$in` query in `list_all_replacements_for_rules`**: If the number of `rule_ids` grows extremely large, the `$in` clause may exceed the 16MB BSON document size limit. (Deferred, pre-existing).
# Deferred Work

This file tracks technical debt and deferred items from code reviews and implementations.

## Deferred from: code review of 1-1-initialize-project-scaffold-directory-structure (2026-06-06)

- **Default MongoDB URI Warn/Error in Production**: Add a check that prevents running with localhost MongoDB URI when in a production environment (to be addressed in Story 1.2 during database setup).
- **UI Enabled Flag verification for static files directory**: When `ui_enabled` settings is true, check if the UI's static build folder exists on start (to be addressed in Story 1.3 during web server shell setup).
- **Logging Ring-Buffer Size Default Configuration**: Evaluate logging ring buffer size constraints for high-traffic environments to prevent early log eviction (to be addressed in Story 5.2 during structured logging implementation).

## Deferred from: code review of 1-2-configure-application-settings-database-client (2026-06-06)

- **SecretRedactor risk of over-scrubbing**: If `API_KEY` or `SECRET_KEY` are very short, `SecretRedactor` might redact safe data in logs. Pre-existing risk but deferred since keys are typically long hashes.

## Deferred from: code review of 1-4-telegram-authentication-session-management (2026-06-08)

- **Session file path detection logic is duplicated**: The logic that appends `.session` if the path doesn't already end with it is copy-pasted in both `TelegramClientHolder.connect()` and `main_auth()`. Refactor into a shared helper function when touching this area again.
- **`/health/telegram` returns HTTP 200 when Telegram is disconnected**: The health endpoint always returns 200 regardless of Telegram status. For proper readiness/liveness probes, it should return 503 when disconnected. Address in the observability epic (Story 5.x).
- **`TelegramClientHolder.connect()` doesn't guard against reconnect when already connected**: If called twice concurrently, the lock protects against overlap, but sequential calls after a successful connect would re-initialize the client. Add a short-circuit guard (`if self.status == "connected": return`) when retry/reconnect logic is introduced in Epic 4.

## Pre-start notes for Epic 2 (from Epic 1 retrospective — 2026-06-09)

### Story 2.1: MongoDB Index Creation in Lifespan
The epic spec says "unique index on `telegram_id` and sparse unique index on `telegram_username` created at startup." This must be wired into the FastAPI lifespan (`app.py: default_lifespan`) before the app begins accepting source-registration requests. The dev agent for Story 2.1 must:
- Add an `ensure_indexes()` call to `default_lifespan` after MongoDB connects
- Create `sources` collection indexes: `{"telegram_id": 1}` (unique) + `{"telegram_username": 1}` (sparse unique)
- Create `source_folders` collection index: `{"name": 1}` (unique) — needed for Story 2.3 but safe to create here
- Indexes must be `background=True` to avoid blocking startup

### Story 2.1: Missing Acceptance Criterion — Telegram Disconnected During Source Registration
The epic spec does not cover what happens when `POST /api/v1/sources` is called while the Telegram client is disconnected. Story 2.1 must include this AC:

> **Given** Telegram is disconnected (status != "connected")
> **When** `POST /api/v1/sources` is called with any valid payload
> **Then** HTTP 503 is returned with `{"error": {"code": "telegram_unavailable", "message": "Telegram client is not connected. Cannot resolve source reference."}}` and no MongoDB write occurs.

### Telethon `get_entity()` Usage Notes
- Use `await client.get_entity(reference)` where reference is a username string (`"@handle"`) or integer Telegram ID
- Returns a `Channel` or `Chat` object — check `isinstance(entity, Channel)` vs `Chat` for type detection
- Raises `ValueError` for unknown references; `ChannelPrivateError` for private channels; `UsernameNotOccupiedError` for non-existent usernames — all should map to `telegram_resolve_failed` (HTTP 422)
- Rate limiting: Telegram allows ~30 resolve calls/second; safe for typical operator usage but document in dev notes

## Deferred from: code review of 3-3-atomic-rule-cache-cache-refresher.md (2026-06-18)

- ~~**Sequential O(N) database queries for replacement rules**~~: **RESOLVED** (2026-06-19, Epic 3 Retro)
  Added `ReplacementRuleRepository.list_all_replacements_for_rules(rule_ids)` — a single `$in` query that fetches all replacement rules for all active rules in one MongoDB round-trip, then groups in-memory. `build_rule_cache` now performs exactly 4 DB queries regardless of rule count (was 4+N). `cache_refresher.py` updated; tests updated in `test_cache_refresher.py`.

## Resolved during: Epic 3 Retrospective (2026-06-19)

- **`_id`/`id` Pydantic v2 serialization-alias pattern documented**: `MongoBaseModel` docstring in `api/schemas/base.py` now contains the definitive two-pattern guide (Pattern A: alias-only subclass; Pattern B: subclass with extra `@field_validator`). Common mistakes listed. Prevents recurrence of the duplicate-validator Pydantic error in Epic 6 schemas.

## Deferred from: code review of 4-1-pipeline-infrastructure-context-protocol-engine-message-mapping (2026-06-19)

- **Pagination missing in `list_sources` and `list_rules` during cache refresh**: Fetching uses a hardcoded `page_size=10000`. If limits exceed this, silent truncation occurs. (Deferred, pre-existing).
- **BSON limit risk for `$in` query in `list_all_replacements_for_rules`**: If the number of `rule_ids` grows extremely large, the `$in` clause may exceed the 16MB BSON document size limit. (Deferred, pre-existing).

## Deferred from: code review of 4-2-filter-pipeline-steps-steps-1-5.md (2026-06-21)

- **Dynamic regex compilation not cached locally when global cache is missing**: If precompiled cache is missing, it dynamically compiles `re.compile(kw)` for every keyword for every message processed. This could be a performance bottleneck under high load.

## Deferred from: code review of 4-5-telegram-worker-end-to-end-message-forwarding.md (2026-06-22)
- Add thread-safe lock for `sampling_counters` mutation [worker.py:252] — deferred, pre-existing

## Deferred from: code review of 6-1-react-spa-foundation-brand-tokens-app-layout-authentication (2026-06-25)

- **TopBar Cache Status Edge Case**: The Rules cache stale warning UI handles timestamps older than 60s, but does not explicitly handle or warn if `cacheRefreshedAt` is entirely absent or null (e.g., fresh startup).

## Deferred from: code review 6-3-dashboard-s1-settings-s8-screens.md (2026-06-25)
- [Review][Defer] ServiceVersion Fallback UX � "0.1.0" fallback masks missing version data [web/src/pages/Settings.tsx]
- [Review][Defer] Client Session Timer Resets � Timer tracks component mount time rather than true session uptime [web/src/pages/Settings.tsx]

## Deferred from: code review (6-4-forwards-list-s2-forward-edit-s3-screens.md)
- handleSelectAll only selects current page items [ForwardsList.tsx] - pre-existing typical behavior, not an immediate failure

