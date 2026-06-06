# Forward Bot — PRD Addendum

This document carries operator-supplied technical constraints and depth that belong with the PRD but are not capability requirements. It is the primary input the `bmad-create-architecture` skill consumes alongside [`prd.md`](prd.md).

**Status of this addendum:** Constraints captured here are treated by downstream skills as **decided** unless the Architect surfaces a specific reason to renegotiate. **Substantially expanded** to reflect the post-Junction-Bot-scan MVP scope: 12 new MVP features, an updated data model with 2 new collections, and a full UI plan (§9–10).

---

## 1. Technology Stack (constraint)

### 1.1 Runtime / language
- **Python 3.12+** — required.
- **Async-first** — every I/O code path is `async`; blocking calls explicitly isolated.

### 1.2 Web framework
- **FastAPI** for the REST API. **Uvicorn** as ASGI server, single worker.

### 1.3 Telegram client
- **Telethon** for MTProto, single client instance for process lifetime. **Session storage** in `SQLiteSession` to a path mounted on a persistent volume.

### 1.4 Persistence
- **MongoDB** with **Motor** (async driver).

### 1.5 Configuration
- **Pydantic Settings** (`pydantic-settings`).

### 1.6 Frontend (UI in MVP — OQ-UI resolved)

- **Stack:** **React 18** + **TypeScript** + **Vite** + **Tailwind CSS** + **TanStack Query** (server state) + **React Router** + **shadcn/ui** (component library).
- **Build:** multi-stage Dockerfile compiles the frontend during image build; runtime image carries only compiled assets.
- **Serving:** FastAPI mounts the built bundle via `StaticFiles` at `/`; API namespace is `/api/v1/*`.
- **Auth:** dashboard authenticates via `POST /api/v1/auth/login` (accepts `X-API-Key`), receives an HttpOnly SameSite=Strict cookie used for subsequent requests (FR-43).

### 1.7 Other constraints
- Type hints throughout.
- Structured logging (`structlog` or `python-json-logger` — Architect picks; must support correlation-ID context-var).

---

## 2. Engineering Standards (constraint)

(Unchanged from prior addendum.) Clean Architecture, DDD where appropriate, SOLID, DI, production-grade error handling, configuration-driven behavior.

---

## 3. Folder Structure (recommendation)

Same as prior addendum, plus optional `web/` subfolder when the UI is built:

```
forward-bot/
├── (all existing folders from prior addendum)
├── src/forward_bot/
│   └── domain/entities/
│       ├── source.py                    # NEW (FR-29)
│       ├── source_folder.py             # NEW (FR-31)
│       ├── forwarding_rule.py
│       ├── replacement_rule.py
│       ├── message_mapping.py
│       └── pipeline_context.py          # carries time-window result, sampling counter, etc.
│   └── application/
│       ├── sources/                     # NEW use-case folder
│       │   ├── register_source.py
│       │   ├── list_sources.py
│       │   ├── update_source.py
│       │   └── delete_source.py
│       ├── folders/                     # NEW
│       │   ├── create_folder.py
│       │   ├── list_folders.py
│       │   ├── rename_folder.py
│       │   └── delete_folder.py
│       └── pipeline/steps/
│           ├── time_window.py           # NEW (FR-32)
│           ├── sampling.py              # NEW (FR-33)
│           ├── media_type_filter.py     # NEW (FR-34)
│           ├── block_keyword.py
│           ├── allow_keyword.py         # NEW (FR-35)
│           ├── media_decision.py
│           ├── reply_lookup.py          # NEW (FR-40)
│           ├── source_ref_replace.py    # NEW (FR-39)
│           ├── text_replacement.py      # supports literal + regex (FR-7/8)
│           ├── link_removal.py
│           ├── hashtag_removal.py
│           ├── mention_removal.py
│           ├── media_replacement.py     # NEW (FR-41)
│           ├── whitespace.py
│           ├── attribution.py           # NEW (FR-31a)
│           └── empty_check.py
│
├── web/                                  # ONLY if UI in MVP (or v1.1)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── routes/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/
│   │   └── styles/
│   └── public/
```

