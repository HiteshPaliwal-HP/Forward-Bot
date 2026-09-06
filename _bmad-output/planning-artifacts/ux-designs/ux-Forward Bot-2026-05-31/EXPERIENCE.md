---
name: Forward Bot
status: final
updated: 2026-09-06
sources:
  - ../../prds/prd-forward-bot-2026-05-31/prd.md
  - ../../prds/prd-forward-bot-2026-05-31/addendum.md
companion: DESIGN.md
---

# Forward Bot — EXPERIENCE.md

> Behavioral spine: information architecture, interactions, states, accessibility, key flows. Cross-references DESIGN.md tokens by name using `{path.to.token}` syntax. **This spine wins on conflict with any mock, import, or downstream interpretation.**

## Foundation

Desktop-first responsive web. **shadcn/ui on React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Router** (per PRD §9 / addendum §9.1). The component library does most of the work; brand discipline is "respect shadcn defaults except where DESIGN.md overrides them."

The dashboard is served by FastAPI at `/`; the REST API at `/api/v1/*`. Single-tenant — one operator, one Telegram account, one instance. Both light and dark are first-class (system-follow with manual toggle in Settings, per Discovery round 1).

The product premise: this is **infrastructure that happens to have a UI**. Optimize for raw operator efficiency over onboarding warmth. Empty states assume "I built this and I know what to do." The trust beat is *watching the pipeline work* — Logs is a verification surface, not an afterthought. See `Logs as verification surface` below.

`DESIGN.md` is the visual identity reference and names the token surface; this spine is the experience.

## Information Architecture

Five top-level sidebar surfaces, plus modal/secondary surfaces, plus Login. From PRD addendum §9.3.

| Surface | Reached from | Purpose |
|---|---|---|
| **Login** | `/login` (unauth redirect) | Single `X-API-Key` field → HttpOnly cookie. No registration, no recovery. |
| **S1 Dashboard** | `/` / sidebar | Four health cards (Telegram, MongoDB, active-rule/source counts, 24h forwarded/blocked/failed) + recent activity panel + quick actions. |
| **S2 Forwards List** | `/forwards` / sidebar / `g f` | Table of Forwarding Rules. Per-row toggle, filter-summary icons, bulk enable/disable, last-forwarded timestamp. → [mockup](mockups/key-s2-forwards-list.html) |
| **S3 Forward Create/Edit** | `/forwards/new`, `/forwards/{id}` / S2 row / "Jump to rule" from log row | Long sectioned form: Source & Destination, Filters, Transforms, Removals, Media, Attribution, Activation. All panels collapsed by default. → [mockup](mockups/key-s3-forward-edit.html) |
| **S4 Sources List** | `/sources` / sidebar / `g s` | Left rail of Folders + right pane of Sources. Folder counts, "Ungrouped" bucket. |
| **S5 Source Create/Edit** | `/sources/new`, `/sources/{id}` | Telegram reference + Display Name + Type + Folder. Delete blocked if active rules reference. |
| **S6 Folder Modals** | S4 "+ New Folder" / rename / delete | Modal CRUD; no dedicated page. |
| **S7 Logs** | `/logs` / sidebar / `g l` / log row in S1 | Live tail (SSE) + filter by event + correlation_id search. Reads only. The verification surface. → [mockup](mockups/key-s7-logs.html) |
| **S8 Settings** | `/settings` / sidebar | Telegram session management card (connect / OTP / 2FA / terminate), env-var summary (read-only), theme toggle, About. **Enhanced (2026-09-06):** Full in-browser OTP auth flow and session termination (FR-46–FR-51). |

**Routing:** React Router; deep-linkable URLs (every state worth resuming is in the URL — surface, filters, expanded panels on S3 via query params).

**Global chrome:** persistent left sidebar, top breadcrumb bar, Telegram-status dot (right side of top bar), global degraded banner (when active) sits directly below the top bar.

**Modal stack:** never deeper than one level. The first-run wizard is the deepest stack; Folder modals and confirmation dialogs are the typical case.

## Voice and Tone

Microcopy. Brand voice and aesthetic posture live in `DESIGN.md`. The product's voice is **terse + technical**. No apology, no warmth, no exclamation marks. The operator built this; the surface talks back at the same register.

