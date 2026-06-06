---
title: Forward Bot
status: final
created: 2026-05-31
updated: 2026-05-31

# PRD: Forward Bot

## 0. Document Purpose

This PRD defines **Forward Bot**, a self-hosted Telegram channel forwarding platform, at the capability level. It is written for the BMad Architect skill (`bmad-create-architecture`) as the immediate downstream consumer, followed by the Epics & Stories skill and the implementation chain. Vocabulary is Glossary-anchored (§3). Features are grouped with functional requirements nested using globally numbered stable IDs (FR-1 through FR-N). Cross-cutting non-functional requirements live in §10. Assumptions are tagged inline with `[ASSUMPTION: …]` and indexed in §13 for explicit confirmation.

This PRD has been **competitively scanned** against Junction Bot's Direct Connection mode (documentation at `junctionbot.io`). The triage decisions are recorded in `[.decision-log.md](.decision-log.md)`; the resulting feature set is reflected directly in §4 and §7.

The user-supplied tech stack (Python 3.12+, FastAPI, Telethon, MongoDB, Motor, Pydantic Settings, Uvicorn), the prescribed folder layout, deployment topology, full data model, the UI plan, and the Clean-Architecture/DDD layering preference are **constraints**, not PRD content. They are recorded in `[addendum.md](addendum.md)` so the Architect inherits them verbatim while the PRD remains free to describe **what the system must do** without prejudicing **how** it does it.

**Scope note:** The original brief framed MVP as "minimal — channel-to-channel forwarding and message filtering." Triage-time decisions added 12 capabilities to MVP (group sources, folders, regex, allow-keywords, media-type filter, N-th sampling, time-window restriction, source-reference auto-replacement, link substitution, media replacement, reply forwarding, per-rule attribution toggle) **plus the web admin dashboard** (UI build now in MVP per OQ-UI resolution). MVP is no longer "minimal"; it is **production-grade with a competitive feature surface and an operator dashboard**. Estimated build effort sits at roughly 2.5–3× the original brief, accepted by the operator.

## 1. Vision

Forward Bot is a **self-hosted Telegram automation service** that mirrors messages from source channels and groups into destination channels in near real-time, applying configurable filters and transformations along the way. A single operator runs one instance, manages a pool of (source → destination) Forwarding Rules through a REST API and a web admin dashboard, and lets the service do the rest: read new messages from Telegram, decide whether each one qualifies under the active rules, clean and rewrite text (remove links / hashtags / mentions, substitute brand or phrasing, replace links, auto-rewrite source references, regex-replace patterns), respect filter conditions (block / allow keywords, media-type gates, time-windows, sampling), keep edits and deletes in sync, propagate replies into the destination thread, and post to the destination — all without the operator restarting anything when rules change.

The product exists because operators of multi-channel Telegram presences (newsletter operators, community managers, niche content curators) currently stitch together brittle scripts or fragile bot accounts to do the same job. Existing commercial offerings exist (Junction Bot, others) but lock features behind tariffs, require trust in third-party servers, and offer no programmable surface. Forward Bot replaces those with a single durable, observable, REST-driven service designed to grow into AI-assisted rewriting, batching, multi-tenant operation, and a full operator dashboard without rewriting the foundation.

In MVP, Forward Bot does the forwarding job at a competitive feature parity with the leading hosted product. Every other capability on the roadmap — summarization, translation, scheduling, RBAC, dashboards built into the binary, message archive — is a building block that snaps onto this foundation rather than replacing it.

## 2. Target User

### 2.1 Jobs To Be Done

The MVP serves a single operator persona — the **Channel Operator** — who self-hosts the service and configures it via REST API. Their jobs:

- **Mirror channels and groups reliably.** "When a new post lands in Source A — whether a public channel or a group I'm in — I want it in Destination X within seconds, every time, without me babysitting it."
- **Clean and rewrite forwarded text.** "The source has hashtags, competitor mentions, links, and references to itself I don't want. The destination should see a polished version with replacements applied, source links swapped, and source references rewritten."
- **Filter what flows through.** "Block messages with banned keywords. Only forward messages that match my allow-list (when I have one). Drop videos but keep photos. Sample every third message from this firehose. Don't forward anything outside business hours."
- **Organize my sources.** "I have 40 source channels. I want them in folders — Crypto, Tech, Politics — so my rules are manageable and I can see related sources together."
- **Tweak rules without taking the service offline.** "I added a new banned keyword. I shouldn't have to restart anything or wake up tomorrow to a stack of unwanted forwards."
- **Keep threads coherent.** "When someone replies to a post in the source, I want the forwarded reply to land as a reply in the destination too — not as a standalone."
- **See what happened.** "If a message didn't make it through, I want to read the logs and know whether Telegram rejected it, my filter blocked it, or the destination is unreachable — and which message it was."
- **Survive restarts and network issues without re-authenticating to Telegram.** "I logged into Telegram once. I should not log in again every time the container restarts."

### 2.2 Non-Users (v1)

- **End consumers of the destination channels** — they never interact with Forward Bot directly; they see only its output in Telegram.
- **Multiple concurrent operators on the same instance** — MVP is single-Telegram-account, single-operator. Multi-tenant operation is explicit future scope.
- **Non-technical operators** — MVP exposes a REST API, JSON logs, **and a web admin dashboard** (§4.14). Operators using the API directly need comfort with curl/Postman, env vars, and Docker; operators using only the dashboard need none of those.
- **Telegram bot account users** — Forward Bot uses Telegram MTProto (a user account), not the Bot API. Bot-API-only use cases are out of scope.

### 2.3 Key User Journeys

User Journeys are intentionally omitted — Forward Bot is internal/operator tooling with a single non-end-user persona. The JTBD list in §2.1, the FRs in §4, the API surface in §9, and the UI plan in [`addendum.md`](addendum.md) §9 cover the same ground that UJs would for a consumer product. If a richer UX design effort is warranted before UI build, route to `bmad-ux` after PRD finalization.

## 3. Glossary

Downstream workflows must use these terms exactly. FRs and operations use Glossary terms verbatim; synonyms anywhere else in the PRD are a discipline violation.

