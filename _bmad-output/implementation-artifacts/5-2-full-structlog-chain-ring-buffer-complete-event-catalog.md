---
baseline_commit: cdb08128d1456802da67398bb7897ef266c3b84e
---
# Story 5.2: Full Structlog Chain, Ring Buffer & Complete Event Catalog

Status: done

## Story

As a **Channel Operator**,
I want every pipeline event logged as structured JSON with a correlation ID so I can trace any message's full journey,
so that I can diagnose any issue from logs alone without restarting or instrumenting the service.

## Acceptance Criteria

1. **Structured Log Chain Configuration (AC-1):**
   - **Given** structlog is fully configured.
   - **When** any log event is emitted in the system.
   - **Then** the processor chain executes in this order: `merge_contextvars` → `add_log_level` → `TimeStamper(fmt="iso")` → `SecretRedactor` → `append_to_ring_buffer` → `JSONRenderer`.
   - **And** every event includes `event`, `level`, `timestamp`, and `correlation_id` fields.
   - **And** output is newline-delimited JSON on stdout.

2. **Log Ring Buffer & Fan-out (AC-2):**
   - **Given** `append_to_ring_buffer` is wired into the processor chain.
   - **When** a log event is processed.
   - **Then** the event dict is appended to the in-process `collections.deque(maxlen=N)` where `N` is derived from `LOG_RING_BUFFER_HOURS` settings (specifically, `max(1000, log_ring_buffer_hours * 3600)` to ensure sufficient sizing).
   - **And** the same event is fanned out to all active SSE subscriber `asyncio.Queue` objects in the fan-out set.

3. **Eviction Behavior (AC-3):**
   - **Given** the ring buffer is full.
   - **When** a new event is appended.
   - **Then** the oldest entry is automatically evicted (standard deque behavior).
   - **And** the ring buffer never blocks the logging process or raises an error.

4. **Event Catalog Compliance (AC-4):**
   - **Given** any pipeline event occurs.
   - **When** the event is logged.
   - **Then** the event name must exactly match a snake_case string in the event catalog:
     - Ingestion & Routing: `source_registered`, `source_resolved`, `telegram_resolve_failed`, `folder_created`
     - Engine & Pipeline: `pipeline_blocked`, `forward_succeeded`, `reply_parent_not_found`, `reply_target_missing`, `media_replacement_failed`
     - Sync & Sweeper: `edit_propagated`, `delete_propagated`, `mapping_sweep_completed`
     - Infrastructure: `telegram_session_invalidated`, `flood_wait`, `cache_refresh_failed`, `source_already_exists`
     - Server / Lifecycle: `server_starting`, `server_interrupted`, `app_starting`, `app_stopping`, `app_stopped`, `mongodb_connected`, `mongodb_connection_failed`, `mongodb_startup_check_failed`, `mongodb_indexes_created`, `mongodb_index_creation_failed`, `telegram_connection_failed`

5. **Secrets Redaction Compliance (AC-5):**
   - **Given** any log output is generated or saved to the ring buffer.
   - **When** the log is inspected.
   - **Then** no log line or event dict contains `API_KEY` value, `SECRET_KEY` value, session file bytes, or any other secret credentials.
   - **And** `SecretRedactor` replaces them with `[REDACTED]` (or `[REDACTED_BYTES]` for bytes).

6. **Initialization Lifecycle (AC-6):**
   - **Given** the FastAPI application is starting up.
   - **When** `main.py` is loaded by Uvicorn.
   - **Then** `setup_logging` is called before the FastAPI `app` instance is initialized or `create_app` is executed, ensuring uvicorn and app startup logs are structured correctly.

## Tasks / Subtasks

- [x] **1. Create in-memory Ring Buffer module** (AC: 2, 3)
  - [x] Implement `infrastructure/logging/ring_buffer.py`
  - [x] Define global `_ring_buffer: deque` and `init_ring_buffer(hours: float) -> None`
  - [x] Implement `append_to_ring_buffer(logger, method_name, event_dict) -> dict` as a structlog processor that copies the dict and appends it to the deque
  - [x] Implement `get_recent_logs() -> list` to return chronological log records
- [x] **2. Create SSE Broadcaster module** (AC: 2)
  - [x] Implement `infrastructure/logging/sse_broadcaster.py`
  - [x] Define global fan-out set `_subscribers: set[asyncio.Queue]`
  - [x] Implement `register_subscriber(queue: asyncio.Queue) -> None`
  - [x] Implement `unregister_subscriber(queue: asyncio.Queue) -> None`
  - [x] Implement `broadcast_log(event: dict) -> None` that iterates over subscribers and calls `put_nowait` (handling `QueueFull` safely)
- [x] **3. Extract setup.py and update existing logging logic** (AC: 1, 5)
  - [x] Create `infrastructure/logging/setup.py`
  - [x] Move the *existing* `SecretRedactor` class and `setup_logging` function from `__init__.py` to `setup.py`
  - [x] **CRITICAL:** Preserve the existing `SecretRedactor` logic that prevents short-key over-scrubbing (skips redaction for keys < 6 chars)
  - [x] Update `setup_logging` to initialize the ring buffer
  - [x] Inject `append_to_ring_buffer` into the existing processor chain: `... → TimeStamper → SecretRedactor → append_to_ring_buffer → JSONRenderer`
