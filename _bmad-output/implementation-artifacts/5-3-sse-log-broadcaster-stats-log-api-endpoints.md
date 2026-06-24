# Story 5.3: SSE Log Broadcaster & Stats/Log API Endpoints

Status: done

## Story

As a **Channel Operator**,
I want to stream live logs via SSE and query recent log history and summary stats via REST endpoints,
so that the operator dashboard has all the backend data feeds it needs.

## Acceptance Criteria

1. **SSE Log Stream Endpoint:**
   - **Given** an authenticated operator connects to `GET /api/v1/logs/stream`.
   - **When** the SSE connection opens.
   - **Then** all current ring buffer entries are replayed to the client first.
   - **And** the client's `asyncio.Queue` is added to the fan-out set.
   - **And** subsequent log events are pushed strictly formatted as `data: <json>\n\n`.
   - **And** the stream is filterable via `?event=<name>` and `?correlation_id=<id>` query params.
   - **And** the endpoint requires `Depends(get_current_operator)` auth (Architecture S1).

2. **Client Disconnection Handling:**
   - **Given** a client disconnects from `GET /api/v1/logs/stream`.
   - **When** the connection closes (client closes, `starlette.requests.ClientDisconnect`, or `asyncio.CancelledError`).
   - **Then** the client's queue is removed from the fan-out set.
   - **And** no further events are pushed.
   - **And** no memory leak occurs.

3. **Recent Logs Endpoint:**
   - **Given** `GET /api/v1/logs/recent?limit=50` is called by an authenticated operator.
   - **When** the endpoint responds.
   - **Then** up to `limit` (default 50, max 500) most-recent ring buffer entries are returned as `{"items": [...]}` in chronological order.
   - **And** it supports optional `?event=` and `?correlation_id=` filters.
   - **And** the endpoint requires `Depends(get_current_operator)` auth.

4. **Search Logs Endpoint:**
   - **Given** `GET /api/v1/logs/search?correlation_id=a3f9b2c1` is called by an authenticated operator.
   - **When** the endpoint responds.
   - **Then** all ring-buffer entries matching that `correlation_id` are returned.
   - **And** `?since=<ISO timestamp>` filters to events after that time (default last 1h, max 24h window).
   - **And** the endpoint requires `Depends(get_current_operator)` auth.

5. **Stats Summary Endpoint:**
   - **Given** `GET /api/v1/stats/summary` is called by an authenticated operator.
   - **When** the endpoint responds.
   - **Then** it returns `{"forwarded_24h": N, "failed_24h": N, "blocked_24h": N}` tallied from the ring buffer.
   - **And** it must explicitly handle the fact that the ring buffer length is bound by `LOG_RING_BUFFER_HOURS` (which defaults to 1h); it will tally all available entries up to 24h and cap at 24h.
   - **And** it is documented as approximate (ring-buffer bounded).
   - **And** the endpoint requires `Depends(get_current_operator)` auth.

6. **Admin Reconnect Endpoint:**
   - **Given** `POST /api/v1/admin/reconnect` is called by an authenticated operator.
   - **When** the endpoint executes.
   - **Then** it triggers a Telegram client reconnect attempt.
   - **And** it returns `{"ok": true}` immediately (fire-and-forget).
   - **And** the reconnect result appears in the log stream.
   - **And** it requires `Depends(get_current_operator)` auth.

## Tasks / Subtasks

- [x] **1. Create API Routers** (AC: 1, 3, 4, 5, 6)
  - [x] Implement `GET /api/v1/logs/stream`
  - [x] Implement `GET /api/v1/logs/recent`
  - [x] Implement `GET /api/v1/logs/search`
  - [x] Implement `GET /api/v1/stats/summary`
  - [x] Implement `POST /api/v1/admin/reconnect`
- [x] **2. Integrate Routers in app.py** (AC: 1-6)
  - [x] Include routers in FastAPI app factory
  - [x] Manage `app.state.worker_task` in lifespan hook
- [x] **3. Implement Unit Tests** (AC: 1-6)
  - [x] Implement tests in `tests/api/test_logs.py`
  - [x] Implement tests in `tests/api/test_stats.py`
  - [x] Implement tests in `tests/api/test_admin.py`
- [x] **4. Run Tests & Verify** (AC: 1-6)
  - [x] Verify all tests pass

### Review Findings

- [x] [Review][Patch] Duplicate log in SSE stream — `stream_logs` streams logs from historical and live queues. If a log is added after subscriber registration but before historical log retrieval, it is yielded twice. [logs.py:stream_logs]
- [x] [Review][Patch] Fire-and-forget reconnect task — `perform_reconnect` is created using `asyncio.create_task` inside a request handler without retaining a strong reference, risking premature garbage collection. [admin.py:reconnect]

## Dev Notes

- **Authentication is Mandatory:** *ALL* endpoints defined in this story MUST declare `Depends(get_current_operator)` as per Architecture S1. Do not accidentally leave the log endpoints exposed.
- **Error Envelopes:** Any 4xx/5xx application errors (e.g., invalid query parameters) MUST use the Architecture A1 standard `{"error": {"code": "...", "message": "..."}}`.
- **Streaming Response without buffering:** Starlette's `StreamingResponse` yields SSE lines using standard format `data: <json>\n\n`. Test using direct generator iteration or mocking the `yield` mechanism, as ASGI testing of streaming responses can hang.
- **Worker task recreation:** Telegram client disconnect unblocks `run_until_disconnected()`, terminating the worker. The reconnect endpoint manages app state and spawns a new task.

### Project Structure Notes

- Keep endpoints organized under `src/forward_bot/api/routers/`.

### References

- [Functional Requirements FR-44, NFR-Obs in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md)
- [Architecture Decision A2, I5 in architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Flash (High))

### Debug Log References

- None

### Completion Notes List

- Implemented standard logging history retrieval (`/recent` and `/search` endpoints) and `/stream` SSE endpoints.
- Implemented `/stats/summary` calculating approximate logs activity metrics over a sliding 24-hour window from the ring buffer.
- Implemented `/admin/reconnect` endpoint that restarts the Telegram worker task upon client reconnect.
- Wrote and passed comprehensive unit tests covering all target endpoints.
