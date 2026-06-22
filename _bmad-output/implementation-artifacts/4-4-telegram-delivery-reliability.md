---
baseline_commit: febe1dd
---
# Story 4.4: Telegram Delivery & Reliability

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want the service to handle Telegram rate limits and transient errors gracefully, retrying failed deliveries without crashing the pipeline for other rules,
so that my 99% reliability target is met even under adverse Telegram API conditions.

## Acceptance Criteria

1. **Successful Delivery (Step 17 & 18 Integration):**
   - **Given** a processed `PipelineContext` is ready for delivery (Step 17).
   - **When** `DeliverStep.apply()` runs.
   - **Then** it delegates to `delivery.py` which sends the message to the target channel (using username or numeric ID resolved as integer) via the Telethon client (`telegram_client.client`).
   - **And** captures the returned `destination_message_id` and `destination_channel_id` and stores them in `ctx.metadata`.
   - **And** subsequent `PersistMappingStep` (Step 18) persists the mapping using `mapping_repository.add_mapping(...)`.

2. **FloodWait Handling:**
   - **Given** Telegram returns a `FloodWaitError` (imported from `telethon.errors`) with a wait duration (e.g. `e.seconds`).
   - **When** the delivery function is invoked.
   - **Then** it logs a warning event `{"event": "flood_wait", "wait_seconds": N, "rule_id": "...", "correlation_id": "..."}` at WARNING.
   - **And** pauses execution using `await asyncio.sleep(e.seconds)` before retrying delivery.
   - **And** this FloodWait retry does NOT count against the transient error retry budget.
   - **And** if `e.seconds` exceeds a sensible maximum threshold (e.g. 300 seconds), it does not wait indefinitely, but rather logs an error and propagates the exception to abort the pipeline run for this rule to prevent hanging in memory.

3. **Transient Telegram Errors (Exponential Backoff):**
   - **Given** a transient Telegram connection/timeout error occurs (specifically `ConnectionError`, `asyncio.TimeoutError`, or `telethon.errors.RPCError`).
   - **When** delivery fails.
   - **Then** it retries delivery with exponential backoff using `delivery_base_delay * (delivery_backoff_factor ** (attempt - 1))`.
   - **And** logs a warning event `{"event": "delivery_transient_error", "attempt": X, ...}` on each failure.
   - **And** if the failures persist and exhaust the `delivery_max_retries` budget, it logs an error event `{"event": "forward_failed", "rule_id": "...", "correlation_id": "...", "error": "..."}` at ERROR and propagates the exception to abort the pipeline run for this rule.

4. **Exception and Failure Isolation (Per-Rule):**
   - **Given** one rule's pipeline execution raises an unhandled exception or delivery fails.
   - **When** multiple rules are evaluated for the same Source Message.
   - **Then** the exception is caught and isolated at the per-rule level in `PipelineEngine.execute`.
   - **And** other rules' pipeline runs continue unaffected.

5. **SIGTERM/SIGINT Graceful Shutdown (FR-25):**
   - **Given** the service receives a SIGTERM or SIGINT shutdown signal.
   - **When** the pipeline is executing a delivery network call.
   - **Then** the critical network execution should be shielded (e.g., using `asyncio.shield` for the actual send operation) or designed to rely on the application lifespan awaiting active tasks with a timeout before cancellation, ensuring that in-flight pipeline runs finish successfully rather than dropping the message permanently.

## Tasks / Subtasks

- [x] **1. Configuration Enhancements**
  - [x] Update `src/forward_bot/config.py` to add settings:
    - `delivery_max_retries` (int, default: 3)
    - `delivery_backoff_factor` (float, default: 2.0)
    - `delivery_base_delay` (float, default: 1.0)
  - [x] Add these properties with comments to `forward-bot/.env.example`.
- [x] **2. Delivery Implementation**
  - [x] Create `src/forward_bot/infrastructure/telegram/delivery.py` to handle pure network communication and retry loops:
    - `async def deliver_message(client, ctx, settings) -> tuple[int, int]` implementing the delivery retry loop.
    - Explicitly import `FloodWaitError` and `RPCError` from `telethon.errors`.
    - Handling of `FloodWaitError` with logging (`"flood_wait"`) and `asyncio.sleep` (capping sleep to a sensible maximum threshold, e.g. 300s, to prevent memory hanging).
    - Handling of transient errors (`ConnectionError`, `asyncio.TimeoutError`, `telethon.errors.RPCError`) with exponential backoff logging (`"delivery_transient_error"`) and `asyncio.sleep`.
    - Exceeded retry budget logging (`"forward_failed"`) and propagation.
    - Identification of destination entity (resolving string IDs like `"-10012345678"` to integer entity).
    - Dispatch of file-based messages using `client.send_message(..., message=ctx.caption, file=ctx.media)` when `ctx.media` is present (converting `Path` objects to string).
    - Dispatch of text-only messages using `client.send_message(..., message=ctx.text)` when `ctx.media` is None.
    - Passing `reply_to=ctx.reply_target_destination_id` to `client.send_message`.
  - [x] Refactor `src/forward_bot/application/pipeline/steps/deliver.py` to handle domain orchestration:
    - Retrieve application settings by importing `get_settings` from `src.forward_bot.config` and invoking it (e.g., inside `apply()`).
    - Map the domain context properties to the parameters needed by `deliver_message`.
    - Import and call `deliver_message` using the global `telegram_client.client` instance and the retrieved settings.
    - Store returned message ID and chat ID into `ctx.metadata["destination_message_id"]` and `ctx.metadata["destination_channel_id"]`.