### 3.1 Layer Responsibilities

Unchanged. New pipeline steps in `application/pipeline/steps/` follow the same `PipelineStep` protocol.

### 3.2 Pipeline Step Contract

Each step in `application/pipeline/steps/` implements the common protocol so steps are composable. The PRD's FR-11 sets the canonical order; the contract lets a future v1.x reorder or skip steps without rewriting unrelated steps.

```python
class PipelineStep(Protocol):
    name: str

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        ...
```

`PipelineContext` carries: `text`, `caption`, `media`, `attribution_decided` (bool), `reply_target_destination_id` (Optional[int]), `correlation_id`, `rule` snapshot, `source` snapshot, and a mutable `metadata` dict for inter-step communication.

`BlockedOutcome` carries the `reason` (matches FR-27 log event names) and any context useful for logging (e.g. which keyword matched).

---

## 4. Deployment Topology

Unchanged. Single container running FastAPI app + Telegram worker + cache refresher + mapping sweeper as cooperative asyncio tasks.

**If UI in MVP:** the same container also serves the built React assets from `/static` (Vite build output mounted into the FastAPI app via `StaticFiles`). No separate deployment target.

### 4.1 Environment variables — additions for new MVP features

| Variable | Purpose | Default |
|---|---|---|
| `TIMEZONE_DEFAULT` | Fallback timezone if a rule's `time_window.timezone` is missing | `UTC` |
| `MEDIA_REPLACEMENT_BASE_DIR` | Filesystem root for `replacement_image_path` resolution (defense-in-depth path containment) | `/app/data/replacement-images` |
| `SAMPLING_PERSIST` | Whether to persist sampling counters to MongoDB (OQ-Sampling-Counter-Persistence) | `false` |
| `UI_ENABLED` | Serve `/static` from the FastAPI app (UI build present) | `false` (true if UI in MVP) |

All other env vars from prior addendum remain.

### 4.2 First-run auth — unchanged

`python -m forward_bot auth` interactively (see prior).

---

## 5. Data Model (rewritten for expanded MVP)

The MVP data model grew from 3 collections to 5: existing `forwarding_rules`, `replacement_rules`, `message_mappings` plus new `sources` and `source_folders`. Each new MVP feature traces back to a specific field.

### 5.1 `sources` **(NEW)**

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Internal stable ID — referenced by `forwarding_rules.source_id` |
| `telegram_id` | int64 | Numeric Telegram channel/chat ID — **canonical key**, resolved at registration |
| `telegram_username` | string \| null | `@username` form; nullable for private channels accessed by ID only |
| `display_name` | string | Operator-facing label |
| `type` | enum | `channel` \| `group` (supergroup folded into `group`) |
| `folder_id` | ObjectId \| null | Reference to `source_folders` (FR-31) |
| `created_at` | datetime (UTC) | |
| `updated_at` | datetime (UTC) | |

**Indexes:**
- Unique on `telegram_id`.
- Unique on `telegram_username` where non-null (sparse index).
- `(folder_id, display_name)` for folder-grouped listings.

### 5.2 `source_folders` **(NEW)**

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `name` | string | Operator-defined; unique |
| `created_at` | datetime (UTC) | |
| `updated_at` | datetime (UTC) | |

**Indexes:** unique on `name`.

### 5.3 `forwarding_rules` **(EXPANDED)**

Existing fields (from prior addendum): `_id`, `is_active`, `remove_links`, `remove_hashtags`, `remove_mentions`, `forward_media`, `created_at`, `updated_at`. `source_channel` and `destination_channel` strings are **removed** and replaced.