| Do | Don't |
|---|---|
| "Invalid regex: unclosed group at col 14." | "Oops! Your regex doesn't look quite right." |
| "Time window: end < start." | "Please make sure your end time is after your start time." |
| "Duplicate rule for source 1234." | "It looks like a rule already exists for this source." |
| "Forward updated. Reload pending — effects within 60s." | "Successfully updated! Your changes will be live soon." |
| "Telegram disconnected — [Reconnect]" | "We've lost connection to Telegram. Don't worry, we're working on it." |
| "Done. 45 enabled, 2 failed. [Show errors]" | "Bulk operation completed with some issues." |
| "No forwards yet. + New Forward." | "Welcome! Get started by creating your first forwarding rule." |
| "47 active · 3 inactive · 0 errored" | "You have 50 total forwarding rules in your system." |
| Pattern: `<field>: <reason>` for validation. | Friendly framing of mechanical truths. |
| `"Invalid regex /pump.*$ : unclosed group at col 14."` (echo the offending pattern). | Generic regex error without the pattern. |
| `"Source 1234: in use by 3 rules — [Crypto Signals → My Crypto Hub, Tech News → Tech Hub, Daily Digest → Personal]."` (delete-blocked with explicit rule list). | "Cannot delete — source is in use." |
| `"Folder name in use: Crypto."` (duplicate folder name). | Raw 422 toast. |
| `"File: outside allowed directory."` (path containment violation). | "Invalid file path." |
| `"Cannot create rule: source equals destination."` (self-referential 422). | Generic "Invalid rule." |
| `"Rule saved. Destination reachability untested — verify after first message."` (no-reachability-check trust beat). | Silently let the operator assume saved == working. |

Numbers and verbs. Field-scoped errors say the field and the reason in that order. The product is a tool — it answers questions, it does not perform.

## Component Patterns

Behavioral. Visual specs live in `DESIGN.md.Components` (or in shadcn defaults, when inherited).