- **Channel Operator** — The single human running a Forward Bot instance. Configures rules via REST API (and the planned UI), monitors logs, owns the Telegram account used by the service.
- **Source** — A Telegram entity Forward Bot listens to. May be a **channel** or (new in MVP) a **group**. Each Source is registered in the Source Catalog (§4.2) with a stable internal ID.
- **Source Channel** — A Source whose Telegram type is `channel`.
- **Source Group** — A Source whose Telegram type is `group` or `supergroup`. (New in MVP.)
- **Destination** — A Telegram channel Forward Bot has permission to post into. MVP supports only the `channel` destination type; destination groups and destination bots are deferred (§11).
- **Source Folder** — An operator-defined collection of Sources used purely for organization in the operator's view. A Source belongs to at most one Folder. (New in MVP.)
- **Forwarding Rule** — A configuration record mapping one Source to one Destination, carrying its own filter / transform / media settings, attribution toggle, time window, sampling configuration, and an `is_active` flag.
- **Replacement Rule** — A child record of a Forwarding Rule defining one text substitution (literal or regex). A Forwarding Rule may have zero or many Replacement Rules.
- **Processing Pipeline** — The ordered sequence of filter and transform steps applied to a Source Message before it becomes a Forwarded Message. Canonical order: §4.7 FR-11.
- **Source Message** — A new message observed by the Telegram worker in a Source.
- **Forwarded Message** — The result of running a Source Message through the Processing Pipeline of a matched Forwarding Rule and posting it to the rule's Destination.
- **Block Keyword** — A literal or regex pattern. If the Source Message text or caption matches any Block Keyword, the rule does not forward.
- **Allow Keyword** — A literal or regex pattern. If a Forwarding Rule has any Allow Keywords, the rule **only** forwards when the Source Message matches at least one. (New in MVP.)
- **Keyword Match Mode** — Per-rule selector: `literal` (case-insensitive substring) or `regex` (Python regex). Applies to both Block and Allow keywords. (New in MVP.)
- **Media-Type Filter** — Per-rule allowlist/blocklist of Telegram media types. (New in MVP.)
- **Sampling** — Per-rule "forward every N-th message" counter. N=1 means forward every message (default); N=3 means forward every third. (New in MVP.)
- **Time Window** — Per-rule active hours: timezone, days of week, start time, end time. Messages arriving outside the window are blocked. (New in MVP.)
- **Source Reference** — A textual reference inside a Source Message to the Source itself, e.g. `@SourceChannel` or `t.me/SourceChannel`. When the Source-Reference Auto-Replacement toggle is on (§4.8), the Pipeline rewrites these to point at the Destination. (New in MVP.)
- **Link Substitution** — A Replacement Rule whose `search_text` and `replacement_text` are URLs; semantically identical to literal replacement but called out for operator clarity. (New in MVP.)
- **Media Replacement** — Per-rule option to swap the Source Message's photo with a configured replacement photo before posting. (New in MVP.)
- **Reply Forwarding** — When a Source Message is a reply to another Source Message that has already been forwarded under the same rule, post the new Forwarded Message as a reply to the corresponding earlier Forwarded Message. (New in MVP.)
- **Attribution Line** — An optional per-rule prefix or suffix appended to forwarded text, e.g. `From @source_channel`. Per-rule toggle. (New in MVP; not to be confused with native Telegram "Forwarded from X" which is deferred to v2 — see §11.)
- **Message Mapping** — A persisted record linking one Source Message to its resulting Forwarded Message for a given Forwarding Rule. Required for edit / delete / reply propagation.
- **Telegram Session** — The persisted MTProto session state.
- **Hot-Reload Interval** — The period at which the worker refreshes its in-memory rule cache. Default 30s; max acceptable end-to-end staleness 60s.

## 4. Features

### 4.1 Telegram Authentication & Session Persistence

**Description:** Forward Bot authenticates to Telegram once as a user account using MTProto. The Channel Operator provides `API_ID`, `API_HASH`, phone number, completes the SMS/2FA challenge during first-run setup; thereafter the service reconnects automatically across restarts using a persisted session.

#### FR-1: First-run interactive authentication

The Channel Operator can authenticate the service to Telegram during initial setup using `API_ID`, `API_HASH`, phone number, and the SMS/2FA code.

**Consequences:** documented setup procedure exists; success writes a session artifact to a configured persistent path; failure exits with non-zero code and an actionable error.

#### FR-2: Automatic reconnect after restart

The service starts and reaches "connected" state without operator interaction whenever a valid session artifact exists.

**Consequences:** cold-start to "connected" within 30s on a healthy network `[ASSUMPTION]`; network blips reconnect transparently; Telegram-side session invalidation exits cleanly with CRITICAL log.

#### FR-3: Session secrecy at rest

The session artifact is stored only in a path explicitly configured by the operator, never logged, never returned by any API endpoint.

**Consequences:** no log line contains session bytes; no API endpoint exposes session; filesystem permissions on the session directory are the operator's responsibility, documented.

### 4.2 Source Catalog & Folders **(NEW in MVP)**

**Description:** Sources (channels and groups) are first-class records in the system, not strings buried inside Forwarding Rules. The Channel Operator registers each Source once — providing its Telegram username or numeric ID, a display name, the type (channel / group), and an optional Folder assignment — and references the Source by its stable internal ID in every Forwarding Rule. This normalization makes folders cheap (a Source belongs to one Folder; Folders carry zero rule data), makes renames safe (Telegram username changes do not orphan rules), and lays the groundwork for the UI plan (`[addendum.md](addendum.md)` §9).

#### FR-29: Source registration

The Channel Operator can register a Source by providing a Telegram reference (username or numeric ID), a display name, and a type (`channel` | `group`).

**Consequences:**

- Each Source has a server-assigned stable internal ID used by Forwarding Rules.
- The service resolves the Telegram numeric ID at registration time (one Telegram resolve call) and stores both the numeric ID and the username for resilience.
- Two Sources with the same numeric Telegram ID → 422 conflict at registration.
- A registered Source whose username later changes on Telegram remains valid — rules continue to work because the numeric ID is the canonical reference.

#### FR-30: Source-type handling

The system handles Source Channels and Source Groups uniformly through the Processing Pipeline; differences (groups have multiple senders, channels have one logical sender) are surfaced via metadata available to filters.

**Consequences:**

- A Source registered as `group` produces Source Messages whose `sender_id` reflects the actual posting member.
- Filtering by author (D4 in triage, deferred to §11) will consume this metadata when added.
- Channels report a synthetic single sender; group dynamics never affect channel behavior.

#### FR-31: Source Folder management

The Channel Operator can create, rename, list, and delete Folders, and can assign or move a Source to a Folder (or unassign it).

**Consequences:**

- A Folder's only behavior is grouping; Folders carry no filter, transform, or rule data.
- Deleting a Folder that contains Sources unassigns them (Sources are not deleted with the Folder).
- A Source can be in at most one Folder; an unassigned Source is shown as "Ungrouped" in the operator's view.

### 4.3 Forwarding Rule Management

