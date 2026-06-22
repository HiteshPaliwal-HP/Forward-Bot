---
baseline_commit: febe1dd
---
# Story 4.5: Telegram Worker & End-to-End Message Forwarding

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want the service to automatically monitor my registered sources and forward qualifying messages as they arrive,
so that forwarding is fully automatic — I configure the rules and the service does the rest.

## Acceptance Criteria

1. **Worker Lifecycle & Dynamic Subscriptions:**
   - **Given** active Forwarding Rules reference registered sources in `RuleCache`.
   - **When** the Telegram worker starts.
   - **Then** the worker issues `JoinChannelRequest` (or `ImportChatInviteRequest` if applicable) for any newly active channel/group sources to ensure it receives messages.
   - **And** registers a **single global** Telethon `NewMessage` event handler, filtering incoming events dynamically against the active sources in the `RuleCache` snapshot.
   - **And** dynamically updates subscriptions if rules or sources change in the `RuleCache` snapshot on subsequent reload cycles.

2. **Ingestion, Dispatch, and Context Isolation:**
   - **Given** a new message arrives in a subscribed source.
   - **When** the worker's event handler fires.
   - **Then** a short `correlation_id` (8-character hex string) is generated.
   - **And** `correlation_id`, `source_id`, and `message_id` are bound to `structlog.contextvars` for full observability.
   - **And** `cache_holder.current` is read exactly once as the snapshot for this dispatch.
   - **And** for each active rule whose `source_id` matches, the pipeline engine `execute()` is called independently.
   - **And** if pipelines run concurrently for multiple rules, the worker MUST use `contextvars.copy_context().run()` to prevent context variable leakage between runs.
   - **And** `structlog` contextvars are cleared after the dispatch completes.

3. **Structured Event Logging:**
   - **Given** the pipeline engine finishes executing a rule.
   - **When** the worker inspects the result (a `BlockedOutcome` or `PipelineContext`).
   - **Then** the worker explicitly emits `{"event": "pipeline_blocked", "reason": "<reason>", "rule_id": "...", "correlation_id": "..."}` at INFO level if blocked.
   - **And** emits `{"event": "forward_succeeded", "rule_id": "...", "source_message_id": N, "destination_message_id": N, "correlation_id": "..."}` at INFO level if successful.
   - **And** no secrets, session bytes, or credentials appear in any log output.

4. **In-Memory Sampling State:**
   - **Given** `SAMPLING_PERSIST=false` (default).
   - **When** the worker starts.
   - **Then** an in-memory `{rule_id: int}` counter dict is initialized and passed in `PipelineContext.metadata["sampling_counters"]` to persist counters across messages during the process lifetime.

5. **Performance and Non-blocking I/O:**
   - **Given** 100 active sources with normal traffic.
   - **When** the worker is running.
   - **Then** P95 forwarding latency from source message receipt to destination post is ≤ 3 seconds.
   - **And** no blocking I/O is performed in the worker or pipeline (any blocking file/database calls must use `asyncio` or `asyncio.to_thread()`).

6. **Lifespan Integration & Graceful Shutdown:**
   - **Given** the FastAPI application is initialized.
   - **When** lifespan starts.
   - **Then** `run_telegram_worker` replaces the stub task from Story 1.3.
   - **And** on shutdown, the task cancels and awaits cancellation gracefully before disconnecting Telegram and closing MongoDB.

## Tasks / Subtasks

- [x] **1. Worker Infrastructure & Lifespan Integration** (AC: 1, 6)
  - [x] Create `src/forward_bot/infrastructure/telegram/worker.py` containing the `TelegramWorker` class.
  - [x] Implement `TelegramWorker` to read `CacheHolder.current` and manage event listeners for active sources.
  - [x] Implement dynamic subscription reload checking if active sources changed on each loop interval.
  - [x] Update `src/forward_bot/tasks.py` to run the real worker loop (checking every `HOT_RELOAD_INTERVAL` seconds).
  - [x] Update `src/forward_bot/app.py` default lifespan to pass `settings` and `mongo_client.db` dependencies to `run_telegram_worker()`.
