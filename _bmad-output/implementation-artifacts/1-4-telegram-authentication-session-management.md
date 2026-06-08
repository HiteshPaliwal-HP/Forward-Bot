---
baseline_commit: 'db15da0e3381c12a2ec6263d9c60421948ad18d0'
status: 'done'
completedAt: '2026-06-08'
---

# Story 1.4: Telegram Authentication & Session Management

Status: done

## Story

As a **Channel Operator**,
I want **to authenticate to Telegram once via the CLI and have the service reconnect automatically on every restart**,
so that **I never need to log in again after the initial setup**.

## Acceptance Criteria

1. **Telegram API Settings:**
   - **Given** `telegram_api_id` and `telegram_api_hash` are added to configuration `Settings`.
   - **When** the environment variables `TELEGRAM_API_ID` (or `API_ID`) and `TELEGRAM_API_HASH` (or `API_HASH`) are set.
   - **Then** they are resolved and validated case-insensitively via Pydantic settings.

2. **Interactive CLI Authentication:**
   - **Given** API_ID, API_HASH, and TELEGRAM_SESSION_PATH are configured.
   - **When** the operator runs `python -m forward_bot auth` or `forward-bot-auth`.
   - **Then** they are prompted for phone number and SMS code (and 2FA password if enabled).
   - **And** on success, the SQLite session is persisted to `TELEGRAM_SESSION_PATH`, and the CLI exits with code 0 and a success message.

3. **CLI Error Handling:**
   - **Given** the interactive authentication fails (invalid credentials, network error, wrong code).
   - **When** the command exits.
   - **Then** the process returns a non-zero exit code (1) and logs/prints an actionable error message.
   - **And** no partial session files remain at `TELEGRAM_SESSION_PATH`.
   - **And** no secret values (phone, password, api key) are logged or printed in errors.

4. **Auto-Reconnection at Startup:**
   - **Given** a valid session file exists at `TELEGRAM_SESSION_PATH`.
   - **When** the FastAPI application starts.
   - **Then** `TelegramClient` connects automatically without operator interaction.
   - **And** `/health/telegram` returns `{"telegram": "connected", "last_event": null}` within 30 seconds.

5. **Auto-Reconnection at Restart:**
   - **Given** the service is running and connected.
   - **When** the container or process is restarted.
   - **Then** it automatically reconnects using the persisted SQLiteSession.

6. **Server-Side Session Invalidation:**
   - **Given** Telegram invalidates the session server-side.
   - **When** the application starts or attempt to use the session.
   - **Then** the service logs a CRITICAL event: `telegram_session_invalidated` and exits cleanly.
   - **And** no secrets are printed in any log lines.

7. **Health Endpoint connection:**
   - **Given** the health router is mounted.
   - **When** `GET /health/telegram` is requested.
   - **Then** it returns the actual status (`connected` | `disconnected` | `reconnecting`) and the ISO timestamp of the `last_event`.

## Dev Notes

- **Interactive CLI:** Implemented `run_auth()` inside `src/forward_bot/__main__.py`, utilizing Telethon's connection flow and sign-in handlers.
- **State Holder:** Created `TelegramClientHolder` in `src/forward_bot/infrastructure/telegram/client.py` as a singleton to manage connectivity status, client reference, and invalidation handlers.
- **Graceful Shutdown:** Configured the invalidation handler to send a `SIGTERM` signal using `os.kill(os.getpid(), signal.SIGTERM)` to trigger uvicorn's native clean shutdown.
- **Script Registration:** Registered the script entry point `forward-bot-auth` in `pyproject.toml`.

## Tasks / Subtasks

- [x] Configure Telegram API settings (`telegram_api_id`, `telegram_api_hash`) in `config.py` (AC: 1)
- [x] Document credentials in `.env.example` and update `.env` (AC: 1)
- [x] Implement connection state manager `TelegramClientHolder` (AC: 4, 5, 6, 7)
- [x] Implement CLI interactive authentication tool `run_auth` (AC: 2, 3)
- [x] Register `forward-bot-auth` in `pyproject.toml` (AC: 2)
- [x] Integrate Telegram connection into FastAPI lifespan context manager (AC: 4, 5, 6)
- [x] Connect `/health/telegram` to real state (AC: 7)
- [x] Update test suites and write unit tests for the connection manager

### Review Findings