- [x] **3. Testing**
  - [x] Create unit tests in `tests/application/pipeline/steps/test_deliver.py`:
    - [x] Verify `DeliverStep` delegates to `deliver_message`, populates metadata correctly on success, and handles step failure gracefully.
  - [x] Create tests in `tests/infrastructure/telegram/test_delivery.py`:
    - [x] Test `deliver_message` success scenario.
    - [x] Test `deliver_message` with `FloodWaitError` (verifying warning logs and wait execution).
    - [x] Test `deliver_message` with transient connection/timeout errors and RPC errors (verifying backoff delays and final failure/exception propagation).
  - [x] Update `tests/application/pipeline/test_engine.py` (specifically `test_engine_default_steps_execution` and `test_engine_steps_6_to_16_integration`):
    - [x] Mock/patch the global `telegram_client.client` during execution to prevent attempts to connect to a real Telegram server.
### Review Findings

- [x] [Review][Patch] Incorrect instantiation of `telethon.errors.RPCError` [src/forward_bot/infrastructure/telegram/delivery.py:59]
- [x] [Review][Patch] Unhandled `TypeError` during Entity Casting [src/forward_bot/infrastructure/telegram/delivery.py:28]
- [x] [Review][Patch] Exception handling location contradicts AC 4 [src/forward_bot/application/pipeline/steps/deliver.py:22]
- [x] [Review][Patch] FloodWait cap propagates exception instead of gracefully aborting pipeline via PipelineEngine [src/forward_bot/infrastructure/telegram/delivery.py:82]

## Dev Notes

- **Avoiding Blocking IO in delivery retry loop:**
  - Always use `asyncio.sleep` (never `time.sleep`) for delays to avoid blocking the single-threaded asyncio event loop.
- **Handling Entity Conversion safely:**
  - Always convert string representation of channel IDs (e.g. `"-10012345"`) to python `int` before passing to Telethon to avoid string resolution issues.
- **Correct Log Events:**
  - Emitted log event keys must be exactly:
    - `flood_wait` (WARNING level)
    - `delivery_transient_error` (WARNING level)
    - `forward_failed` (ERROR level)
- **Do not catch `BaseException`:**
  - Ensure the try-except blocks catch `Exception` but let `asyncio.CancelledError` propagate to facilitate graceful shutdown during container exits.

### Project Structure Notes

- New modules must follow clean architecture guidelines, with `infrastructure/telegram/delivery.py` executing client commands and `application/pipeline/steps/deliver.py` encapsulating the application step.

### References

- [Functional Requirements FR-22, FR-23, FR-24, FR-25 in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L840)
- [Architecture Guidelines in architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L53)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Debug Log References

- Passed all 319 unit and integration tests under `forward-bot/tests` locally.

### Completion Notes List

- Added configuration settings for delivery retry logic: `delivery_max_retries`, `delivery_backoff_factor`, and `delivery_base_delay`.
- Created `src/forward_bot/infrastructure/telegram/delivery.py` implementing message delivery retry loop.
- Added support for both file-based and text-only dispatch, replies (`reply_to`), and numeric/string entity parsing.
- Incorporated `FloodWaitError` handling with logging and `asyncio.sleep` (capped to 300s maximum threshold).
- Handled transient connection/timeout/RPC errors using exponential backoff retries.
- Wrapped delivery calls in `asyncio.shield` to protect network calls against premature SIGTERM cancellation.
- Refactored `DeliverStep` in `deliver.py` to retrieve config settings and invoke `deliver_message`.
- Created comprehensive unit tests for `DeliverStep` and `deliver_message` retry loops.
- Patched Telethon client in pipeline engine tests to prevent network dependencies.

### File List

- [config.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/config.py)
- [.env.example](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/.env.example)
- [delivery.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/telegram/delivery.py)
- [deliver.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/application/pipeline/steps/deliver.py)
- [test_config.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/test_config.py)
- [test_deliver.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/application/pipeline/steps/test_deliver.py)
- [test_delivery.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/telegram/test_delivery.py)
- [test_engine.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/application/pipeline/test_engine.py)