| Component | Use | Behavioral rules |
|---|---|---|
| **Collapsible panel (S3)** | All seven S3 panels (Source/Dest, Filters, Transforms, Removals, Media, Attribution, Activation) | All collapsed by default on edit. Header displays panel name + summary string in `{colors.foreground-muted}` (e.g., "Filters — Block: 14 keywords, Time: off, Sampling: off, Media: all"). Click anywhere on header expands. Multiple panels can be open. Expanded state persists in URL (`?panels=filters,media`). |
| **Filter icon row (S2)** | Forwards List, per row | One lucide icon per filter type, in order: `clock`, `shuffle`, `image`, `key`. Active uses `{components.filter-icon-active}` (`{colors.accent}` tint, full opacity). Inactive uses `{components.filter-icon-inactive}` (40% opacity, no tint). Hover surfaces shadcn `Tooltip` with the configured value (e.g., "Mon–Fri 09:00–17:00 Europe/Warsaw"). |
| **Status pill** | Dashboard health cards, Settings, S2 rows | `{components.pill-success}` for connected / active / resolved. `{colors.state-degraded-foreground}` text on `{colors.state-degraded-bg}` for disconnected. Always icon + label + color, never color alone. |
| **Global degraded banner** | Top of every authed screen | Renders when Telegram is disconnected OR MongoDB unreachable. Uses `{colors.state-degraded-bg}` and `{colors.state-degraded-bg-dark}`, edge-to-edge, `radius: 0`. Holds message ("Telegram disconnected — last event 4m ago") + `[Reconnect]` button. While present: all dashboard actions remain enabled. The operator decides what's safe to edit during a disconnect. Rules edited or activated during the disconnect take effect when Telegram reconnects (worker hot-reload picks them up automatically). `role="alert"` and `aria-live="assertive"` so screen readers announce the condition. Non-dismissible until condition clears. |
| **File picker (S3 media replacement)** | Media panel only | shadcn `Combobox` listing existing files in `MEDIA_REPLACEMENT_BASE_DIR`. Operator places files via SFTP / `docker cp` / bind-mount; dashboard only **picks**, never writes. Picking populates `replacement_image_path` (relative to base dir). Empty state when directory has no files: "No replacement images. Place files under `MEDIA_REPLACEMENT_BASE_DIR` to pick from here." Server endpoint required: `GET /api/v1/media/replacement-images` returning the file listing — read-only, scoped to base dir. Path-containment is enforced server-side at pipeline time when the rule runs, not at picker time. |
| **First-run wizard** | Cold first login only | shadcn `Dialog`, three steps: (1) Telegram connection check → (2) register first source → (3) create first forward. Skippable at any step. Dismissed permanently after first source registers or operator skips. Never resurfaces. |
| **Save toast (rule writes)** | After `POST/PUT/PATCH /api/v1/rules` | shadcn `Toast`, default variant. Copy: "Forward updated. Reload pending — effects within 60s." With small `clock` icon. Auto-dismiss at 5s. The "≤60s" language is load-bearing — it's how the operator avoids restarting the service unnecessarily. |
| **Progress-bar toast (bulk)** | Bulk enable / disable in S2 | shadcn `Toast` extended with progress bar. Live counter: "Enabling 23 of 47 forwards…". On completion, replaces with summary toast: "Done. 45 enabled, 2 failed. [Show errors]". The summary toast **persists until dismissed** when any failures exist (errors expand inline on click). |
| **Activation banner (S3 post-save)** | Edit surface for any rule with `is_active=false` | shadcn `Alert` variant, `state-warning` tint, sits at top of S3 form. Copy: "This forward is inactive. [Activate] to begin processing." Disappears the moment the rule is first activated; does not reappear if deactivated later. |
| **Log row** | S7 Logs, S1 Dashboard recent-activity panel | Left-edge accent stripe color-coded by event severity per `{components.log-row-*}`. Lucide icon + bold event label + mono payload preview + timestamp on right. Rule name is a clickable affordance ("Jump to rule") → navigates to `/forwards/{id}` (S3). Click anywhere else on row expands inline to show full JSON payload + correlation_id link. |
| **"Jump to rule" affordance** | Every log row that names a rule | Rule name renders as a link (`{colors.accent}` underline). Cmd/Ctrl+click opens in new tab. Surfaced in PRD §9.3 implicitly; promoted to explicit pattern by the verification journey. |
| **Bulk action bar (S2)** | S2 when ≥ 1 row checked | Sticky bar at top of table with selected count + Enable / Disable / Delete buttons. Disable button confirms before dispatching ≥ 5 rows. |
| **Theme toggle (S8)** | Settings → Appearance | Three-state: System / Light / Dark. Default System. Manual selection persists in `localStorage` (theme is the only thing in localStorage — API key never goes there). |
| **Resolved-ID echo (S5)** | Source create/edit, post-save | On Source create/edit save, the API returns the resolved numeric Telegram ID. UI shows it post-save as a small subdued line under the Display Name: `"Resolved ID: 1234567890"` in `{colors.foreground-muted}`. Trust beat — proves Telegram accepted the reference. |
| **Source delete 409 dialog** | S5 / S4 delete action | Confirmation dialog uses shadcn `AlertDialog`. When DELETE returns 409 with referencing rules, dialog body lists every blocking rule with link to its S3 edit page. Copy pattern: "Source 1234 is referenced by 3 rules: [Crypto Signals → My Crypto Hub], [Tech News → Tech Hub], [Daily Digest → Personal]. Delete those or reassign first." |
| **Folder modal duplicate-name validation** | S6 Folder create/rename | Inline validation in shadcn `Dialog` form: as user types, debounce 300ms, GET `/api/v1/folders?name=...`; if exists and not the current folder, show inline error `"Folder name in use: Crypto."` below the input. Save button disabled while error present. |
| **Attribution panel placeholder help** | S3 Attribution panel | `format` text input below shows live preview using a sample source: input `"From {source_name}"` → preview `"From Crypto Signals Pro"`. Available tokens listed as chips below the input: `{source_name}`, `{source_username}` — click to insert at cursor. |
| **Cross-midnight time window summary** | S3 Filters panel header | When `time_window.end < time_window.start`, panel header summary reads `"Time: 22:00 → 06:00 (overnight)"` with the `(overnight)` qualifier in `{colors.foreground-muted}` to flag that the spine intentionally accepts wrap-around windows. |
| **Filter panel summary disambiguation** | S3 Filters panel header | Allowlist empty (default = allow all) renders as `"Allow: all"`. Explicit empty allowlist (`[]` set by operator) renders as `"Allow: 0 (none allowed)"`. Media all-types renders as `"Media: all"`; explicit subset renders as `"Media: photo only"`. |
| **Reconnect button (S8)** | Settings → Telegram, degraded banner | Button states: idle = `[Reconnect]`; in-flight = `[Reconnecting…]` with spinner, disabled; success = green checkmark for 2s then revert to idle; failure = button shakes once, toast `"Reconnect failed — see logs."` with `[Open logs]` action button on toast. |

### Session Management Card (S8) — FR-46 through FR-51

The Settings page contains a dedicated **Telegram Session** card. It is the only surface that shows the full session state machine; the top-bar dot is a read-only compact mirror of the same state.