- [x] **4. Refactor logging packaging (`__init__.py`)** (AC: 1-5)
  - [x] Update `infrastructure/logging/__init__.py` to import and export `setup_logging`, `logger`, `get_recent_logs`, and broadcaster helper functions (`register_subscriber`, `unregister_subscriber`)
- [x] **5. Initialize logging early on startup** (AC: 6)
  - [x] Update `src/forward_bot/main.py` to call `setup_logging(settings)` prior to instantiating/creating `app`
- [x] **6. Run Event Catalog & Secrets audit** (AC: 4, 5)
  - [x] Audit the codebase to ensure all occurrences of `logger.info`, `logger.error`, `logger.critical`, etc., use consistent event catalog keys and do not leak credentials
- [x] **7. Write tests and verify** (AC: 1-6)
  - [x] Implement tests in `tests/infrastructure/logging/test_logging.py`
  - [x] Verify ring buffer size derivation, eviction, and queue fan-out
  - [x] Verify `SecretRedactor` replaces configured secrets and bytes
  - [x] Verify early initialization works and does not raise exceptions

## Dev Notes

- **Collections Deque thread safety**: `append()` on a `collections.deque` is atomic and thread-safe under the Python GIL. Since FastAPI and Telethon run within a single event loop thread, using deque directly is safe.
- **Queue Put in Processor**: When logging an event, the `broadcast_log` function is called inside the structlog logging flow, which runs synchronously. Since `asyncio.Queue.put_nowait` is a synchronous method that appends to a queue's internal list, it is safe to call from a synchronous context inside the event loop thread.
- **Secrets Redactor Placement & Logic**: Always place `SecretRedactor` *before* `append_to_ring_buffer` in the structlog processor chain. Ensure you preserve its existing logic that skips redaction for keys under 6 characters to prevent over-scrubbing.
- **Uvicorn log interception (Optional/Info)**: Uvicorn standard logging will still output to stderr/stdout with its default format. We only configure the application's `structlog` logger.

### Project Structure Notes

- Keep all logging logic enclosed in `src/forward_bot/infrastructure/logging/`.

### References

- [Functional Requirements FR-26, FR-27, FR-28 in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md)
- [Architecture Decision A2, I1, I2, I5 in architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- None

### Completion Notes List

- Designed and implemented `infrastructure/logging/ring_buffer.py` to maintain a thread-safe, in-process, non-blocking log history capped dynamically based on `log_ring_buffer_hours`.
- Created `infrastructure/logging/sse_broadcaster.py` to support real-time log event fan-out using subscriber queues.
- Moved and refactored structured logging setup and the existing `SecretRedactor` logic (with the <6 characters protection check preserved) to `infrastructure/logging/setup.py`.
- Replaced the packaging of the logging module (`__init__.py`) to export public APIs properly.
- Updated early initialization lifecycle in `src/forward_bot/main.py` so that structured logging is configured prior to FastAPI app instantiation.
- Audited and updated event catalog logging across routing/resolution events to ensure strict catalog compliance and introduced duplicate source check warnings.
- Wrote and executed comprehensive unit tests in `tests/infrastructure/logging/test_logging.py` validating ring buffer capacity, eviction, SSE fan-out, secrets redaction, and early lifespan startup.

### File List

- [ring_buffer.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/logging/ring_buffer.py) [NEW]
- [sse_broadcaster.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/logging/sse_broadcaster.py) [NEW]
- [setup.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/logging/setup.py) [NEW]
- [__init__.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/logging/__init__.py) [MODIFY]
- [main.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/main.py) [MODIFY]
- [delivery.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/telegram/delivery.py) [MODIFY]
- [register_source.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/application/sources/register_source.py) [MODIFY]
- [test_logging.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/logging/test_logging.py) [MODIFY]

### Change Log

- Implemented structured logging chain, global in-process ring buffer, SSE broadcasting mechanism, and integrated with early FastAPI lifecycle. (Date: 2026-06-23)

### Review Findings

- [x] [Review][Decision] Memory Leak in SSE Broadcaster — `_subscribers` set never unregisters clients if they disconnect unexpectedly. Should we defer this to the upcoming SSE API endpoint story (5-3) or handle it now?
- [x] [Review][Patch] Local Import Overhead [`forward_bot/infrastructure/logging/ring_buffer.py`] — `from ...sse_broadcaster import broadcast_log` inside `append_to_ring_buffer` executes on every log line.
- [x] [Review][Patch] Application Instantiation Side Effect [`forward_bot/main.py`] — `settings = Settings()` and `setup_logging(settings)` execute at module import time, which can break test suites mocking env vars.
- [x] [Review][Patch] Overflow Edge Case [`forward_bot/infrastructure/logging/ring_buffer.py`] — `init_ring_buffer` casts `hours * 3600` to `int()`. If configured too high, it raises `OverflowError`. Add a max cap.
