# Reconcile: PRD ↔ Spines — 2026-05-31

## Captured (✓)

- All 8 IA surfaces (S1–S8) plus Login present in EXPERIENCE §IA, matching addendum §9.3.
- shadcn/ui + React 18 + TS + Vite + Tailwind + TanStack Query + React Router stack named in EXPERIENCE Foundation (addendum §1.6).
- Cookie-based UI auth (HttpOnly, single API-key login) reflected in IA + State Patterns (FR-43).
- Live-tail SSE Logs as verification surface with correlation_id filter (FR-44).
- "Build-and-serve from same container" + `UI_ENABLED` topology referenced via Foundation (FR-45).
- Filter-icon summary on S2 rows (clock/shuffle/image/key) per addendum §9.3 S2 and decision round 4.
- S3 seven-panel collapsible form with summary headers per round 3 / addendum §9.3 S3.
- Default `is_active=false` activation banner pattern (OQ-RuleActiveDefault).
- Voice: terse, `<field>: <reason>`, no apology — matches operator persona (§2.1) and round 3.
- Bulk enable/disable with progress + summary toasts (round 3).
- Degraded mode: global non-dismissible banner + write-disable while reads stay live (round 4).
- Source Catalog + Folders + "Ungrouped" bucket (FR-29/30/31, addendum §9.3 S4).
- Media-replacement file picker located in `MEDIA_REPLACEMENT_BASE_DIR` (FR-41, addendum §4.1).
- "Jump to rule" affordance from log rows mapped to S3 (verification beat).
- Recent-activity panel and 24h stats card on S1 (addendum §9.3 S1, FR-42).

## Dropped or weakened (⚠)

- PRD fragment: "**OQ-UI-Stream.** SSE or WebSocket for live logs (FR-44)?" (prd.md:683); addendum §10 also lists `GET /api/v1/logs/stream` as "SSE / WebSocket live tail" (addendum.md:426).
  - Recommendation: accept the drop — EXPERIENCE commits to SSE explicitly ("SSE connection on mount" in Logs as verification surface), which is consistent with FR-44 `[ASSUMPTION]` favoring SSE. Note the closure in the decision log.

- PRD fragment: "**OQ-UI-Auth-Cookie-TTL.** Session cookie expiry (FR-43): 24h or browser-session-only?" (prd.md:682), and FR-43 `[ASSUMPTION]` "Cookie expiry default 24h" (prd.md:448).
  - Recommendation: fold into EXPERIENCE §State Patterns or §IA Login — spines say nothing about session expiry, re-auth behavior, or what happens when the cookie lapses mid-session. At minimum specify "cookie lapse → redirect to `/login` with return-URL preserved."

- PRD fragment: "in-memory ring buffer plus whatever the host's log aggregator exposes" + "default last 1h, max 24h" (prd.md:458, 595).
  - Recommendation: fold into EXPERIENCE §State Patterns (S7 Logs). The spines treat Logs as boundless; operators need to know when scrolling back hits the ring-buffer floor. Add an empty/edge state: "Beyond 1h — older events not retained."

- PRD fragment: "Reachability of the Destination channel is **not** validated at create-time" (prd.md:173) and "no `source==destination`" check (prd.md:170, addendum.md:405).
  - Recommendation: fold into EXPERIENCE §State Patterns / §Voice and Tone — S3 must surface server-side 422s for self-referential rules and accept the no-reachability-check gap explicitly (so operators understand a "saved" rule may still fail at first delivery). Add a toast pattern: "Rule saved. Destination reachability untested until first message."

- PRD fragment: "**Source resolved**" / `source_resolved` log event after registration (prd.md:426); addendum S5: "On create, the API resolves the Telegram numeric ID and persists both; UI shows the resolved ID after save." (addendum.md:337).
  - Recommendation: fold into EXPERIENCE §Component Patterns or §Key Flows — the resolved-ID echo on S5 post-save is a meaningful trust beat (operator sees Telegram accepted the reference) and the spines don't surface it.

