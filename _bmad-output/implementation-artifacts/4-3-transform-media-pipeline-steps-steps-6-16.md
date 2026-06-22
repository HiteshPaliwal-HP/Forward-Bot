---
baseline_commit: 343be125cf74a3fef57c093a5518b0c8227b689e
---
# Story 4.3: Transform & Media Pipeline Steps (Steps 6â€“16)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want forwarded messages to be cleaned and rewritten â€” stripping links/hashtags/mentions, substituting text patterns, auto-replacing source references, and optionally swapping the photo â€” before delivery,
so that destination channels receive polished, on-brand content without manual editing.

## Acceptance Criteria

1. **Media Decision Step (Step 6):**
   - **Given** `forward_media="forward"` and the message has a photo.
   - **When** `MediaDecisionStep.apply()` runs.
   - **Then** `ctx.media` remains set to the photo and `ctx.caption` is preserved.
   - **Given** `forward_media="ignore"`.
   - **When** `MediaDecisionStep.apply()` runs.
   - **Then** both `ctx.media` and `ctx.caption` are set to `None`.
   - **Given** `forward_media="caption_only"`.
   - **When** `MediaDecisionStep.apply()` runs.
   - **Then** `ctx.media` is set to `None` and the caption text is retained. (If `ctx.text` is empty/None and `ctx.caption` is populated, the caption text is promoted to `ctx.text` so that downstream text-based transforms process it, and `ctx.caption` is set to `None`).

2. **Reply Lookup Step (Step 7):**
   - **Given** the source message is a Telegram reply (e.g. `ctx.metadata.get("reply_to_msg_id")` is present) and `mapping_repository` is injected.
   - **When** `ReplyLookupStep.apply()` runs.
   - **Then** it queries `mapping_repository.get_by_source_message(source_channel_id=ctx.source.telegram_id, source_message_id=reply_to_msg_id, forwarding_rule_id=ctx.rule.id)`.
   - **And** if a mapping is found, it sets `ctx.reply_target_destination_id = parent_mapping.destination_message_id`.
   - **And** if no parent mapping is found (filtered or outside retention), it logs a warning `{"event": "reply_parent_not_found", ...}` and leaves `ctx.reply_target_destination_id = None`, continuing the pipeline.
   - **And** if `mapping_repository` is not configured, it fails open (logs warning and leaves `ctx.reply_target_destination_id = None`).

3. **Source Reference Auto-Replacement Step (Step 8):**
   - **Given** `auto_replace_source_refs.enabled=true` and a registered source.
   - **When** `SourceRefReplaceStep.apply()` runs.
   - **Then** it scans `ctx.text` and `ctx.caption` and case-insensitively replaces references to the source username:
     - `@<source.telegram_username>`
     - `t.me/<source.telegram_username>`
     - `https://t.me/<source.telegram_username>`
   - **And** replaces them with the destination's reference (defaults to the rule's `destination_channel` username, or `auto_replace_source_refs.replacement` if provided).
   - **And** if `auto_replace_source_refs.replace_display_name=true`, it case-sensitively replaces `<source.display_name>` in text/caption as well.
   - **And** this step runs before any generic Replacement Rules.

4. **Text Replacement Rules Step (Step 9):**
   - **Given** the forwarding rule has active child `ReplacementRules`.
   - **When** `TextReplacementStep.apply()` runs.
   - **Then** it applies each active replacement rule to `ctx.text` and `ctx.caption` in ascending order of `created_at`.
   - **And** if `match_mode="literal"`, case-insensitive substring replacement is performed.
   - **And** if `match_mode="regex"`, Python regex matching and `re.sub` replacement are performed, supporting capture-group backreferences (e.g. `\1`, `\2`), using pre-compiled patterns from the `RuleCache` snapshot (`CacheHolder.current.compiled_patterns.get(rule.id).replacement_patterns`).
   - **And** if pre-compiled patterns are missing from cache (e.g., in test environments), it compiles the regex pattern dynamically with case insensitivity (`re.IGNORECASE`), logging a warning on compile error and skipping the invalid pattern.

5. **Link Removal Step (Step 10):**
   - **Given** `remove_links=true` on the forwarding rule.
   - **When** `LinkRemovalStep.apply()` runs.
   - **Then** it strips links from both `ctx.text` and `ctx.caption`.
   - **And** the stripped patterns include: `http://`, `https://`, `t.me/`, `telegram.me/`, `tg://`, and joinchat link structures (`t.me/joinchat/...` or `t.me/+...`).

6. **Hashtag & Mention Removal Steps (Steps 11 and 12):**
   - **Given** `remove_hashtags=true` / `remove_mentions=true`.
   - **When** `HashtagRemovalStep.apply()` and `MentionRemovalStep.apply()` run.
   - **Then** hashtag tokens (e.g., `#hashtag`) and mention tokens (e.g., `@username`) are stripped from `ctx.text` and `ctx.caption`.