- [x] [Review][Decision] **Session invalidation shutdown strategy** — Resolved: option 3 chosen — `os.kill(SIGTERM)` removed; `_handle_session_invalidated` now logs CRITICAL and raises `RuntimeError`, which propagates through FastAPI lifespan for a clean exit [client.py:108]
- [x] [Review][Patch] **`python -m forward_bot auth` broken — nested `asyncio.run()` raises RuntimeError** — Fixed: `main()` now calls `await main_auth()` directly [__main__.py:44]
- [x] [Review][Patch] **`last_event` field never updated — always `null`** — Fixed: `last_event` now set to UTC ISO timestamp on connect, disconnect, and invalidation events [client.py:22]
- [x] [Review][Patch] **Dead code `lifespan` in `__main__.py` overrides `default_lifespan`** — Fixed: local `lifespan` function removed; `create_app(settings)` now uses `default_lifespan` from `app.py` which handles both MongoDB and Telegram [__main__.py]
- [x] [Review][Patch] **Auth CLI error message may leak Telethon exception details including phone number** — Fixed: generic message printed; exception type logged via structlog [__main__.py:154]
- [x] [Review][Patch] **Unused imports in `client.py`** — Fixed: removed `os`, `sys`, `signal`, `Any`; added `datetime`, `timezone` [client.py:1-9]
- [x] [Review][Defer] **Session file path logic duplicated** [client.py:38-40, __main__.py:104-106] — deferred, pre-existing design, refactor candidate for a later story
- [x] [Review][Defer] **`/health/telegram` returns HTTP 200 when disconnected** [health.py:35-41] — deferred, AC-7 doesn't mandate HTTP status codes; address in observability epic
- [x] [Review][Defer] **`connect()` doesn't guard against reconnect-if-already-connected** [client.py:30] — deferred, no retry/reconnect logic in scope for this story

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Completion Notes

- Created `TelegramClientHolder` connection manager inside `src/forward_bot/infrastructure/telegram/client.py` using Telethon `TelegramClient` with full authentication and session verification.
- Added `telegram_api_id` and `telegram_api_hash` configuration fields to `Settings` in `src/forward_bot/config.py` mapping to alias variants.
- Implemented `run_auth()` in `src/forward_bot/__main__.py` facilitating interactive SMS and 2FA password prompting, clean session file disposal on failure, and CLI error handling.
- Registered script entrypoint `forward-bot-auth` under `[project.scripts]` in `pyproject.toml`.
- Linked the `/health/telegram` router inside `src/forward_bot/api/routers/health.py` to retrieve actual connection status and last event timestamp.
- Updated `tests/test_config.py` to isolate settings tests and written mock-based tests inside `tests/infrastructure/telegram/test_telegram_client.py` verifying state transitions.

### File List

- [NEW] [client.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/telegram/client.py)
- [MODIFY] [__init__.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/telegram/__init__.py)
- [MODIFY] [config.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/config.py)
- [MODIFY] [__main__.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/__main__.py)
- [MODIFY] [app.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py)
- [MODIFY] [health.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/health.py)
- [MODIFY] [pyproject.toml](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/pyproject.toml)
- [MODIFY] [test_config.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/test_config.py)
- [NEW] [test_telegram_client.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/telegram/test_telegram_client.py)
- [MODIFY] [.env.example](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/.env.example)
- [MODIFY] [.env](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/.env)

## Change Log

| Date | Description |
|------|-------------|
| 2026-06-08 | Implemented `TelegramClientHolder` singleton (`client.py`) with connect/disconnect/session-invalidation logic (AC 4–7) |
| 2026-06-08 | Added `telegram_api_id` and `telegram_api_hash` to `Settings` with `AliasChoices` for env aliases `API_ID`/`API_HASH` (AC 1) |
| 2026-06-08 | Implemented `run_auth()` / `main_auth()` interactive CLI in `__main__.py` with phone+SMS+2FA flow, session cleanup on failure, and exit-code handling (AC 2–3) |
| 2026-06-08 | Registered `forward-bot-auth` script entry point in `pyproject.toml` (AC 2) |
| 2026-06-08 | Integrated Telegram `connect`/`disconnect` into FastAPI `default_lifespan` in `app.py` (AC 4–5) |
| 2026-06-08 | Wired `/health/telegram` endpoint to live `telegram_client.status` and `last_event` (AC 7) |
| 2026-06-08 | Added 5 unit tests in `tests/infrastructure/telegram/test_telegram_client.py`; updated `tests/test_config.py` to cover Telegram fields |
| 2026-06-08 | All 19 tests pass with no regressions |