- PRD fragment: "Delete: blocked with a message if active Forwarding Rules reference this Source; the message lists the rules." (addendum.md:338) and "409 conflict" on Source delete (prd.md:579).
  - Recommendation: fold into EXPERIENCE §State Patterns — the spines describe destructive confirms generically but not the 409-with-rule-list pattern, which is the load-bearing UX for "why can't I delete this?"

- PRD fragment: "Folder rename to a name that already exists → 422 (uniqueness index enforces it)." (addendum.md:253).
  - Recommendation: fold into EXPERIENCE §Component Patterns (Folder modals, S6) — add inline validation pattern for duplicate folder name; otherwise operators will see a raw 422 toast.

- PRD fragment: `replacement_caption_mode` `use_replacement | use_source | none` (prd.md:379, addendum.md:204) and Attribution `position: prefix | suffix` + `format` placeholders `{source_name}`, `{source_username}` (prd.md:177–183).
  - Recommendation: fold into EXPERIENCE §Component Patterns or DESIGN §Components — S3 Media and Attribution panels reference these only obliquely ("`replacement_caption_mode` radio"); placeholder help-text behavior (live preview? token chip?) is undefined.

- PRD fragment: "time-window logical check (end > start unless cross-midnight)" (addendum.md:327) and "Windows may cross midnight (e.g. `22:00–06:00`)" (prd.md:243).
  - Recommendation: fold into EXPERIENCE §State Patterns / §Voice — cross-midnight is a non-obvious affordance. Spines have one Voice example ("Time window: end < start.") but don't describe how the form communicates the cross-midnight escape valve.

- PRD fragment: "Empty allowlist = 'allow everything' (the default)" (prd.md:275) and `media_type_filter` default `["text","photo"]` (prd.md:264).
  - Recommendation: fold into DESIGN §Components or EXPERIENCE §Component Patterns — the panel-header summary string ("Allow: 0", "Media: all") needs to differentiate "no allowlist (= allow all)" from "allowlist empty by mistake." Currently ambiguous.

- PRD fragment: "**OQ-Sampling-Counter-Persistence.** Sampling counter is in-memory and resets at restart" (prd.md:680).
  - Recommendation: accept the drop at UX layer — counter persistence is a backend toggle (`SAMPLING_PERSIST`) and operators won't observe it through the UI in MVP. No spine change needed.

## Explicit overrides (Δ)

- Spine decision: **Both light and dark are first-class (system-follow + manual toggle in Settings)** overrides PRD: "**Out of scope for MVP UI:** Accessibility commitments, i18n, **theme switching**, offline." (addendum.md:367–369). Captured in decision log (round 1).

- Spine decision: **First-run wizard modal (3 steps)** overrides PRD's empty-state-only first-run framing: "A new operator can install the service, open the dashboard, register a Source, create a Forwarding Rule with filters and transforms, and see it forwarding" (prd.md:438) — no wizard named. Captured in decision log (round 2, "Slight delta from PRD").

## Implicit contradictions (?)

- Spines say degraded banner **disables forwarding write actions** ("toggle on, save rule, save source") (EXPERIENCE State Patterns). PRD never specifies write-disable on degraded; FR-12 hot-reload and FR-4 CRUD are silent on Telegram-connection preconditions. Reconciliation: this is a spine-introduced safety behavior. Confirm with operator — a power user might want to edit rules during disconnect so they're ready when reconnect lands. Recommend EXPERIENCE clarify: rule **CRUD** stays enabled, only `is_active=true` flips and Source registration (which requires a live Telegram resolve) disable.

- Spines say S7 "Live tail is the default mode" with auto-stream on mount (Logs as verification surface). PRD FR-44 names SSE but addendum §9.3 S7 says "Live tail view (WebSocket or SSE)" (addendum.md:344) — neither commits to auto-open. Reconciliation: auto-open is a spine refinement; harmless but should be noted as a UX commitment, not a PRD constraint.