| Component | Use | Behavioral rules |
|---|---|---|
| **Session card — CONNECTED state** | S8 when session active | Uses `{components.session-card-connected}` styling (green tinted border + background). Displays: green `circle-check` icon, bold "CONNECTED" label in `{colors.state-success-foreground}`, the phone number (last 4 digits visible, rest masked), and session file path (read-only mono text). Action: **[Terminate Session]** button (destructive variant). Polling every 10s via TanStack Query `refetchInterval`. |
| **Session card — DISCONNECTED state** | S8 when no session / session invalidated | Uses `{components.session-card-disconnected}` styling (red tinted border + background). Displays: red `circle-x` icon, bold "DISCONNECTED" label in `{colors.state-error}`. When `phone_required: true` (env var absent): an editable `tel` input (placeholder `+1234567890`, E.164 format, client-side validates `+` prefix + numeric-only). When phone is pre-filled from env: phone shown read-only, masked. Action: **[Send OTP]** button (primary variant). |
| **Session card — OTP step** | S8 after Send OTP clicked | Card transitions in-place (no navigation). Displays: status `"OTP sent to +1•••••┆5"` in muted text, a **6-box OTP input** (`{components.session-otp-input}`) — each box accepts one digit, focus auto-advances. **[Connect]** button disabled until all 6 boxes filled. **[Send OTP]** button disabled for 60s post-click (client-side cooldown; countdown shown). OTP fields accept only numeric digits. On error: ring flips to `{components.session-otp-input.error-ring}`, inline error below the input (see Voice and Tone patterns). |
| **Session card — 2FA step** | S8 after OTP submit when `requires_2fa: true` (HTTP 202) | OTP input area replaced by a `password`-type shadcn `Input` labelled "Telegram Cloud Password". Help text: "This account requires Two-Factor Authentication. Enter your Telegram cloud password." **[Submit]** button (primary variant). Password field is masked; no show/hide toggle (internal tool). On wrong password: inline error `"Cloud password: incorrect — try again."` 2FA field persists active. |
| **Terminate session — confirmation modal** | S8 CONNECTED card → [Terminate Session] click | Opens shadcn `AlertDialog`. Header: "Terminate Telegram Session?". Body explains: "This will log out the MTProto session and delete the session file. All in-flight forwards will be dropped." Below body: a `{components.session-terminate-danger-zone}` section containing an `Input` with label `"Type terminate to confirm"`. The **[Confirm Terminate]** button (destructive variant) is **disabled** until the input matches `terminate` exactly (case-insensitive). **[Cancel]** (ghost variant) aborts without side-effects. |
| **OTP cooldown countdown** | S8 OTP step | A small mono `{colors.foreground-muted}` countdown beneath the disabled [Send OTP] button: `"Resend available in 45s"`. Counts down in 1s increments (client-side interval). At 0s, [Send OTP] re-enables with label `"Resend OTP"`. |
| **Session status dot (top bar)** | All authed screens | The existing Telegram connection dot in the top bar reflects session state: green = CONNECTED, red = DISCONNECTED, amber pulse = auth in progress / reconnecting. It is a read-only compact mirror of the session card; clicking it navigates to `/settings`. |

## State Patterns

Every list surface and form surface has an opinion about each of these states. Inherit shadcn's `Skeleton`, `Alert`, `Toast` primitives.

