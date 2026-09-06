---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - prds/prd-forward-bot-2026-05-31/prd.md
  - prds/prd-forward-bot-2026-05-31/addendum.md
  - architecture.md
  - ux-designs/ux-Forward Bot-2026-05-31/DESIGN.md
  - ux-designs/ux-Forward Bot-2026-05-31/EXPERIENCE.md
  - ux-designs/ux-Forward Bot-2026-05-31/reconcile-prd-forward-bot-2026-05-31.md
---

# Forward Bot - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Forward Bot, decomposing the requirements from the PRD, Architecture, and UX Design documents into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1: The operator can authenticate the service to Telegram during initial setup using API_ID, API_HASH, phone number, and SMS/2FA code; success writes a session artifact to a configured persistent path; failure exits with non-zero code and an actionable error.

FR-2: The service starts and reaches "connected" state without operator interaction whenever a valid session artifact exists; cold-start to "connected" within 30s on a healthy network; network blips reconnect transparently; Telegram-side session invalidation exits cleanly with CRITICAL log.

FR-3: The session artifact is stored only in a path explicitly configured by the operator, never logged, never returned by any API endpoint.

FR-4: The operator can create, retrieve, list, update, and delete Forwarding Rules through the REST API; create takes source_id, destination_channel, and per-rule config; list is paginated (default 50, max 200), filterable by source_id, destination_channel, is_active, folder_id; duplicate (source_id, destination_channel) pairs are permitted.

FR-5: The operator can flip a Forwarding Rule's is_active flag via dedicated enable/disable endpoints without restart; disabled rules are ignored within the Hot-Reload Interval.

FR-6: The system rejects malformed rule payloads at the API boundary with HTTP 422 and a machine-readable error body identifying the offending field (missing required fields, unknown fields, self-referential rules, invalid regex, non-existent source_id).

FR-7: The operator can create, list, update, and delete Replacement Rules scoped to a parent Forwarding Rule; each has search_text, replacement_text, match_mode (literal|regex), is_active, created_at, updated_at; cascade delete with parent.

FR-8: Literal match mode performs case-insensitive substring replacement of all non-overlapping occurrences; regex mode applies re.sub-equivalent with Python regex semantics including capture-group backreferences; both apply to message text and media captions.

FR-9: The worker maintains an active subscription to every Source referenced by at least one active Forwarding Rule (channel or group); subscription begins within the Hot-Reload Interval after a new Source is used in an active rule; teardown is best-effort.

FR-10: When a Source Message arrives, the worker evaluates every active Forwarding Rule whose source_id matches and runs the Processing Pipeline independently for each; one Source Message may produce zero, one, or many Forwarded Messages.

FR-11: For each (Source Message, Forwarding Rule) pair, the pipeline runs in this canonical 18-step order: (1) Time-Window check, (2) Sampling check, (3) Media-Type filter, (4) Block-Keyword check, (5) Allow-Keyword check, (6) Media decision, (7) Reply lookup, (8) Source-Reference Auto-Replacement, (9) Text Replacement Rules, (10) Link removal, (11) Hashtag removal, (12) Mention removal, (13) Media Replacement, (14) Whitespace normalization, (15) Attribution prefix/suffix, (16) Empty-result check, (17) Deliver, (18) Persist Message Mapping.

FR-12: Rule Cache Management & Multi-Tier Refresh Strategy — The Processing Pipeline reads from an in-memory `RuleCache` snapshot of active Sources, Folders, Forwarding Rules, and Replacement Rules, operating on a three-tier refresh model: event-driven instant rebuild, manual trigger, and periodic background fallback.

FR-12a: Event-Driven Instant Cache Refresh on DB Operations — Whenever a REST API operation mutates rules, replacement rules, sources, or folders (Create, Update, Delete, Enable, Disable), the system immediately triggers an asynchronous in-memory rebuild of `RuleCache` and atomically swaps `CacheHolder.current` in <1 second without blocking API response.

FR-12b: Manual UI & REST Endpoint Cache Refresh — Backend exposes `POST /api/v1/admin/cache/refresh` (and `/api/v1/cache/refresh`) and Web Admin Dashboard (Settings S8 & top bar) features a "Refresh Cache" button, allowing on-demand cache rebuild with toast notification surfacing version, rule_count, source_count, and refreshed_at.

FR-12c: Fallback Periodic Background Refresh — Background `run_cache_refresher` task continues to run periodically based on `HOT_RELOAD_INTERVAL` (default 30 seconds) as a fallback safety net to guarantee eventual consistency.

FR-13: remove_links=true removes http://, https://, t.me/, telegram.me/, tg://, and joinchat/+ invite-link forms.

FR-14: forward_media accepts forward | ignore | caption_only per Forwarding Rule.

FR-15: MVP supports photos with optional captions and text messages; other media types (video, document, voice, sticker, GIF, poll, location, contact) are dropped silently (logged as unsupported_media_type).

FR-16: Each item in a Telegram media album is processed independently; albums fragment (accepted MVP gap).

FR-19: A Message Mapping record is persisted for every forwarded message, linking source→destination for a given Forwarding Rule, required for edit/delete/reply propagation.

FR-20: When a Source Message is edited, the corresponding Forwarded Message(s) are edited in their destination(s).

FR-21: When a Source Message is deleted, the corresponding Forwarded Message(s) are deleted in their destination(s).

FR-22: FloodWait responses from Telegram are handled gracefully (respect the wait duration, then retry).

FR-23: Failed deliveries are retried with exponential backoff up to a configured retry budget.

FR-24: A failure in one Forwarding Rule's pipeline does not abort pipeline runs for other rules on the same Source Message.

FR-25: On SIGTERM/SIGINT, the service finishes in-flight pipeline runs and disconnects from Telegram cleanly before exiting.

FR-26: All log output is structured JSON with correlation IDs; event names are consistent snake_case strings.

FR-27: Event coverage includes all pipeline outcomes: forwarded, blocked_keyword, no_allow_keyword_matched, outside_time_window, sampled_out, media_type_filtered, unsupported_media_type, empty_after_processing, reply_parent_not_found, reply_target_missing, media_replacement_failed, source_registered, source_resolved, folder_created, edit_propagated, delete_propagated, flood_wait, cache_refresh_failed.

FR-28: No log line contains session bytes, API keys, or any secret credential.

FR-29: The operator can register a Source by providing a Telegram reference (username or numeric ID), display name, and type (channel|group); server resolves and stores the numeric Telegram ID at registration; duplicate numeric ID → 422 conflict.

FR-30: Source Channels and Source Groups are handled uniformly through the Processing Pipeline; group messages carry sender_id metadata.

FR-31: The operator can create, rename, list, and delete Folders, and assign/move/unassign a Source to a Folder; deleting a Folder unassigns its Sources (does not delete them); a Source belongs to at most one Folder.

FR-31a: Each Forwarding Rule carries attribution config: enabled (bool), position (prefix|suffix), format template with {source_name} and {source_username} placeholders; default format "From {source_name}" prefix; attribution applies after all transforms; if source message is photo-only, attribution becomes the caption.

FR-32: Each Forwarding Rule carries an optional time_window config: timezone (IANA name), days_of_week (set of MON–SUN), start_time, end_time; messages outside the window are blocked (logged outside_time_window); windows may cross midnight; no buffering — messages are dropped.

FR-33: Each Forwarding Rule carries optional sampling config: integer n ≥ 1; pipeline maintains per-rule counter; only every n-th Source Message is forwarded (logged sampled_out when skipped); counter is in-memory by default (SAMPLING_PERSIST=false) and resets on restart.

FR-34: Each Forwarding Rule carries optional media_type_filter config: allowlist of Telegram media types; default allowlist = ["text", "photo"]; messages whose media type is not in the allowlist are blocked (logged media_type_filtered).

FR-35: Each Forwarding Rule carries optional allow_keywords array; if non-empty, the Source Message must match at least one Allow Keyword (under keyword_match_mode) or the pipeline blocks (logged no_allow_keyword_matched); empty = allow everything.

FR-36: Each Forwarding Rule carries optional block_keywords array; if Source Message matches any Block Keyword (under keyword_match_mode), the pipeline blocks (logged blocked_keyword with which keyword matched).

FR-37: Each Forwarding Rule carries keyword_match_mode: literal (case-insensitive substring; default) or regex (Python regex); applies uniformly to block_keywords and allow_keywords; invalid regex at save → 422.

FR-38: URL→URL substitutions use the standard Replacement Rule mechanism; no separate collection or endpoint required.

FR-39: Each Forwarding Rule has auto_replace_source_refs config: enabled (bool), replacement (string|null), replace_display_name (bool); when enabled, rewrites @<source_username>, t.me/<source_username>, https://t.me/<source_username>, and optionally <source_display_name> in the text to point at the Destination; runs before generic Replacement Rules.

FR-40: When a Source Message is a reply (Telegram reply_to_msg_id populated), the pipeline looks up the parent Source Message's Mapping for the same Forwarding Rule; if found and within retention, the Forwarded Message is posted as a reply; otherwise posted standalone (logged reply_parent_not_found or reply_target_missing).

FR-41: Each Forwarding Rule has optional media_replacement config: enabled (bool), replacement_image_path (filesystem path relative to MEDIA_REPLACEMENT_BASE_DIR), replacement_caption_mode (use_replacement|use_source|none); when enabled and Source Message has a photo, the Forwarded Message uses the replacement image; text-only messages unchanged; fallback to source photo on read failure (logged WARNING).

FR-42: The web admin dashboard provides UI affordances for every operator action exposed by the REST API; 8 screens total: Dashboard (S1), Forwards List (S2), Forward Create/Edit (S3), Sources List (S4), Source Create/Edit (S5), Folder modals (S6), Logs (S7), Settings (S8).

FR-43: POST /api/v1/auth/login accepts {"api_key": "..."} and sets an HttpOnly, SameSite=Strict session cookie (24h TTL) on match; POST /api/v1/auth/logout clears the cookie; cookie never exposed in browser-accessible storage.

FR-44: GET /api/v1/logs/stream is an SSE endpoint pushing live JSON log events, filterable by event and correlation_id query params; GET /api/v1/logs/recent returns last N log lines from the in-memory ring buffer; GET /api/v1/logs/search supports correlation_id lookup over the recent past (default last 1h, max 24h).