- [x] **2. Message Event Handling & Pipeline Dispatch** (AC: 2, 4, 5)
  - [x] Implement a global Telethon `NewMessage` event callback in `TelegramWorker`.
  - [x] Bind `correlation_id`, `source_id`, and `message_id` to `structlog` contextvars.
  - [x] Capture the atomic `RuleCache` snapshot at the beginning of message processing.
  - [x] For each matching rule, execute the pipeline engine independently (using `copy_context().run()` if concurrent).
  - [x] Initialize and pass the `sampling_counters` dict to the pipeline context.
  - [x] Clear contextvars when dispatch finishes.
- [x] **3. Structured Logging & Security** (AC: 3)
  - [x] Log `pipeline_blocked` event with correct schema at INFO level.
  - [x] Log `forward_succeeded` event with correct schema at INFO level.
  - [x] Ensure no secret API keys, session details, or credentials are logged.
- [x] **4. Automated Testing** (AC: 1-6)
  - [x] Create unit/integration tests in `tests/infrastructure/telegram/test_worker.py`.
  - [x] Mock Telethon client, events, and repositories to test dynamic registration, dispatch, logging, and error isolation.
  - [x] Run full test suite `pytest` to verify all tests pass with no regressions.

## Technical Requirements

- **Telethon Client Lifecycle:** The worker task MUST await `telegram_client.client.run_until_disconnected()` inside a `try...except asyncio.CancelledError` block to ensure correct graceful shutdown upon SIGINT/SIGTERM, rather than using an arbitrary polling loop.
- **Dynamic Telethon Event Handlers:** Do NOT register an event handler per source. Register ONE global handler on `events.NewMessage` and filter dynamically against the `RuleCache` snapshot (checking if `event.chat_id` or username matches).
- **Group/Channel Uniform IDs:** Resolve source references correctly, noting that Telegram channel IDs are often negative integers in Telethon.

### Project Structure Notes

- Worker class resides in `src/forward_bot/infrastructure/telegram/worker.py`.
- Background task wrapper resides in `src/forward_bot/tasks.py`.
- Tests are co-located in `tests/infrastructure/telegram/test_worker.py`.

### References

- [Functional Requirements FR-9, FR-10, FR-11, FR-12, FR-22, FR-23, FR-24, FR-25 in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L872)
- [Architecture Guidelines in architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L490)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- Mock tests output: 6 passed, 0 failed in `tests/infrastructure/telegram/test_worker.py`
- Complete tests suite output: 325 passed, 0 failed in `pytest`

### Completion Notes List

- ✅ Resolved the existing regression test failure in `DeliverStep`.
- ✅ Implemented the real `TelegramWorker` with global Telethon events monitoring and dynamic reloads.
- ✅ Isolated execution scopes of concurrent forwarding rules via `contextvars.copy_context().run()`.
- ✅ Passed and mutated in-memory `sampling_counters` to support local sampling state.
- ✅ Added 6 new unit/integration tests to ensure robust validation.

### File List

- `src/forward_bot/application/pipeline/steps/deliver.py`
- `src/forward_bot/infrastructure/telegram/worker.py`
- `src/forward_bot/tasks.py`
- `src/forward_bot/app.py`
- `tests/infrastructure/telegram/test_worker.py`

### Review Findings

- [x] [Review][Patch] Fix sequential pipeline execution context leakage (`ctx_copied.run`) [worker.py:257]
- [x] [Review][Patch] Prevent traceback leakage in blocked outcome details [deliver.py:21]
- [x] [Review][Patch] Clear removed sources from `joined_sources` dynamically [worker.py:126]
- [x] [Review][Patch] Strip query params/trailing slashes from parsed invite links [worker.py:151]
- [x] [Review][Patch] Validate integer conversion for `-100` fallback channel IDs [worker.py:192]
- [x] [Review][Patch] Avoid passing unresolved string targets to `JoinChannelRequest` fallback [worker.py:161]
- [x] [Review][Patch] Re-raise `asyncio.CancelledError` before catching generic `Exception` in event processor [worker.py:221]
- [x] [Review][Defer] Add thread-safe lock for `sampling_counters` mutation [worker.py:252] — deferred, pre-existing