| State | Surfaces | Treatment |
|---|---|---|
| **Empty (cold)** | S2 (no rules), S4 (no sources), S7 (no logs yet) | Single sentence + primary action. "No forwards yet. + New Forward." "No sources yet. + New Source." "No events in the last hour." No illustration, no hero. |
| **Loading** | All list/detail surfaces | shadcn `Skeleton` rows matching final layout (S2: 6 skeleton rows; S3: panel chrome with skeleton summaries; S7: 10 skeleton log rows). Resolves on data. |
| **Error (fetch)** | Any read | shadcn `Alert` (destructive variant), inline above the failed region. Copy pattern: `<surface>: <reason>`. Example: "Sources: 503 Service Unavailable. [Retry]" |
| **Error (write)** | Any write | shadcn `Toast` (destructive). Copy: "Save failed: <reason>." Form retains unsaved state. Another submit retries. No "are you sure" — operator trust. |
| **Validation (field)** | S3 form, S5 form | Inline below the offending input, `{colors.state-error}` text, terse pattern `<field>: <reason>`. Examples per Voice and Tone. Form's primary action disabled while any field invalid. |
| **Degraded** | Global (any surface) | `{components.banner-degraded}` at top. All actions remain enabled — banner is announce-only. The operator decides what's safe to edit during the disconnect; rules saved while degraded are picked up by the worker on reconnect. See Component Patterns above. |
| **Optimistic** | S2 row toggle (enable/disable) | Toggle flips immediately; row enters "saving" sub-state (subtle opacity + spinner on the toggle track). On `2xx`, settle. On `4xx/5xx`, rollback with shadcn `Toast` destructive: "Toggle failed: <reason>." |
| **Partial failure (bulk)** | S2 bulk action | Sequential dispatch. Progress-bar toast counts running totals. Summary toast at end with `[Show errors]` link → expands inline panel under bulk bar listing failed rule IDs + per-row reasons. |
| **Stale / cache pending** | S3 after rule save | Save toast communicates the ≤60s window explicitly. No spinner on the parent surface — the operator can navigate away. The Logs verification beat closes the loop. |
| **Reconnecting** | Telegram status (S1 card, top bar dot, global banner) | Pulse animation on the status dot. Banner copy: "Telegram reconnecting…". On success, banner dismisses; pill flips to connected. On failure after retry budget, banner copy switches to "Telegram disconnected — [Reconnect]". |
| **Auth expired (cookie lapse mid-session)** | Any authed surface | Any API call returning 401 triggers redirect to `/login?return=<current-path>` with the protected URL preserved. On successful re-auth, return to the saved URL. Toast on the login page: `"Session expired — sign in to continue."` |
| **Log ring-buffer floor** | S7 Logs historical pane | When operator scrolls past the in-memory buffer's oldest entry (default 1h, max 24h), surface an inline note: `"Beyond 1h — older events not retained."` Render at the end of the historical pane, not a separate page. |
| **Cache-refresh failure** | Global (top bar) | When the worker's 30s cache-refresh fails (logged as `cache_refresh_failed`), dashboard surfaces a subdued warning pill in the top bar next to the Telegram dot: `{colors.state-warning}` background, copy `"Rules cache stale (last refresh 4m ago)"`. Clears when next refresh succeeds. |
| **OTP send in-flight** | S8 session card | [Send OTP] button enters `[Sending…]` with spinner. Disabled until server responds. On success: OTP step card variant renders. On failure: button re-enables, inline error below the phone input. |
| **OTP verify in-flight** | S8 session card OTP step | [Connect] button enters `[Connecting…]` with spinner. OTP boxes become read-only. On 2FA required (HTTP 202): transition to 2FA step without error. On error (wrong OTP, expired OTP): boxes clear, re-editable, inline error displayed. |
| **OTP expired** | S8 session card OTP step | When polling detects the `phone_code_hash` is gone (backend cleared after 10 min) OR the server returns `otp_expired`: inline note below OTP boxes: `"OTP expired — start again."` [Send OTP] re-enables immediately. |
| **Auth in progress (concurrent)** | S8 session card | If a prior `/start` is still active (server 409 `auth_in_progress`): card shows the OTP step with the cooldown timer already running (remaining seconds from the 409 response body). `"OTP already sent — check your Telegram app."` in muted text. |
| **Max OTP retries reached** | S8 session card OTP step | After 3 failed OTP attempts, server returns `too_many_attempts` with Telegram's error detail. OTP boxes disabled, [Connect] disabled. Inline error shows the Telegram message verbatim. Operator must reload the page to retry. |
| **Terminate in-flight** | S8 terminate modal | [Confirm Terminate] enters `[Terminating…]` with spinner; modal cannot be dismissed. On success: modal closes, card transitions to DISCONNECTED state, toast `"Session terminated. Worker stopped."` On failure: modal closes, toast destructive `"Terminate failed: <reason> — see logs."` |
| **Session terminated drops** | S7 Logs | Events `telegram_session_terminated_drop` render using `{components.log-row-session-terminated-drop}` (warning amber stripe, `zap-off` icon, bold label "Session drop: in-flight event discarded"). These are expected during a deliberate termination — not errors. |

## Interaction Primitives

**Mouse-first with keyboard escape hatches.** Unlike a developer tool (Linear / Drift), Forward Bot's operator does not live in a keyboard-only flow — config sessions are slow and deliberative. But basic keyboard navigation is the non-negotiable floor.

- **Tab order** matches reading order on every surface.
- **`Esc`** closes the topmost modal/popover and exits inline edit mode in subforms (S3 Replacement Rules).
- **`Enter`** in any form submits the primary action of the smallest enclosing form (subform Save before parent Save).
- **`Cmd/Ctrl+Enter`** on the S3 main form saves the rule regardless of focus position.
- **`g` then key** sidebar shortcuts (vim-style): `g d` (Dashboard), `g f` (Forwards), `g s` (Sources), `g l` (Logs), `g ,` (Settings).
- **Click targets** ≥ 32px on the primary surface; toggles and icon buttons ≥ 26px (per shadcn defaults). Filter icons on S2 rows are smaller (14px) but the hover tooltip target extends to a 24px hit area.
- **Scroll behaviors:** S7 Logs auto-scrolls to bottom on new events when the user is already at the bottom; pauses auto-scroll the moment the user scrolls up (shadcn `ScrollArea` with a "Jump to latest" floating button on pause). S2 table virtualizes at >200 rows. S3 form is a single scrollable column; sticky save bar at bottom right.
- **Banned everywhere:** drag-to-reorder (deferred per PRD §9.3 nice-to-have on S4 only), hover-only affordances on `sm` viewports, modal stacks > 1 level deep, infinite scroll (S2 paginates, S7 windows by time range).