- Spines specify `Cmd/Ctrl+Enter` saves S3, and `g`-prefix vim-style sidebar shortcuts. PRD/addendum say nothing about keyboard shortcuts; addendum §9.5 lists "Mobile responsive design" and other items as out of scope but is silent on keyboard. Reconciliation: spine-introduced; consistent with "operator efficiency" persona but goes beyond the addendum's "accessibility floor is out of scope" posture.

- Spines say theme is "the only thing in localStorage — API key never goes there" (Component Patterns, Theme toggle). PRD FR-43 says cookie is HttpOnly and API key "never persisted in browser-accessible storage" (prd.md:443) — consistent in intent. Reconciliation: align; no contradiction, just an implementation reinforcement to flag for the dev agent.

- Spines treat the file picker (S3 media replacement) as **upload-or-pick combo**; PRD FR-41 says "The replacement image is read from a configured filesystem path the operator controls; the operator must ensure read access. No remote URL fetching in MVP" (prd.md:385). Reconciliation: the "upload" leg adds a server-side file write into `MEDIA_REPLACEMENT_BASE_DIR` that the PRD does not authorize. DESIGN.md `[NOTE FOR UX]` already flags this; recommend the dev agent either (a) demote to plain path input + dropdown listing, or (b) add an explicit FR for the upload endpoint with path-containment requirements.

## PRD acceptance criteria not currently addressed in spines

The PRD/addendum don't carry per-screen acceptance criteria as a structured block; instead they list per-FR `Consequences` clauses. Items the spines do not currently address:

- FR-6 422-error surfacing for **self-referential rules** (`source` == `destination`) (prd.md:170)
  - Where it should land: EXPERIENCE §State Patterns → Validation (field) — add the specific pattern.

- FR-6 invalid-regex surfacing with **offending pattern echoed** (prd.md:171, 198)
  - Where it should land: EXPERIENCE §Voice and Tone — extend the "Invalid regex" example to show that the offending pattern is included.

- FR-12 hot-reload **cache refresh failure resilience** — what does the UI do if reads succeed but the worker's cache is stale? (prd.md:336)
  - Where it should land: EXPERIENCE §State Patterns → "Stale / cache pending" — currently only the happy-path ≤60s toast is described.

- FR-19/20/21/40 **edit, delete, reply propagation** — there is no UI surface for the operator to *trigger* edit/delete propagation (it's automatic), but no surface to *verify* it either.
  - Where it should land: EXPERIENCE §Logs as verification surface — add `event=edit_propagated`, `event=delete_propagated`, `reply_parent_not_found`, `reply_target_missing` to the visible log-row event catalog. DESIGN currently names only forwarded / filter-blocked / telegram_rejected / destination_unreachable.

- FR-22 **FloodWait** observable state — when Telegram throttles, the operator should see it (it's not "disconnected"; it's "rate-limited").
  - Where it should land: DESIGN §Components Log row variants + EXPERIENCE §State Patterns — add a FloodWait log-row variant and (recommended) a separate top-bar pill distinct from `degraded`.

- FR-25 **graceful shutdown** — operator-initiated reconnect (`POST /api/v1/admin/reconnect`, addendum S8) lacks defined UX feedback states (button disabled while in-flight, success/failure copy).
  - Where it should land: EXPERIENCE §Component Patterns → S8 Settings.

- FR-27 expanded event coverage: `source_registered`, `source_resolved`, `folder_created`, `media_replacement_failed` (prd.md:426)
  - Where it should land: EXPERIENCE §Logs as verification surface — confirm these surface in the live tail or accept that admin-CRUD events are excluded.

- Addendum §4.1 `MEDIA_REPLACEMENT_BASE_DIR` **path-containment** enforcement (defense against `../` traversal, addendum.md:261)
  - Where it should land: EXPERIENCE §Component Patterns (File picker) already alludes ("Server-side path-containment validation on every selection") — surfacing the **error UX** when containment fails is not specified. Add the Voice pattern: "File: outside allowed directory."

- FR-43 cookie expiry behavior at lapse / 401 mid-session (prd.md:448)
  - Where it should land: EXPERIENCE §IA → Login row, or §State Patterns → new "Auth expired" row.
