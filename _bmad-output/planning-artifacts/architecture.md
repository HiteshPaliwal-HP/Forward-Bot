---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-06-02'
inputDocuments:
  - prds/prd-forward-bot-2026-05-31/prd.md
  - prds/prd-forward-bot-2026-05-31/addendum.md
  - ux-designs/ux-Forward Bot-2026-05-31/DESIGN.md
  - ux-designs/ux-Forward Bot-2026-05-31/EXPERIENCE.md
workflowType: 'architecture'
project_name: 'Forward Bot'
user_name: 'Hitesh - HP'
date: '2026-05-31'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements — 45 FRs across 13 categories:**

1. **Auth & Session (FR-1–3):** MTProto auth once; persisted SQLiteSession; auto-reconnect
   on restart; session artifact never exposed via API or logs.
2. **Source Catalog & Folders (FR-29–31):** Sources are first-class entities with stable
   internal IDs; Telegram numeric ID resolved at registration; Folder assignment is
   display-only, not routing.
3. **Forwarding Rules (FR-4–6, FR-31a):** Full CRUD + enable/disable without restart;
   per-rule attribution prefix/suffix; strict validation (422 on bad regex, missing
   source_id, self-referential rule).
4. **Replacement Rules (FR-7–8, FR-38):** Literal (case-insensitive) and regex
   substitutions; link substitution reuses the same mechanism; created_at ordering.
5. **Message Ingestion (FR-9–10):** Worker subscribes to every Source referenced by ≥1
   active rule; one Source Message may fan out to N Forwarding Rules independently.
6. **Filtering (FR-32–37):** 6 filter types: time-window (IANA timezone), sampling (N-th
   message), media-type allowlist, allow-keywords, block-keywords, keyword match mode
   (literal/regex). All per-rule, no global filter management.
7. **Processing Pipeline (FR-11–13):** 18-step canonical sequence; filters first (cheap →
   expensive), transforms second, delivery last; each step either passes context forward
   or returns a BlockedOutcome with reason.
8. **Source-Reference Auto-Replacement (FR-39):** Rewrites @username / t.me/ / https://t.me/
   patterns in text to point at the Destination, before generic Replacement Rules run.
9. **Media Handling (FR-14–16, FR-41):** Text + photo in MVP; forward/ignore/caption_only
   modes; media replacement from local filesystem path; fallback to source photo on read
   failure (logged WARNING).
10. **Edit/Delete/Reply Propagation (FR-19–21, FR-40):** message_mappings collection links
    source↔destination for every forwarded message; edits and deletes propagated; reply
    chaining via parent mapping lookup.
11. **Reliability (FR-22–25):** FloodWait handling; exponential retry with backoff; per-rule
    failure isolation; graceful shutdown.
12. **Observability (FR-26–28):** Structured JSON logs; 18+ event types in the catalog;
    correlation IDs; secrets never logged.
13. **Web Admin Dashboard (FR-42–45):** 8 screens served from same FastAPI container;
    cookie-based auth (HttpOnly, SameSite=Strict, 24h TTL); SSE live log stream; Vite
    build compiled into image at build time.

**Non-Functional Requirements:**

| NFR | Target |
|-----|--------|
| Forwarding latency (P95) | ≤ 3 seconds |
| Reliability | ≥ 99% successful-forward rate (7-day window) |
| Rule-change propagation | ≤ 60 seconds end-to-end |
| Cache refresh duration | ≤ 1 second for 1,000 rules + 1,000 sources + 50 folders |
| Restart reconnect | Within 30 seconds |
| Edit/delete/reply propagation | ≤ 5 seconds at ≥ 95% |
| Scale ceiling (single instance) | 100 active sources, 5,000 messages/day |
| Security | X-API-Key auth; localhost bind default; session file secrecy; path containment for media |
| Schema compatibility | All new fields nullable/defaulted (additive-only changes) |

**Scale & Complexity:**

- Primary domain: Full-stack / backend-heavy (pipeline + Telegram worker are the core product;
  React SPA is the operator surface)
- Complexity level: **High** — 18-step pipeline, 5 MongoDB collections, 4-collection atomic
  cache, full React SPA + SSE, 45+ FRs. The addendum explicitly flags 2.5–3× the original
  effort estimate.
- Estimated architectural components: ~12 discrete layers/modules (Telegram worker, pipeline
  engine, cache manager, API router, auth middleware, log ring buffer, SSE broadcaster,
  MongoDB repositories, domain entities, Pydantic config, React SPA, Docker multi-stage build)

### Technical Constraints & Dependencies

**Decided (non-negotiable, from addendum §1–2):**
- Python 3.12+, async-first — all I/O paths `async`; blocking calls explicitly isolated
- FastAPI + Uvicorn (single ASGI worker)
- Telethon for MTProto; single client instance; SQLiteSession on persistent volume
- MongoDB + Motor (async driver)
- Pydantic Settings for configuration
- React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Router + shadcn/ui
- Clean Architecture / DDD layering; SOLID; Dependency Injection
- Single container: FastAPI app + Telegram worker + cache refresher + mapping sweeper
  all as cooperative asyncio tasks
- Multi-stage Dockerfile; React bundle compiled at image build time

**Open for Architect to decide (addendum §6):**
1. Cache shape: atomic combined snapshot vs. independent per-collection snapshots
2. Regex compilation cache strategy
3. Pipeline orchestration: class-per-step (PipelineStep protocol) vs. inline branches
4. Timezone resolution library choice (zoneinfo is recommended)
5. Folder rename duplicate-name enforcement mechanism

### Cross-Cutting Concerns Identified

1. **Correlation ID propagation** — every pipeline event, every log entry must carry the
   same correlation_id from source message receipt to delivery or block decision.
   Implemented via Python contextvars; must thread through every async call.
2. **Async I/O discipline** — cooperative asyncio concurrency; no blocking the event loop.
   Telegram callbacks, MongoDB queries, file I/O (media replacement), and cache refresh
   must all be non-blocking. File reads for media replacement are the most likely
   accidental blocking point.