| Field | Type | Notes / FR |
|---|---|---|
| `_id` | ObjectId | |
| `source_id` | ObjectId | **REPLACES** `source_channel` string — references `sources._id` (FR-29) |
| `destination_channel` | string | Destination is still a raw string in MVP (no destination catalog yet — A4/A5 deferred) |
| `is_active` | bool | |
| `keyword_match_mode` | enum | `literal` \| `regex` — FR-37 |
| `block_keywords` | string[] | FR-36 |
| `allow_keywords` | string[] | FR-35 (NEW) — empty means "allow all" |
| `media_type_filter` | string[] | FR-34 (NEW) — allowlist of `{"text", "photo"}` in MVP |
| `remove_links` | bool | |
| `remove_hashtags` | bool | |
| `remove_mentions` | bool | |
| `forward_media` | enum | `forward` \| `ignore` \| `caption_only` |
| `sampling` | object | `{ "n": int }` — FR-33 (NEW). Counter is in-process unless `SAMPLING_PERSIST=true` |
| `time_window` | object \| null | `{ "timezone", "days_of_week", "start_time", "end_time" }` — FR-32 (NEW) |
| `attribution` | object | `{ "enabled": bool, "position": "prefix"\|"suffix", "format": str }` — FR-31a (NEW) |
| `auto_replace_source_refs` | object | `{ "enabled": bool, "replacement": str\|null, "replace_display_name": bool }` — FR-39 (NEW) |
| `media_replacement` | object | `{ "enabled": bool, "replacement_image_path": str\|null, "replacement_caption_mode": "use_replacement"\|"use_source"\|"none" }` — FR-41 (NEW) |
| `created_at`, `updated_at` | datetime (UTC) | |

**Indexes:**
- Compound on `(source_id, is_active)` for per-Source dispatch.
- `(is_active)` for cache refresh.
- `(destination_channel)` for ops-time lookup.

### 5.4 `replacement_rules` **(EXPANDED)**

| Field | Type | Notes / FR |
|---|---|---|
| `_id` | ObjectId | |
| `forwarding_rule_id` | ObjectId | Parent reference |
| `search_text` | string | |
| `replacement_text` | string | May contain `\1`, `\2`, ... when `match_mode=regex` |
| `match_mode` | enum | `literal` (case-insensitive substring) \| `regex` (Python regex) — FR-7/8 (NEW) |
| `is_active` | bool | |
| `created_at`, `updated_at` | datetime (UTC) | Ordering by `created_at` |

**Indexes:** `(forwarding_rule_id, is_active, created_at)`.

### 5.5 `message_mappings` (unchanged in schema; usage extended)

Schema same as prior addendum: `_id`, `forwarding_rule_id`, `source_channel_id`, `source_message_id`, `destination_channel_id`, `destination_message_id`, `forwarded_at`.

**New consumer in MVP:** the **Reply lookup** pipeline step (FR-40) queries by `(forwarding_rule_id, source_channel_id, source_message_id)` to find the parent's destination ID when the new Source Message is a reply. The existing index `(source_channel_id, source_message_id)` already covers this lookup.

### 5.6 `sampling_counters` *(conditional — only if `SAMPLING_PERSIST=true`)*

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `forwarding_rule_id` | ObjectId | Unique |
| `counter` | int64 | Current count |
| `updated_at` | datetime (UTC) | |

Resolved by OQ-Sampling-Counter-Persistence. If left at the default (`SAMPLING_PERSIST=false`), this collection is unused.

---

## 6. Mechanism-Level Decisions Deferred to Architect

(All from prior addendum, plus:)