FR-45: The dashboard is built as a static asset bundle (React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Router + shadcn/ui) compiled in a multi-stage Docker build and served by the same FastAPI process at / (with API at /api/v1/*); UI_ENABLED=true (default) mounts static assets.

FR-46: Settings page (S8) fetches and displays current Telegram session state (CONNECTED green indicator with "Terminate Session" button, or DISCONNECTED red indicator with "Connect Telegram" card). Shows phone input field in E.164 format (+<country><number>) when phone_required: true (if TELEGRAM_PHONE is absent from env). Refreshes status every 10s via TanStack Query.

FR-47: Operator clicks "Send OTP" to trigger POST /api/v1/telegram/auth/start (calls Telethon send_code_request(), stores phone_code_hash in memory). Enters 6-digit OTP and clicks "Connect", triggering POST /api/v1/telegram/auth/verify (calls Telethon sign_in(), writes .session, calls TelegramClientHolder.reconnect() dynamically without service restart). "Send OTP" button throttled for 60s client-side.

FR-48: 2FA support: if account has cloud password, sign_in() returning SessionPasswordNeededError causes backend to return HTTP 202 { "requires_2fa": true }. UI reveals password input field; operator submits password via POST /api/v1/telegram/auth/verify with password field (masked, never logged).

FR-49: Operator clicks "Terminate Session" on Settings page; confirmation modal requires typing terminate (case-insensitive) to confirm. Triggers POST /api/v1/telegram/auth/terminate (calls Telethon client.log_out(), deletes .session file, sets TelegramClientHolder _connected = False). In-flight pipeline runs complete; subsequent incoming messages are dropped and logged as telegram_session_terminated_drop.

FR-50: Auth edge cases handled gracefully: wrong OTP (HTTP 400 invalid_otp), expired OTP (HTTP 400 otp_expired), concurrent auth attempt (HTTP 409 auth_in_progress), already connected (HTTP 409 already_connected), OTP timeout window (10 min in-memory cleanup via TELEGRAM_OTP_TIMEOUT_SECS), max OTP retries (surface Telethon error message), terminate while disconnected (HTTP 409 not_connected).

FR-51: TelegramClientHolder lifecycle methods: reconnect(session_path: str) reinstantiates Telethon client from session file, re-registers event handlers, marks _connected = True; terminate() sets _connected = False, revokes session, deletes session file. Both acquire an asyncio.Lock. Hot-reload loop pauses while _connected is False. Event dispatch drops events when _connected is False.

### NonFunctional Requirements

NFR-Perf: P95 forwarding latency ≤3 seconds under nominal load; cache refresh ≤1 second for up to 1,000 active rules + 1,000 active Sources + 50 Folders.

NFR-Scale: Single-instance target: 100 active Sources (channels + groups combined), 5,000 messages/day.

NFR-Rel: Successful-forward rate ≥99% across a 7-day window, excluding messages legitimately blocked by filters or destinations made permanently unreachable.

NFR-RuleChange: A rule change committed via the API takes effect within 60 seconds in 100% of cases.

NFR-Reconnect: Service restarts re-establish Telegram connection within 30 seconds in 100% of cases where a valid session exists.

NFR-Propagation: Edits, deletes, and reply linkage within Mapping retention propagate within 5 seconds in ≥95% of cases.

NFR-FilterAccuracy: For each filter step (time-window, sampling, media-type, allow-keyword, block-keyword), false-positive and false-negative rates each ≤0.5% on a curated test corpus.

NFR-Sec: X-API-Key authentication; localhost bind default; session file secrecy; path containment for media replacement (MEDIA_REPLACEMENT_BASE_DIR); HttpOnly SameSite=Strict cookie for UI; secrets.compare_digest for timing-attack prevention.

NFR-Obs: Structured JSON logs (structlog) with correlation IDs (contextvars); secrets never logged; 18+ event types in the catalog; log ring buffer (default 1h, max 24h configurable via LOG_RING_BUFFER_HOURS).

NFR-Maint: Schema backward-compatible — all new fields nullable or carry defaults; application layer tolerates documents missing new fields.

NFR-Compat: Adding fields to forwarding_rules, sources, source_folders must be additive-only (nullable/defaulted).

### Additional Requirements

From Architecture decisions that affect implementation:

- Project scaffold: backend initialized with `uv init forward-bot --python 3.12` + deps (fastapi, uvicorn[standard], telethon, motor, pydantic-settings, structlog, itsdangerous); frontend initialized with `npx shadcn@latest init -t vite web` + @tanstack/react-query + react-router-dom. This is Epic 1 Story 1.

- Atomic combined cache snapshot (D1): RuleCache frozen dataclass fetches all 4 collections (sources, source_folders, forwarding_rules, replacement_rules) in one background coroutine and atomically replaces CacheHolder.current; prevents torn reads.

- Regex compilation per snapshot (D2): all regex patterns from block_keywords, allow_keywords, and replacement_rules compiled during cache refresh and stored in RuleCache.compiled_patterns; compile failure logs ERROR and skips pattern for that snapshot lifetime.

- Message Mapping retention sweep (D4): hourly asyncio background task sweeps message_mappings where forwarded_at < utcnow() - MAPPING_RETENTION_DAYS; runs as one of four lifespan tasks.

- Dual-auth FastAPI dependency (S1): get_current_operator checks X-API-Key header first (via secrets.compare_digest), then falls back to session cookie; all protected routes declare Depends(get_current_operator).

- Session cookie via itsdangerous.TimestampSigner (S2): signed with SECRET_KEY (required env var; missing at startup → immediate exit); stateless verification; Secure flag set when BIND_HOST != 127.0.0.1.

- Path containment for media replacement (S3): resolve full candidate path and assert it stays within MEDIA_REPLACEMENT_BASE_DIR before opening; runs at pipeline execution time, not rule-save time; traversal attempts logged and fall back to source photo.

- Error response envelope (A1): 422 Validation errors use FastAPI/Pydantic default format; other errors (400, 401, 403, 404, 409, 500) use {"error": {"code": "snake_case_code", "message": "..."}} envelope.

- Log ring buffer + SSE broadcaster (A2): in-process collections.deque(maxlen=N) appended by structlog processor; fan-out to asyncio.Queue set for active SSE subscribers; SSE endpoint replays deque on connect, then subscribes to fan-out.

- structlog processor chain (I1): merge_contextvars → add_log_level → TimeStamper(fmt="iso") → append_to_ring_buffer → JSONRenderer; correlation_id bound via contextvars at message receipt, cleared after dispatch (I2).

- FastAPI lifespan (I5): four cooperative asyncio tasks started/stopped — cache_refresher, mapping_sweeper, telegram_worker, and the MongoDB client; startup order: MongoDB first, then Telegram, then tasks; startup health check exits on failure within 30s.

- Docker multi-stage build (I3): Stage 1 (node:22-slim) compiles React bundle to /web/dist/; Stage 2 (python:3.12-slim) installs Python deps via uv and copies /web/dist/ to /app/static/.

- TanStack Query stale times (F1): rules list=30s, sources+folders=60s, health endpoints=0 refetch every 10s, stats summary=0 refetch every 30s, logs recent=0 refetch every 5s; SSE log stream via direct EventSource (not TanStack Query).

- React Router v7 Declarative mode (F2): BrowserRouter + Routes; FastAPI serves index.html catch-all for any non-/api/v1/* path; catch-all registered last after all API routers.

- Global client state (F3): No Redux/Zustand; only ThemeContext (system/light/dark, persisted in localStorage — theme is the only localStorage item) and SseContext (EventSource instance + connection status).

- MongoDB collections: forwarding_rules, replacement_rules, message_mappings, sources, source_folders, sampling_counters (conditional on SAMPLING_PERSIST=true). All with correct indexes as specified in addendum §5.

- snake_case JSON field naming throughout; ObjectIds serialized as 24-char hex strings via MongoBaseModel; datetimes serialized as ISO 8601 UTC strings with Z suffix.

- PipelineStep protocol: each step implements async apply(ctx) → PipelineContext | BlockedOutcome; exceptions caught inside apply(), never propagate; broken patterns are no-ops.

- Pipeline step naming: {StepName}Step; Repository naming: {Entity}Repository; Use case naming: verb + noun.

- TypeScript interfaces use snake_case property names matching JSON exactly; query keys centralized in queryKeys.ts; shadcn components in components/ui/ never hand-edited — overrides in components/shared/.

- asyncio.to_thread() for all blocking I/O inside coroutines (especially media file reads).

- Sampling counter runtime state: in-memory dict in worker.py passed via PipelineContext.metadata; when SAMPLING_PERSIST=true, reads/writes sampling_counters collection via sampling_repository.py.

- First-run auth CLI: src/forward_bot/__main__.py; pyproject.toml script entry forward-bot-auth.

- CI/CD deferred; Makefile/scripts/build.sh for docker build + docker compose up.

### UX Design Requirements

UX-DR1: Implement DESIGN.md brand-layer CSS token system in web/src/index.css — warm-stone neutral palette (light: #FAFAF9 background, #16A34A accent; dark: #14130F background, #22C55E accent), Forwarding Green accent, three state colors (success/warning/error/degraded), all light/dark token pairs as CSS variables; shadcn defaults inherited for all unlisted tokens.

UX-DR2: Implement persistent left sidebar layout with 5 nav items (Dashboard, Forwards, Sources, Logs, Settings) + global top bar (breadcrumbs left, Telegram status dot right) + max-w-6xl content pane; sidebar collapses to Sheet below md (768px); Logs screen uses full-width layout.

UX-DR3: Implement global degraded banner (DegradedBanner component) — full-width, radius:0, state-degraded red (distinct from state-error), non-dismissible, role="alert" aria-live="assertive"; displays when Telegram disconnected OR MongoDB unreachable; holds message + [Reconnect] button; all dashboard actions remain enabled while banner present.

UX-DR4: Implement 8 log row variants (LogRow component) — left-edge 4px accent stripe + lucide icon + bold event label + mono payload preview + timestamp; variants: forwarded (success/arrow-up-right), filter-blocked (muted/circle-slash), telegram-rejected (error/alert-triangle), destination-unreachable (error/ban), flood-wait (warning/clock), edit-propagated (success/pencil), delete-propagated (success/trash-2), reply-orphaned (warning/corner-down-right with strike modifier).

UX-DR5: Implement filter icon row (FilterIconRow component) — 4 lucide icons in order (clock/shuffle/image/key) per Forwards List row; active = accent color + full opacity; inactive = foreground-muted + 40% opacity; hover surfaces shadcn Tooltip with configured value (e.g., "Mon–Fri 09:00–17:00 Europe/Warsaw"); icon hit area ≥24px.

UX-DR6: Implement StatusPill component — pill-success (tinted green bg + border + foreground, distinct from solid accent) and pill-cache-stale (warning tinted) variants; always icon + label + color, never color alone.

UX-DR7: Implement CollapsiblePanel component (S3 Forward Edit) — all 7 panels (Source/Dest, Filters, Transforms, Removals, Media, Attribution, Activation) collapsed by default on open/edit; header shows panel name + summary string in foreground-muted; multiple panels can be open simultaneously; expanded state persists in URL query params (?panels=filters,media).

UX-DR8: Implement ActivationBanner component — shadcn Alert with state-warning tint; sits at top of S3 for any rule with is_active=false; copy "This forward is inactive. [Activate] to begin processing."; disappears on first activation, never reappears if deactivated again.

UX-DR9: Implement vim-style keyboard shortcuts: g+d → Dashboard, g+f → Forwards, g+s → Sources, g+l → Logs, g+, → Settings; also Cmd/Ctrl+Enter saves S3 rule form; Esc closes topmost modal/popover and exits S3 inline subform edit mode.

UX-DR10: Implement S7 Logs auto-scroll and URL-persistent filter — auto-scroll to bottom on new events when user is at bottom; pause on scroll-up with floating "Jump to latest" button; beyond ring-buffer inline note "Beyond 1h — older events not retained."; filter chips (event, correlation_id) persist in URL.

UX-DR11: Implement S2 Forwards List bulk action bar — sticky bar appears when ≥1 row checked; shows selected count + Enable/Disable/Delete buttons; Disable confirms (shadcn AlertDialog) when ≥5 rows selected; progress-bar toast for bulk operations with live counter; summary toast persists until dismissed when failures exist; [Show errors] expands inline panel.

UX-DR12: Implement file picker for S3 Media panel — shadcn Combobox populated by GET /api/v1/media/replacement-images; lists files in MEDIA_REPLACEMENT_BASE_DIR; pick-only, never writes; empty state "No replacement images. Place files under MEDIA_REPLACEMENT_BASE_DIR to pick from here."

UX-DR13: Implement attribution format live preview (S3 Attribution panel) — input "From {source_name}" → preview "From Crypto Signals Pro"; available token chips ({source_name}, {source_username}) are clickable to insert at cursor position.

UX-DR14: Implement first-run wizard — shadcn Dialog, 3 steps: (1) Telegram connection check showing pill-success or error, (2) register first source inline form, (3) create first forward mini-form with pre-populated source picker; skippable at any step; dismissed permanently after first source registers or operator skips; never resurfaces.

UX-DR15: Implement S2 row optimistic toggle (enable/disable) with rollback — toggle flips immediately; row enters saving sub-state (subtle opacity + spinner on toggle track); on 4xx/5xx, rollback toggle + destructive toast "Toggle failed: <reason>."

UX-DR16: Implement resolved-ID echo (S5 Source create/edit) — after save, show resolved numeric Telegram ID as "Resolved ID: 1234567890" in foreground-muted below Display Name field.

UX-DR17: Implement Source delete 409 dialog — shadcn AlertDialog listing every blocking rule with link to its S3 edit page; copy pattern: "Source [ID] is referenced by N rules: [Rule 1], [Rule 2]. Delete those or reassign first."

UX-DR18: Implement folder modal duplicate-name inline validation — debounce 300ms GET /api/v1/folders?name=...; if name exists and is not current folder, show inline error "Folder name in use: {name}." below input; Save button disabled while error present.

UX-DR19: Implement Login page (/login) — single X-API-Key input field, submit calls POST /api/v1/auth/login; any 401 mid-session redirects to /login?return=<current-path>; on successful re-auth, returns to saved URL; toast "Session expired — sign in to continue." on expired redirect.

UX-DR20: Implement cache-refresh failure top-bar warning — subdued pill-cache-stale pill next to Telegram status dot reading "Rules cache stale (last refresh Nm ago)" when cache_refresh_failed event received; clears when next refresh succeeds.

UX-DR21: Implement accessibility floor — Tab order matches reading order on every surface; no color-only signals (every state paired with icon + label); shadcn ring focus indicators on all focusable elements; semantic HTML (ul, table, form, label); ARIA on degraded banner (role="alert", aria-live="assertive"); form validation aria-invalid + aria-describedby; shadcn Toast aria-live="polite" (destructive → "assertive").

UX-DR22: Implement three-state theme toggle (S8 Settings) — System / Light / Dark options; default System; selection persists in localStorage; ThemeContext drives body class; API key never stored in localStorage.

UX-DR23: Implement correlation ID trace flow — click log row → expand inline showing full JSON payload + correlation_id with copy-button; click correlation_id → sets /logs?correlation_id=... URL filter to trace one message's full pipeline journey.

UX-DR24: Implement Reconnect button states (S8 Settings + degraded banner) — idle state [Reconnect]; in-flight [Reconnecting…] with spinner + disabled; success green checkmark for 2s then reverts to idle; failure button shakes once + toast "Reconnect failed — see logs." with [Open logs] action.

UX-DR25: Implement flood-wait top-bar pill — warning-tinted pill alongside Telegram status dot when a FloodWait event is active; copy indicates per-rule throttle (not system disconnection); clears when FloodWait resolves.

UX-DR26: Implement Telegram Session Management UI card on S8 Settings page — displays CONNECTED (green dot) + "Terminate Session" button OR DISCONNECTED (red dot) + "Connect Telegram" card. When phone_required: true, shows E.164 phone input field (+<country><number>) before "Send OTP" button.

UX-DR27: Implement OTP and 2FA input flows — 60s throttle on "Send OTP" button, reveals 6-digit numeric OTP input field; upon HTTP 202 requires_2fa: true, reveals masked password input field with inline error handling for wrong OTP/password.

UX-DR28: Implement Terminate Session confirmation modal — requires operator to type "terminate" (case-insensitive) to enable "Confirm Terminate" button; on completion transitions UI to DISCONNECTED state.

### FR Coverage Map

| FR | Epic | Brief description |
|---|---|---|
| FR-1 | Epic 1 | First-run auth CLI |
| FR-2 | Epic 1 | Auto-reconnect from SQLiteSession |
| FR-3 | Epic 1 | Session secrecy at rest |
| FR-4 | Epic 3 | Forwarding Rule CRUD |
| FR-5 | Epic 3 | Rule enable/disable endpoints |
| FR-6 | Epic 3 | 422 validation at API boundary |
| FR-7 | Epic 3 | Replacement Rule CRUD |
| FR-8 | Epic 3 | Literal + regex replacement semantics |
| FR-9 | Epic 4 | Source subscription in worker |
| FR-10 | Epic 4 | Per-rule dispatch for each source message |
| FR-11 | Epic 4 | 18-step canonical pipeline |
| FR-12 | Epics 3+4 | Rule Cache Management & Multi-Tier Refresh Strategy |
| FR-12a | Epics 3+4 | Event-Driven Instant Cache Refresh on DB operations (<1s) |
| FR-12b | Epics 3+5+6 | REST endpoint `POST /api/v1/admin/cache/refresh` (Epic 3/5) & Dashboard "Refresh Cache" UI button (Epic 6) |
| FR-12c | Epics 3+4 | Fallback periodic background refresh task (30s) |
| FR-13 | Epic 4 | URL stripping step in pipeline |
| FR-14 | Epic 4 | Media mode decision step |
| FR-15 | Epic 4 | Media-type scope (text+photo only) |
| FR-16 | Epic 4 | Album fragmentation (accepted gap) |
| FR-19 | Epics 4+5 | Mapping persistence in Epic 4; retention sweep in Epic 5 |
| FR-20 | Epic 5 | Edit propagation |
| FR-21 | Epic 5 | Delete propagation |
| FR-22 | Epic 4 | FloodWait handling in delivery.py |
| FR-23 | Epic 4 | Exponential retry in delivery.py |
| FR-24 | Epic 4 | Per-rule failure isolation in engine.py |
| FR-25 | Epic 4 | Graceful shutdown in lifespan |
| FR-26 | Epics 1+5 | Basic structlog in Epic 1; full chain in Epic 5 |
| FR-27 | Epic 5 | Complete 18+ event catalog |
| FR-28 | Epics 1+5 | No-secrets rule established in Epic 1; audited in Epic 5 |
| FR-29 | Epic 2 | Source registration + Telegram ID resolve |
| FR-30 | Epic 2 | Channel/group type handling |
| FR-31 | Epic 2 | Folder CRUD + source assignment |
| FR-31a | Epic 3 | Per-rule attribution toggle |
| FR-32 | Epic 3 | Time-window restriction config + validation |
| FR-33 | Epic 3 | Sampling config (runtime counter in Epic 4) |
| FR-34 | Epic 3 | Media-type filter config |
| FR-35 | Epic 3 | Allow-keyword whitelist config |
| FR-36 | Epic 3 | Block-keyword filter config |
| FR-37 | Epic 3 | Keyword match mode config |
| FR-38 | Epic 3 | Link substitution via Replacement Rule |
| FR-39 | Epic 3 | Source-ref auto-replacement config |
| FR-40 | Epic 4 | Reply forwarding via mapping lookup |
| FR-41 | Epic 3 | Media replacement config + path containment |
| FR-42 | Epic 6 | All 8 dashboard screens |
| FR-43 | Epic 6 | Cookie-based UI auth |
| FR-44 | Epics 5+6 | SSE backend in Epic 5; S7 Logs screen in Epic 6 |
| FR-45 | Epic 6 | Vite build + StaticFiles serve + SPA catch-all |
| FR-46 | Epics 5+6 | Session status endpoint + Settings page session card |
| FR-47 | Epics 5+6 | OTP connect endpoint + UI connect flow |
| FR-48 | Epics 5+6 | 2FA verification support in backend + UI |
| FR-49 | Epics 5+6 | Terminate session endpoint + UI modal |
| FR-50 | Epics 5+6 | Session auth edge-case error handling |
| FR-51 | Epics 1+5 | TelegramClientHolder reconnect & terminate lifecycle methods |
| UX-DR1–28 | Epic 6 | All UX design requirements |
| NFR-Perf | Epic 4 | Async pipeline, early filter short-circuit |
| NFR-Rel | Epic 4 | Per-rule isolation + retry |
| NFR-RuleChange | Epic 3 | Instant event-driven cache rebuild (<1s) & 30s background fallback |
| NFR-Reconnect | Epic 1 | SQLiteSession auto-reconnect |
| NFR-Propagation | Epic 5 | Edit/delete sync ≤5s |
| NFR-FilterAccuracy | Epic 4 | All 5 filter steps tested |
| NFR-Sec | Epics 1+3+6 | Session secrecy / path containment / cookie auth |
| NFR-Obs | Epic 5 | Full structlog + ring buffer |
| NFR-Maint/Compat | Epics 1–5 | MongoBaseModel + null-safe reads throughout |

## Epic List

### Epic 1: Project Foundation & Telegram Connectivity
Operator can install and start the service, authenticate to Telegram once, and have it auto-reconnect on every subsequent restart; a `/health` endpoint confirms all systems operational.

**FRs covered:** FR-1, FR-2, FR-3, FR-26 (partial), FR-28 (partial), NFR-Reconnect

**Architecture covered:** project scaffold (uv + shadcn init), Pydantic Settings, MongoDB Motor client + base repository, FastAPI app with Clean Architecture skeleton, Docker multi-stage build, FastAPI lifespan, health endpoints, basic structlog + contextvars setup

---

### Epic 2: Source Catalog & Folder Organization
Operator can register Telegram channels/groups as Sources with stable IDs, organize them into Folders, and manage that catalog entirely via the REST API.

**FRs covered:** FR-29, FR-30, FR-31

---

### Epic 3: Forwarding Rule Configuration
Operator can create comprehensive forwarding rules — source/destination, all 5 filter types, all text/media transforms, replacement rules, and attribution — via the REST API; rules are cached atomically in-memory with event-driven instant rebuild (<1s) on mutations, manual refresh endpoint, and periodic 30s background fallback.

**FRs covered:** FR-4, FR-5, FR-6, FR-7, FR-8, FR-12, FR-12a, FR-12b, FR-12c, FR-31a, FR-32, FR-33, FR-34, FR-35, FR-36, FR-37, FR-38, FR-39, FR-41, NFR-RuleChange

---

### Epic 4: Core Message Forwarding Engine
The service actively monitors all registered sources and automatically forwards qualifying messages through the complete 18-step pipeline — the core product working end-to-end.

**FRs covered:** FR-9, FR-10, FR-11, FR-12 (consumed), FR-12a (consumed), FR-12c (consumed), FR-13, FR-14, FR-15, FR-16, FR-19, FR-22, FR-23, FR-24, FR-25, FR-40, NFR-Perf, NFR-Rel, NFR-FilterAccuracy

---

### Epic 5: Edit/Delete Propagation, Full Observability & Stats API
Operator can see edits and deletions reflected in destination channels in near real-time, trace every message's full lifecycle through structured JSON logs with correlation IDs, and manage admin actions via REST (including manual cache refresh endpoint).

**FRs covered:** FR-12b (endpoint), FR-19 (mapping sweeper), FR-20, FR-21, FR-26 (full), FR-27, FR-28 (full), FR-44 (backend SSE infrastructure), NFR-Obs, NFR-Propagation

---

### Epic 6: Web Admin Dashboard
Operator can manage every aspect of the service through a browser — registering sources, creating rules, monitoring live logs, and verifying the pipeline is working — without ever touching curl.

**FRs covered:** FR-42, FR-43, FR-44 (S7 screen), FR-45, UX-DR1 through UX-DR28

---

### Epic 7: Session Management UI & Multi-Tier Cache Control
Operator can authenticate, verify, and terminate Telegram MTProto sessions directly from the Web Admin Settings page without CLI access or restarts, and trigger or automate multi-tier cache rebuilds (instant event rebuild, manual refresh endpoint/button, and fallback background coroutine).

**FRs covered:** FR-12a, FR-12b, FR-12c, FR-46, FR-47, FR-48, FR-49, FR-50, FR-51

---

## Epic 1: Project Foundation & Telegram Connectivity

Operator can install and start the service, authenticate to Telegram once, and have it auto-reconnect on every subsequent restart; `/health` confirms all systems operational.

### Story 1.1: Initialize Project Scaffold & Directory Structure

As a Channel Operator,
I want the project initialized with its complete directory structure and dependency manifests,
So that the development team has a working starting point with clean import boundaries and reproducible builds.

**Acceptance Criteria:**

**Given** the developer runs `uv init forward-bot --python 3.12` plus backend dependencies (fastapi, uvicorn[standard], telethon, motor, pydantic-settings, structlog, itsdangerous) and `npx shadcn@latest init -t vite web` plus @tanstack/react-query and react-router-dom
**When** the commands complete
**Then** the full directory skeleton exists: `src/forward_bot/` with subdirectories domain/entities/, application/pipeline/steps/, application/sources/, application/folders/, application/rules/, application/replacements/, infrastructure/mongo/repositories/, infrastructure/telegram/, infrastructure/logging/, infrastructure/cache/, api/routers/, api/dependencies/, api/schemas/; and `web/src/` with components/ui/, components/shared/, components/layout/, pages/, hooks/, api/, contexts/, lib/, types/

**Given** the project scaffold exists
**When** `uv run python -c "import forward_bot"` is executed
**Then** the import succeeds with no errors (src layout enforces clean import boundaries)

**Given** the project scaffold exists
**When** `cd web && npm run build` is executed
**Then** Vite build completes and outputs to `web/dist/` with no TypeScript errors (strict mode enabled)

**And** `.gitignore` excludes `__pycache__/`, `.venv/`, `.env`, `*.session`, `web/node_modules/`, `web/dist/`; `uv.lock` is committed; `.env.example` documents all env vars with descriptions and no secret values; `pyproject.toml` is the single project manifest

---

### Story 1.2: Configure Application Settings & Database Client

As a Channel Operator,
I want the application to read all configuration from environment variables and connect to MongoDB on startup,
So that I can configure the service by editing `.env` without touching code, and the service fails fast if required vars are missing.

**Acceptance Criteria:**

**Given** a required env var (MONGO_URI, API_KEY, or SECRET_KEY) is missing
**When** the application starts
**Then** startup fails immediately with a clear error message naming the missing variable before any server port is bound

**Given** all required env vars are set
**When** the Settings class is instantiated
**Then** all env vars from addendum §4.1 are parsed with correct types and defaults: MONGO_URI, API_KEY, SECRET_KEY, TELEGRAM_SESSION_PATH, MEDIA_REPLACEMENT_BASE_DIR, SAMPLING_PERSIST (default false), UI_ENABLED (default true), MAPPING_RETENTION_DAYS (default 30), LOG_RING_BUFFER_HOURS (default 1), HOT_RELOAD_INTERVAL (default 30), BIND_HOST (default 127.0.0.1)

**Given** a valid MONGO_URI is configured
**When** a MongoDB document is read via any repository
**Then** ObjectIds are serialized as 24-char hex strings; datetime fields serialize as ISO 8601 UTC strings with Z suffix (e.g., `"2026-05-31T14:23:11Z"`); `MongoBaseModel` base class in `api/schemas/base.py` enforces both conversions for all response models; all six collection names are defined as constants: `forwarding_rules`, `replacement_rules`, `message_mappings`, `sources`, `source_folders`, `sampling_counters`

**Given** the app logs any event
**When** the log output is inspected
**Then** no log line contains the value of API_KEY, SECRET_KEY, or any session bytes; structlog is configured with at minimum: add_log_level, TimeStamper(fmt="iso"), JSONRenderer; every log event includes `event`, `level`, `timestamp` fields (FR-28 foundation)

---

### Story 1.3: FastAPI Application Shell, Health Endpoints & Docker Build

As a Channel Operator,
I want the service to expose health endpoints and be deployable as a Docker container,
So that I can verify the service is running and deploy it to my VPS with `docker compose up`.

**Acceptance Criteria:**

**Given** the FastAPI app is started
**When** `GET /health` is called
**Then** HTTP 200 is returned with `{"status": "ok"}` (liveness — always 200 if process runs)

**Given** MongoDB is reachable
**When** `GET /health/ready` is called
**Then** HTTP 200 is returned with `{"mongodb": "up"}`

**Given** MongoDB is unreachable
**When** `GET /health/ready` is called
**Then** HTTP 503 is returned with `{"mongodb": "down"}`

**Given** Telegram is not yet connected
**When** `GET /health/telegram` is called
**Then** HTTP 200 is returned with `{"telegram": "disconnected", "last_event": null}` (informational, not an error)

**Given** the FastAPI `lifespan` context manager is implemented
**When** the app starts
**Then** MongoDB client connects; future background task coroutines (cache_refresher, mapping_sweeper, telegram_worker) exist as stubs returning immediately — to be replaced in later epics; app shuts down by disconnecting MongoDB cleanly

**Given** `docker build -t forward-bot:latest .` is run
**When** the build completes
**Then** Stage 1 (node:22-slim) runs `npm ci && npm run build` outputting to `/web/dist/`; Stage 2 (python:3.12-slim) installs Python deps via `uv sync --frozen --no-dev` and copies assets to `/app/static/`; `docker run` starts the server and `GET /health` returns 200

**And** `docker-compose.yml` defines app and mongodb services with volume mounts for TELEGRAM_SESSION_PATH, MongoDB data, and MEDIA_REPLACEMENT_BASE_DIR; `Makefile` provides `build`, `run`, and `auth` targets; `/docs` (Swagger UI) and `/redoc` are accessible on a running server

---

### Story 1.4: Telegram Authentication & Session Management

As a Channel Operator,
I want to authenticate to Telegram once via the CLI and have the service reconnect automatically on every restart,
So that I never need to log in again after the initial setup.

**Acceptance Criteria:**

**Given** API_ID, API_HASH, and TELEGRAM_SESSION_PATH are configured
**When** the operator runs `python -m forward_bot auth` inside the container for the first time
**Then** they are prompted for their phone number, then the SMS/2FA code; on success the SQLiteSession artifact is written to TELEGRAM_SESSION_PATH and the process exits 0 with "Authentication successful. Session saved to <path>."

**Given** the authentication step fails (wrong code, network error, invalid credentials)
**When** the command completes
**Then** the process exits with a non-zero code and an actionable error message; no partial session file remains at the path; no secret values appear in error output

**Given** a valid session file exists at TELEGRAM_SESSION_PATH
**When** the FastAPI app starts
**Then** `TelegramClient` connects using `SQLiteSession` without operator interaction; `GET /health/telegram` returns `{"telegram": "connected", "last_event": null}` within 30 seconds (NFR-Reconnect)

**Given** the service is running and connected
**When** the container is restarted
**Then** the service reconnects to Telegram automatically within 30 seconds using the persisted SQLiteSession

**Given** Telegram invalidates the session server-side
**When** the worker attempts to use the session
**Then** the service logs CRITICAL `{"event": "telegram_session_invalidated", "level": "critical", ...}` and exits cleanly; session bytes, API_KEY, and SECRET_KEY values are never present in any log line (FR-3, FR-28)

**And** `src/forward_bot/__main__.py` implements the interactive auth flow; `pyproject.toml` registers `forward-bot-auth = "forward_bot.__main__:run_auth"`; `infrastructure/telegram/client.py` exposes `connect()`, `disconnect()`, and `is_connected` property consumed by the `/health/telegram` endpoint; `GET /health/telegram` returns `{"telegram": "connected" | "disconnected" | "reconnecting", "last_event": "<ISO timestamp or null>"}`

---

## Epic 2: Source Catalog & Folder Organization

Operator can register Telegram channels/groups as Sources with stable IDs, organize them into Folders, and manage that catalog entirely via the REST API.

### Story 2.1: Source Registration & Retrieval

As a Channel Operator,
I want to register a Telegram channel or group as a Source with a display name and have the service resolve its numeric Telegram ID,
So that my forwarding rules reference stable internal IDs that survive Telegram username changes.

**Acceptance Criteria:**

**Given** a valid Telegram username (`@handle`) or numeric ID and display name are provided
**When** `POST /api/v1/sources` is called
**Then** HTTP 201 is returned with the created Source including: server-assigned `id` (ObjectId hex), `telegram_id` (resolved numeric int64), `telegram_username` (null if only numeric ID provided), `display_name`, `type` (`channel` | `group`), `folder_id` (null), `created_at`, `updated_at`

**Given** a Source with the same numeric Telegram ID already exists
**When** `POST /api/v1/sources` is called with the same reference
**Then** HTTP 422 is returned with `{"error": {"code": "source_already_exists", "message": "..."}}` and the `source_registered` event is not logged

**Given** Telegram cannot resolve the provided reference (username not found, private channel not accessible)
**When** `POST /api/v1/sources` is called
**Then** HTTP 422 is returned with `{"error": {"code": "telegram_resolve_failed", "message": "..."}}` — the service attempts one Telegram round-trip to resolve; logs `source_resolve_failed` event

**Given** a Source exists with `id` = `{source_id}`
**When** `GET /api/v1/sources/{source_id}` is called
**Then** HTTP 200 is returned with the full Source document; non-existent ID → HTTP 404 with error envelope `{"error": {"code": "source_not_found", ...}}`

**Given** a Source is referenced by at least one Forwarding Rule
**When** `DELETE /api/v1/sources/{source_id}` is called
**Then** HTTP 409 is returned with `{"error": {"code": "source_in_use", "message": "Source {id} is referenced by {n} rules."}}` listing the rule IDs; the Source is not deleted

**Given** a Source has no Forwarding Rule references
**When** `DELETE /api/v1/sources/{source_id}` is called
**Then** HTTP 204 is returned and the Source document is removed from MongoDB

**And** `Source` domain entity exists in `domain/entities/source.py`; `SourceRepository` in `infrastructure/mongo/repositories/source_repository.py`; `RegisterSource` and `DeleteSource` use cases in `application/sources/`; unique index on `telegram_id` and sparse unique index on `telegram_username` created at startup; logs `source_registered` and `source_resolved` events (FR-27)

---

### Story 2.2: Source Listing & Updates

As a Channel Operator,
I want to list all my registered Sources filtered by type or folder, and update a Source's display name or folder assignment,
So that I can manage a large source catalog efficiently.

**Acceptance Criteria:**

**Given** Sources exist in the catalog
**When** `GET /api/v1/sources` is called
**Then** HTTP 200 is returned with `{"items": [...], "total": N, "page": 1, "page_size": 50}`; each item includes all Source fields; default page_size is 50, max is 200

**Given** a `type` query param is provided
**When** `GET /api/v1/sources?type=channel` is called
**Then** only Sources with `type=channel` are returned; `type=group` returns groups only

**Given** a `folder_id` query param is provided
**When** `GET /api/v1/sources?folder_id={id}` is called
**Then** only Sources assigned to that folder are returned; `?folder_id=null` returns unassigned Sources (folder_id is null in MongoDB)

**Given** a Source exists
**When** `PUT /api/v1/sources/{id}` is called with updated `display_name`, `type`, or `folder_id`
**Then** HTTP 200 is returned with the updated Source; `updated_at` is refreshed to current UTC

**Given** `folder_id` in the update payload references a non-existent folder
**When** `PUT /api/v1/sources/{id}` is called
**Then** HTTP 422 is returned with `{"error": {"code": "folder_not_found", ...}}`

**Given** a Source's Telegram username changes externally
**When** the operator updates `telegram_username` via `PATCH /api/v1/sources/{id}`
**Then** the new username is stored; forwarding rules continue to work because they reference the stable internal `id`

**And** `ListSources` and `UpdateSource` use cases in `application/sources/`; `PATCH /api/v1/sources/{id}` supports partial updates (any subset of `display_name`, `telegram_username`, `folder_id`)

---

### Story 2.3: Folder CRUD

As a Channel Operator,
I want to create, rename, and delete Folders to organize my Sources into logical groups,
So that I can manage 40+ sources without visual clutter and filter forwarding rules by folder.

**Acceptance Criteria:**

**Given** a unique folder name is provided
**When** `POST /api/v1/folders` is called
**Then** HTTP 201 is returned with the created Folder: `id`, `name`, `created_at`, `updated_at`; logs `folder_created` event (FR-27)

**Given** a folder name that already exists is provided
**When** `POST /api/v1/folders` is called
**Then** HTTP 422 is returned with `{"error": {"code": "folder_name_in_use", "message": "Folder name in use: {name}."}}`

**Given** folders exist
**When** `GET /api/v1/folders` is called
**Then** HTTP 200 is returned with all folders; each entry includes a `source_count` showing how many Sources are assigned to it

**Given** a folder exists
**When** `GET /api/v1/folders/{id}?include=sources` is called
**Then** the response includes the folder plus an embedded `sources` array of all Sources assigned to it

**Given** a new unique name is provided
**When** `PUT /api/v1/folders/{id}` (rename) is called
**Then** HTTP 200 is returned with the updated folder; if the new name collides with an existing folder → HTTP 422 with `folder_name_in_use`

**Given** a folder contains Sources
**When** `DELETE /api/v1/folders/{id}` is called
**Then** HTTP 204 is returned; all Sources assigned to this folder have their `folder_id` set to null; the Sources themselves are not deleted; the folder document is removed

**And** `SourceFolder` domain entity in `domain/entities/source_folder.py`; `FolderRepository` in `infrastructure/mongo/repositories/folder_repository.py`; use cases: `CreateFolder`, `ListFolders`, `RenameFolder`, `DeleteFolder` in `application/folders/`; unique index on `source_folders.name` created at startup

---

## Epic 3: Forwarding Rule Configuration

Operator can create comprehensive forwarding rules — source/destination, all 5 filter types, all text/media transforms, replacement rules, and attribution — via the REST API; rules are cached atomically in-memory and hot-reloaded every 30s.

### Story 3.1: Forwarding Rule CRUD API

As a Channel Operator,
I want to create, read, update, delete, enable, and disable Forwarding Rules via the REST API with complete filter and transform configuration,
So that I can precisely control what gets forwarded and how, without restarting the service.

**Acceptance Criteria:**

**Given** a valid payload with `source_id`, `destination_channel`, and optional config fields
**When** `POST /api/v1/rules` is called
**Then** HTTP 201 is returned with the persisted rule including all fields at their defaults: `is_active=false`, `keyword_match_mode="literal"`, `block_keywords=[]`, `allow_keywords=[]`, `media_type_filter=["text","photo"]`, `remove_links=false`, `remove_hashtags=false`, `remove_mentions=false`, `forward_media="forward"`, `sampling={"n":1}`, `time_window=null`, `attribution={"enabled":false,"position":"prefix","format":"From {source_name}"}`, `auto_replace_source_refs={"enabled":false,"replacement":null,"replace_display_name":false}`, `media_replacement={"enabled":false,"replacement_image_path":null,"replacement_caption_mode":"use_source"}`, `created_at`, `updated_at`

**Given** `source_id` references a non-existent Source
**When** `POST /api/v1/rules` is called
**Then** HTTP 422 is returned with `{"error": {"code": "source_not_found", ...}}`

**Given** `source_id` and `destination_channel` refer to the same Telegram entity
**When** `POST /api/v1/rules` is called
**Then** HTTP 422 is returned with `{"error": {"code": "self_referential_rule", "message": "Cannot create rule: source equals destination."}}`

**Given** `keyword_match_mode` is `regex` and a keyword contains an invalid regex pattern
**When** `POST` or `PUT /api/v1/rules/{id}` is called
**Then** HTTP 422 is returned identifying the offending pattern: `{"error": {"code": "invalid_regex", "message": "Invalid regex /{pattern}/: {reason}."}}`

**Given** `time_window.end_time` < `time_window.start_time`
**When** `POST` or `PUT` is called
**Then** the rule is accepted without error (cross-midnight windows are valid per FR-32)

**Given** `time_window.timezone` is not a valid IANA timezone name
**When** `POST` or `PUT` is called
**Then** HTTP 422 is returned with `{"error": {"code": "invalid_timezone", ...}}`

**Given** `media_replacement.enabled=true` and `replacement_image_path` is null
**When** `POST` or `PUT` is called
**Then** HTTP 422 is returned with `{"error": {"code": "media_replacement_path_required", ...}}`

**Given** a rule exists
**When** `POST /api/v1/rules/{id}/enable` is called
**Then** HTTP 200 is returned with `{"ok": true}`; `is_active` becomes `true` in MongoDB

**Given** a rule exists
**When** `POST /api/v1/rules/{id}/disable` is called
**Then** HTTP 200 is returned with `{"ok": true}`; `is_active` becomes `false` in MongoDB

**Given** rules exist
**When** `GET /api/v1/rules` is called with optional filters `?source_id=`, `?destination_channel=`, `?is_active=`, `?folder_id=`
**Then** paginated response `{"items":[...],"total":N,"page":N,"page_size":50}` is returned; `folder_id` filter joins via the Source's `folder_id`

**Given** a rule is deleted
**When** `DELETE /api/v1/rules/{id}` is called
**Then** HTTP 204 is returned; all associated Replacement Rules are cascade-deleted

**And** `ForwardingRule` domain entity in `domain/entities/forwarding_rule.py` with all sub-config dataclasses; `ForwardingRuleRepository` in `infrastructure/mongo/repositories/rule_repository.py`; use cases `CreateRule`, `ListRules`, `UpdateRule`, `DeleteRule`, `EnableRule`, `DisableRule` in `application/rules/`; compound index `(source_id, is_active)` and index `(is_active)` created at startup; A1 error envelope used for all non-422 errors; `get_current_operator` dependency (X-API-Key check via `secrets.compare_digest`) wired to all rule endpoints

---

### Story 3.2: Replacement Rule CRUD API

As a Channel Operator,
I want to create, list, update, and delete Replacement Rules scoped to a Forwarding Rule supporting both literal and regex substitutions,
So that I can rewrite forwarded text — removing competitor names, swapping links, or applying regex patterns — without touching code.

**Acceptance Criteria:**

**Given** a parent rule exists and valid `search_text`, `replacement_text`, and `match_mode` are provided
**When** `POST /api/v1/rules/{rule_id}/replacement-rules` is called
**Then** HTTP 201 is returned with: `id`, `forwarding_rule_id`, `search_text`, `replacement_text`, `match_mode` (`literal`|`regex`), `is_active` (default `true`), `created_at`, `updated_at`

**Given** `match_mode` is `regex` and `search_text` is an invalid regex pattern
**When** `POST` or `PUT` on a replacement rule is called
**Then** HTTP 422 is returned with `{"error": {"code": "invalid_regex", "message": "Invalid regex /{pattern}/: {reason}."}}`

**Given** replacement rules exist for a parent rule
**When** `GET /api/v1/rules/{rule_id}/replacement-rules` is called
**Then** HTTP 200 is returned with all replacement rules ordered by `created_at` ascending (this is the pipeline application order per FR-7)

**Given** a replacement rule exists
**When** `PUT /api/v1/rules/{rule_id}/replacement-rules/{id}` is called with updated fields
**Then** HTTP 200 is returned with the updated replacement rule; `updated_at` is refreshed

**Given** a replacement rule exists
**When** `DELETE /api/v1/rules/{rule_id}/replacement-rules/{id}` is called
**Then** HTTP 204 is returned; the document is removed

**Given** the parent Forwarding Rule is deleted via `DELETE /api/v1/rules/{rule_id}`
**When** the delete executes
**Then** all child Replacement Rules for that rule are cascade-deleted from MongoDB

**And** `ReplacementRule` domain entity in `domain/entities/replacement_rule.py`; `ReplacementRuleRepository` in `infrastructure/mongo/repositories/replacement_repository.py`; use cases in `application/replacements/`; compound index `(forwarding_rule_id, is_active, created_at)` created at startup; literal match is case-insensitive substring replacement (FR-8); regex supports Python `re` semantics with capture-group backreferences in `replacement_text`

---

### Story 3.3: Multi-Tier Rule Cache & Cache Refresher

As a Channel Operator,
I want rule changes I make via the API to take effect in the forwarding pipeline instantly (<1s) and have a manual refresh endpoint as well as a background safety net,
So that configuration changes take effect immediately without needing service restarts or periodic delays.

**Acceptance Criteria:**

**Given** active Forwarding Rules and their Replacement Rules exist in MongoDB
**When** the periodic cache refresher coroutine runs (every `HOT_RELOAD_INTERVAL` seconds, default 30)
**Then** it fetches all four collections (sources, source_folders, forwarding_rules, replacement_rules) in sequence, builds a new frozen `RuleCache` dataclass, and replaces `CacheHolder.current` in a single Python assignment — atomic under the asyncio event loop; the new cache is visible to the next pipeline dispatch (FR-12c)

**Given** any REST API operation mutates rules, replacement rules, sources, or folders (Create, Update, Delete, Enable, Disable)
**When** the DB operation completes successfully
**Then** the system immediately triggers an asynchronous in-memory rebuild of `RuleCache` and atomically swaps `CacheHolder.current` in <1 second without blocking the API HTTP response (FR-12a)

**Given** the operator wants to force a cache refresh out-of-band or via the admin API
**When** `POST /api/v1/admin/cache/refresh` (or `/api/v1/cache/refresh`) is called
**Then** HTTP 200 is returned with cache metadata (`version`, `rule_count`, `source_count`, `refreshed_at` timestamp) after triggering an immediate `build_rule_cache()` call (FR-12b)

**Given** rules contain regex patterns in `block_keywords`, `allow_keywords`, or `replacement_rules`
**When** the cache is refreshed
**Then** all regex patterns are compiled to `re.Pattern` objects and stored in `RuleCache.compiled_patterns` keyed by rule ID; compilation happens once per refresh cycle, not per message dispatched

**Given** a regex pattern in a rule fails to compile
**When** the cache is refreshed
**Then** an ERROR is logged with `rule_id` and the offending pattern; that pattern is skipped (no-op) for this snapshot's lifetime; the refresh completes normally and all other rules load correctly

**Given** MongoDB is temporarily unreachable during a refresh attempt
**When** the refresh fails
**Then** `CacheHolder.current` retains the last valid snapshot; a WARNING is logged with `{"event": "cache_refresh_failed", "last_successful_refresh": "<ISO timestamp>", ...}`; the refresher retries on the next interval without crashing

**And** `RuleCache` frozen dataclass and `CacheHolder` in `infrastructure/cache/rule_cache.py`; `RuleCache` fields: `sources: dict[ObjectId, Source]`, `folders: dict[ObjectId, SourceFolder]`, `rules: list[ForwardingRule]` (active only), `replacements: dict[ObjectId, list[ReplacementRule]]`, `compiled_patterns: dict[ObjectId, CompiledPatterns]`, `version: int`; `cache_refresher` coroutine in `infrastructure/cache/cache_refresher.py`; FastAPI admin router in `api/routers/admin.py` exposing `POST /api/v1/admin/cache/refresh`; mutation hooks calling `trigger_cache_rebuild()` wired across rule, source, folder, and replacement routers

---

## Epic 4: Core Message Forwarding Engine

The service actively monitors all registered sources and automatically forwards qualifying messages through the complete 18-step pipeline — the core product working end-to-end.

### Story 4.1: Pipeline Infrastructure — Context, Protocol, Engine & Message Mapping

As a Channel Operator,
I want the forwarding pipeline to have a well-defined structure so that each processing step can be built, tested, and replaced independently,
So that the system is maintainable as new filter and transform steps are added.

**Acceptance Criteria:**

**Given** the pipeline infrastructure is implemented
**When** `application/pipeline/protocol.py` is inspected
**Then** it defines the `PipelineStep` protocol with `name: str` and `async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome`

**Given** a `PipelineContext` is created for a Source Message + Forwarding Rule pair
**When** it is passed through `pipeline/engine.py`
**Then** it carries: `text`, `caption`, `media`, `attribution_decided: bool`, `reply_target_destination_id: int | None`, `correlation_id: str`, `rule` (frozen snapshot), `source` (frozen snapshot), `metadata: dict` (mutable); the engine iterates the 18-step sequence and returns either the final `PipelineContext` or the first `BlockedOutcome`

**Given** a step raises an unexpected exception
**When** the engine runs that step
**Then** the exception is caught inside the step's `apply()` method, logged as ERROR with `correlation_id`, and returned as `BlockedOutcome(reason="step_error")`; the exception never propagates to the worker loop

**Given** a message is successfully forwarded
**When** the pipeline delivers it (delivery stub at this stage)
**Then** a `MessageMapping` document is persisted with: `forwarding_rule_id`, `source_channel_id`, `source_message_id`, `destination_channel_id`, `destination_message_id`, `forwarded_at`

**Given** a `source_message_id` and `forwarding_rule_id` are known
**When** `MappingRepository.get_by_source_message` is queried
**Then** the matching `MessageMapping` is returned (supports reply lookup in step 7)

**And** `PipelineContext` and `BlockedOutcome` in `domain/entities/pipeline_context.py`; `MessageMapping` in `domain/entities/message_mapping.py`; `MappingRepository` in `infrastructure/mongo/repositories/mapping_repository.py`; `pipeline/engine.py` orchestrates steps with per-rule exception isolation; index on `(forwarding_rule_id, source_channel_id, source_message_id)` on `message_mappings` created at startup; `BLOCK_REASONS` constant set defined: `{"outside_time_window","sampled_out","media_type_filtered","blocked_keyword","no_allow_keyword_matched","empty_after_processing","unsupported_media_type","step_error"}`

---

### Story 4.2: Filter Pipeline Steps (Steps 1–5)

As a Channel Operator,
I want incoming messages to be filtered by time-window, sampling rate, media type, and keyword rules before any expensive transforms run,
So that irrelevant messages are dropped early and the pipeline stays efficient.

**Acceptance Criteria:**

**Given** a rule has `time_window` configured and a message arrives outside the window
**When** `TimeWindowStep.apply()` runs (step 1)
**Then** it returns `BlockedOutcome(reason="outside_time_window")`; window is evaluated against message `date` in the rule's IANA timezone via Python `zoneinfo`; cross-midnight windows (end < start) are handled correctly

**Given** a rule has `sampling.n=3` and this message does not fall on a 3rd-cycle position
**When** `SamplingStep.apply()` runs (step 2)
**Then** it returns `BlockedOutcome(reason="sampled_out")`; the n-th message passes through; counter is stored in `PipelineContext.metadata["sampling_counters"]` (in-memory dict keyed by rule ID); when `SAMPLING_PERSIST=true`, counter reads/writes `sampling_counters` collection via `SamplingRepository`

**Given** a rule has `media_type_filter=["text"]` and the message contains a photo
**When** `MediaTypeFilterStep.apply()` runs (step 3)
**Then** it returns `BlockedOutcome(reason="media_type_filtered")`

**Given** a rule has `block_keywords=["pump"]`, `keyword_match_mode="literal"`, and message text contains "pumping"
**When** `BlockKeywordStep.apply()` runs (step 4)
**Then** it returns `BlockedOutcome(reason="blocked_keyword", matched_keyword="pump")` (case-insensitive substring match per FR-36)

**Given** a rule has `block_keywords=["pump"]`, `keyword_match_mode="regex"`, and message text matches
**When** `BlockKeywordStep.apply()` runs (step 4)
**Then** it uses the pre-compiled `re.Pattern` from `RuleCache.compiled_patterns`

**Given** a rule has `allow_keywords=["BTC","ETH"]` and the message text matches neither
**When** `AllowKeywordStep.apply()` runs (step 5)
**Then** it returns `BlockedOutcome(reason="no_allow_keyword_matched")`

**Given** a rule has `allow_keywords=[]` (default — allow everything)
**When** `AllowKeywordStep.apply()` runs (step 5)
**Then** the context passes through unchanged

**Given** any filter step returns `BlockedOutcome`
**When** the engine processes it
**Then** all subsequent steps are skipped; the outcome is returned immediately (short-circuit)

**And** step classes: `TimeWindowStep`, `SamplingStep`, `MediaTypeFilterStep`, `BlockKeywordStep`, `AllowKeywordStep` in `application/pipeline/steps/`; `SamplingRepository` in `infrastructure/mongo/repositories/sampling_repository.py`; each step has a test file in `tests/application/pipeline/steps/` covering pass and block cases; false-positive and false-negative rates ≤0.5% per filter type on a curated test corpus (NFR-FilterAccuracy)

---

### Story 4.3: Transform & Media Pipeline Steps (Steps 6–16)

As a Channel Operator,
I want forwarded messages to be cleaned and rewritten — stripping links/hashtags/mentions, substituting text patterns, auto-replacing source references, and optionally swapping the photo — before delivery,
So that destination channels receive polished, on-brand content without manual editing.

**Acceptance Criteria:**

**Given** `forward_media="forward"` and the message has a photo
**When** `MediaDecisionStep.apply()` runs (step 6)
**Then** context `media` is set to forward the photo; `forward_media="ignore"` → media set to None; `forward_media="caption_only"` → media set to None, caption text retained

**Given** the message is a Telegram reply and a `MessageMapping` exists for the parent under the same rule
**When** `ReplyLookupStep.apply()` runs (step 7)
**Then** `ctx.reply_target_destination_id` is set to the parent's `destination_message_id`

**Given** the message is a reply but no parent mapping exists (filtered or outside retention)
**When** `ReplyLookupStep.apply()` runs (step 7)
**Then** `ctx.reply_target_destination_id` remains `None`; `reply_parent_not_found` is logged; message proceeds as standalone

**Given** `auto_replace_source_refs.enabled=true` and message text contains `@SourceChannel`
**When** `SourceRefReplaceStep.apply()` runs (step 8)
**Then** all occurrences of `@<source_username>`, `t.me/<source_username>`, `https://t.me/<source_username>` are replaced with the destination's identifier; runs before generic replacement rules (FR-39)

**Given** active Replacement Rules exist for the rule
**When** `TextReplacementStep.apply()` runs (step 9)
**Then** literal rules perform case-insensitive substring replacement; regex rules apply `re.sub` semantics with capture-group backreferences; applied in `created_at` order using pre-compiled patterns from `RuleCache`

**Given** `remove_links=true`
**When** `LinkRemovalStep.apply()` runs (step 10)
**Then** `http://`, `https://`, `t.me/`, `telegram.me/`, `tg://`, and joinchat/+ invite-link patterns are stripped from text and caption (FR-13)

**Given** `remove_hashtags=true` / `remove_mentions=true`
**When** steps 11 and 12 run
**Then** `#hashtag` tokens stripped (step 11); `@username` tokens stripped (step 12)

**Given** `media_replacement.enabled=true` and Source Message has a photo
**When** `MediaReplacementStep.apply()` runs (step 13)
**Then** candidate path resolved as `Path(MEDIA_REPLACEMENT_BASE_DIR) / replacement_image_path`; path asserted to be within base dir (S3 security check) — traversal attempt logs WARNING `media_replacement_path_traversal_attempt` and falls back to source photo; unreadable file logs WARNING `media_replacement_failed` and falls back; `asyncio.to_thread()` used for the file read (no blocking I/O in coroutine)

**Given** removal steps introduced multiple consecutive spaces
**When** `WhitespaceStep.apply()` runs (step 14)
**Then** runs of whitespace collapsed to single spaces; leading/trailing whitespace stripped

**Given** `attribution.enabled=true` and `position="prefix"`
**When** `AttributionStep.apply()` runs (step 15)
**Then** formatted attribution line (with `{source_name}` and `{source_username}` substituted) is prepended to text; if source message is photo-only with no caption, attribution becomes the caption

**Given** all transforms have run and the resulting text/caption is empty AND no media is being forwarded
**When** `EmptyCheckStep.apply()` runs (step 16)
**Then** `BlockedOutcome(reason="empty_after_processing")` is returned

**And** step classes in `application/pipeline/steps/`: `MediaDecisionStep`, `ReplyLookupStep`, `SourceRefReplaceStep`, `TextReplacementStep`, `LinkRemovalStep`, `HashtagRemovalStep`, `MentionRemovalStep`, `MediaReplacementStep`, `WhitespaceStep`, `AttributionStep`, `EmptyCheckStep`; steps 6–16 wired into `engine.py` in canonical order

---

### Story 4.4: Telegram Delivery & Reliability

As a Channel Operator,
I want the service to handle Telegram rate limits and transient errors gracefully, retrying failed deliveries without crashing the pipeline for other rules,
So that my 99% reliability target is met even under adverse Telegram API conditions.

**Acceptance Criteria:**

**Given** a forwarded message is ready (step 17)
**When** `delivery.py` sends it via Telethon
**Then** the message is sent; `destination_message_id` is captured; `MessageMapping` is persisted (step 18)

**Given** Telegram returns `FloodWaitError` with a wait duration
**When** delivery attempts to send
**Then** delivery waits the specified duration then retries; logs `{"event": "flood_wait", "wait_seconds": N, "rule_id": "...", "correlation_id": "..."}` at WARNING

**Given** a transient Telegram error occurs (connection reset, timeout)
**When** delivery fails
**Then** it retries with exponential backoff up to a configured retry budget; after exhausting retries, logs ERROR `{"event": "forward_failed", ...}` and gives up on that message for that rule (FR-23)

**Given** one rule's delivery raises an unhandled exception
**When** the engine processes multiple rules for the same Source Message
**Then** the exception is caught at the per-rule level; other rules' pipeline runs are unaffected (FR-24)

**Given** SIGTERM or SIGINT is received
**When** the service shuts down
**Then** in-flight pipeline runs finish before exit; Telegram client disconnects cleanly; `lifespan` cancels all background tasks and awaits `CancelledError`; no partial `MessageMapping` documents left uncommitted (FR-25)

**And** `delivery.py` in `infrastructure/telegram/` handles send, FloodWait, retry, and mapping persistence; `engine.py` wraps each rule's pipeline in `try/except` for per-rule isolation; delivery (step 17) and mapping persistence (step 18) are final steps in `engine.py`

---

### Story 4.5: Telegram Worker & End-to-End Message Forwarding

As a Channel Operator,
I want the service to automatically monitor my registered sources and forward qualifying messages as they arrive,
So that forwarding is fully automatic — I configure the rules and the service does the rest.

**Acceptance Criteria:**

**Given** active Forwarding Rules reference registered sources
**When** the Telegram worker starts (replaces lifespan stub from Story 1.3)
**Then** the worker subscribes to all unique sources referenced by active rules within one `HOT_RELOAD_INTERVAL`; Telethon event handlers are registered for `NewMessage` events on all active sources

**Given** a new message arrives in a subscribed source
**When** the worker's event handler fires
**Then** a short `correlation_id` (8-char hex) is generated and bound via `structlog.contextvars.bind_contextvars`; `cache_holder.current` is read once as the snapshot for this dispatch; for each active rule whose `source_id` matches, the pipeline engine is called independently; contextvars are cleared after all rules are processed

**Given** the pipeline returns a `BlockedOutcome`
**When** the worker logs the result
**Then** `{"event": "pipeline_blocked", "reason": "<reason>", "rule_id": "...", "correlation_id": "..."}` is emitted at INFO

**Given** the pipeline delivers a message successfully
**When** the worker logs the result
**Then** `{"event": "forward_succeeded", "rule_id": "...", "source_message_id": N, "destination_message_id": N, "correlation_id": "..."}` is emitted at INFO

**Given** `SAMPLING_PERSIST=false` (default)
**When** the worker starts
**Then** an in-memory `{rule_id: int}` counter dict is initialized and passed via `PipelineContext.metadata["sampling_counters"]`; the dict persists across messages within a process lifetime and resets on restart (FR-33)

**Given** 100 active sources with normal message traffic
**When** the worker is running
**Then** P95 forwarding latency from message receipt to destination post ≤ 3 seconds (NFR-Perf); no blocking I/O in the event handler or pipeline — all I/O is `async` or via `asyncio.to_thread()`

**And** `worker.py` in `infrastructure/telegram/`; the telegram_worker asyncio task replaces the stub from Story 1.3; all four lifespan tasks now live: MongoDB client, cache_refresher, mapping_sweeper (stub replaced in Epic 5), telegram_worker; end-to-end smoke test: register source → create + activate rule → send test message → verify `forward_succeeded` log and message in destination

---

## Epic 5: Edit/Delete Propagation, Full Observability & Stats API

Operator can see edits and deletions reflected in destination channels in near real-time, trace every message's full lifecycle through structured JSON logs with correlation IDs, and access the stats/log endpoints the dashboard needs.

### Story 5.1: Edit & Delete Propagation + Mapping Sweeper

As a Channel Operator,
I want edits and deletions to source messages to be reflected automatically in the forwarded copies, and old mapping records cleaned up periodically,
So that destination channels stay in sync with source content and my database stays lean.

**Acceptance Criteria:**

**Given** a Source Message is edited in a source channel
**When** Telethon fires an `EditMessage` event
**Then** the worker looks up all `MessageMappings` for that `(source_channel_id, source_message_id)` pair; for each mapping, the destination message is edited via Telethon with the updated text/caption; logs `{"event": "edit_propagated", "rule_id": "...", "source_message_id": N, "destination_message_id": N, "correlation_id": "..."}`

**Given** a Source Message is deleted from a source channel
**When** Telethon fires a `DeleteMessage` event
**Then** the worker looks up all `MessageMappings` for that source message; for each mapping the destination message is deleted via Telethon; logs `{"event": "delete_propagated", "rule_id": "...", "source_message_id": N, "destination_message_id": N, "correlation_id": "..."}`

**Given** a source message has no `MessageMapping` (was filtered out or never forwarded)
**When** an edit or delete event arrives for it
**Then** the event is silently ignored; no error logged

**Given** the edit or delete Telegram call fails (destination message already deleted, permissions lost)
**When** the propagation attempt runs
**Then** the failure is logged at WARNING; `FloodWaitError` is handled with the same wait-and-retry logic as delivery; the failure does not crash the worker

**Given** `message_mappings` documents exist with `forwarded_at` older than `MAPPING_RETENTION_DAYS`
**When** the `mapping_sweeper` coroutine runs (hourly, replacing the lifespan stub from Story 4.5)
**Then** all expired documents are deleted via a single indexed Motor query on `forwarded_at`; logs `{"event": "mapping_sweep_completed", "deleted_count": N}`

**And** edit and delete event handlers wired into `worker.py`; `mapping_sweeper` in `infrastructure/mongo/mapping_sweeper.py` replaces the lifespan stub; propagation ≤5s at ≥95% of cases (NFR-Propagation)

---

### Story 5.2: Full Structlog Chain, Ring Buffer & Complete Event Catalog

As a Channel Operator,
I want every pipeline event logged as structured JSON with a correlation ID so I can trace any message's full journey,
So that I can diagnose any issue from logs alone without restarting or instrumenting the service.

**Acceptance Criteria:**

**Given** structlog is fully configured
**When** any log event is emitted anywhere in the system
**Then** the processor chain executes: `merge_contextvars` → `add_log_level` → `TimeStamper(fmt="iso")` → `append_to_ring_buffer` → `JSONRenderer`; every event includes `event`, `level`, `timestamp`, `correlation_id` fields; output is newline-delimited JSON on stdout

**Given** `append_to_ring_buffer` is wired into the processor chain
**When** a log event is processed
**Then** the event dict is appended to the in-process `collections.deque(maxlen=N)` where N is derived from `LOG_RING_BUFFER_HOURS`; the same event is fanned out to all active SSE subscriber `asyncio.Queue` objects in the fan-out set

**Given** the ring buffer is full
**When** a new event is appended
**Then** the oldest entry is automatically evicted (deque behavior); no error; the ring buffer never blocks the processor chain

**Given** any pipeline event occurs across all event types
**When** the event is logged
**Then** the correct snake_case event name from the catalog is used (FR-27): `forward_succeeded`, `pipeline_blocked`, `edit_propagated`, `delete_propagated`, `flood_wait`, `cache_refresh_failed`, `mapping_sweep_completed`, `source_registered`, `source_resolved`, `folder_created`, `reply_parent_not_found`, `reply_target_missing`, `media_replacement_failed`, `telegram_session_invalidated`, `source_already_exists`, `telegram_resolve_failed`; event names use underscores, never hyphens

**Given** any log output is inspected
**When** any event from any module is examined
**Then** no log line contains API_KEY, SECRET_KEY, session file bytes, or any other secret credential (FR-28 complete coverage)

**And** `infrastructure/logging/setup.py` configures structlog; `infrastructure/logging/ring_buffer.py` implements the deque and the structlog processor step; `infrastructure/logging/sse_broadcaster.py` manages the asyncio.Queue fan-out set; logging initialized in `main.py` before lifespan starts

---

### Story 5.3: SSE Log Broadcaster & Stats/Log API Endpoints

As a Channel Operator,
I want to stream live logs via SSE and query recent log history and summary stats via REST endpoints,
So that the operator dashboard has all the backend data feeds it needs.

**Acceptance Criteria:**

**Given** a client connects to `GET /api/v1/logs/stream`
**When** the SSE connection opens
**Then** all current ring buffer entries are replayed to the client first; the client's `asyncio.Queue` is added to the fan-out set; subsequent log events are pushed as SSE `data:` messages (JSON-encoded); filterable via `?event=<name>` and `?correlation_id=<id>` query params

**Given** a client disconnects from `GET /api/v1/logs/stream`
**When** the connection closes (client closes or `CancelledError`)
**Then** the client's queue is removed from the fan-out set; no further events pushed; no memory leak

**Given** `GET /api/v1/logs/recent?limit=50` is called
**When** the endpoint responds
**Then** up to `limit` (default 50, max 500) most-recent ring buffer entries returned as `{"items": [...]}` in chronological order; supports optional `?event=` and `?correlation_id=` filters

**Given** `GET /api/v1/logs/search?correlation_id=a3f9b2c1` is called
**When** the endpoint responds
**Then** all ring-buffer entries matching that `correlation_id` are returned; `?since=<ISO timestamp>` filters to events after that time (default last 1h, max 24h window)

**Given** `GET /api/v1/stats/summary` is called
**When** the endpoint responds
**Then** returns `{"forwarded_24h": N, "failed_24h": N, "blocked_24h": N}` tallied from the ring buffer over the last 24 hours; documented as approximate (ring-buffer bounded)

**Given** `POST /api/v1/admin/reconnect` is called by an authenticated operator
**When** the endpoint executes
**Then** it triggers a Telegram client reconnect attempt; returns `{"ok": true}` immediately (fire-and-forget); reconnect result appears in the log stream; requires `get_current_operator` auth

**And** `api/routers/logs.py`, `api/routers/stats.py`, `api/routers/admin.py` implement their respective endpoints; all endpoints protected by `get_current_operator`; SSE endpoint registered before the SPA catch-all route

---

## Epic 6: Web Admin Dashboard

### Story 6.1: React SPA Foundation — Brand Tokens, App Layout & Authentication

As a Channel Operator,
I want a polished, consistently branded single-page application that authenticates me with a session cookie and provides a persistent sidebar navigation,
So that I can operate the bot confidently from a professional interface without re-entering credentials on every page refresh.

**Acceptance Criteria:**

**Given** the frontend scaffold is initialized with `npx shadcn@latest init -t vite web` inside `web/`
**When** the Vite build runs (`npm run build`)
**Then** the compiled output lands in `web/dist/` and FastAPI's `StaticFiles` mount at `/` serves it; the FastAPI catch-all route `GET /{full_path:path}` returning `index.html` is the last route registered in `api/main.py` (after all API routers and the SSE endpoint)

**Given** the DESIGN.md brand token YAML is present
**When** `web/src/styles/tokens.css` is written
**Then** it declares all CSS custom properties for both `[data-theme="light"]` and `[data-theme="dark"]` selectors: warm-stone palette (`--color-bg`, `--color-surface`, `--color-border`, `--color-text-primary`, `--color-text-secondary`), Forwarding Green (`--color-active` = `#16A34A` light / `#22C55E` dark), state colors (`--color-success`, `--color-warning`, `--color-error`, `--color-degraded`), and monospace font stack (`--font-mono`)

**Given** a user visits any page when no session cookie is present
**When** the `RequireAuth` wrapper evaluates auth state via `GET /api/v1/auth/me`
**Then** the user is redirected to `/login`; the Login page renders an operator-password field and Submit button; on success `POST /api/v1/auth/login` returns HTTP 200 and sets the `session` cookie; the user is redirected to `/` (Dashboard); on wrong password HTTP 401 renders an inline error message

**Given** the user is authenticated
**When** any page mounts
**Then** the persistent sidebar renders: Forward Bot logo/wordmark, nav items for Dashboard (`/`), Forwards (`/forwards`), Sources (`/sources`), Logs (`/logs`), Settings (`/settings`); active route is highlighted; a theme-toggle button switches `data-theme` on `<html>` and persists choice to `localStorage`

**Given** the user is on any screen
**When** they press `g` then `d` (vim-style two-key chord)
**Then** they navigate to Dashboard; `g→f` → Forwards; `g→s` → Sources; `g→l` → Logs; `g→,` → Settings; chord resets after 1 000 ms with no second key

**Given** React Router v7 Declarative mode is used
**When** `web/src/main.tsx` is reviewed
**Then** it uses `BrowserRouter` + `Routes` (not `createBrowserRouter`); all route definitions live in `web/src/routes/`

**And** `web/src/api/client.ts` exports the Axios instance with `baseURL: '/api/v1'` and `withCredentials: true`; `web/src/lib/queryClient.ts` exports the TanStack Query `QueryClient` instance; `web/src/lib/queryKeys.ts` exports the centralized key factory; `web/src/api/auth.ts` contains `login`, `logout`, `me` calls; auth state is managed via a `useAuth` hook backed by TanStack Query

---

### Story 6.2: Shared UI Component Library

As a Channel Operator,
I want all recurring UI elements — degraded banners, log rows, status pills, collapsible panels, and activation banners — implemented as reusable components with full accessibility support,
So that every screen is visually consistent and usable with keyboard and screen readers.

**Acceptance Criteria:**

**Given** the component library exists in `web/src/components/ui/`
**When** `DegradedBanner` is rendered
**Then** it displays with `--color-degraded` background and a reconnect affordance matching the banner-degraded DESIGN.md spec; it accepts `onReconnect: () => void` and `message: string` props; it renders with `role="alert"` and `aria-live="assertive"`

**Given** `LogRow` is rendered with a log entry prop
**When** the entry has severity `error`
**Then** it applies the `log-row-error` variant token (red left border, red text); severity variants are: `info` (neutral), `warning` (amber), `error` (red), `success` (green) — all four matching the DESIGN.md log-row spec

**Given** `FilterIconRow` is rendered with a rule's filter configuration
**When** the rule has `time_window` active, `block_keywords` set, and `sampling` set
**Then** each active filter renders its icon in `--color-active` (green); inactive filters render in `--color-text-secondary` (muted); icons use accessible `title` attributes describing the filter

**Given** `StatusPill` is rendered with a status value
**When** the status is `active`
**Then** it renders with the pill-success token (`--color-success` background, white text); `inactive` renders neutral; `error` renders `--color-error`

**Given** `CollapsiblePanel` is rendered
**When** the user clicks the panel header or presses `Enter`/`Space` on it
**Then** the panel body toggles open/closed with an animated chevron; the trigger has `aria-expanded` toggled and `aria-controls` pointing to the panel body; the panel body has a matching `id`

**Given** `ActivationBanner` is rendered with `isFirstRun={true}`
**When** the dashboard mounts and no forwarding rules exist
**Then** the activation banner renders with the activation-banner DESIGN.md spec and a "Create your first rule" CTA button that navigates to `/forwards/new`

**And** all interactive components meet the accessibility floor: minimum 4.5:1 contrast ratio for text, `aria-label` on icon-only buttons, keyboard focus rings visible in both themes; components are exported from `web/src/components/ui/index.ts`

---

### Story 6.3: Dashboard (S1) & Settings (S8) Screens

As a Channel Operator,
I want a dashboard showing system health and recent activity, and a settings page for system configuration,
So that I can assess bot status at a glance and adjust operational settings without editing config files.

**Acceptance Criteria:**

**Given** the operator navigates to `/` (Dashboard, S1)
**When** the page loads
**Then** TanStack Query fetches `GET /api/v1/health` with `staleTime: 30_000` and `GET /api/v1/stats/summary` with `staleTime: 60_000`; the health card displays: Telegram connectivity status (green/red), MongoDB status (green/red), active rule count; the stats panel displays `forwarded_24h`, `failed_24h`, `blocked_24h`

**Given** the health endpoint returns `telegram_status: "degraded"`
**When** the Dashboard renders
**Then** the `DegradedBanner` component mounts above the health cards with the reconnect affordance visible; clicking "Reconnect" calls `POST /api/v1/admin/reconnect` and shows a toast "Reconnect initiated"

**Given** the Recent Activity panel is on the Dashboard
**When** the panel renders
**Then** it displays the last 20 log entries from the ring buffer via `GET /api/v1/logs?limit=20` with `staleTime: 10_000`; each entry renders as a `LogRow` with its severity variant; a "View all logs →" link navigates to `/logs`

**Given** the operator navigates to `/settings` (S8)
**When** the page loads
**Then** it fetches `GET /api/v1/health` (reused from cache) and displays: service version, uptime, MongoDB connection string (masked), session TTL; a "Logout" button calls `POST /api/v1/auth/logout` and redirects to `/login`

**Given** the operator is on Settings page (S8) or the header action bar
**When** the operator clicks the **"Refresh Cache"** button
**Then** `POST /api/v1/admin/cache/refresh` is called; on HTTP 200 a success toast notification appears surfacing the refreshed cache metadata (`version`, `rule_count`, `source_count`, `refreshed_at` timestamp); on failure an error toast appears (FR-12b)

**Given** the operator clicks the theme toggle in the sidebar
**When** the click fires
**Then** `data-theme` on `<html>` toggles between `light` and `dark`; the chosen theme is saved to `localStorage` under key `fb-theme`; on next page load the persisted theme is applied before first render (no flash of wrong theme)

**And** `web/src/pages/Dashboard.tsx` and `web/src/pages/Settings.tsx` implement the screens; `web/src/api/health.ts` exports `fetchHealth`; `web/src/api/stats.ts` exports `fetchStats`; query keys follow the `queryKeys` factory pattern

---

### Story 6.4: Forwards List (S2) & Forward Edit (S3) Screens

As a Channel Operator,
I want to view all forwarding rules in a filterable table, enable/disable them individually or in bulk, and edit every aspect of a rule through a multi-panel form,
So that I can manage my forwarding configuration efficiently without using the raw API.

**Acceptance Criteria:**

**Given** the operator navigates to `/forwards` (S2)
**When** the page loads
**Then** `GET /api/v1/rules?page=1&page_size=50` is fetched with `staleTime: 30_000`; the table renders columns: Source, Destination, Status pill, FilterIconRow (active filters), Actions (Edit, Enable/Disable toggle); pagination controls appear when total > 50

**Given** the operator clicks the Enable/Disable toggle on a rule row
**When** the toggle fires
**Then** an optimistic update flips the toggle state immediately in the UI; `POST /api/v1/rules/{id}/enable` or `/disable` is called; on success the cache is invalidated; on failure the optimistic update is rolled back and an error toast appears

**Given** one or more rule checkboxes are selected
**When** any checkbox is checked
**Then** a bulk action bar slides in at the bottom with "Enable selected", "Disable selected", and "Delete selected" buttons; "Delete selected" shows a confirmation dialog listing the count before proceeding; bulk operations execute sequentially and a progress-bar toast tracks completion (e.g., "3 of 5 complete")

**Given** the operator navigates to `/forwards/new` or `/forwards/{id}/edit` (S3)
**When** the form renders
**Then** seven `CollapsiblePanel` sections appear: (1) Basic Config (source_id selector, destination_channel, is_active toggle), (2) Time Window (days_of_week checkboxes, start_time/end_time pickers), (3) Sampling (sample_rate slider 0–100%), (4) Keyword Filters (block_keywords textarea, allow_keywords textarea), (5) Content Transforms (remove_links, remove_hashtags, remove_mentions toggles; forward_media radio), (6) Attribution (prefix/suffix text inputs + live preview), (7) Replacement Rules (inline CRUD table for child replacement rules)

**Given** the Attribution panel is open and the operator types in prefix/suffix fields
**When** text changes
**Then** a live preview renders below showing `"{prefix}\n\nSample message text\n\n{suffix}"` updating on every keystroke

**Given** the Media Replacement section in panel (5)
**When** `forward_media` is set to `forward` or `caption_only`
**Then** a file path input and "Browse" button appear; clicking "Browse" opens the `GET /api/v1/media/replacement-images` endpoint response in a modal gallery; the operator selects a file and the path populates the input field

**Given** the operator submits the form for a new rule
**When** validation passes
**Then** `POST /api/v1/rules` is called; on HTTP 201 the operator is redirected to `/forwards`; on HTTP 422 field-level errors are displayed inline next to the offending fields

**And** `web/src/pages/ForwardsList.tsx`, `web/src/pages/ForwardEdit.tsx` implement the screens; `web/src/api/rules.ts` exports all rule CRUD calls; `web/src/api/media.ts` exports `fetchReplacementImages`; the `GET /api/v1/media/replacement-images` FastAPI endpoint is implemented in `api/routers/media.py` and lists filenames from `MEDIA_REPLACEMENT_BASE_DIR`

---

### Story 6.5: Sources List (S4), Source Edit (S5) & Folder Modals (S6)

As a Channel Operator,
I want to register and manage Telegram sources with folder organization, with clear feedback when a source is already in use by rules,
So that I can maintain an organized source catalog and understand the impact of removing a source.

**Acceptance Criteria:**

**Given** the operator navigates to `/sources` (S4)
**When** the page loads
**Then** `GET /api/v1/sources?page=1&page_size=50` and `GET /api/v1/source-folders` are fetched with `staleTime: 30_000`; the left rail renders folder tabs (including "All"); clicking a folder tab filters the source table; each source row shows: display_name, channel_id/username, folder badge, active rule count, Edit and Delete actions

**Given** the operator navigates to `/sources/new` or `/sources/{id}/edit` (S5)
**When** the form renders
**Then** fields shown are: `channel_identifier` (Telegram username or channel ID input), `display_name`, `folder_id` (dropdown populated from folders); after entering `channel_identifier` and tabbing out, `GET /api/v1/sources/resolve/{identifier}` is called and the resolved `channel_id` echo appears below the field as read-only confirmation text

**Given** the operator attempts to delete a source that is referenced by active forwarding rules
**When** `DELETE /api/v1/sources/{id}` returns HTTP 409
**Then** a dialog appears listing the conflicting rule names with "Jump to rule" links that navigate to `/forwards/{id}/edit`; the delete is not performed

**Given** the operator opens the "New Folder" or "Edit Folder" modal (S6)
**When** the modal renders
**Then** a single `folder_name` text input appears; on submit `POST /api/v1/source-folders` or `PUT /api/v1/source-folders/{id}` is called; if the folder name already exists the API returns HTTP 409 and the modal shows an inline error "A folder with this name already exists"

**Given** a folder has sources assigned to it
**When** the operator attempts to delete the folder
**Then** a confirmation dialog lists the count of sources that will be unassigned (moved to no-folder) before confirming the delete

**And** `web/src/pages/SourcesList.tsx`, `web/src/pages/SourceEdit.tsx`, `web/src/components/FolderModal.tsx` implement the screens; `web/src/api/sources.ts` and `web/src/api/folders.ts` export all relevant calls; `GET /api/v1/sources/resolve/{identifier}` FastAPI endpoint is implemented in `api/routers/sources.py`

---

### Story 6.6: Logs Screen (S7), SSE Client & First-Run Wizard

As a Channel Operator,
I want a live log tail with filter chips, correlation-ID tracing, and a first-run setup wizard that guides me through initial configuration,
So that I can diagnose forwarding issues in real time and get the bot configured correctly on first use.

**Acceptance Criteria:**

**Given** the operator navigates to `/logs` (S7)
**When** the page mounts
**Then** an `EventSource` connection opens to `GET /api/v1/logs/stream`; incoming SSE events are prepended to the log list and displayed as `LogRow` components; auto-scroll is enabled by default (newest entries scroll into view); a "Pause" toggle stops auto-scroll without closing the SSE connection

**Given** the SSE connection drops (e.g., network interruption)
**When** the `EventSource` `onerror` fires
**Then** the `DegradedBanner` appears above the log list with message "Live log stream disconnected — reconnecting…"; `EventSource` reconnects automatically via its built-in retry; the banner dismisses when the connection re-establishes

**Given** filter chips are rendered above the log list
**When** the operator clicks severity chips (info/warning/error/success) or rule filter chips
**Then** the active filter state is reflected in the URL query string (e.g., `?severity=error&rule_id=abc123`); on page load the URL query string is read and filter chips are pre-selected; the log list filters client-side to show only matching entries

**Given** a log entry includes a `correlation_id`
**When** the operator clicks the correlation ID badge on a log row
**Then** the filter chips update to show only entries matching that `correlation_id`; a "Jump to rule" link appears in the filter bar if the log entry includes a `rule_id`, navigating to `/forwards/{rule_id}/edit`

**Given** this is the operator's first visit after installation (no forwarding rules exist)
**When** the Dashboard mounts and `GET /api/v1/rules?page_size=1` returns an empty list
**Then** the First-Run Wizard 3-step dialog opens automatically: Step 1 "Register a Source" (links to Sources page), Step 2 "Create a Forwarding Rule" (links to Forwards new page), Step 3 "Verify Live Logs" (links to Logs page); the wizard can be dismissed and does not reappear once a rule exists; wizard state persists in `localStorage` under key `fb-first-run-dismissed`

**Given** the operator uses the Logs screen
**When** `GET /api/v1/logs?limit=200` is called on initial mount before SSE starts
**Then** the last 200 historical log entries are loaded and displayed; the SSE stream then appends new entries in real time without duplicating the historical batch

**And** `web/src/pages/Logs.tsx` implements the screen; `web/src/hooks/useSseLog.ts` encapsulates the `EventSource` lifecycle (open, close on unmount, reconnect banner state); `web/src/components/FirstRunWizard.tsx` implements the 3-step dialog using a shadcn `Dialog`; all SSE and filter logic is tested with the existing structlog ring buffer from Story 5.2

---

## Epic 7: Session Management UI & Multi-Tier Cache Control

### Story 7.1: Multi-Tier Rule Cache Rebuild & Admin Refresh API

As a Channel Operator,
I want rule changes made via the API to take effect in the forwarding pipeline instantly (<1s) and have a manual refresh endpoint as well as a background safety net,
So that configuration changes take effect immediately without needing service restarts or periodic delays.

**Acceptance Criteria:**

**Given** active Forwarding Rules and Replacement Rules exist in MongoDB
**When** any REST API operation mutates rules, replacement rules, sources, or folders (Create, Update, Delete, Enable, Disable)
**Then** the system immediately triggers an asynchronous in-memory rebuild of `RuleCache` and atomically swaps `CacheHolder.current` in <1 second without blocking the API HTTP response (FR-12a)

**Given** the operator wants to force a cache refresh out-of-band or via the admin API
**When** `POST /api/v1/admin/cache/refresh` (or `/api/v1/cache/refresh`) is called
**Then** HTTP 200 is returned with cache metadata (`version`, `rule_count`, `source_count`, `refreshed_at` timestamp) after triggering an immediate `build_rule_cache()` call (FR-12b)

**Given** MongoDB is temporarily unreachable during a refresh attempt
**When** the periodic background refresher runs (`HOT_RELOAD_INTERVAL` default 30s)
**Then** `CacheHolder.current` retains the last valid snapshot, logs a WARNING `cache_refresh_failed`, and retries on the next interval without crashing (FR-12c)

**And** `RuleCache` frozen dataclass and `CacheHolder` in `infrastructure/cache/rule_cache.py`; `cache_refresher` coroutine in `infrastructure/cache/cache_refresher.py`; FastAPI admin router in `api/routers/admin.py` exposing `POST /api/v1/admin/cache/refresh`; mutation hooks calling `trigger_cache_rebuild()` wired across rule, source, folder, and replacement routers

---

### Story 7.2: Telegram Session Management Backend API & Lifecycle Methods

As a Channel Operator,
I want backend endpoints to check Telegram session status, request/verify OTPs, submit 2FA passwords, and terminate active sessions,
So that session lifecycle actions can be executed dynamically at runtime without restarting the process.

**Acceptance Criteria:**

**Given** the Web Admin Dashboard requests Telegram session status
**When** `GET /api/v1/telegram/auth/status` is called
**Then** HTTP 200 returns `{ "connected": bool, "phone": "<masked or null>", "phone_required": bool, "session_path": "<path>" }` (FR-46)

**Given** the operator initiates Telegram login
**When** `POST /api/v1/telegram/auth/start` is called with `{ "phone": "+1234567890" }`
**Then** Telethon `send_code_request()` is called, `phone_code_hash` is saved in memory, and HTTP 200 returns `{ "status": "code_sent" }` (FR-47)

**Given** the operator submits an OTP code
**When** `POST /api/v1/telegram/auth/verify` is called with `{ "otp": "123456" }`
**Then** Telethon `sign_in()` completes, `.session` file is written, `TelegramClientHolder.reconnect()` is invoked, and HTTP 200 returns `{ "status": "connected" }` (FR-47); if 2FA password is required, HTTP 202 `{ "requires_2fa": true }` is returned (FR-48)

**Given** an active session exists and the operator chooses to terminate
**When** `POST /api/v1/telegram/auth/terminate` is called
**Then** `TelegramClientHolder._connected` is set to `False` (new events dropped), Telethon `client.log_out()` is called, the `.session` file is deleted, and HTTP 200 returns `{ "status": "terminated" }` (FR-49, FR-51)

**And** `TelegramClientHolder` methods `reconnect()` and `terminate()` in `infrastructure/telegram/client.py`; router mounted at `/api/v1/telegram/auth` in `api/routers/telegram_auth.py`

---

### Story 7.3: Web Admin Settings Page UI for Cache Refresh & Telegram Session Control

As a Channel Operator,
I want UI controls on the Settings page (S8) and top header bar to trigger cache refreshes and manage the Telegram session,
So that I can control caching and session authentication directly from my browser.

**Acceptance Criteria:**

**Given** the operator is on Settings (S8) or the header action bar
**When** the operator clicks the **"Refresh Cache"** button
**Then** `POST /api/v1/admin/cache/refresh` is called; on HTTP 200 a success toast notification appears with `version`, `rule_count`, `source_count`, and `refreshed_at` timestamp (FR-12b)

**Given** the operator navigates to `/settings` (S8)
**When** the Telegram Session Card renders
**Then** it fetches `GET /api/v1/telegram/auth/status`; if connected, displays a green "CONNECTED" badge and "Terminate Session" button; if disconnected, displays a red "DISCONNECTED" badge and OTP connect form (FR-46)

**Given** the operator clicks "Terminate Session"
**When** the confirmation modal opens and operator types `terminate`
**Then** `POST /api/v1/telegram/auth/terminate` is called, the modal closes, and the session status badge updates to "DISCONNECTED" (FR-49)

**And** `web/src/pages/Settings.tsx` updated with Telegram Session Card & Refresh Cache button; `web/src/components/HeaderBar.tsx` updated with Refresh Cache button; API client functions added to `web/src/api/telegramAuth.ts`