## Accessibility Floor

PRD §9.5 explicitly lists accessibility as **out of scope for the UI MVP**. This is the non-negotiable floor anyway — these are not commitments, they are the price of admission for a tool the operator will use under low-trust conditions (Friday evening, second coffee, real money or real friends affected).

- **Keyboard navigation throughout.** Every interactive element reachable via Tab in reading order. No mouse-only flows.
- **No color-only signal.** Every state communicated by color is also paired with an **icon and a label**. The forwarded vs. blocked vs. error distinction reads at every color-vision baseline because the icon (`arrow-up-right` vs. `circle-slash` vs. `alert-triangle` vs. `ban`) and the bold event label carry the same information.
- **Focus indicators.** shadcn's `ring` token applied to every focusable element. Verified to contrast against both `{colors.background}` and `{colors.background-dark}`.
- **Semantic HTML.** Lists are `<ul>`, tables are `<table>`, forms are `<form>` with `<label>` association. shadcn primitives already do this; the discipline is "don't break it."
- **ARIA on the global banner.** `{components.banner-degraded}` carries `role="alert"` and `aria-live="assertive"` — the banner appearing must announce to screen readers even mid-task.
- **Form validation.** Field errors are `aria-invalid="true"` and `aria-describedby` the error message. shadcn `Form` handles this.
- **Toast announcements.** shadcn `Toast` uses `aria-live="polite"` by default; destructive toasts upgrade to `aria-live="assertive"`.

WCAG 2.2 AA contrast verified on all token pairs in `DESIGN.md`. Beyond this floor, no formal accessibility commitments — that's the PRD scope boundary.

## Logs as verification surface

The journey draft promoted Logs from "diagnostic" to **the surface where the operator confirms a fix landed**. This has design consequences that don't fit cleanly elsewhere.

- **Live tail is the default mode.** Open `/logs` and events stream in immediately. No "click to start streaming" button — the SSE connection (`GET /api/v1/logs/stream`) opens on mount.
- **Severity is glanceable.** Per `{components.log-row-forwarded}`, `{components.log-row-filter-blocked}`, `{components.log-row-telegram-rejected}`, `{components.log-row-destination-unreachable}` — the left-edge stripe + icon + bold label combination must make a forwarded event visually unmistakable from a blocked one. This is the climax beat of the journey: green ↗ appearing where muted ⊘ was.
- **Filter chips persist in URL.** Filter by `event=blocked_keyword` and the URL becomes `/logs?event=blocked_keyword`. Reload preserves the filter. The operator can hand a colleague (or themselves, weeks later) a link to a specific diagnostic view.
- **"Jump to rule" on every row.** Rule name is clickable → S3 for that rule. This is the path from "I see the symptom" to "I'm editing the cause" — make it one click.
- **Correlation ID link.** Click expands the row inline to show full JSON payload + correlation_id as a copy-button. Click the correlation_id to filter by it (`/logs?correlation_id=…`) — trace one message's full journey through the pipeline.
- **No "verified by external check" dependency.** The operator should never need to open Telegram to confirm a forward happened. Logs is the proof surface; design accordingly.
- **Event catalog extensions.** Beyond `forwarded` / `filter-blocked` / `telegram_rejected` / `destination_unreachable`, the catalog also carries:
  - `edit_propagated` — info severity, reuses `{components.log-row-forwarded}` styling but with `pencil` icon to differentiate.
  - `delete_propagated` — info severity, reuses `{components.log-row-forwarded}` styling with `trash-2` icon.
  - `reply_parent_not_found` / `reply_target_missing` — warning severity, `{colors.state-warning}`, icon `corner-down-right` with a strike (`{components.log-row-reply-orphaned}`).
  - `flood_wait` — **new severity bucket** (rate-limited; not error, not forwarded). Uses `{colors.state-warning}` styling via `{components.log-row-flood-wait}`, icon `clock` with a pause modifier. Distinct from `degraded` — FloodWait is per-rule throttle, not system disconnection. Surfaced both inline in log rows AND as a top-bar pill (warning-tinted) alongside the Telegram dot when active.
  - `source_registered` / `source_resolved` / `folder_created` / `media_replacement_failed` — admin events. Surface in the log catalog if `event=admin` filter is enabled. `media_replacement_failed` uses error styling because it's a runtime failure that fell back to source photo.
  - `telegram_session_terminated` — admin severity. Rendered with `{components.log-row-forwarded}` styling (green stripe, `log-out` icon) to signal this was a **deliberate operator action** — not a failure. Visible when `event=admin` filter is enabled.
  - `telegram_session_terminated_drop` — warning severity, rendered with `{components.log-row-session-terminated-drop}` (warning amber stripe, `zap-off` icon, label `"Session drop: in-flight event discarded"`). Expected during a planned termination; not an error. Visible in the default stream.