7. **Media Replacement Step (Step 13):**
   - **Given** `media_replacement.enabled=true` and the message context has a photo (`ctx.media` is present).
   - **When** `MediaReplacementStep.apply()` runs.
   - **Then** it resolves the path as `Path(settings.media_replacement_base_dir) / rule.media_replacement.replacement_image_path`.
   - **And** it enforces path containment to prevent directory traversal: asserts the resolved path is within `settings.media_replacement_base_dir`. If a traversal attempt is detected, it logs a warning `{"event": "media_replacement_path_traversal_attempt", ...}` and falls back to the original source photo.
   - **And** it checks if the file exists using `asyncio.to_thread(candidate.exists)`. On missing file or read failure, it logs a warning `{"event": "media_replacement_failed", ...}` and falls back to the original source photo.
   - **And** if the file exists, it assigns the resolved `Path` object to `ctx.media` instead of reading the file into memory as bytes, so that `DeliveryStep` can later pass the path string directly to Telethon, saving significant memory.
   - **And** based on `replacement_caption_mode`:
     - `"none"`: sets caption to `None`.
     - `"use_source"`: keeps the processed caption.
     - `"use_replacement"`: since there is no custom replacement caption field, sets caption to `None` or leaves it empty.

8. **Whitespace Normalization Step (Step 14):**
   - **Given** preceding removal transforms have run.
   - **When** `WhitespaceStep.apply()` runs.
   - **Then** all multiple consecutive spaces, tabs, or newlines in `ctx.text` and `ctx.caption` are collapsed to single spaces/newlines, and leading/trailing whitespace is stripped.

9. **Attribution Prefix/Suffix Step (Step 15):**
   - **Given** `attribution.enabled=true`.
   - **When** `AttributionStep.apply()` runs.
   - **Then** it formats the template string (replacing `{source_name}` with `ctx.source.display_name` and `{source_username}` with `ctx.source.telegram_username` or display name fallback if username is missing).
   - **And** if `position="prefix"`, it prepends the formatted attribution.
   - **And** if `position="suffix"`, it appends the formatted attribution.
   - **And** attribution target logic strictly follows: `if ctx.media:` apply to `ctx.caption` (initialize to `""` if `None`); `else:` apply to `ctx.text`.

10. **Empty Result Check Step (Step 16):**
    - **Given** the processed text is empty, caption is empty/None, AND no media is being forwarded.
    - **When** `EmptyCheckStep.apply()` runs.
    - **Then** it safely evaluates `if not ctx.text and not ctx.caption and ctx.media is None:` (handling `ctx.media` potentially being a `Path` object) and returns `BlockedOutcome(reason="empty_after_processing")`.

11. **Integration and Exception Isolation:**
    - **Given** steps 6â€“16 are implemented.
    - **When** `PipelineEngine` is instantiated.
    - **Then** all steps are registered in the canonical 18-step sequence, and `ReplyLookupStep` is correctly passed the `mapping_repository`.
    - **And** unexpected catastrophic exceptions raised inside a step are caught, logged, and return `BlockedOutcome(reason="step_error")` to isolate failures.
    - **And** expected step-specific fallbacks (like `MediaReplacementStep` falling back to the source photo on read error) MUST take precedence and return the context rather than dropping the message.

## Tasks / Subtasks

- [x] **Infrastructure & Steps Refactoring**
  - [x] Update `PipelineEngine.__init__` in `src/forward_bot/application/pipeline/engine.py` to accept `mapping_repository: MappingRepository` as an argument and instantiate `ReplyLookupStep(mapping_repository)`.
  - [x] Update dependency injection in `src/forward_bot/api/dependencies/providers.py` (or where the engine is constructed) to inject `MappingRepository` into the `PipelineEngine` factory.
  - [x] Implement `MediaDecisionStep` in `src/forward_bot/application/pipeline/steps/media_decision.py`.
  - [x] Implement `ReplyLookupStep` in `src/forward_bot/application/pipeline/steps/reply_lookup.py` taking `mapping_repository`.
  - [x] Implement `SourceRefReplaceStep` in `src/forward_bot/application/pipeline/steps/source_ref_replace.py`.
  - [x] Implement `TextReplacementStep` in `src/forward_bot/application/pipeline/steps/text_replacement.py`.
  - [x] Implement `LinkRemovalStep` in `src/forward_bot/application/pipeline/steps/link_removal.py`.
  - [x] Implement `HashtagRemovalStep` in `src/forward_bot/application/pipeline/steps/hashtag_removal.py`.
  - [x] Implement `MentionRemovalStep` in `src/forward_bot/application/pipeline/steps/mention_removal.py`.
  - [x] Implement `MediaReplacementStep` in `src/forward_bot/application/pipeline/steps/media_replacement.py`.
  - [x] Implement `WhitespaceStep` in `src/forward_bot/application/pipeline/steps/whitespace.py`.
  - [x] Implement `AttributionStep` in `src/forward_bot/application/pipeline/steps/attribution.py`.
  - [x] Implement `EmptyCheckStep` in `src/forward_bot/application/pipeline/steps/empty_check.py`.
  - [x] Update `src/forward_bot/application/pipeline/steps/__init__.py` to import and expose these new steps instead of placeholders.