**Description:** Forwarding Rules are the central configuration object. Each rule connects one Source to one Destination and carries the full set of per-rule filters, transforms, media settings, attribution preference, time window, and sampling configuration. Rules are managed through the REST API; UI manipulation comes from the same endpoints when the dashboard ships. The system supports **N:N** mapping.

#### FR-4: Forwarding Rule CRUD

The Channel Operator can create, retrieve, list, update, and delete Forwarding Rules through the REST API.

**Consequences:**

- Create takes a `source_id` (FR-29 reference), `destination_channel`, and the per-rule configuration block; returns the persisted record with `id`, `created_at`, `updated_at`.
- Retrieve non-existent → 404. Updates preserve `id` / `created_at` and refresh `updated_at`. Delete cascades to the rule's Replacement Rules.
- List supports filtering by `source_id`, `destination_channel`, `is_active`, `folder_id` (joining via the Source); paginated, page size 50 / max 200 `[ASSUMPTION]`.
- Two rules with identical (`source_id`, `destination_channel`) pairs are permitted `[ASSUMPTION: allows different filter profiles for the same hop — confirm]`.

#### FR-5: Rule enable / disable

The Channel Operator can flip a Forwarding Rule's `is_active` flag via dedicated `enable` / `disable` endpoints without restart. Disabled rules are ignored within the Hot-Reload Interval.

#### FR-6: Validation on create / update

The system rejects malformed rule payloads at the API boundary with HTTP 422 and a machine-readable error body identifying the offending field.

**Consequences:**

- Missing required fields, unknown fields (strict schema), or self-referential rules (`source` references same channel as `destination`) → 422.
- Invalid regex in `block_keywords` / `allow_keywords` / Replacement Rules when `match_mode=regex` → 422 with the offending pattern surfaced.
- A reference to a `source_id` that does not exist in the Source Catalog → 422.
- Reachability of the Destination channel is **not** validated at create-time (would require Telegram round-trips); accepted MVP gap.

#### FR-31a: Per-rule attribution toggle **(NEW in MVP)**

Each Forwarding Rule carries an `attribution` configuration: `enabled` (bool), `position` (`prefix` | `suffix`), and a `format` template. When enabled, the configured line is added to the Forwarded Message's text, with `{source_name}` and `{source_username}` placeholders substituted from the registered Source.

**Consequences:**