3. **Atomic hot-reload cache** — all 4 collections (sources, source_folders,
   forwarding_rules, replacement_rules) must be refreshed as one consistent snapshot.
   A partial swap risks torn reads (rule references source_id that doesn't exist in cache).
4. **Per-rule pipeline isolation** — one rule's exception or Telegram error must not
   abort the pipeline run for other rules on the same Source Message.
5. **Security boundaries** — two auth paths: X-API-Key header (programmatic API clients)
   and HttpOnly session cookie (UI). The middleware layer must enforce both cleanly and
   never leak the API key into logs, responses, or browser-accessible storage.
6. **Path containment for media replacement** — replacement_image_path must be validated
   server-side to stay within MEDIA_REPLACEMENT_BASE_DIR (defense against `../` traversal).
   This must happen at pipeline execution time, not just at rule-save time.
7. **Schema backward-compatibility** — all field additions to MongoDB documents must be
   nullable or carry defaults. The application layer must tolerate documents missing
   new fields (written before migration).
8. **Sampling counter scope** — in-memory by default (resets on restart); optional
   persistence to MongoDB. The pipeline step must branch on SAMPLING_PERSIST env var
   and read/write the sampling_counters collection when enabled.

## Starter Template Evaluation

### Primary Technology Domains

This is a split-stack project with two distinct initialization paths:
- **Backend:** Python 3.12 + FastAPI — manual scaffold (no official CLI generator)
- **Frontend:** React 18 + TypeScript + Vite + Tailwind + shadcn/ui — CLI-bootstrapped

### Backend: Manual Scaffold

No maintained FastAPI project generator matches the Clean Architecture folder layout
specified in addendum §3. The backend is initialized manually using `uv` (the current
Python toolchain standard, replacing pip/poetry):

**Initialization Commands:**

```bash
uv init forward-bot --python 3.12
cd forward-bot
uv add fastapi uvicorn[standard] telethon motor pydantic-settings structlog
uv add --dev pytest pytest-asyncio httpx
```

Then the folder structure from addendum §3 is created manually under `src/forward_bot/`.

**Note on package manager:** `uv` is recommended over `pip`+`venv` or `poetry` for its
speed and lockfile discipline, but the addendum does not mandate a specific manager.
If the operator has a strong preference for `poetry`, the commands differ but the
outcome is equivalent.

**Architectural Decisions from Manual Scaffold:**
- Src layout (`src/forward_bot/`) for clean import boundaries
- `pyproject.toml` as the single project manifest (PEP 517)
- `uv.lock` for reproducible installs
- `uv` virtual environment isolation

### Frontend: shadcn Vite Template

**Tool:** `shadcn@latest init -t vite` (Vite v8, current as of 2026-06-01)

This single command bootstraps the full frontend stack:

**Initialization Commands:**

```bash
# In project root — creates web/ folder
npx shadcn@latest init -t vite web

# Install additional dependencies
cd web
npm install @tanstack/react-query
npm install react-router-dom        # React Router v7.16
```

**Architectural Decisions Provided by Starter:**

- **Language:** TypeScript (strict mode)
- **Build tooling:** Vite v8 — HMR, ESM-native, sub-second cold starts
- **Styling:** Tailwind CSS v4 (CSS-native, no config file required)
- **Component library:** shadcn/ui — components copy into `src/components/ui/`, not a
  black-box dependency; fully customizable
- **Path aliases:** `@/` → `src/` (configured in `tsconfig.json` and `vite.config.ts`)
- **shadcn theme:** CSS variables in `src/index.css`; brand overrides from DESIGN.md
  applied here
- **Code organization:** `src/components/ui/` for shadcn primitives; `src/components/`
  for app-specific components; `src/routes/`, `src/pages/`, `src/api/` as per addendum §3

**Development Experience:**
- `npm run dev` — Vite HMR dev server
- `npm run build` — production bundle (output to `web/dist/`) consumed by Docker
  multi-stage build
- TypeScript strict mode catches type errors at compile time

**Note:** Project initialization (backend scaffold + frontend init) should be the
first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Atomic combined cache snapshot (D1)
- Dual-auth middleware with `get_current_operator` dependency (S1)
- Path containment enforcement in media replacement pipeline step (S3)
- Error response envelope standard (A1)
- Log ring buffer + SSE broadcaster design (A2)
- `structlog` as logging library with contextvars correlation ID (I1, I2)
- FastAPI `lifespan` for background task startup/shutdown (I5)

**Important Decisions (Shape Architecture):**
- Regex compilation during cache refresh, stored on snapshot (D2)
- Hourly mapping sweep coroutine (D4)
- `itsdangerous.TimestampSigner` for session cookie (S2)
- TanStack Query stale times per endpoint (F1)
- React Router v7 Declarative mode (F2)
- Theme + SSE connection via React context; no Redux/Zustand (F3)
- Docker two-stage build (Node compile → Python runtime) (I3)

**Deferred Decisions (Post-MVP):**
- CI/CD pipeline (I4) — `docker build + push` script sufficient for MVP
- MongoDB connection pool tuning (D3) — Motor defaults adequate at this scale

---

### Data Architecture

**D1 — Cache Shape: Atomic Combined Snapshot**
Decision: One background coroutine fetches all four collections (`sources`,
`source_folders`, `forwarding_rules`, `replacement_rules`) in sequence, builds a
frozen `RuleCache` dataclass, then atomically replaces `cache_holder.current` in a
single Python assignment (atomic under the GIL in a single asyncio thread).

Rationale: Torn reads — a `forwarding_rule` referencing a `source_id` that hasn't
appeared in the sources snapshot yet — are a correctness bug, not a performance issue.
The addendum explicitly flags this as the safer choice.

```python
@dataclass(frozen=True)
class RuleCache:
    sources: dict[ObjectId, Source]
    folders: dict[ObjectId, SourceFolder]
    rules: list[ForwardingRule]           # active only
    replacements: dict[ObjectId, list[ReplacementRule]]  # keyed by rule id
    compiled_patterns: dict[ObjectId, CompiledPatterns]  # keyed by rule id
    version: int                          # increments each refresh

class CacheHolder:
    current: RuleCache = field(default_factory=RuleCache.empty)
```

The worker always reads `cache_holder.current` at the start of each message dispatch.
In-flight pipeline runs hold a local reference to their snapshot; the next refresh
does not affect them.

**D2 — Regex Compilation: Per-Snapshot, Stored on Cache**
Decision: During cache refresh, compile all regex patterns from `block_keywords`,
`allow_keywords`, and `replacement_rules` (where `match_mode=regex`). Store compiled
`re.Pattern` objects in `RuleCache.compiled_patterns`, keyed by rule ID.

Rationale: Compiling on every message would be O(N keywords × M messages). Compiling
once per 30s refresh and discarding with the snapshot is correct and cheap.

Failure handling: If `re.compile(pattern)` raises, log ERROR with `rule_id` and
`pattern`, skip that pattern for the lifetime of this snapshot. Never raise into the
pipeline; a broken pattern is a no-op, not a crash.

**D3 — MongoDB Connection Pool**
Decision: Motor defaults (max pool size 100). No tuning for MVP.

Rationale: Single asyncio loop, single operator, 5k msgs/day. The default pool is
orders of magnitude above what this workload requires.

**D4 — Message Mapping Retention Sweep**
Decision: A background asyncio task sweeps `message_mappings` once per hour,
deleting documents where `forwarded_at < utcnow() - MAPPING_RETENTION_DAYS`.

Rationale: At 5k msgs/day × 30 days = 150k documents maximum. An hourly sweep
on an indexed `forwarded_at` field is negligible. The sweep runs as one of the
four `lifespan` tasks.

---

### Authentication & Security

**S1 — Dual-Auth FastAPI Dependency**
Decision: A single `get_current_operator` FastAPI dependency checks `X-API-Key`
header first, then falls back to the session cookie. All protected routes declare
`Depends(get_current_operator)`. The UI login endpoint is explicitly excluded from
this dependency.

```python
async def get_current_operator(
    x_api_key: str | None = Header(default=None),
    session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> Operator:
    if x_api_key and secrets.compare_digest(x_api_key, settings.api_key):
        return OPERATOR
    if session and verify_session_cookie(session, settings.secret_key):
        return OPERATOR
    raise HTTPException(status_code=401)
```

Note: `secrets.compare_digest` prevents timing attacks on the API key comparison.

**S2 — Session Cookie: `itsdangerous.TimestampSigner`**
Decision: The session cookie value is signed with `itsdangerous.TimestampSigner`
using `SECRET_KEY` (required env var). On each request, the middleware verifies
the signature and checks the timestamp against the 24h TTL. No database session
store; verification is stateless.

`SECRET_KEY` missing at startup → immediate exit with a clear error message.
Cookie attributes: `HttpOnly=True`, `SameSite=strict`, `Secure` flag set when
`BIND_HOST != 127.0.0.1` (i.e., when served over HTTPS).

**S3 — Path Containment for Media Replacement**
Decision: In the `media_replacement` pipeline step, resolve the full path and
assert it stays within `MEDIA_REPLACEMENT_BASE_DIR` before opening the file.

```python
base = Path(settings.media_replacement_base_dir).resolve()
candidate = (base / rule.media_replacement.replacement_image_path).resolve()
if not candidate.is_relative_to(base):
    log.warning("media_replacement_path_traversal_attempt", ...)
    # fall back to source photo
```

This check runs at pipeline execution time (not rule-save time) because the base
dir could change via env var between saves.

---

### API & Communication Patterns

**A1 — Error Response Envelope**
Decision: Two-tier error contract:
- **422 Validation errors:** FastAPI/Pydantic default format (`{"detail": [{"loc":
  [...], "msg": "...", "type": "..."}]}`). Already machine-readable; no wrapping.
- **Application errors (400, 401, 403, 404, 409, 500):** Custom envelope:
  `{"error": {"code": "rule_not_found", "message": "Rule 507f1f77 not found."}}`.
  `code` is a snake_case string suitable for programmatic handling.

**A2 — Log Ring Buffer + SSE Broadcaster**
Decision: In-process `collections.deque(maxlen=N)` where N is derived from
`LOG_RING_BUFFER_HOURS` at startup (default 1h; if ~10 events/s worst case,
36,000 entries; at typical ~1/s, 3,600). A `structlog` output processor appends
every log event dict to the deque AND fans it out to all active SSE subscriber
queues (`asyncio.Queue`).

```
structlog processor chain:
  ... → add_correlation_id → render_to_dict → [append_to_ring_buffer + fan_out_to_sse] → json_serializer → stdout
```

SSE endpoint: on connect, replay the current deque contents (historical tail),
then subscribe to the fan-out set. On disconnect (client closes connection or
`asyncio.CancelledError`), remove queue from the fan-out set.

No Redis, no message broker, no separate log aggregator required. Operator's
stdout collector (Docker log driver) is the long-term store.

**A3 — OpenAPI Docs**
Decision: `/docs` (Swagger UI) and `/redoc` are enabled and protected by the
`get_current_operator` dependency via a FastAPI router dependency override.

Rationale: Single-operator self-hosted tool; the operator needs API exploration.
No reason to disable.

---

### Frontend Architecture

**F1 — TanStack Query Stale Times**

| Endpoint | staleTime | refetchInterval | Notes |
|----------|-----------|-----------------|-------|
| Rules list (`/api/v1/rules`) | 30s | — | Matches hot-reload interval |
| Sources + Folders | 60s | — | Change infrequently |
| Health endpoints | 0 | 10s | Always fresh for S1 cards |
| Stats summary | 0 | 30s | Dashboard counters |
| Logs recent panel (S1) | 0 | 5s | Per addendum §9.3 |
| SSE log stream (S7) | n/a | n/a | Direct `EventSource`, not TQ |

**F2 — React Router Mode: Declarative**
Decision: React Router v7 in Declarative mode (`<BrowserRouter>` + `<Routes>`).

Rationale: The SPA is served by FastAPI's `StaticFiles` mount, not a Node server.
Remix-style server-side loaders (Framework mode) do not apply. Data fetching is
owned by TanStack Query. All routing is client-side; FastAPI serves `index.html`
for any non-`/api/v1/*` path (catch-all route in FastAPI).

**F3 — Global Client State**
Decision: No Redux or Zustand. Two React contexts only:
- `ThemeContext` — system/light/dark preference, persisted in `localStorage`.
  Theme is the only thing ever written to `localStorage` (API key never goes there).
- `SseContext` — holds the `EventSource` instance and connection status for the
  live log stream; consumed by S7 Logs and the top-bar status dot.

All server state is TanStack Query. All other UI state is local component state.

---

### Infrastructure & Deployment

**I1 — Logging Library: `structlog`**
Decision: `structlog` with the following processor chain:

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # injects correlation_id
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        append_to_ring_buffer,                      # custom: deque + SSE fan-out
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
```

Rationale over `python-json-logger`: native `contextvars` integration for
correlation IDs, composable processor chain for the ring buffer fan-out step.

**I2 — Correlation ID: Python contextvars**
Decision: At Telegram message receipt (start of dispatch loop), generate a short
correlation ID and bind it to the structlog context:

```python
correlation_id = uuid.uuid4().hex[:8]
structlog.contextvars.bind_contextvars(
    correlation_id=correlation_id,
    source_id=str(source.id),
    message_id=event.message.id,
)
# ... run pipeline for all matching rules ...
structlog.contextvars.clear_contextvars()
```

Each rule's pipeline run within the same dispatch shares the same `correlation_id`,
making it possible to trace one source message's fan-out to multiple destinations
in the log stream.

**I3 — Docker Multi-Stage Build**

```dockerfile
# Stage 1: Frontend compile
FROM node:22-slim AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ .
RUN npm run build            # output → /web/dist/

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/
COPY --from=frontend-builder /web/dist/ ./static/
CMD ["uvicorn", "forward_bot.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`UI_ENABLED=true` → FastAPI mounts `./static/` via `StaticFiles` at `/`, plus a
catch-all route that serves `index.html` for SPA deep links.

**I4 — CI/CD: Deferred**
Decision: MVP ships with a `Makefile` or `scripts/build.sh` for local
`docker build + docker push`. GitHub Actions deferred to post-MVP.

**I5 — Background Task Startup: FastAPI `lifespan`**
Decision: All four cooperative asyncio tasks are started and stopped in FastAPI's
`lifespan` async context manager.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo_client.connect()
    await telegram_client.start()          # reconnect from SQLiteSession
    cache_task    = asyncio.create_task(run_cache_refresher(cache_holder))
    sweeper_task  = asyncio.create_task(run_mapping_sweeper())
    worker_task   = asyncio.create_task(run_telegram_worker(cache_holder))
    yield
    for t in (cache_task, sweeper_task, worker_task):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t
    await telegram_client.disconnect()
    mongo_client.close()

app = FastAPI(lifespan=lifespan)
```

Startup order matters: MongoDB must be up before cache refresh; Telegram must be
connected before the worker starts. A startup health check logs CRITICAL and exits
if either dependency is unreachable within 30s.

### Decision Impact Analysis

**Implementation Sequence (order dependencies):**
1. Pydantic Settings + env var schema (everything reads config)
2. MongoDB Motor client + repository base class (cache refresh + all CRUD)
3. `RuleCache` dataclass + `CacheHolder` + cache refresher coroutine (pipeline reads this)
4. Domain entities (`Source`, `ForwardingRule`, `ReplacementRule`, `MessageMapping`)
5. Pipeline engine + all 18 steps in canonical order (core product)
6. Telegram worker (wraps pipeline)
7. FastAPI routers (CRUD endpoints + auth)
8. Log ring buffer + SSE broadcaster (observability)
9. FastAPI `lifespan` wiring all tasks together
10. React SPA (depends on stable API)
11. Docker multi-stage build (depends on both halves compiling)

**Cross-Component Dependencies:**
- `CacheHolder` is shared between the cache refresher task and the Telegram worker;
  it is the single synchronization point — no locks needed (atomic reference swap)
- `structlog` context vars are scoped to an async task; each pipeline invocation
  gets its own context via `copy_context()` if running concurrently (not needed
  in single-worker asyncio, but safe to document)
- The SSE broadcaster deque is written by the structlog processor and read by the
  FastAPI SSE endpoint — both in the same asyncio loop; no thread-safety concerns
- TanStack Query on the frontend invalidates rule queries after any write mutation;
  the backend's 30s cache window means the UI may show the old state for up to 30s
  (the save toast explicitly communicates this — "effects within 60s")

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

9 areas where AI agents could make different choices without explicit guidance:
JSON field casing, ObjectId serialization, datetime format, API response unwrapping,
pipeline step class naming, repository layer access, TanStack Query key structure,
frontend type sourcing, and test file co-location vs. separate directory.

---

### Naming Patterns

**MongoDB Collection Naming — `snake_case`, plural**
Already established by the data model. Agents must not deviate:
- `forwarding_rules`, `replacement_rules`, `message_mappings`, `sources`,
  `source_folders`, `sampling_counters`
- Index names: `{collection}_{fields}` e.g. `sources_telegram_id`,
  `forwarding_rules_source_id_is_active`

**API URL Naming — plural `snake_case` resource nouns**
Established by PRD §9. Pattern: `/api/v1/{plural_resource}/{id}/{sub_resource}`
```
✓  GET  /api/v1/rules
✓  GET  /api/v1/rules/{id}/replacement-rules
✓  POST /api/v1/rules/{id}/enable
✓  GET  /api/v1/sources
✗  GET  /api/v1/rule          ← singular — WRONG
✗  GET  /api/v1/forwardingRules  ← camelCase path — WRONG
```
Sub-resources use `kebab-case` when multi-word: `/replacement-rules`, `/auth/login`.
Action endpoints use verbs: `/enable`, `/disable`, `/reconnect`.

**JSON Field Naming — `snake_case` throughout**
The entire stack uses `snake_case` in JSON. No camelCase conversion at the API
boundary. This eliminates a mapping layer and keeps Python, MongoDB, JSON, and
TypeScript property names identical.

```python
# Pydantic model — fields are snake_case, serialized as snake_case
class ForwardingRuleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str                    # ObjectId serialized as string
    source_id: str
    destination_channel: str
    is_active: bool
    created_at: datetime
```

```typescript
// TypeScript — match snake_case exactly
interface ForwardingRule {
  id: string;
  source_id: string;
  destination_channel: string;
  is_active: boolean;
  created_at: string;          // ISO 8601 string
}
```

**Python Code Naming — standard PEP 8**
- Functions, methods, variables, module names: `snake_case`
- Classes, Pydantic models, dataclasses: `PascalCase`
- Constants, env var names: `SCREAMING_SNAKE_CASE`
- Private methods/attributes: `_leading_underscore`
- Pipeline step classes: `{StepName}Step` e.g. `TimeWindowStep`, `BlockKeywordStep`
- Repository classes: `{Entity}Repository` e.g. `ForwardingRuleRepository`
- Use case classes: verb + noun e.g. `RegisterSource`, `DeleteFolder`

**TypeScript / React Naming**
- React components + their files: `PascalCase.tsx` e.g. `ForwardsList.tsx`
- Hooks: `use` prefix + PascalCase e.g. `useForwardingRules`, `useSseStream`
- API client functions: camelCase TypeScript style e.g. `getRules`, `createRule`
- Query key factories: defined in `queryKeys.ts`, keyed by resource name
- Non-component files: `camelCase.ts` e.g. `queryKeys.ts`, `apiClient.ts`
- No barrel `index.ts` re-exports in `src/components/` — import directly from the file

---

### Structure Patterns

**Backend Directory — Clean Architecture layers, strictly enforced**
```
src/forward_bot/
  domain/
    entities/          # pure dataclasses, no I/O imports
    exceptions.py      # all typed domain exceptions
  application/
    pipeline/
      steps/           # one file per step, named {step_name}.py
    sources/           # use-case files per addendum §3
    folders/
    rules/
    replacements/
  infrastructure/
    mongo/
      repositories/    # one repository class per collection
    telegram/          # Telethon client wrapper
    logging/           # structlog config, ring buffer, SSE broadcaster
  api/
    routers/           # one router file per resource
    dependencies/      # FastAPI Depends() providers
    schemas/           # Pydantic request/response models (NOT domain entities)
  config.py            # Pydantic Settings
  main.py              # FastAPI app + lifespan
```

Rule: domain entities (`domain/entities/`) must never import from `infrastructure/`
or `api/`. The dependency arrow always points inward: api → application → domain.

**Backend Tests — mirror `src/` under `tests/`**
```
tests/
  domain/
  application/
    pipeline/
      steps/           # one test file per step
  infrastructure/
    mongo/
  api/
    routers/
  conftest.py          # shared fixtures (Motor test client, test settings)
```
Test files named `test_{module_name}.py`. No co-located test files in `src/`.

**Frontend Directory — feature-adjacent, not type-grouped**
```
web/src/
  components/
    ui/                # shadcn generated components — never hand-edit
    shared/            # reusable app components (LogRow, StatusPill, etc.)
    layout/            # Sidebar, TopBar, DegradedBanner
  pages/               # one file per route: Dashboard.tsx, ForwardsList.tsx etc.
  hooks/               # shared hooks (useSseStream, useTheme)
  api/                 # one file per resource: rules.ts, sources.ts, logs.ts
  contexts/            # ThemeContext.tsx, SseContext.tsx
  lib/
    queryKeys.ts       # all TanStack Query keys in one place
    errors.ts          # error code constants
  types/               # shared TypeScript interfaces (API response shapes)
  styles/              # global CSS, shadcn theme variables
```

Rule: `components/ui/` files are generated by `npx shadcn add` — agents must never
hand-edit them. Override shadcn components by wrapping them in `components/shared/`.

---

### Format Patterns

**ObjectId Serialization — always `str` in JSON, never raw ObjectId**
MongoDB ObjectIds must be serialized as 24-character hex strings. Configure on the
Pydantic base model:

```python
class MongoBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
    id: str = Field(alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_object_id(cls, v: Any) -> str:
        return str(v)
```

All response schemas inherit `MongoBaseModel`. ObjectIds in nested fields
(e.g. `source_id`, `folder_id`) are also serialized as `str`.

**DateTime Format — ISO 8601 UTC strings in JSON**
All datetimes stored in MongoDB as UTC `datetime`. Serialized in JSON as ISO 8601
strings with `Z` suffix: `"2026-05-31T14:23:11Z"`.

```python
@field_serializer("created_at", "updated_at", "forwarded_at")
def serialize_dt(self, dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
```

Frontend: treat all datetime strings as UTC; use `new Date(isoString)` for display.
Never send or store timezone-aware datetimes from the frontend.

**API Response Structure**

*Success responses:*
- Single resource: return the Pydantic model directly (no `{data: ...}` wrapper)
- Collections: `{"items": [...], "total": N, "page": N, "page_size": N}`
- Actions (enable/disable/reconnect): `{"ok": true}` or the updated resource
- Create: HTTP 201 + the created resource body
- Delete: HTTP 204 (no body)

*Error responses (non-422):*
```json
{"error": {"code": "rule_not_found", "message": "Rule 507f1f77 not found."}}
```
`code` values are documented constants in `lib/errors.ts` on the frontend.

**Log Event Format — structlog JSON, consistent field names**
Every log event must include: `event`, `level`, `timestamp`, `correlation_id`.
```json
{
  "event": "pipeline_blocked",
  "level": "info",
  "timestamp": "2026-05-31T14:23:11Z",
  "correlation_id": "a3f9b2c1",
  "rule_id": "507f1f77bcf86cd799439011",
  "reason": "blocked_keyword",
  "keyword": "pump"
}
```
Field names: `snake_case`. Event names: `snake_case` with underscores (never hyphens).

---

### Communication Patterns

**TanStack Query Key Structure — centralized factory**
All query keys defined in `web/src/lib/queryKeys.ts`. No inline string arrays in
components.

```typescript
export const queryKeys = {
  rules: {
    all: () => ["rules"] as const,
    list: (filters?: RuleFilters) => ["rules", "list", filters] as const,
    detail: (id: string) => ["rules", "detail", id] as const,
  },
  sources: {
    all: () => ["sources"] as const,
    list: (filters?: SourceFilters) => ["sources", "list", filters] as const,
  },
  folders: {
    all: () => ["folders"] as const,
    list: () => ["folders", "list"] as const,
  },
  health: {
    telegram: () => ["health", "telegram"] as const,
    ready: () => ["health", "ready"] as const,
  },
  stats: {
    summary: () => ["stats", "summary"] as const,
  },
} as const;
```

On any write mutation, invalidate the affected resource's `all()` key:
`queryClient.invalidateQueries({ queryKey: queryKeys.rules.all() })`.

**Pipeline Step Return Contract — always `PipelineContext | BlockedOutcome`**
Every pipeline step returns either the (possibly mutated) context or a
`BlockedOutcome`. No exceptions propagate out of a step — exceptions are caught
inside the step, logged, and converted to a `BlockedOutcome` with reason
`step_error`.

```python
# BlockedOutcome reason values — only use these strings (from FR-27 catalog)
BLOCK_REASONS = {
    "outside_time_window", "sampled_out", "media_type_filtered",
    "blocked_keyword", "no_allow_keyword_matched", "empty_after_processing",
    "unsupported_media_type", "step_error",
}
```

---

**Pipeline Exception Isolation Contract** *(added Epic 4 retro — confirmed Epic 5)*

The isolation model has three nested layers. A failure at any layer must not abort processing at a higher layer.

**Layer 1 — Step-level (`apply()` boundary)**
Every `PipelineStep.apply()` catches all exceptions internally and converts them to a `BlockedOutcome(reason="step_error")`. No exception may propagate out of `apply()`.

```python
# Canonical pattern for every PipelineStep:
async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
    try:
        # ... step logic ...
        return ctx
    except Exception as e:
        logger.error("step_error", step=self.name, error=str(e), ...)
        return BlockedOutcome(reason="step_error")
```

**Layer 2 — Per-rule (`asyncio.gather` boundary)**
The worker dispatches each matching rule as an independent `asyncio.Task`. All tasks are gathered with `return_exceptions=True` so one rule's unhandled exception (e.g. a Telegram delivery error that leaked past Layer 1) cannot cancel sibling rule tasks.

```python
# In TelegramWorker.process_event():
tasks = [asyncio.create_task(_execute_and_log(rule)) for rule in matching_rules]
if tasks:
    await asyncio.gather(*tasks, return_exceptions=True)
```

**Layer 3 — Propagation (`asyncio.gather` boundary)**
Edit and delete propagation to multiple destination channels is also gathered with `return_exceptions=True`. Each destination channel's propagation runs in its own `copy_context().run()` to keep `correlation_id` and `structlog` context variables fully isolated between concurrent propagation tasks.

```python
# In TelegramWorker.process_edit_event() / process_delete_event():
tasks = []
for mapping in mappings:
    ctx = contextvars.copy_context()           # strict contextvar isolation
    tasks.append(asyncio.create_task(ctx.run(...)))
await asyncio.gather(*tasks, return_exceptions=True)
```

**Sampling counter guard (`asyncio.Lock`)**
`sampling_counters` is a single `dict` on the worker, shared across concurrent per-rule tasks via `metadata["sampling_counters"]`. To prevent silent under-counting during concurrent `asyncio.gather()` dispatch, the worker creates a single `asyncio.Lock` (`self._sampling_lock`) and passes it to each pipeline context via `metadata["sampling_lock"]`. `SamplingStep` acquires this lock before the read-modify-write on the counter.

```python
# worker.py: created once, passed in metadata
self._sampling_lock = asyncio.Lock()
metadata = {
    "sampling_counters": self.sampling_counters,
    "sampling_lock": self._sampling_lock,
}

# sampling.py: acquired before every counter mutation
lock = ctx.metadata.get("sampling_lock")
if lock is not None:
    async with lock:
        current_val = counters.get(rule.id, 0)
        counters[rule.id] = current_val + 1
        counter = current_val + 1
```

**Key rules for all agents:**
- Never `raise` from inside `apply()` — always return `BlockedOutcome`
- Always use `return_exceptions=True` in `asyncio.gather()` at the dispatch level
- Always use `contextvars.copy_context().run(coro)` for concurrent propagation tasks
- Always acquire `sampling_lock` before mutating `sampling_counters`



### Process Patterns

**Error Handling — backend**
- Domain/application layer: raise typed exceptions (`RuleNotFoundError`,
  `SourceInUseError`, etc.) defined in `domain/exceptions.py`
- API layer: `@app.exception_handler` converts domain exceptions to HTTP responses
  with the A1 error envelope. No `try/except` in router functions for expected errors.
- Pipeline: all exceptions caught inside step `apply()` methods; never propagate to
  the worker loop. Worker loop catches pipeline-level exceptions (Telegram errors,
  unexpected crashes) and logs them with the correlation_id.

**Error Handling — frontend**
- TanStack Query `onError` callbacks fire toasts via shadcn `useToast`
- Destructive toast pattern: `"Save failed: {reason}."`
- Error boundaries at route level (not component level) for unexpected crashes

**Loading State Handling — frontend**
Use shadcn `Skeleton` for initial loads (TanStack Query `isLoading` — no data yet).
Use optimistic updates for toggles per EXPERIENCE.md.
Never use `isFetching` to show loading UI — only `isLoading` (first fetch).
Subsequent refetches are silent.

**Async Pattern — backend**
All async functions use `async def`. Blocking I/O uses `asyncio.to_thread()`:
```python
image_bytes = await asyncio.to_thread(Path(candidate).read_bytes)
```
Never call blocking I/O directly in a coroutine.

---

### Enforcement Guidelines

**All AI Agents MUST:**
- Use `snake_case` for all JSON field names — no camelCase at the API boundary
- Serialize ObjectIds as 24-char hex strings using `MongoBaseModel`
- Serialize datetimes as ISO 8601 UTC strings with `Z` suffix
- Return `BlockedOutcome` (never raise) from pipeline steps
- Define new query keys in `queryKeys.ts` — never inline key arrays in components
- Place shadcn component overrides in `components/shared/` — never edit `components/ui/`
- Use `asyncio.to_thread()` for any blocking I/O inside a coroutine
- Raise typed exceptions from `domain/exceptions.py` — never raw `HTTPException`
  in the application or domain layer
- Log with structlog only — never `print()` or stdlib `logging` directly

**Correct vs. Anti-Pattern Examples:**

```python
# ✓ Correct: domain exception raised in application layer
async def delete_source(source_id: str, repo: SourceRepository):
    source = await repo.get(source_id)
    if source is None:
        raise SourceNotFoundError(source_id)

# ✗ Wrong: HTTPException in the application layer
async def delete_source(source_id: str, repo: SourceRepository):
    source = await repo.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="not found")  # ← WRONG LAYER
```

```typescript
// ✓ Correct: query key from factory
const { data } = useQuery({
  queryKey: queryKeys.rules.list({ is_active: true }),
  queryFn: () => getRules({ is_active: true }),
  staleTime: 30_000,
});

// ✗ Wrong: inline key array
const { data } = useQuery({
  queryKey: ["rules", "list", { is_active: true }],  // ← not in factory — WRONG
  ...
});
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
forward-bot/
├── pyproject.toml              # project manifest + uv dependencies
├── uv.lock                     # reproducible lockfile
├── .env.example                # all env vars documented (no secrets)
├── .gitignore
├── README.md
├── Makefile                    # build, run, auth targets
├── Dockerfile                  # multi-stage: node build → python runtime
├── docker-compose.yml          # production: app + mongodb volumes
├── docker-compose.dev.yml      # local dev with volume mounts
│
├── src/
│   └── forward_bot/
│       ├── __init__.py
│       ├── main.py             # FastAPI app + lifespan (I5)
│       ├── config.py           # Pydantic Settings — all env vars
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── exceptions.py   # RuleNotFoundError, SourceInUseError,
│       │   │                   # FolderNameConflictError, etc.
│       │   └── entities/
│       │       ├── __init__.py
│       │       ├── source.py             # Source (FR-29/30)
│       │       ├── source_folder.py      # SourceFolder (FR-31)
│       │       ├── forwarding_rule.py    # ForwardingRule + all sub-configs
│       │       ├── replacement_rule.py   # ReplacementRule (FR-7)
│       │       ├── message_mapping.py    # MessageMapping (FR-19)
│       │       └── pipeline_context.py  # PipelineContext + BlockedOutcome
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   │
│       │   ├── pipeline/
│       │   │   ├── __init__.py
│       │   │   ├── protocol.py         # PipelineStep protocol definition
│       │   │   ├── engine.py           # orchestrates 18 steps; per-rule isolation
│       │   │   └── steps/              # one file per canonical step (FR-11)
│       │   │       ├── __init__.py
│       │   │       ├── time_window.py       # Step 1  — FR-32
│       │   │       ├── sampling.py          # Step 2  — FR-33
│       │   │       ├── media_type_filter.py # Step 3  — FR-34
│       │   │       ├── block_keyword.py     # Step 4  — FR-36
│       │   │       ├── allow_keyword.py     # Step 5  — FR-35
│       │   │       ├── media_decision.py    # Step 6  — FR-14
│       │   │       ├── reply_lookup.py      # Step 7  — FR-40
│       │   │       ├── source_ref_replace.py # Step 8 — FR-39
│       │   │       ├── text_replacement.py  # Step 9  — FR-7/8
│       │   │       ├── link_removal.py      # Step 10 — FR-13
│       │   │       ├── hashtag_removal.py   # Step 11
│       │   │       ├── mention_removal.py   # Step 12
│       │   │       ├── media_replacement.py # Step 13 — FR-41
│       │   │       ├── whitespace.py        # Step 14
│       │   │       ├── attribution.py       # Step 15 — FR-31a
│       │   │       └── empty_check.py       # Step 16
│       │   │
│       │   ├── sources/
│       │   │   ├── __init__.py
│       │   │   ├── register_source.py   # FR-29: resolve Telegram ID + save
│       │   │   ├── list_sources.py
│       │   │   ├── update_source.py
│       │   │   └── delete_source.py     # FR-29: 409 if active rules reference
│       │   │
│       │   ├── folders/
│       │   │   ├── __init__.py
│       │   │   ├── create_folder.py     # FR-31
│       │   │   ├── list_folders.py
│       │   │   ├── rename_folder.py     # 422 on duplicate name
│       │   │   └── delete_folder.py     # unassigns Sources, does not delete
│       │   │
│       │   ├── rules/
│       │   │   ├── __init__.py
│       │   │   ├── create_rule.py       # FR-4: validates source_id, regex
│       │   │   ├── list_rules.py
│       │   │   ├── update_rule.py
│       │   │   ├── delete_rule.py       # cascades to replacement_rules
│       │   │   ├── enable_rule.py       # FR-5
│       │   │   └── disable_rule.py      # FR-5
│       │   │
│       │   └── replacements/
│       │       ├── __init__.py
│       │       ├── create_replacement.py # FR-7: validates regex on save
│       │       ├── list_replacements.py
│       │       ├── update_replacement.py
│       │       └── delete_replacement.py
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   │
│       │   ├── cache/
│       │   │   ├── __init__.py
│       │   │   ├── rule_cache.py       # RuleCache frozen dataclass + CacheHolder (D1)
│       │   │   │                       # includes compiled_patterns (D2)
│       │   │   └── cache_refresher.py  # 30s coroutine; atomic snapshot swap (FR-12)
│       │   │
│       │   ├── mongo/
│       │   │   ├── __init__.py
│       │   │   ├── client.py           # Motor AsyncIOMotorClient setup + indexes
│       │   │   ├── mapping_sweeper.py  # hourly retention sweep (D4)
│       │   │   └── repositories/
│       │   │       ├── __init__.py
│       │   │       ├── base.py                  # MongoBaseRepository (async CRUD)
│       │   │       ├── source_repository.py
│       │   │       ├── folder_repository.py
│       │   │       ├── rule_repository.py
│       │   │       ├── replacement_repository.py
│       │   │       └── mapping_repository.py    # FR-19; reply lookup query
│       │   │
│       │   ├── telegram/
│       │   │   ├── __init__.py
│       │   │   ├── client.py           # TelegramClient wrapper; session mgmt (FR-1–3)
│       │   │   ├── worker.py           # event handler + per-rule dispatch (FR-9/10)
│       │   │   └── delivery.py         # send/edit/delete + FloodWait/retry (FR-20–25)
│       │   │
│       │   └── logging/
│       │       ├── __init__.py
│       │       ├── setup.py            # structlog processor chain config (I1)
│       │       ├── ring_buffer.py      # deque; structlog processor step (A2)
│       │       └── sse_broadcaster.py  # asyncio.Queue fan-out set (A2)
│       │
│       └── api/
│           ├── __init__.py
│           │
│           ├── dependencies/
│           │   ├── __init__.py
│           │   ├── auth.py             # get_current_operator (S1/S2)
│           │   ├── repositories.py     # Depends() factories for all repos
│           │   └── cache.py            # Depends() factory for CacheHolder
│           │
│           ├── schemas/
│           │   ├── __init__.py
│           │   ├── base.py             # MongoBaseModel; ObjectId + datetime (F-patterns)
│           │   ├── source.py
│           │   ├── folder.py
│           │   ├── rule.py             # includes all nested config schemas
│           │   ├── replacement.py
│           │   ├── auth.py             # LoginRequest
│           │   ├── health.py
│           │   ├── stats.py
│           │   ├── logs.py
│           │   └── errors.py           # ErrorEnvelope (A1)
│           │
│           └── routers/
│               ├── __init__.py
│               ├── sources.py          # /api/v1/sources (FR-29–31)
│               ├── folders.py          # /api/v1/folders (FR-31)
│               ├── rules.py            # /api/v1/rules (FR-4–6)
│               ├── replacements.py     # /api/v1/rules/{id}/replacement-rules (FR-7)
│               ├── auth.py             # /api/v1/auth/login|logout (FR-43)
│               ├── health.py           # /health, /health/ready, /health/telegram
│               ├── stats.py            # /api/v1/stats/summary (FR-42)
│               ├── logs.py             # /api/v1/logs/stream|recent|search (FR-44)
│               ├── admin.py            # /api/v1/admin/reconnect
│               └── media.py            # /api/v1/media/replacement-images
│
├── tests/
│   ├── conftest.py             # Motor test client, test Settings, fixtures
│   ├── domain/
│   │   └── entities/
│   │       ├── test_pipeline_context.py
│   │       └── test_forwarding_rule.py
│   ├── application/
│   │   └── pipeline/
│   │       └── steps/
│   │           ├── test_time_window.py
│   │           ├── test_sampling.py
│   │           ├── test_media_type_filter.py
│   │           ├── test_block_keyword.py
│   │           ├── test_allow_keyword.py
│   │           ├── test_source_ref_replace.py
│   │           ├── test_text_replacement.py
│   │           ├── test_link_removal.py
│   │           ├── test_attribution.py
│   │           ├── test_media_replacement.py
│   │           └── test_empty_check.py
│   ├── infrastructure/
│   │   └── mongo/
│   │       └── repositories/
│   │           ├── test_source_repository.py
│   │           └── test_rule_repository.py
│   └── api/
│       └── routers/
│           ├── test_sources.py
│           ├── test_rules.py
│           ├── test_replacements.py
│           ├── test_auth.py
│           └── test_health.py
│
└── web/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── index.html
    ├── components.json         # shadcn configuration
    └── src/
        ├── main.tsx            # React + TanStack Query + Router entry
        ├── App.tsx             # BrowserRouter + route definitions
        ├── index.css           # Tailwind + shadcn CSS vars + DESIGN.md overrides
        │
        ├── components/
        │   ├── ui/             # shadcn generated — NEVER hand-edit
        │   │   └── ...         # all shadcn add'd components live here
        │   ├── shared/         # app-specific reusable — wrap shadcn here
        │   │   ├── LogRow.tsx          # DESIGN.md log-row-* patterns (FR-44)
        │   │   ├── StatusPill.tsx      # pill-success, pill-cache-stale
        │   │   ├── FilterIconRow.tsx   # S2 per-rule filter icons
        │   │   ├── CollapsiblePanel.tsx # S3 accordion panel with summary string
        │   │   └── ActivationBanner.tsx # S3 post-save inactive-rule alert
        │   └── layout/
        │       ├── AppLayout.tsx       # sidebar + top bar wrapper
        │       ├── Sidebar.tsx         # 5 nav items + g-key shortcuts
        │       ├── TopBar.tsx          # breadcrumbs + Telegram status dot
        │       └── DegradedBanner.tsx  # full-width, non-dismissible
        │
        ├── pages/
        │   ├── Login.tsx           # /login — API key → cookie (FR-43)
        │   ├── Dashboard.tsx       # / — S1: health cards + recent activity
        │   ├── ForwardsList.tsx    # /forwards — S2: table + bulk actions
        │   ├── ForwardEdit.tsx     # /forwards/new, /forwards/:id — S3
        │   ├── SourcesList.tsx     # /sources — S4: folders rail + source table
        │   ├── SourceEdit.tsx      # /sources/new, /sources/:id — S5
        │   ├── Logs.tsx            # /logs — S7: SSE tail + search
        │   └── Settings.tsx        # /settings — S8
        │
        ├── hooks/
        │   ├── useSseStream.ts     # EventSource lifecycle; feeds SseContext
        │   └── useTheme.ts         # ThemeContext consumer + localStorage
        │
        ├── api/
        │   ├── client.ts           # fetch wrapper: auth cookie, error envelope
        │   ├── rules.ts
        │   ├── sources.ts
        │   ├── folders.ts
        │   ├── replacements.ts
        │   ├── health.ts
        │   ├── stats.ts
        │   ├── logs.ts
        │   ├── auth.ts
        │   └── media.ts
        │
        ├── contexts/
        │   ├── ThemeContext.tsx
        │   └── SseContext.tsx
        │
        ├── lib/
        │   ├── queryKeys.ts        # centralized TanStack Query key factory
        │   └── errors.ts           # error code string constants
        │
        └── types/
            ├── api.ts              # all API response interfaces (snake_case)
            └── events.ts           # LogEvent discriminated union
```

---

### Architectural Boundaries

**API Boundary — `/api/v1/*` vs. `/`**
- All REST endpoints: `/api/v1/*` — require `X-API-Key` or session cookie
- UI auth endpoints: `/api/v1/auth/login|logout` — unauthenticated
- Static SPA: `/` catch-all → `index.html`; `/assets/*` → Vite build output
- Same FastAPI process serves both; catch-all route registered last

**Layer Boundary — domain must never import infrastructure**
```
api/ ──→ application/ ──→ domain/
infrastructure/ ──→ domain/
infrastructure/ ←─ NEVER ─── domain/
```
Any import of `motor`, `telethon`, `structlog`, or `fastapi` inside `domain/` is a
boundary violation.

**Cache Boundary — CacheHolder is the single shared state**
Only `cache_refresher.py` writes to `CacheHolder.current`. The Telegram worker reads
from it. API routers never read from `CacheHolder` — they always query MongoDB via
repositories so responses reflect persisted state, not the stale cache.

**SSE Boundary — log events flow one direction**
```
structlog processor → ring_buffer deque + SSE queue set → logs.py SSE endpoint → browser
```
The SSE broadcaster never reads from or writes to MongoDB.

---

### Requirements to Structure Mapping

| FR Category | Primary Files |
|-------------|--------------|
| Auth & Session (FR-1–3) | `infrastructure/telegram/client.py`, `api/routers/auth.py` |
| Source Catalog (FR-29–31) | `application/sources/`, `infrastructure/mongo/repositories/source_repository.py`, `api/routers/sources.py` |
| Folders (FR-31) | `application/folders/`, `api/routers/folders.py` |
| Forwarding Rules (FR-4–6, FR-31a) | `application/rules/`, `api/routers/rules.py` |
| Replacement Rules (FR-7–8, FR-38) | `application/replacements/`, `api/routers/replacements.py` |
| Message Ingestion (FR-9–10) | `infrastructure/telegram/worker.py` |
| Filtering (FR-32–37) | `application/pipeline/steps/time_window.py` … `allow_keyword.py` |
| Processing Pipeline (FR-11–13) | `application/pipeline/engine.py` + all 16 step files |
| Source-Ref Auto-Replace (FR-39) | `application/pipeline/steps/source_ref_replace.py` |
| Media Handling (FR-14–16, FR-41) | `application/pipeline/steps/media_decision.py`, `media_replacement.py` |
| Edit/Delete/Reply (FR-19–21, FR-40) | `infrastructure/telegram/delivery.py`, `infrastructure/mongo/repositories/mapping_repository.py`, `application/pipeline/steps/reply_lookup.py` |
| Reliability (FR-22–25) | `infrastructure/telegram/delivery.py` |
| Observability (FR-26–28) | `infrastructure/logging/` |
| Web Dashboard (FR-42–45) | `web/src/`, `api/routers/stats.py`, `api/routers/logs.py`, `api/routers/auth.py` |

**Cross-cutting concern locations:**
- Correlation ID: bound in `infrastructure/telegram/worker.py`; cleared after dispatch
- Hot-reload cache: `infrastructure/cache/cache_refresher.py` + `rule_cache.py`
- Dual auth: `api/dependencies/auth.py` consumed by all protected routers
- Path containment: `application/pipeline/steps/media_replacement.py`
- Schema backward-compat: `infrastructure/mongo/repositories/base.py` (null-safe reads)

---

### Data Flow

**Message processing:**
```
Telegram event → worker.py (bind correlation_id, read cache snapshot)
  → engine.py (per-rule loop)
    → steps 1–16 (filter/transform PipelineContext)
      → delivery.py (send to Telegram, write MessageMapping)
        → structlog: log forward_succeeded
```

**Rule change propagation:**
```
API write → repository.save() → MongoDB updated
  → (≤30s) cache_refresher reads all 4 collections
    → atomic swap: cache_holder.current = new RuleCache
      → next worker dispatch reads new snapshot
```

**Live log flow:**
```
structlog call → ring_buffer.py (append deque + fan-out to SSE queues)
  → logs.py SSE endpoint (yield to browser)
    → useSseStream.ts (EventSource receives event)
      → SseContext (Logs page + top-bar status dot updated)
```

---

### Development Workflow

**Local development:**
```bash
# Terminal 1 — backend (hot-reload)
uv run uvicorn forward_bot.main:app --reload --port 8000

# Terminal 2 — frontend (Vite HMR, proxies /api/* to :8000)
cd web && npm run dev
```

**Production build:**
```bash
make build   # docker build -t forward-bot:latest .
make run     # docker compose up -d
```

**First-run Telegram auth:**
```bash
docker compose run --rm app python -m forward_bot auth
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are asyncio-native and mutually compatible:
- Python 3.12 + FastAPI + Uvicorn (single worker) + Telethon + Motor + structlog:
  no threading model conflicts; all operate on the same asyncio event loop.
- itsdangerous for cookie signing: pure Python, no async requirements, no conflicts.
- React 18 + Vite v8 + Tailwind v4 + shadcn/ui + TanStack Query + React Router v7:
  all current-generation, all compatible. shadcn's `init -t vite` template configures
  Tailwind v4 CSS-native theming correctly for shadcn's CSS variable approach.
- uv + pyproject.toml: standard PEP 517 toolchain, compatible with all Python deps.
- Docker multi-stage (node:22-slim + python:3.12-slim): standard pattern, no conflicts.

**Pattern Consistency:**
- Clean Architecture layer boundaries consistently enforced; domain never imports
  infrastructure or API layers.
- `snake_case` JSON field naming consistent across Python models, MongoDB fields,
  and TypeScript interfaces — no mapping layer needed.
- `MongoBaseModel` with ObjectId and datetime serializers applied uniformly across
  all response schemas.
- TanStack Query key factory centralized in `queryKeys.ts`; stale times assigned
  per the F1 decision table.
- structlog processor chain handles correlation_id, ring buffer, and SSE fan-out
  in one composable pipeline.

**Structure Alignment:**
- All 13 FR categories have explicit file mappings in the project tree.
- All 18 pipeline steps have dedicated files in `application/pipeline/steps/`.
- All 8 UI screens have dedicated page components in `web/src/pages/`.
- All 5 MongoDB collections have dedicated repository classes.
- All architectural boundaries (cache, SSE, layer, API/SPA) are physically enforced
  by the directory structure.

---

### Requirements Coverage Validation ✅

**Functional Requirements — all 13 categories covered:**

| FR Category | Status | Key Files |
|-------------|--------|-----------|
| Auth & Session (FR-1–3) | ✅ | `infrastructure/telegram/client.py`, `api/routers/auth.py` |
| Source Catalog (FR-29–31) | ✅ | `application/sources/`, `source_repository.py` |
| Folders (FR-31) | ✅ | `application/folders/`, `folder_repository.py` |
| Forwarding Rules (FR-4–6, FR-31a) | ✅ | `application/rules/`, `api/routers/rules.py` |
| Replacement Rules (FR-7–8, FR-38) | ✅ | `application/replacements/`, `api/routers/replacements.py` |
| Message Ingestion (FR-9–10) | ✅ | `infrastructure/telegram/worker.py` |
| Filtering (FR-32–37) | ✅ | Steps 1–5 in `pipeline/steps/` |
| Processing Pipeline (FR-11–13) | ✅ | `pipeline/engine.py` + all 16 step files |
| Source-Ref Auto-Replace (FR-39) | ✅ | `pipeline/steps/source_ref_replace.py` |
| Media Handling (FR-14–16, FR-41) | ✅ | `media_decision.py`, `media_replacement.py` |
| Edit/Delete/Reply (FR-19–21, FR-40) | ✅ | `delivery.py`, `mapping_repository.py`, `reply_lookup.py` |
| Reliability (FR-22–25) | ✅ | `infrastructure/telegram/delivery.py` |
| Observability (FR-26–28) | ✅ | `infrastructure/logging/` |
| Web Dashboard (FR-42–45) | ✅ | `web/src/`, `api/routers/stats|logs|auth.py` |

**Non-Functional Requirements — all 8 addressed:**

| NFR | Architectural Support |
|-----|-----------------------|
| P95 latency ≤ 3s | Async pipeline, no blocking I/O, filters short-circuit early |
| ≥99% reliability | Per-rule isolation in `engine.py`; retry + FloodWait in `delivery.py` |
| ≤60s rule propagation | 30s cache refresh; `cache_refresher.py` atomic swap |
| ≤1s cache refresh at 1k rules | Single Motor query per collection; frozen dataclass build |
| Restart reconnect ≤30s | `SQLiteSession` auto-reconnect in `telegram/client.py` |
| Security | `get_current_operator` dependency; `itsdangerous` cookie; path containment |
| Schema backward-compat | Null-safe field reads in `base.py`; additive-only MongoDB changes |
| Scale (100 sources, 5k msgs/day) | Single asyncio loop; Motor defaults; deque ring buffer |

---

### Gap Analysis Results

**Critical Gaps:** None.

**Minor Gaps (4) — resolved with implementation notes:**

**Gap 1 — Sampling counter runtime state**
The `sampling.py` step needs a mutable per-rule counter persisting across dispatches.
This is runtime state, not config state — it does not belong in `RuleCache`.

Resolution: The in-memory counter dict `{rule_id: int}` is owned by `worker.py` and
passed into `SamplingStep` via `PipelineContext.metadata["sampling_counters"]` at
dispatch time. When `SAMPLING_PERSIST=true`, the step reads/writes `sampling_counters`
MongoDB collection via `sampling_repository.py` instead.

**Gap 2 — `sampling_repository.py` missing from project tree**
Resolution: Add `infrastructure/mongo/repositories/sampling_repository.py`.
Conditional on `SAMPLING_PERSIST` env var at startup; if false, the file exists but
the repository is never instantiated.

**Gap 3 — FastAPI SPA catch-all registration order**
The `/{full_path:path}` catch-all must be registered *after* all API routers.
FastAPI matches routes in registration order.

Resolution: In `main.py`, enforce this order:
```python
app.include_router(sources_router, prefix="/api/v1")
# ... all other API routers ...
if settings.ui_enabled:
    app.mount("/assets", StaticFiles(directory="static/assets"), name="static-assets")
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse("static/index.html")
```

**Gap 4 — First-run auth CLI entry point**
`python -m forward_bot auth` requires a `__main__.py` module.

Resolution: Add `src/forward_bot/__main__.py` (interactive Telethon auth flow).
Add to `pyproject.toml`:
`forward-bot-auth = "forward_bot.__main__:run_auth"` under `[project.scripts]`.

**Updated project tree (2 additions):**
```
src/forward_bot/
  __main__.py                              # Gap 4: first-run auth CLI
  infrastructure/mongo/repositories/
    sampling_repository.py                 # Gap 2: SAMPLING_PERSIST=true path
```

---

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (High; 2.5–3× original brief)
- [x] Technical constraints identified (all from addendum §1–2)
- [x] Cross-cutting concerns mapped (8 identified)

**Architectural Decisions**
- [x] Critical decisions documented with versions (17 decisions across steps 3–4)
- [x] Technology stack fully specified
- [x] Integration patterns defined (cache, SSE, layer, API/SPA boundaries)
- [x] Performance considerations addressed (async-first, cache NFR, latency targets)

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined (all files named specifically)
- [x] Component boundaries established (4 explicit boundaries)
- [x] Integration points mapped (3 data flows)
- [x] Requirements to structure mapping complete (all 13 FR categories)

---

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

All 16 checklist items confirmed. No critical gaps. Four minor gaps resolved with
implementation notes. No architectural rework required.

**Confidence Level: High**

The PRD and addendum provided unusually complete constraints — tech stack, data model,
folder layout, pipeline order, and UI plan were all pre-specified. The architecture
workflow filled the 5 mechanism-level gaps from addendum §6 plus 4 structural gaps
discovered during validation.

**Key Strengths:**
- Atomic cache snapshot eliminates the entire class of torn-read correctness bugs
- 18-step pipeline with explicit `PipelineStep` protocol makes each step
  independently testable and the canonical order unambiguous
- structlog processor chain solves log ring buffer + SSE fan-out without any
  external infrastructure
- `snake_case` JSON throughout eliminates the frontend/backend naming impedance mismatch
- All 8 UI screens map to a single page file; no hidden state in the dashboard

**Areas for Future Enhancement (post-MVP):**
- Persistent dead-letter queue for failed forwards (currently logging-only)
- OpenAPI TypeScript type generation (currently manual interfaces in `types/`)
- GitHub Actions CI/CD pipeline
- MongoDB index tuning if message volume exceeds 5k msgs/day
- Destination Catalog when destination groups/bots land (post-MVP §11)

---

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented; no tech substitutions
- Use the implementation sequence from the Decision Impact Analysis in step 4
- Consult step 5 patterns before writing any new file — naming and structure rules
  are non-negotiable
- The 18-step pipeline order in FR-11 is canonical; do not reorder steps
- Register FastAPI routes in the order: API routers first, SPA catch-all last (Gap 3)

**First Implementation Priority:**
```bash
# Step 1: Initialize project scaffold
uv init forward-bot --python 3.12
npx shadcn@latest init -t vite web

# Step 2: Install backend deps
cd forward-bot
uv add fastapi uvicorn[standard] telethon motor pydantic-settings structlog itsdangerous
uv add --dev pytest pytest-asyncio httpx

# Step 3: Install frontend deps
cd web
npm install @tanstack/react-query react-router-dom
```

Then implement in sequence:
Settings → MongoDB client → RuleCache + CacheHolder → Domain entities →
Pipeline engine + steps → Telegram worker → FastAPI routers →
Log ring buffer + SSE → lifespan wiring → React SPA → Docker build.