## Key Flows

### Flow 1 — Hitesh tunes a too-aggressive filter (Friday evening)

**Protagonist:** Hitesh, the operator. Friday evening, second coffee. He runs ~40 sources across three folders (Crypto, Tech, Politics), forwarding into three destination channels for a private Telegram group of friends.

**Why he's here:** A friend in the group pinged him: "your Crypto Hub is dead silent today — markets are moving, what gives?" Hitesh suspects the keyword filter on his Crypto rule is over-blocking after he tightened it last week.

**Goal:** Find which messages got dropped, why, and fix the rule — within 10 minutes so he can get back to the weekend.

**Surfaces touched:** S1 Dashboard → S7 Logs → S3 Forward Edit → S7 Logs.

1. **Hitesh opens the dashboard** at `/`. The four health cards show Telegram `{colors.state-success}`, MongoDB `{colors.state-success}`, 47 active rules / 38 sources, 24h: **127 forwarded / 89 blocked / 0 failed**. The blocked count is higher than he remembers — confirms his suspicion. He goes straight to the sidebar.

2. **He goes to Logs** (`/logs`). The live tail is rolling. He filters by `event=blocked_keyword`. The list is mostly his Crypto rule, blocking messages he'd actually want — "BTC dropped 4%", "ETH ATH", "SOL pumping." Each row uses `{components.log-row-filter-blocked}` — muted-grey stripe, `circle-slash` icon, source channel, blocked keyword, correlation_id.

3. **He clicks a representative blocked row.** It expands inline to reveal: `blocked_keyword = "pump"`. He thinks: *right, I added that to filter out shitcoin spam, but it's also catching every "SOL pumping" post from the actual signal channels.*

4. **He clicks the rule name** in the log row — the "Jump to rule" affordance navigates to `/forwards/{id}` (S3). All seven panels collapsed by default. The Filters panel header summarizes: **"Filters — Block: 14 keywords, Allow: 0, Time: off, Sampling: off, Media: all"**. He clicks Filters to expand.

5. **He edits the block list** — finds `pump`, removes it. Below the field, client-side validation runs: no regex error, list is now 13 items. He scrolls to the sticky save bar and clicks Save. A `{components.button-primary}` press fires the toast: **"Forward updated. Reload pending — effects within 60s."** The rule is still active (was already on); no activation banner. He doesn't have to do anything else.

6. **[CLIMAX]** He goes back to Logs. The blocked feed is quieter already. Within ~40 seconds, a new event streams in: a row using `{components.log-row-forwarded}` — green `{colors.state-success}` left stripe, `arrow-up-right` icon, bold "Forwarded" — from the same Crypto channel: **"SOL pumping past $200"**. The dashboard just proved his fix in real time, without him having to bounce to Telegram to verify. He breathes out. He didn't have to think about cache invalidation or restart the service. *This is the trust beat — the visual delta between the muted ⊘ row he was reading 60 seconds ago and the green ↗ row that just arrived is the entire reason the color separation in `DESIGN.md` exists.*

7. **He spot-checks two more events**, sees the green count tick up in the live tail. Pings his friend: "fixed, give it a minute." Closes the laptop.

### Flow 2 — First-run setup (new operator, cold install)

**Goal:** Get from `git pull && docker compose up` to "one forward running" in under 10 minutes.

1. Operator opens `http://localhost:8000/`. Auth middleware redirects to `/login`. They paste their `X-API-Key` and submit; HttpOnly cookie set, redirect to `/`.

2. **First-run wizard** auto-opens (shadcn `Dialog`). Step 1: Telegram connection check. The wizard reads `GET /health/telegram` and shows a `{components.pill-success}` "Connected" or surfaces a `{colors.state-error}` "Disconnected — check session file" with a link to Settings.