- Default format: `"From {source_name}"` with `position: prefix` `[ASSUMPTION: this is the right default — confirm]`.
- Attribution applies after all transforms; the line itself is not subject to link / hashtag / mention removal.
- If the Source Message has only a photo with no caption and `forward_media: forward`, the attribution becomes the photo's caption.
- This is **not** native Telegram forwarding (the "Forwarded from X" header — that's deferred to v2 / B2). It is a plain-text prefix/suffix the operator controls.

### 4.4 Replacement Rule Management

**Description:** Each Forwarding Rule can have zero or many Replacement Rules — text substitutions applied during the Processing Pipeline. As of this MVP, replacement supports both **literal** and **regex** match modes (regex promoted into MVP from prior future scope). Literal substitutions are case-insensitive `[ASSUMPTION: change from prior PRD's case-sensitive default — confirm]`; regex substitutions follow Python `re` semantics, with capture-group backreferences (`\1`, `\2`, etc.) supported in `replacement_text`.

#### FR-7: Replacement Rule CRUD

The Channel Operator can create, list, update, and delete Replacement Rules scoped to a parent Forwarding Rule.

**Consequences:**

- Each Replacement Rule has `forwarding_rule_id`, `search_text`, `replacement_text`, `match_mode` (`literal` | `regex`), `is_active`, `created_at`, `updated_at`.
- Cascade delete with parent Forwarding Rule (unchanged from prior PRD).
- Invalid regex on save → 422 with the offending pattern.
- Ordering: applied in `created_at` order; an explicit priority field is **not** in MVP `[ASSUMPTION: same as prior — operators with order-sensitive rules will re-create in order]`.

#### FR-8: Replacement semantics

`literal` mode performs case-insensitive substring replacement of all non-overlapping occurrences. `regex` mode applies a `re.sub`-equivalent with Python regex semantics. Both modes apply to message text and to media captions.

**Consequences:**

- A literal Replacement Rule `"old brand"` → `"new brand"` rewrites `"Old Brand"`, `"old brand"`, `"OLD BRAND"` identically.
- A regex Replacement Rule `(\d{4})-(\d{2})-(\d{2})` → `\3/\2/\1` rewrites `2026-05-31` to `31/05/2026`.
- Regex patterns are compiled once per rule per cache refresh; compilation failure logs an error and skips that Replacement Rule for the lifetime of that cache window.

#### FR-38: Link substitution as Replacement Rule **(NEW in MVP — F4)**

URL → URL substitutions use the same Replacement Rule mechanism. Operators may register a Replacement Rule with URL strings in `search_text` and `replacement_text` (in either match mode). The system documents this pattern; no separate collection or endpoint is required.

**Consequences:**

- An operator wanting to swap `https://oldsite.com/promo` for `https://newsite.com/promo` creates a literal Replacement Rule.
- An operator wanting to redirect every URL on `oldsite.com` to the same path on `newsite.com` uses a regex Replacement Rule with capture groups.
- Bare-domain detection (URL without protocol) remains out of MVP scope; the system does not auto-detect "this looks like a URL."

### 4.5 Message Ingestion

#### FR-9: Source subscription

The worker maintains an active subscription to every Source referenced by at least one active Forwarding Rule, whether the Source is a channel or a group. Subscription begins within the Hot-Reload Interval after a new Source is registered and used in an active rule; subscription teardown is best-effort when the Source is no longer referenced.

#### FR-10: Per-rule dispatch

When a Source Message arrives, the worker evaluates every active Forwarding Rule whose `source_id` matches and runs the Processing Pipeline independently for each. One Source Message may produce zero, one, or many Forwarded Messages.

### 4.6 Filtering **(restructured, expanded in MVP)**

**Description:** Filters decide whether a Source Message becomes a Forwarded Message for a given Forwarding Rule. MVP filtering combines time-window gating, sampling, media-type checks, allow-keyword whitelisting, and block-keyword blocklisting. All filters operate per-rule; there is no global / cross-rule filter management UX in MVP (per user instruction, "SKIP E COMPLETELY"). The cheapest filters run first to short-circuit the pipeline before expensive operations.

#### FR-32: Time-window restriction **(NEW in MVP — D7 + I4)**

Each Forwarding Rule carries an optional `time_window` config: timezone (IANA name), days of week (set of `MON..SUN`), start time, end time. If configured and the Source Message arrives outside the window, the pipeline blocks.

**Consequences:**

- `time_window` is optional; absence means the rule runs 24/7.
- Window evaluated against the Source Message's `date` field (Telegram-provided receipt time), interpreted in the rule's timezone.
- Windows may cross midnight (e.g. `22:00–06:00`).
- Logged as `pipeline_blocked` with reason `outside_time_window`.
- This is **not** a delayed-delivery / queue / scheduled-publish mechanism — there is no buffering. Outside the window, messages are dropped (logged) and never delivered.

#### FR-33: Sampling — every N-th message **(NEW in MVP — D3)**

Each Forwarding Rule carries an optional `sampling` config: an integer `n` ≥ 1. The pipeline maintains a per-rule counter; only every n-th Source Message is forwarded.

**Consequences:**

- `n = 1` (default) → every message is forwarded.
- `n = 3` → counter starts at the n-th position (message 3, 6, 9, …). Counter is in-memory and resets on restart (OQ-Sampling-Counter-Persistence closed; opt-in persistence via `SAMPLING_PERSIST=true`).
- Counter resets on service restart (in-memory). This is acceptable — sampling is not a precise mathematical guarantee; operators choosing sampling accept approximate ratios.
- Logged as `pipeline_blocked` with reason `sampled_out` when a message is skipped.

#### FR-34: Media-type filter **(NEW in MVP — D1)**

Each Forwarding Rule carries an optional `media_type_filter` config: an allowlist of Telegram media types from the supported set (`text`, `photo`, plus the deferred set documented as v2). A Source Message whose media type is not in the allowlist is blocked.

**Consequences:**

- Default: allowlist = `["text", "photo"]` (matching the MVP-supported types).
- Setting allowlist = `["text"]` blocks photos for that rule (a useful "text-only digest" pattern).
- Unsupported media types (video, document, voice, sticker, GIF, poll, location, contact) are blocked anyway by FR-15; this filter is the user-facing knob for the subset that *is* supported.
- Logged as `pipeline_blocked` with reason `media_type_filtered`.

#### FR-35: Allow-keyword whitelist **(NEW in MVP — C2)**

Each Forwarding Rule carries an optional `allow_keywords` array. If non-empty, the Source Message must match at least one Allow Keyword (under the rule's Keyword Match Mode) or the pipeline blocks.

**Consequences:**

- Empty allowlist = "allow everything" (the default — preserves backward-compatible "no whitelist" behavior).
- Non-empty allowlist + no match → blocked. Logged with reason `no_allow_keyword_matched`.
- Evaluated against the Source Message text and caption (concatenated).

#### FR-36: Block-keyword filter **(MOVED here, semantics updated)**

Each Forwarding Rule carries an optional `block_keywords` array. If the Source Message matches any Block Keyword (under the rule's Keyword Match Mode), the pipeline blocks.

**Consequences:**

- Matching is case-insensitive substring by default (`match_mode: literal`) or full regex (`match_mode: regex`).
- Match is evaluated against the Source Message text and caption (concatenated).
- Logged with reason `blocked_keyword`, including which keyword matched.

#### FR-37: Keyword Match Mode **(NEW in MVP — C3)**

Each Forwarding Rule carries `keyword_match_mode`: `literal` (case-insensitive substring; default) or `regex` (Python regex).

**Consequences:**

- The mode applies uniformly to `block_keywords` and `allow_keywords` for that rule.
- Invalid regex pattern at rule save → 422 (FR-6).
- Regex compilation is cached per rule per refresh window.

### 4.7 Processing Pipeline

**Description:** The pipeline executes filters first (cheap), then transforms (work), then delivery. Reordering for cost-efficiency: time-window and sampling check first (constant-time), then media-type filter (constant-time), then keyword filters (linear in text length), then transforms.

#### FR-11: Canonical pipeline order **(UPDATED)**

For each (Source Message, Forwarding Rule) pair, the pipeline runs in this exact order:

1. **Time-Window check** (FR-32) — abort with `outside_time_window` if configured and outside.
2. **Sampling check** (FR-33) — increment counter; abort with `sampled_out` if not the N-th message.
3. **Media-Type filter** (FR-34) — abort with `media_type_filtered` if blocked.
4. **Block-Keyword check** (FR-36) — abort with `blocked_keyword` if any matches.
5. **Allow-Keyword check** (FR-35) — abort with `no_allow_keyword_matched` if allowlist non-empty and no match.
6. **Media decision** (FR-14) — choose how media is handled in the eventual post.
7. **Reply lookup** (FR-40) — if Source Message is a reply, look up the parent's Forwarded Message ID for this rule.
8. **Source-Reference Auto-Replacement** (FR-39) — if enabled, rewrite occurrences of the Source's identifiers to point at the Destination.
9. **Text Replacement Rules** (FR-7/8 — literal and regex) — apply in `created_at` order.
10. **Link removal** (FR-13) — if `remove_links=true`, strip URLs.
11. **Hashtag removal** — if `remove_hashtags=true`, strip `#hashtag` tokens.
12. **Mention removal** — if `remove_mentions=true`, strip `@username` tokens.
13. **Media Replacement** (FR-41) — if enabled, swap the Source's photo with the configured replacement.
14. **Whitespace normalization** — collapse runs introduced by removals.
15. **Attribution prefix/suffix** (FR-31a) — if `attribution.enabled=true`, prepend / append the line.
16. **Empty-result check** — if final text/caption is empty AND media is not being forwarded → abort with `empty_after_processing`.
17. **Deliver** — post the resulting Forwarded Message; if step 7 produced a parent ID, post as a reply.
18. **Persist Message Mapping** — write the source→destination mapping for edit / delete / reply propagation.

**Consequences:**

- Blocks short-circuit before transforms; blocking is based on the **original** Source Message content.
- Sampling counter increments only when the time-window check passes — so a sampled rule outside its window does not consume sample-cycle counter.
- A message containing `"giveaway"` (Block Keyword) with `remove_hashtags=true` and `#giveaway` somewhere — still blocked (step 4 precedes step 11).
- An Allow-listed message containing a Block Keyword is still blocked (step 4 before step 5).

#### FR-12: Hot-reloaded rule cache

The pipeline reads from an in-memory cache of active Sources, Folders (for UI joins), Forwarding Rules, and Replacement Rules. The cache is refreshed from MongoDB every 30 seconds (configurable). End-to-end staleness from rule change to next applied evaluation ≤ 60 seconds.

**Consequences:** unchanged from prior PRD. Non-blocking refresh; in-flight pipeline runs use their snapshot; new cache becomes visible to the next pipeline run.

#### FR-13: URL stripping coverage

`remove_links=true` removes `http://…`, `https://…`, `t.me/…`, `telegram.me/…`, `tg://…`, and joinchat / `+` invite-link forms. Bare-domain stripping remains deferred (§11).

### 4.8 Source-Reference Auto-Replacement **(NEW in MVP — F3)**

**Description:** Forward Bot can rewrite occurrences of the Source's identifiers (its `@username`, its `t.me/<username>` URL form, and an operator-supplied display alias) into corresponding identifiers of the Destination — keeping forwarded content "talking about" the operator's destination rather than the upstream source. This is the single most-requested feature for white-label channel mirroring.

#### FR-39: Source-Reference Auto-Replacement

Each Forwarding Rule has an `auto_replace_source_refs` config: `enabled` (bool), `replacement` (string template, optional).

**Consequences:**

- When enabled and `replacement` is empty, the Destination's `@username` is substituted (resolved at pipeline time from the rule's `destination_channel`).
- When `replacement` is provided, that literal string is substituted instead.
- Patterns rewritten: `@<source_username>`, `t.me/<source_username>`, `https://t.me/<source_username>`, and `<source_display_name>` if the operator opts in to display-name rewriting (boolean sub-toggle `replace_display_name`).
- Matching is case-insensitive for `@username` patterns; case-sensitive for display-name patterns `[ASSUMPTION]`.
- Runs in the pipeline *before* generic text Replacement Rules — so that operator-defined Replacement Rules can further rewrite the substituted text if needed.

### 4.9 Media Handling **(updated)**

**Description:** MVP supports text messages and photos with optional captions. Per-rule, the operator chooses how media is treated and, new in MVP, whether the photo should be **replaced** with a configured override before posting.

#### FR-14: Media mode selection

`forward_media` accepts `forward` | `ignore` | `caption_only` (unchanged from prior PRD).

**Consequences:** unchanged from prior PRD (see prior text).

#### FR-15: Media-type scope

MVP supports **photos** with optional captions and **text messages**. Other media types — videos, documents, voice notes, stickers, GIFs, polls, locations, contacts — are dropped silently (logged `unsupported_media_type`). FR-34 (Media-Type Filter) gives the operator a knob to deselect even the supported types.

#### FR-16: Media album limitation

Each item in a Telegram media album is processed independently in MVP — albums fragment. `[NOTE FOR PM]` — prioritize album reassembly early in v2 if operator feedback shows fragmentation is jarring.

#### FR-41: Media Replacement **(NEW in MVP — H2)**

Each Forwarding Rule has an optional `media_replacement` config: `enabled` (bool), `replacement_image_path` (filesystem path to an image), optional `replacement_caption_mode` (`use_replacement` | `use_source` | `none`).

**Consequences:**

- When enabled and the Source Message contains a photo, the Forwarded Message uses the configured `replacement_image_path` photo instead of the Source's photo.
- When the Source Message has no photo (text-only), Media Replacement does nothing — there is no synthetic photo injection in MVP `[ASSUMPTION: text-only messages stay text-only; confirm we don't want "always attach this image"]`.
- The replacement image is read from a configured filesystem path the operator controls; the operator must ensure read access. No remote URL fetching in MVP `[ASSUMPTION: simpler / safer than HTTP-fetching at pipeline time — confirm]`.
- Image transforms (resize, crop, filter) are **out of scope** in MVP. The configured image is sent as-is.
- If the replacement image cannot be read at pipeline time (file missing, no permission), the rule falls back to forwarding the source photo with a logged WARNING `[ASSUMPTION: fallback rather than fail-loud — confirm preference]`.

### 4.10 Rule Hot-Reload

Unchanged from prior PRD (FR-17, FR-18).

### 4.11 Edit, Delete & Reply Propagation **(updated to include reply forwarding)**

**Description:** When a Source Message is edited or deleted, Forward Bot keeps the destination in sync (existing FR-20, FR-21). New in MVP: when a Source Message is itself a reply to another Source Message that has been forwarded under the same rule, the Forwarded Message is also posted as a reply to the corresponding earlier Forwarded Message — preserving thread coherence in the destination (I8 in triage).

#### FR-19: Message-mapping persistence

Unchanged from prior PRD. Schema captured in `[addendum.md](addendum.md)` §5.

#### FR-20: Edit propagation

Unchanged from prior PRD.

#### FR-21: Delete propagation

Unchanged from prior PRD.

#### FR-40: Reply forwarding **(NEW in MVP — I8)**

When a Source Message is a reply to another Source Message (Telegram's `reply_to_msg_id` field is populated), the pipeline looks up the parent Source Message's Message Mapping for the **same Forwarding Rule**. If a mapping exists and is within retention, the Forwarded Message is posted as a reply to the parent's Forwarded Message; otherwise the Forwarded Message is posted standalone.

**Consequences:**

- Reply chains in groups are preserved when both parent and child are forwarded under the same rule.
- If the parent was blocked by a filter or fell outside Mapping retention, the reply is forwarded standalone (logged `reply_parent_not_found`) — the message itself is not dropped.
- If the destination message that should be the reply target has since been deleted on the destination side, the reply is posted standalone (logged `reply_target_missing`).
- Cross-rule reply linking is **not** in scope (replies in destination D1 only chain when both parent and child were forwarded by the same rule).

### 4.12 Failure Handling & Reliability

Unchanged from prior PRD: FR-22 (FloodWait), FR-23 (retry with backoff), FR-24 (per-rule isolation), FR-25 (graceful shutdown).

### 4.13 Observability

Unchanged from prior PRD: FR-26 (structured JSON), FR-27 (event coverage), FR-28 (secrets never logged). **Event coverage extended** to include the new pipeline outcomes: `outside_time_window`, `sampled_out`, `media_type_filtered`, `no_allow_keyword_matched`, `reply_parent_not_found`, `reply_target_missing`, `media_replacement_failed`, `source_registered`, `source_resolved`, `folder_created`.

### 4.14 Web Admin Dashboard **(NEW in MVP — OQ-UI resolved: in MVP build)**

**Description:** A browser-based operator dashboard delivered as part of the MVP build. Eight screens (Dashboard, Forwards List, Forward Create/Edit, Sources List, Source Create/Edit, Folder modals, Logs, Settings) cover every operator workflow that the REST API supports — no operator should need to drop to curl. Architecture, screens, IA, and screen→DB→API mapping live in [`addendum.md`](addendum.md) §9–10.

#### FR-42: Dashboard surface coverage

The web admin dashboard provides UI affordances for every operator action exposed by the REST API in §9 (Forwarding Rules CRUD + enable/disable, Replacement Rules CRUD, Sources CRUD, Folders CRUD, health view).

**Consequences:**
- Every entity in §5 of the addendum (forwarding_rules, replacement_rules, sources, source_folders) has a list view and a detail / edit view.
- A new operator can install the service, open the dashboard, register a Source, create a Forwarding Rule with filters and transforms, and see it forwarding — without ever touching `curl` or the API.
- Health state (Telegram connection, MongoDB reachability) is visible on the Dashboard surface (S1) and a global indicator in the top bar.

#### FR-43: Cookie-based UI auth

A dedicated UI auth endpoint accepts the `X-API-Key` value and exchanges it for an HttpOnly, SameSite=Strict session cookie scoped to the bind host. The dashboard uses the cookie for subsequent requests; the API key is never persisted in browser-accessible storage.

**Consequences:**
- `POST /api/v1/auth/login` accepts `{ "api_key": "..." }`; on match, sets the session cookie; mismatch → 401.
- `POST /api/v1/auth/logout` clears the cookie.
- Cookie expiry: **24 hours** (OQ-UI-Auth-Cookie-TTL closed).
- The cookie-auth path applies only to UI traffic; programmatic API consumers continue to use `X-API-Key` directly.

#### FR-44: Live log streaming

The Logs screen (S7) connects to a streaming endpoint that pushes JSON log lines as they happen, filterable by `event` and `correlation_id`.

**Consequences:**
- Server-Sent Events (SSE) is the chosen mechanism (OQ-UI-Stream closed).
- A separate `GET /api/v1/logs/search` endpoint supports correlation-ID lookup over the recent past (default last 1h, max 24h).
- Log retention beyond what stdout collectors hold is **not** in MVP scope; the search endpoint operates over a small in-memory ring buffer plus whatever the host's log aggregator exposes.

#### FR-45: Build & serve

The dashboard is built as a static asset bundle and served by the same FastAPI process at `/` (with API at `/api/v1/*`). No separate frontend deploy.

**Consequences:**
- Tech stack: React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Router + shadcn/ui (addendum §1.6).
- The Docker image multi-stage build compiles the frontend during image build; runtime image carries only the compiled assets.
- A single env var `UI_ENABLED` (default `true` for MVP) controls whether the static assets are mounted; disabling it returns 404 for non-API paths.

## 5. Constraints and Guardrails

Unchanged from prior PRD: §5.1 Telegram Platform Constraints, §5.2 Security Constraints (API key + localhost bind), §5.3 Operational Constraints (single instance, MongoDB mandatory).

## 6. Non-Goals (Explicit)

Same as prior PRD with these added: **Forward Bot is not a moderation product** (Review-mode I2 is explicitly out, both MVP and tracked future). **Forward Bot is not a scheduler / queue** (I3 scheduled publishing dropped from tracked scope; time-window restriction FR-32 is a *filter* not a queue). **Forward Bot is not a deduplication product** (D6 dropped). **Forward Bot does not analyze who said what** (D4 author filter deferred; D5 own-messages filter dropped).

## 7. MVP Scope

### 7.1 In Scope

**Auth & session.** Telegram MTProto authentication, session persistence, automatic reconnect (FR-1–3).

**Source Catalog & Folders (new).** Source registration with channel/group type, Telegram-ID resolution at register time, Folder CRUD, Folder assignment (FR-29, FR-30, FR-31).

**Forwarding & Replacement Rules.** Forwarding Rule CRUD + enable/disable + per-rule attribution toggle (FR-4, FR-5, FR-6, FR-31a). Replacement Rule CRUD with literal + regex match modes, link substitution via Replacement Rules (FR-7, FR-8, FR-38).

**N:N source→destination mapping.** (FR-4, FR-10.)

**Filtering (expanded).** Time-window restriction, sampling, media-type filter, allow-keyword whitelist, block-keyword filter, keyword match mode literal/regex (FR-32–37).

**Processing Pipeline.** Reordered to filter-cheap-first, with all new MVP transforms slotted in (FR-11).

**Source-Reference Auto-Replacement (new).** Rewriting `@source` patterns into destination references (FR-39).

**Media handling.** Text + photo with caption, `forward` / `ignore` / `caption_only` modes, media replacement with configured image (FR-14, FR-15, FR-41). Albums fragment (FR-16, accepted gap).

**Hot-reload of rules.** Periodic 30s cache refresh, refresh-failure resilience (FR-12, FR-17, FR-18).

**Edit, delete & reply propagation.** Edits and deletes propagate to forwarded copies; replies in source thread post as replies in destination thread when parent mapping exists (FR-19, FR-20, FR-21, FR-40).

**Reliability.** FloodWait handling, exponential retry, per-rule failure isolation, graceful shutdown (FR-22–25).

**Observability.** Structured JSON logs with correlation IDs, expanded event coverage (FR-26–28).

**REST API endpoints** listed in §9.

**API auth.** Local-bind-by-default + `X-API-Key` (§5.2).

**Deployment** via Docker / Docker Compose to a Linux VPS (`[addendum.md](addendum.md)` §4).

**Web admin dashboard (NEW — OQ-UI resolved: in MVP).** 8 screens — Dashboard, Forwards List, Forward Create/Edit, Sources List, Source Create/Edit, Folder modals, Logs (live SSE stream + correlation-ID search), Settings. Cookie-based UI auth, live log streaming, and "build-and-serve from same container" delivery (FR-42, FR-43, FR-44, FR-45). Tech stack: React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Router + shadcn/ui. Plan + screen-to-DB mapping in `[addendum.md](addendum.md)` §9–10.

### 7.2 Out of Scope for MVP — see §11 for future tracking

- Multi-user / RBAC.
- Native Telegram repost (the "Forwarded from X" header — `attribution` in MVP is plain-text prefix/suffix).
- AI features (rewrite, translate, summarize).
- Expanded source types beyond channel + group (bots, DMs).
- Expanded destination types (groups, bots).
- Expanded media types beyond photo (video, document, voice, sticker, GIF, poll, location).
- Album reassembly.
- All-word-forms / morphology matching.
- Author filtering (D4).
- Direct-only filtering (D2).
- Header / footer text fields beyond the attribution line.
- Truncation / max-length.
- Format conversion (HTML / Markdown / plain).
- Premium emoji handling.
- Inline-button creation.
- Media watermarks; media transforms beyond swap (resize, crop, filter).
- Batching (combining N source messages into one destination post).
- Reactions / pin mirroring.
- Persistent dead-letter queue.
- Reachability validation on rule create.

### 7.3 Removed from all scope tracking — explicit drops

These were considered and rejected; they will not be tracked in §11 future scope:

- **Review / moderation mode** (I2) — Forward Bot is not a moderation product.
- **Scheduled publishing / queue** (I3) — out; time-windowing (FR-32) covers the operator pain point without buffering.
- **Filter own messages** (D5) — operator pattern doesn't justify.
- **Duplicate filter** (D6) — operator pattern doesn't justify.
- **Delayed filter** (D8) — too clever; not requested.
- **All filter-management UX** (E1–E5) — global filter library, copy filter between rules, dry-run, filter ordering, AI semantic filtering — dropped wholesale.

## 8. Success Metrics

**Primary**

- **SM-1: Forwarding latency.** P95 time from Source Message receipt to Forwarded Message delivered ≤ **3 seconds** under nominal load. Validates FR-10, FR-11.
- **SM-2: Forwarding reliability.** Successful-forward rate ≥ **99%** across a 7-day window, excluding messages legitimately blocked by filters or destinations made permanently unreachable. Validates FR-22, FR-23, FR-24.
- **SM-3: Configuration responsiveness.** A rule change committed via the API takes effect within **60 seconds** in 100% of cases. Validates FR-12, FR-17.
- **SM-6: Filter correctness (new).** For each filter step (time-window, sampling, media-type, allow-keyword, block-keyword), the false-positive (incorrectly blocked) and false-negative (incorrectly allowed) rates are each **≤ 0.5%** on a curated test corpus. Validates FR-32–37.

**Secondary**

- **SM-4: Restart resilience.** Service restarts re-establish Telegram connection within **30 seconds** in 100% of cases where a valid session exists.
- **SM-5: Edit/delete/reply propagation accuracy.** Edits, deletes, and reply linkage within Mapping retention propagate within **5 seconds** in ≥ **95%** of cases. Validates FR-20, FR-21, FR-40.

**Counter-metrics (do not optimize)**

- **SM-C1: Aggressive retry rate.** Do not maximize SM-2 by triggering FloodWait or risking account restriction. Counterbalances SM-2.
- **SM-C2: Throughput at the cost of latency.** Not a batch system. Counterbalances SM-1.
- **SM-C3: Storage growth.** Mapping retention defaults to 30d. Counterbalances SM-5.
- **SM-C4: Pipeline complexity drift (new).** With 12 new MVP features, the canonical pipeline (FR-11) is at the edge of "still readable." Resist adding further filter or transform steps for v1.x without explicit cost-justification. Counterbalances feature-completeness pressure.

## 9. API Surface

Unchanged endpoint families from prior PRD, plus:

**Sources (new)**

- `POST   /api/v1/sources` — register a Source (FR-29).
- `GET    /api/v1/sources` — list (filter by `type`, `folder_id`; paginated).
- `GET    /api/v1/sources/{id}` — retrieve.
- `PUT    /api/v1/sources/{id}` / `PATCH …` — update (rename, reassign folder, change display name).
- `DELETE /api/v1/sources/{id}` — delete (blocked if any active Forwarding Rule references it; 409).

**Folders (new)**

- `POST   /api/v1/folders` — create.
- `GET    /api/v1/folders` — list with Source counts.
- `GET    /api/v1/folders/{id}` — retrieve with optional `?include=sources`.
- `PUT    /api/v1/folders/{id}` — rename.
- `DELETE /api/v1/folders/{id}` — delete (unassigns its Sources; does not delete them).

**UI-supporting endpoints (NEW in MVP — supports §4.14)**

- `POST   /api/v1/auth/login` — exchange `X-API-Key` for HttpOnly session cookie (FR-43).
- `POST   /api/v1/auth/logout` — clear session cookie.
- `GET    /api/v1/stats/summary` — last-24h forwards succeeded / failed / blocked counters (Dashboard S1).
- `GET    /api/v1/logs/recent?limit=N` — last N log lines from the ring buffer (S1 recent-activity panel).
- `GET    /api/v1/logs/stream` — SSE stream of live log events (S7), filterable by query params `event`, `correlation_id`.
- `GET    /api/v1/logs/search?correlation_id=…&since=…` — search recent log ring buffer (FR-44).
- `POST   /api/v1/admin/reconnect` — operator-triggered Telegram reconnect (S8 Settings).
- `GET    /` (and any non-API path) — serves the compiled UI bundle when `UI_ENABLED=true` (FR-45).

**Forwarding Rules, Replacement Rules, Health** — same as prior PRD.

## 10. Cross-Cutting Non-Functional Requirements

Unchanged from prior PRD with updates:

- **NFR-Perf.** P95 forwarding latency ≤ 3s — measured *after* the new pipeline steps (FR-11). Cache refresh must remain ≤ 1s for up to **1,000 active rules + 1,000 active Sources + 50 Folders**.
- **NFR-Scale.** Single-instance target: **100 active Sources** (channels + groups combined), **5,000 messages/day**. `[ASSUMPTION]` confirm specific scale target.
- **NFR-Rel / Sec / Obs / Maint.** Unchanged.
- **NFR-Compat.** Adding fields to `forwarding_rules`, `sources`, `source_folders` must be backward-compatible (nullable / defaulted).

## 11. Future Roadmap (post-MVP)

Cleaned-up future-tracking. Items that have been **dropped** entirely from scope tracking are in §7.3, not here.

- **Dashboard v2 additions** (post-MVP UI work): in-browser filter diagnostics / dry-run pane (re-considers E4 if operators ask), drag-and-drop folder reorganization, multi-user views (depends on RBAC below), real-time push beyond SSE, custom themes, internationalization.
- **Expanded sources.** Telegram bots as senders, direct messages / DMs.
- **Expanded destinations.** Telegram groups, Telegram bots.
- **Native Telegram repost mode.** The "Forwarded from X" header (B2 in triage); attribution `position`/`format` plays alongside.
- **All-word-forms / morphology** matching for keywords (C4).
- **Author filtering** (D4) — depends on group-source maturity.
- **Direct-only filter** (D2) — block messages the Source itself was forwarding from elsewhere.
- **Header / footer text fields** beyond the attribution line (F5, F6).
- **Truncation / max-length** (F7).
- **Format conversion** (HTML ↔ Markdown ↔ plain) (F8).
- **Premium emoji handling** (F9).
- **Inline-button creation** on forwarded messages (F10).
- **Media watermarks** (H1).
- **Image transforms** on the configured replacement image (resize, crop, filter).
- **Expanded media types** (video, document, voice, sticker, GIF, poll, location, contact) (H4).
- **Media album reassembly.**
- **Batching** — combine N source messages into one destination post (I5).
- **Reaction forwarding** (I9).
- **Pin handling** (I10).
- **AI processing layer.** Summarize, translate, rewrite. Per-rule AI step configurable.
- **Analytics.** Counts, success rates, per-channel statistics.
- **Multi-user & RBAC.**
- **Full message archive & search.**
- **Reachability validation on rule create.**
- **Persistent dead-letter queue** for forwards that exhausted retries; manual replay endpoint.
- **Bot API mode** as an alternative transport.

## 12. Risks and Mitigations

All risks from prior PRD remain. **New risk introduced by MVP scope expansion:**


| Risk                                                                                                                                                                                             | Likelihood | Impact | Mitigation                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pipeline complexity drift.** The canonical pipeline (FR-11) has 18 steps in MVP; reasoning about why a specific message was or wasn't forwarded becomes harder for the operator.               | Medium     | Medium | Observability discipline (FR-27 expanded event coverage); each block decision logs the *specific reason*; SM-6 establishes a measurable correctness floor.                                                |
| **Source Catalog migration cost** if a Source ID strategy changes. The Catalog is new; if numeric IDs vs usernames vs display IDs need to shift, every Forwarding Rule rewrites its `source_id`. | Low        | Medium | Numeric Telegram ID as the canonical key (FR-29); usernames are mutable metadata. Migration tooling is a v1.1 ask, not MVP.                                                                               |
| **Time-window mis-evaluation across DST transitions** in operator's chosen timezone.                                                                                                             | Low        | Low    | Use IANA timezone names + `zoneinfo` (Python stdlib); rely on OS tzdata being current; document in operator runbook to keep host tzdata updated.                                                          |
| **Reply forwarding produces orphan replies** when parent was blocked by filter — destination shows replies-to-nothing                                                                            | Medium     | Low    | FR-40 explicitly defines fallback (post standalone with log); accepted MVP behavior. `[NOTE FOR PM]` — observe in production; if confusing, add "Re:" prefix or skip the reply entirely as a v1.1 toggle. |
| **Media Replacement file path mistakes** (operator typos / file deletions) cause silent fallback to source photo                                                                                 | Medium     | Low    | FR-41 fallback is logged WARNING; readiness check at startup verifies configured replacement paths exist (best-effort).                                                                                   |


## 13. Assumptions Index

All assumptions from prior PRD that remain valid, **plus new MVP-feature assumptions:**

- FR-7 / FR-8: **Literal Replacement is now case-insensitive** (was case-sensitive in prior PRD). Confirm preference; case-insensitive is closer to what operators expect when they configure brand-name rewrites.
- FR-31a: **Attribution default format** `"From {source_name}"` with `position: prefix`. Confirm.
- FR-33 (Sampling): **Counter starts at the N-th position by default** (so n=3 means message 3, 6, 9). Confirm vs "forward 1st, then 4th, 7th."
- FR-34 (Media-Type Filter): **Default allowlist = supported types** (`["text", "photo"]`). Confirm.
- FR-39 (Source-Reference Auto-Replacement): **Case-insensitive `@username`, case-sensitive display-name**. Confirm.
- FR-41 (Media Replacement): **No synthetic image injection** for text-only messages — confirm.
- FR-41: **Replacement image read from local filesystem path only** (no HTTP fetch). Confirm.
- FR-41: **Fallback to source photo on read failure** (with WARNING). Confirm vs fail-loud.
- §10 NFR-Perf: **Cache refresh ≤ 1s for 1,000 rules + 1,000 Sources + 50 Folders.** Confirm scale targets.
- All assumptions from prior PRD that did not relate to dropped features remain unchanged.

## 14. Open Questions

All open questions resolved as of 2026-05-31.

1. **OQ-Name. Closed.** "Forward Bot" is the confirmed product name.
2. **OQ-ChannelRef. Closed.** Settled by FR-29: numeric Telegram ID is canonical; username stored as metadata.
3. **OQ-MappingRetention. Closed.** 30-day retention is **global** (one `MAPPING_RETENTION_DAYS` env var, default 30). Per-rule retention deferred to post-MVP.
4. **OQ-DLQ. Closed.** Logging-only in MVP. Failed forwards are observable via structured logs and correlation-ID search (FR-44). `GET /api/v1/failures` deferred to post-MVP.
5. **OQ-AuthUX. Closed.** First-run Telegram authentication via `python -m forward_bot auth` inside the container (interactive CLI). Already documented in addendum §4.2. No REST endpoint for auth in MVP.
6. **OQ-Seed. Closed.** API-only. No YAML/JSON seed file at startup. Operators configure via dashboard or REST API. Seed file support deferred to post-MVP.
7. **OQ-RuleActiveDefault. Closed.** Created rules default to `is_active=false`. Operator explicitly activates after review. (Confirmed by EXPERIENCE.md §Key Flows, Flow 2.)
8. **OQ-FolderDefault. Closed.** Newly-registered Sources are unassigned by default. Operator assigns to a Folder afterward.
9. **OQ-Sampling-Counter-Persistence. Closed.** Sampling counter is in-memory only (`SAMPLING_PERSIST=false` default). Resets on restart; approximate ratios are acceptable. Operator opts in to persistence via `SAMPLING_PERSIST=true` (addendum §4.1).
10. **OQ-UI. Closed.** UI BUILD is in MVP scope. Plan in `[addendum.md](addendum.md)` §9; FRs FR-42 through FR-45 in §4.14.
11. **OQ-UI-Auth-Cookie-TTL. Closed.** Session cookie expiry is **24 hours** (HttpOnly, SameSite=Strict). Browser-session-only is insufficient for a self-hosted tool used across sessions.
12. **OQ-UI-Stream. Closed.** **SSE** (Server-Sent Events) for the live log stream (`GET /api/v1/logs/stream`). One-way server-push; simpler than WebSocket; sufficient for the read-only log tail use case. (Confirmed by EXPERIENCE.md.)
13. **OQ-Logs-Retention. Closed.** In-memory ring buffer sized for **1 hour** by default, configurable up to **24 hours** via `LOG_RING_BUFFER_HOURS` env var. Older events are not retained server-side; stdout collectors are the operator's long-term log store.

---

*End of PRD. Companion documents:*

- `[addendum.md](addendum.md)` — tech stack, folder layout, deployment topology, full data model, **UI plan**, screen-to-DB mapping, mechanism-level decisions deferred from §4.
- `[.decision-log.md](.decision-log.md)` — audit trail including the Junction-Bot competitive scan and the triage decisions that produced this MVP scope.