- [x] **Unit & Integration Testing**
  - [x] Write unit tests for each step under `tests/application/pipeline/steps/`:
    - `test_media_decision.py`
    - `test_reply_lookup.py`
    - `test_source_ref_replace.py`
    - `test_text_replacement.py`
    - `test_link_removal.py`
    - `test_hashtag_removal.py`
    - `test_mention_removal.py`
    - `test_media_replacement.py`
    - `test_whitespace.py`
    - `test_attribution.py`
    - `test_empty_check.py`
  - [x] Update engine integration tests in `tests/application/pipeline/test_engine.py` to cover steps 6â€“16 end-to-end.


### Review Findings

- [x] [Review][Patch] Naive datetime.min used in sorting active_rr may cause TypeError [forward_bot/application/pipeline/steps/text_replacement.py:22]

## Dev Notes

- **Dependency Injection Wiring (`PipelineEngine`):**
  - Ensure `mapping_repository` is injected properly when building the engine:
    ```python
    # In providers.py or worker.py setup:
    engine = PipelineEngine(
        sampling_repository=sampling_repo,
        mapping_repository=mapping_repo
    )
    ```
- **Non-blocking File Checks (`MediaReplacementStep`):**
  - Always use `asyncio.to_thread` when performing file system I/O (e.g. `candidate.exists()`), preventing thread-blocking in the single ASGI worker event loop. Store the `Path` object in `ctx.media` instead of reading the file into memory.
- **Path Containment/Traversal Guard (`MediaReplacementStep`):**
  - Ensure the resolved path `candidate_path` is safely enclosed in `settings.media_replacement_base_dir`:
    ```python
    base = Path(settings.media_replacement_base_dir).resolve()
    candidate = (base / rule.media_replacement.replacement_image_path).resolve()
    if not candidate.is_relative_to(base):
        # Log warning "media_replacement_path_traversal_attempt"
        # Fall back to original photo
    ```
- **Regular Expressions compilation cache (`TextReplacementStep`):**
  - Import `CacheHolder` and look up pre-compiled regex pattern objects via the atomic snapshot (`CacheHolder.current.compiled_patterns.get(rule.id)`).
  - If cache lookup fails or the ID isn't found, gracefully fallback to dynamically compiling patterns using `re.compile(pattern, re.IGNORECASE)`.
  - Wrap compilation in try/except and fail-safe on error (log warning, skip pattern).
- **Auto-Replacement Source References (`SourceRefReplaceStep`):**
  - Match `@<source_username>`, `t.me/<source_username>`, and `https://t.me/<source_username>` case-insensitively, substituting them with the rule's destination channel reference or custom replacement.
  - If display name auto-replace is enabled, perform case-sensitive replacement of `<source_display_name>`.
- **Formatting Attribution (`AttributionStep`):**
  - Safely replace `{source_name}` and `{source_username}` placeholders in the template string using `ctx.source.display_name` and `ctx.source.telegram_username` (use display name if username is not configured).

### Project Structure Notes

- New steps should be placed in separate files under `src/forward_bot/application/pipeline/steps/` rather than keeping them in `placeholders.py`.
- Update `__init__.py` imports to reference the correct file paths.

### References

- [Functional Requirements FR-7, FR-8, FR-11, FR-13, FR-14, FR-15, FR-31a, FR-39, FR-40, FR-41 in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L40)
- [Clean Architecture guidelines in architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L621)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- Task id 0003c108-4c08-4828-b400-dcaa368975ed/task-225: pytest run verification output.

### Completion Notes List

- Implemented 11 pipeline steps (Steps 6-16) under `src/forward_bot/application/pipeline/steps/` and updated `steps/__init__.py`.
- Refactored `PipelineEngine` to receive and inject `mapping_repository` into `ReplyLookupStep`.
- Configured FastAPI dependency providers in `providers.py` to wire `MappingRepository` and `PipelineEngine`.
- Wrote full unit test coverage for the 11 new steps under `tests/application/pipeline/steps/`.
- Created an end-to-end integration test `test_engine_steps_6_to_16_integration` in `tests/application/pipeline/test_engine.py` verifying full pipeline functionality.

### File List

- `forward-bot/src/forward_bot/application/pipeline/engine.py` (Modified)
- `forward-bot/src/forward_bot/application/pipeline/steps/__init__.py` (Modified)
- `forward-bot/src/forward_bot/application/pipeline/steps/placeholders.py` (Modified)
- `forward-bot/src/forward_bot/api/dependencies/providers.py` (Modified)
- `forward-bot/src/forward_bot/application/pipeline/steps/media_decision.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/reply_lookup.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/source_ref_replace.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/text_replacement.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/link_removal.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/hashtag_removal.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/mention_removal.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/media_replacement.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/whitespace.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/attribution.py` (New)
- `forward-bot/src/forward_bot/application/pipeline/steps/empty_check.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_media_decision.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_reply_lookup.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_source_ref_replace.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_text_replacement.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_link_removal.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_hashtag_removal.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_mention_removal.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_media_replacement.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_whitespace.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_attribution.py` (New)
- `forward-bot/tests/application/pipeline/steps/test_empty_check.py` (New)
- `forward-bot/tests/application/pipeline/test_engine.py` (Modified)