3. Step 2: "Register your first source." Inline form (Telegram reference + Display Name + Type + Folder). Operator pastes a channel `@handle`, names it, picks Channel. Submit → `POST /api/v1/sources`. Server resolves the numeric ID; the resolved ID renders below the form. Wizard advances.

4. Step 3: "Create your first forward." Inline mini-form with just Source picker (pre-populated with the source they just registered) + Destination text input + Save. Submit → `POST /api/v1/rules` with `is_active=false` (the default per Discovery round 3).

5. **[CLIMAX]** The wizard closes. The operator lands on `/forwards/{new_id}` (S3) with the activation banner at the top: "This forward is inactive. [Activate] to begin processing." A single click flips `is_active=true`. The save toast fires; within 60s the cache refreshes; the next message from the source appears in `/logs` as a green ↗ row. *The system proves itself by running.*

Failure: any wizard step fails → operator can skip and resume manually. Wizard never resurfaces; the operator-tool stakes don't justify it.

### Flow 3 — Bulk disable a noisy folder (operator triage)

**Goal:** Operator goes on vacation; wants to mute the "Politics" folder for a week.

1. Operator opens `/forwards` (S2). Filters by Folder = "Politics" via the top filter bar. Table re-renders with 12 rules.

2. Checks the table-header checkbox to select all 12. The **bulk action bar** appears at the top: "12 selected · [Enable] [Disable] [Delete]".

3. Clicks **Disable**. Because the count is ≥ 5, shadcn `AlertDialog` confirms: "Disable 12 forwards in folder 'Politics'?" with [Cancel] and [Disable] (destructive variant).

4. Confirm. The **progress-bar toast** appears: "Disabling 1 of 12 forwards…" → "Disabling 8 of 12 forwards…" → completes.

5. **[CLIMAX]** Summary toast: "Done. 11 disabled, 1 failed. [Show errors]". The operator clicks [Show errors] — inline panel under the bulk bar expands with the one failed row ID and reason: "rule_id=4f2a: 409 Conflict — already disabled." The operator shrugs (idempotency edge case, no actual problem), dismisses the toast, closes the laptop. *Partial failure surfaces the truth without forcing remediation; the operator decides what's a real problem.*

---

### Flow 4 — Hitesh reconnects after a session invalidation (Settings page auth flow)

**Protagonist:** Hitesh, the operator. He sees the global degraded banner fire — "Telegram disconnected" — but the session file wasn't lost on restart; Telegram invalidated the session server-side (e.g., logged out from another device).

**Goal:** Re-authenticate to Telegram from the browser, without SSH or a container restart, in under 3 minutes.

**Surfaces touched:** S1 Dashboard → S8 Settings (session card).

1. **Hitesh notices the banner.** The `{components.banner-degraded}` fires at the top of the Dashboard. Red badge, "Telegram disconnected — last event 2m ago". The Reconnect button at the top bar navigates him to `/settings`.

2. **He lands on Settings.** The Telegram section shows the session card in `{components.session-card-disconnected}` state — red `circle-x` icon, bold "DISCONNECTED", phone pre-filled (masked) from `TELEGRAM_PHONE` env var. He clicks **[Send OTP]**.

3. **OTP step renders.** Card transitions in-place to the OTP step. The [Send OTP] button disables with a `"Resend available in 59s"` countdown. Status line: `"OTP sent to +1•••••┆2"`. Six empty OTP boxes wait, each focused ring ready in `{components.session-otp-input.focused-ring}` (Forwarding Green).

4. **Hitesh enters the OTP** from his Telegram app. Focus auto-advances box to box as he types. All six filled — [Connect] button enables (primary variant).

5. **He hits [Connect].** Button enters `[Connecting…]` spinner state; OTP boxes freeze. Server calls `sign_in()` and triggers `TelegramClientHolder.reconnect()`. HTTP 200 returns `{ "status": "connected" }`.

6. **[CLIMAX]** The card transitions in-place to `{components.session-card-connected}` — green `circle-check` icon, bold "CONNECTED", phone masked, session path shown. The global degraded banner dismisses. The top-bar dot turns green. Toast: `"Telegram session connected. Worker resumed."` *The operator never touched a terminal. The service resumed without a restart. The green card is the trust beat — same visual language as the green log-row in Flow 1, same verification posture.*

7. **He switches to Logs** (`/logs`). Within ≤60s the cache refreshes and new `forwarded` rows start streaming. He closes the laptop.

---

*End of EXPERIENCE.md. Mockups under [mockups/](mockups/) are illustrative — this spine wins on conflict.*