- **Cache shape for the multi-collection refresh.** With `sources`, `source_folders`, `forwarding_rules`, `replacement_rules` all read every 30s, decide: one combined snapshot atomically swapped, or four independent snapshots? Atomic is safer (no torn reads — a Forwarding Rule's `source_id` always resolves in the snapshot).
- **Regex compilation cache.** Compile once per `(rule_id, refresh_version)` and discard with the snapshot. Failure compiles → log once, skip pattern for that snapshot.
- **Timezone resolution.** Use Python `zoneinfo`; document host tzdata requirement.
- **Pipeline orchestration.** Whether each step is a class implementing `PipelineStep` or whether `pipeline.py` is a single function with branches. Recommendation: classes per step — supports the future "add AI step" cleanly.
- **Folder rename semantics.** A rename to a name that already exists → 422 (uniqueness index enforces it).

---

## 7. Operational Runbook seeds

Unchanged from prior addendum. New runbook items added:

- **Replacement-image management.** Operator places replacement images under `MEDIA_REPLACEMENT_BASE_DIR`; restart not required (pipeline reads file at use time). Document the path-containment rule (resolved path must stay under the base dir — defense against `../` traversal in `replacement_image_path`).
- **Time-window troubleshooting.** When a rule isn't forwarding and the operator expected it to, the readiness procedure is: check `LOG_LEVEL=DEBUG`, observe the `outside_time_window` log line; verify timezone string is IANA-valid; check host tzdata.
- **Folder organization.** Operator-facing convention: folders are display-only; they do not affect routing. Renaming or deleting a folder cannot break forwarding.

---

## 8. Future-Roadmap Architectural Hooks

(All from prior addendum, plus:)

- **Header/Footer text (F5/F6 future).** Same machinery as `attribution` (FR-31a) — likely consolidated into an `prefix_lines` / `suffix_lines` field that holds N lines including attribution.
- **Author filtering (D4 future).** `PipelineContext.metadata["sender_id"]` is already available (FR-30); the future filter step reads it. Schema lands at that time.
- **AI step (future).** Slots between text-replacement and link-removal in the pipeline; reads per-rule config object `ai_processing: { provider, prompt, ... }` — placeholder field can be added to `forwarding_rules` now if needed.
- **Destination Catalog (future).** Mirror of `sources` collection for destinations once destination groups/bots (A4/A5) are added.

---

## 9. UI Plan **(IN MVP — OQ-UI resolved)**

This is the operator-facing dashboard delivered as part of the MVP build per OQ-UI resolution (2026-05-31). Corresponding FRs FR-42 through FR-45 are documented in PRD §4.14.

### 9.1 Persona & posture

- **Single operator.** No auth screens (the API key in env var is the only credential; the UI uses it). When multi-user lands (future), a login screen is added.
- **Read + write parity with the REST API.** Every API endpoint has a UI surface; the UI is not a strict subset.
- **Pragmatic, not glossy.** Functional internal-tool aesthetic. shadcn/ui defaults are fine.

### 9.2 Information architecture

Five top-level surfaces in the left sidebar:

1. **Dashboard** — at-a-glance system health, recent activity.
2. **Forwards** — Forwarding Rules: list, create, edit.
3. **Sources** — Source Catalog with Folder organization.
4. **Logs** — Live and historical event stream (JSON view).
5. **Settings** — Telegram connection status, API key info (read-only), env-var summary.

### 9.3 Screens

#### S1. Dashboard (`/`)
- **Top row:** four health cards.
  - **Telegram status** — `connected | reconnecting | disconnected`, last event timestamp. Reads `GET /health/telegram`.
  - **MongoDB status** — `up | down`. Reads `GET /health/ready`.
  - **Active Forwarding Rules** count and **Sources** count. Reads list endpoints with `is_active=true`.
  - **Last 24h** — forwards succeeded / failed / blocked counters. Reads aggregated log query (or a lightweight in-memory counter exposed via a new `GET /api/v1/stats/summary` endpoint).
- **Recent activity panel:** last 50 log lines parsed live (or polled every 5s from a new `GET /api/v1/logs/recent` endpoint).
- **Quick actions:** "+ New Forward", "+ New Source", "+ New Folder".

#### S2. Forwards List (`/forwards`)
- **Table:** columns = Source (Folder · Display Name), Destination, Active toggle, Block/Allow keyword counts, Filters summary (icons for time-window, sampling, media-type), Last forwarded timestamp, Actions (View / Edit / Delete).
- **Filters at top:** filter by `is_active`, by `folder_id` (joined via Source), by destination, free-text search on display name.
- **Bulk:** enable / disable many at once via checkbox + bulk action button.
- **Reads:** `GET /api/v1/rules?folder_id=…&is_active=…`. Display Name joined client-side from a parallel `GET /api/v1/sources`.
- **Writes:** `POST /api/v1/rules/{id}/enable|disable` per-row; bulk dispatches sequentially.

#### S3. Forward — Create / Edit (`/forwards/new`, `/forwards/{id}`)
Single long form, sectioned with collapsible panels:

- **Source & Destination panel** — Source picker (typeahead over registered Sources, "+ New Source" inline link), Destination text input with help (`@username` or numeric ID).
- **Filters panel** — Time-window (timezone, days, hours), Sampling (`n`), Media-Type Filter (checkbox grid), Keyword Match Mode (literal / regex toggle), Block Keywords (multi-input), Allow Keywords (multi-input). Each filter shows a "test it" link that opens a side-pane (future-scope diagnostic).
- **Transforms panel** — Replacement Rules list (subform — add/edit/delete inline), `auto_replace_source_refs` toggle (with `replacement` text input and `replace_display_name` checkbox), link substitution help text ("Add a Replacement Rule with URLs in both fields").
- **Removals panel** — `remove_links`, `remove_hashtags`, `remove_mentions` checkboxes.
- **Media panel** — `forward_media` radio (Forward / Ignore / Caption-only), Media Replacement (`enabled`, file picker for `replacement_image_path` browsing `MEDIA_REPLACEMENT_BASE_DIR`), `replacement_caption_mode` radio.
- **Attribution panel** — `enabled`, `position` (Prefix / Suffix), `format` text with placeholders help.
- **Activation panel** — `is_active` toggle (defaults per OQ-RuleActiveDefault).
- **Save / Cancel** at bottom-right.
- **Validation:** client-side regex check, time-window logical check (end > start unless cross-midnight), conflict detection (same Source + same Destination already exists).

#### S4. Sources List (`/sources`)
- **Layout:** left rail of Folders (with Source counts; "Ungrouped" bucket at bottom; "+ New Folder"). Right pane: table of Sources in selected Folder.
- **Source row:** Display Name, Telegram ID, Username, Type (channel/group), Used in N Forwarding Rules, Actions.
- **Drag-to-move-folder** is a nice-to-have; basic operator-flow uses an "Assign to folder" dropdown per row.
- **Reads:** `GET /api/v1/folders` + `GET /api/v1/sources?folder_id=…`.
- **Writes:** `PUT /api/v1/sources/{id}` (folder reassignment); folder CRUD via folder endpoints.

#### S5. Source — Create / Edit (`/sources/new`, `/sources/{id}`)
- **Fields:** Telegram reference (username or numeric ID — required), Display Name (required), Type (channel/group — required), Folder (dropdown — optional). On create, the API resolves the Telegram numeric ID and persists both; UI shows the resolved ID after save.
- **Delete:** blocked with a message if active Forwarding Rules reference this Source; the message lists the rules.

#### S6. Folders — modal-based CRUD (no dedicated page)
- Folder create / rename via small modals on the Sources page.

#### S7. Logs (`/logs`)
- **Live tail** view (WebSocket or SSE — `GET /api/v1/logs/stream`). Filter by `event` and `correlation_id`.
- **Search** historical (last N hours) by `correlation_id` to trace one message's full journey.
- **Reads only.**

#### S8. Settings (`/settings`)
- **Telegram:** connection status (live), session file path (read-only display), "Reconnect" button (calls a `POST /api/v1/admin/reconnect` endpoint to be added).
- **System:** env var summary table (read-only) — log level, hot-reload interval, FloodWait cap, retry config, mapping retention, sampling persist. Edits are env-var changes + container restart (documented).
- **About:** version, build info.

### 9.4 Navigation & global behavior

- **Top bar:** breadcrumbs + global status indicator (red dot if Telegram disconnected or MongoDB unreachable).
- **Routing:** React Router; deep-linkable URLs.
- **Toaster:** success/error feedback on every write.
- **Optimistic updates** on enable/disable toggles; rollback on API error.
- **Empty states:** every list page has a helpful empty state pointing to the create action.
- **API auth:** UI reads the API key from a session-cookie set by a tiny `POST /api/v1/auth/login` endpoint that accepts the API key and sets an HttpOnly cookie scoped to `127.0.0.1`. The key is never persisted in localStorage. *(This is a small new API endpoint requiring an MVP add if UI is in MVP.)*

### 9.5 Out of scope for UI MVP

- Multi-user views (no per-user filtering, no roles).
- Mobile responsive design beyond "doesn't break at narrow widths."
- Internationalization.
- Custom themes.
- Real-time push beyond the logs SSE.
- In-browser regex tester / diagnostic side-pane (deferred — would re-introduce E4 filter-diagnostics which the user explicitly skipped).

---

## 10. Screen → Data Model Mapping **(NEW — answers "FORWARDS WE HAVE, CREATE FORWARD, ETC..")**

This is the screen-to-DB-and-API mapping the operator asked for. Read this top-down: each UI surface is grounded in the data model it manipulates.

| UI Screen | Reads from | Writes to | API endpoints used |
|---|---|---|---|
| **S1. Dashboard** | `forwarding_rules` (count), `sources` (count), `health` endpoints, log stream | — | `GET /health`, `GET /health/ready`, `GET /health/telegram`, `GET /api/v1/rules?is_active=true&page_size=1`, `GET /api/v1/sources?page_size=1`, `GET /api/v1/stats/summary` (new), `GET /api/v1/logs/recent` (new) |
| **S2. Forwards List** | `forwarding_rules` joined with `sources` (for Display Name) and `source_folders` (for folder name) | `forwarding_rules.is_active` toggles | `GET /api/v1/rules`, `GET /api/v1/sources`, `POST /api/v1/rules/{id}/enable`, `POST /api/v1/rules/{id}/disable`, `DELETE /api/v1/rules/{id}` |
| **S3. Forward Create/Edit** | `sources` (for picker), `source_folders` (for picker grouping), `forwarding_rules.{id}` (edit), `replacement_rules` (for subform) | `forwarding_rules`, `replacement_rules` | `GET /api/v1/sources`, `POST/PUT/PATCH /api/v1/rules`, `POST/PUT/DELETE /api/v1/replacement-rules` |
| **S4. Sources List** | `source_folders`, `sources`, count-of-`forwarding_rules`-per-source | `sources.folder_id` (reassignment) | `GET /api/v1/folders`, `GET /api/v1/sources`, `PATCH /api/v1/sources/{id}` |
| **S5. Source Create/Edit** | `sources.{id}` (edit), `source_folders` (for folder picker) | `sources` | `POST/PUT/PATCH/DELETE /api/v1/sources` |
| **S6. Folder modal** | `source_folders` | `source_folders` | `POST/PUT/DELETE /api/v1/folders` |
| **S7. Logs** | Log stream | — | `GET /api/v1/logs/stream` (SSE — new), `GET /api/v1/logs/search?correlation_id=…` (new) |
| **S8. Settings** | `health/telegram`, env vars | (admin actions) | `GET /health/telegram`, `POST /api/v1/admin/reconnect` (new) |

### 10.1 "Forwards we have, create forward" flow walk-through

The user named this specific flow. Walking it end-to-end:

1. **Operator opens `/forwards`** (S2).
   - UI calls `GET /api/v1/rules?page=1&page_size=50` → array of Forwarding Rule documents.
   - UI calls `GET /api/v1/sources` in parallel → keyed map of Sources, used to render Display Name in the Source column.
   - UI calls `GET /api/v1/folders` for the Folder filter dropdown.
   - Table renders. Each row's Source column shows `<Folder · Display Name>`; Filters column shows icons for whatever `time_window` / `sampling` / `media_type_filter` is configured.

2. **Operator clicks "+ New Forward"** → navigates to `/forwards/new` (S3).
   - UI calls `GET /api/v1/sources` (already cached from step 1, served from TanStack Query cache).
   - The Source picker is populated. If no Sources exist yet, the picker shows an inline "+ Register a Source first" link to `/sources/new`.
   - Each form panel is populated with defaults (per the assumptions in PRD §13).

3. **Operator picks a Source, enters Destination, configures filters and transforms, clicks Save.**
   - UI calls `POST /api/v1/rules` with the full Forwarding Rule body (Pydantic-validated server-side per FR-6).
   - Server validates: regex compiles, time-window is logical, `source_id` exists, `destination_channel` syntactically valid, no `source==destination`.
   - On 201 Created, UI navigates back to `/forwards` and shows a toast "Forwarding Rule created." Table re-fetches and shows the new row.
   - On 422 Validation Error, UI surfaces field-scoped errors inline next to the offending inputs.

4. **Operator wants to add a Replacement Rule to the new Forwarding Rule.**
   - From the Forwarding Rule edit screen, the Replacement Rules subform is a list with "+ Add" button.
   - Each row is an inline form; on save it `POST`s to `/api/v1/replacement-rules` with `forwarding_rule_id` referencing the parent.
   - Existing rules can be edited (`PUT/PATCH`) or deleted (`DELETE`); changes are local to the subform until parent save commits.

5. **Within ≤ 60s, the worker's cache refreshes.** The new Forwarding Rule is now applied; the worker subscribes to the Source (if not already subscribed); messages arriving from that Source begin running through the new rule's Processing Pipeline.

6. **Operator can verify in Logs (S7):** filter the log stream by `event=forward_succeeded` and `correlation_id` containing the new rule's ID → see traffic flowing.

### 10.2 New API endpoints required to support the UI plan

These are endpoints **not in the prior PRD §9** that the UI plan calls for. They are deferred until UI build:

- `GET /api/v1/sources` family — already in PRD §9 (added with FR-29).
- `GET /api/v1/folders` family — already in PRD §9 (added with FR-31).
- `GET /api/v1/stats/summary` — last 24h success/failure/blocked counters.
- `GET /api/v1/logs/recent` — last N log lines (default 50, max 500).
- `GET /api/v1/logs/stream` — SSE / WebSocket live tail.
- `GET /api/v1/logs/search?correlation_id=…` — search recent logs by correlation ID.
- `POST /api/v1/auth/login` — accept API key, set HttpOnly session cookie (used by the UI to avoid storing the key in JS).
- `POST /api/v1/admin/reconnect` — operator-triggered Telegram reconnect.

Each of these is small. If UI is **v1.1**, none of them are MVP work. If UI is **MVP**, they are added to PRD §9 at OQ-UI resolution time.

---

## 11. Scope Expansion Note **(NEW)**

For Architect awareness: the MVP scope grew significantly between the first PRD draft (2026-05-31 morning) and this addendum revision (2026-05-31 afternoon). The user's original brief said "MVP focuses only on channel-to-channel forwarding and message filtering" and "will keep it minimal." After the Junction Bot competitive scan, the MVP now includes:

- Group sources alongside channels
- Source Catalog + Folders
- Per-rule attribution toggle
- Allow keywords + regex match mode + regex replacement
- Media-type filter, sampling, time-window restriction
- Auto-replacement of source references
- Link substitution (via existing replacement mechanism)
- Media replacement
- Reply forwarding

**Architect cost estimate:** roughly **2.5× to 3× the original brief's estimated effort**. The decision log notes this; the user should be reminded if velocity is a constraint.

---

*End of addendum. Architect: consume alongside [`prd.md`](prd.md). Open Questions and Assumptions remain in the PRD.*
