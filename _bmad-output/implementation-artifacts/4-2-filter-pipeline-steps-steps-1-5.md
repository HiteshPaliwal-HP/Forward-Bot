---
baseline_commit: 0838a33a62b81c669346ccaecddab270bf7d26f6
---
# Story 4.2: Filter Pipeline Steps (Steps 1–5)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want incoming messages to be filtered by time-window, sampling rate, media type, and keyword rules before any expensive transforms run,
so that irrelevant messages are dropped early and the pipeline stays efficient.

## Acceptance Criteria

1. **Short-Circuit on Blocked Outcomes:**
   - **Given** any filter step returns a `BlockedOutcome`.
   - **When** the pipeline engine in `engine.py` processes it.
   - **Then** all subsequent pipeline steps are skipped, and the `BlockedOutcome` is returned immediately.

2. **Time-Window Filter Step (Step 1):**
   - **Given** a forwarding rule has `time_window` configured.
   - **When** `TimeWindowStep.apply()` runs.
   - **Then** if the message date (extracted from `ctx.metadata.get("date")`, defaulting to current UTC time) falls outside the active time window, it returns `BlockedOutcome(reason="outside_time_window")`.
   - **And** the window is evaluated in the rule's configured timezone (using standard Python `zoneinfo`).
   - **And** cross-midnight windows (where `end_time < start_time`) are handled correctly.
   - **And** the active day of week check handles cross-midnight boundaries correctly (i.e., if local time falls in the trailing cross-midnight window, the active day is evaluated as the previous calendar day).
   - **And** if timezone resolution fails or `time_window` config is malformed, it logs a warning and fails open (passes context through unchanged) instead of crashing the pipeline.

3. **Sampling Filter Step (Step 2):**
   - **Given** a forwarding rule has `sampling.n` configured (where `n >= 1`).
   - **When** `SamplingStep.apply()` runs.
   - **Then** only every `n`-th message passes through, and other messages return `BlockedOutcome(reason="sampled_out")`.
   - **And** if `SAMPLING_PERSIST=true` (or `settings.sampling_persist` is True), the counter is read, incremented, and persisted in MongoDB using `SamplingRepository` in the `sampling_counters` collection.
   - **And** if `SAMPLING_PERSIST=false`, the counter is managed in the in-memory dict passed in `ctx.metadata["sampling_counters"]`. If this metadata dictionary is missing, it falls back to a step-level default dictionary to avoid crashes.

4. **Media Type Filter Step (Step 3):**
   - **Given** a forwarding rule has `media_type_filter` configured (default: `["text", "photo"]`).
   - **When** `MediaTypeFilterStep.apply()` runs.
   - **Then** if the message's media type is not present in the allowlist, it returns `BlockedOutcome(reason="media_type_filtered")`.
   - **And** the message media type is determined by inspecting the `ctx.media` object:
     - `None` maps to `"text"`.
     - `MessageMediaPhoto` maps to `"photo"`.
     - Other Telethon `MessageMedia` types map to their corresponding categories (`"video"`, `"gif"`, `"sticker"`, `"voice"`, `"audio"`, `"document"`, `"poll"`, `"contact"`, `"location"`, `"dice"`, `"game"`, `"invoice"`, or `"other"`) based on their class names, MIME types, or attributes.
     - Mock objects in unit tests can set `getattr(ctx.media, "type_name", None)` to stub the resolved type directly. Unrecognized media types default to `"other"`.

5. **Block Keyword Filter Step (Step 4):**
   - **Given** a forwarding rule has `block_keywords` configured.
   - **When** `BlockKeywordStep.apply()` runs.
   - **Then** if the message text or media caption matches any block keyword, it returns `BlockedOutcome(reason="blocked_keyword", matched_keyword=keyword)`.
   - **And** if `keyword_match_mode="regex"`, matching uses the pre-compiled `re.Pattern` objects from the cache (`compiled_patterns[rule.id].block_patterns` via `CacheHolder.current`).
   - **And** if the compiled patterns cache lookup fails or is missing, it falls back to compiling patterns dynamically with `re.IGNORECASE`.
   - **And** if `keyword_match_mode="literal"`, matching is a case-insensitive substring search.
   - **And** both text (`ctx.text`) and media caption (`ctx.caption`) are checked.

6. **Allow Keyword Filter Step (Step 5):**
   - **Given** a forwarding rule has `allow_keywords` configured (non-empty list).
   - **When** `AllowKeywordStep.apply()` runs.
   - **Then** if the message text and media caption match none of the allow keywords, it returns `BlockedOutcome(reason="no_allow_keyword_matched")`.
   - **And** if `allow_keywords` is empty (default), the context passes through unchanged.
   - **And** matching honors `keyword_match_mode` (literal case-insensitive or regex) and evaluates both `ctx.text` and `ctx.caption`.

## Tasks / Subtasks

- [x] **Infrastructure & Persistence Setup**
  - [x] Create `forward_bot/infrastructure/mongo/repositories/sampling_repository.py` subclassing `BaseRepository`.
  - [x] Implement `get_counter(rule_id: str) -> int` and atomic `increment_counter(rule_id: str) -> int` using MongoDB `$inc` via `find_one_and_update`.
  - [x] Register `SamplingRepository` in `src/forward_bot/api/dependencies/providers.py` and register database collection constant `SAMPLING_COUNTERS = "sampling_counters"`.
  - [x] Update `PipelineEngine` to accept `sampling_repository` parameter and pass it to `SamplingStep`.
- [x] **Filter Steps Implementation**
  - [x] Implement `TimeWindowStep` in `src/forward_bot/application/pipeline/steps/time_window.py`.
  - [x] Implement `SamplingStep` in `src/forward_bot/application/pipeline/steps/sampling.py`.
  - [x] Implement `MediaTypeFilterStep` in `src/forward_bot/application/pipeline/steps/media_type_filter.py`.
  - [x] Implement `BlockKeywordStep` in `src/forward_bot/application/pipeline/steps/block_keyword.py`.
  - [x] Implement `AllowKeywordStep` in `src/forward_bot/application/pipeline/steps/allow_keyword.py`.
  - [x] Update `src/forward_bot/application/pipeline/steps/__init__.py` to import and expose the actual step classes instead of placeholders.
- [x] **Unit & Integration Testing**
  - [x] Write unit tests in `tests/infrastructure/mongo/test_sampling_repository.py` using mock database calls.
  - [x] Write unit tests for each step under `tests/application/pipeline/steps/`:
    - `test_time_window.py` (verify zones, day matching, cross-midnight shifts, fail-open handling).
    - `test_sampling.py` (verify persisted vs in-memory counters, N-th check, fallback dictionaries).
    - `test_media_type_filter.py` (verify text, photo, and other types with class & `type_name` fallbacks).
    - `test_block_keyword.py` (verify literal vs regex matching, case insensitivity, caption checks, cache fallback).
    - `test_allow_keyword.py` (verify empty allow list passes, literal vs regex checks on text/caption).
  - [x] Update `tests/application/pipeline/test_engine.py` to cover integrated engine execution with the actual steps.

## Dev Notes

- **Timezone Calculations (`TimeWindowStep`):**
  - Convert `date` to local time: `local_dt = date.astimezone(ZoneInfo(rule.time_window.timezone))`.
  - Check cross-midnight: if `end_t < start_t`:
    - A message is within the time window if `local_t >= start_t` OR `local_t <= end_t`.
    - If `local_t <= end_t`, the window started on the previous day. So match day check against `(local_dt - timedelta(days=1)).strftime("%a").upper()`.
    - Otherwise, match day check against `local_dt.strftime("%a").upper()`.
  - Wrap timezone and date operations in a try/except block. On error, log a warning and return `ctx` (fail-open).
- **Sampling Counter Database Operations (`SamplingStep`):**
  - Use `from pymongo import ReturnDocument` and Motor's `find_one_and_update(..., {"$inc": {"counter": 1}}, upsert=True, return_document=ReturnDocument.AFTER)` to atomically increment counters.
- **Rule Cache Compiled Patterns Lookup:**
  - Access precompiled regex patterns from cache: `CacheHolder.current.compiled_patterns.get(rule.id)`. If patterns are missing or cache is not populated, compile patterns dynamically using `re.compile(kw, re.IGNORECASE)` as a fallback.
- **Media Object Class Mapping (`MediaTypeFilterStep`):**
  - Map `ctx.media` class names:
    - Check if `getattr(ctx.media, "type_name", None)` exists first. If so, return it directly.
    - Otherwise check class name:
      - `"MessageMediaPhoto"` -> `"photo"`
      - `"MessageMediaDocument"` -> inspect attributes / MIME types (e.g. check attributes for `DocumentAttributeSticker`, `DocumentAttributeAnimated` -> `"gif"`, `DocumentAttributeVideo` -> `"video"`, `DocumentAttributeAudio` -> `"voice"` if voice attribute is True).
      - If unrecognized, default to `"other"`.

### Project Structure Notes

- New steps should be placed in separate files under `src/forward_bot/application/pipeline/steps/` rather than keeping them in `placeholders.py`.
- Update `__init__.py` imports to reference the correct file paths.

### References

- [Time Window & Regex Filter requirements: epics.md#FR-32, FR-33, FR-34, FR-35, FR-36, FR-37](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L81)
- [Rule Cache properties: rule_cache.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py#L37)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- Mock context NameError: Resolved by importing `Source` in `test_time_window.py`.
- `sampling_counters` KeyError in `test_sampling.py`: Resolved by passing explicit initial metadata with dictionary in `test_sampling_step_in_memory_counters`.

### Completion Notes List

- Implemented `SamplingRepository` to manage counter database operations atomically via `$inc` and `find_one_and_update`.
- Integrated `SamplingRepository` in providers dependency injection and update `PipelineEngine` to inject repository in `SamplingStep`.
- Implemented `TimeWindowStep` evaluating timezone conversions via Python's standard `ZoneInfo` and handling cross-midnight time and weekday transitions cleanly. Fail-open (returns context unchanged) on malformed configurations.
- Implemented `SamplingStep` matching every `N`-th message. Persistence logic correctly targets MongoDB via `SamplingRepository` if `sampling_persist` settings are True, else falls back to in-memory dictionaries in metadata or class.
- Implemented `MediaTypeFilterStep` identifying Telethon's class types and custom stubs, filtering messages based on media type allowlist.
- Implemented `BlockKeywordStep` and `AllowKeywordStep` evaluating case-insensitive substring and regex matching (using precompiled expressions from the atomic cache snapshot or dynamically compiled fallback) against both text and caption.
- Created extensive mock-based unit tests for all implemented steps and repository.
- Verified 100% test pass rate with 0 regressions.

### File List

- `forward-bot/src/forward_bot/infrastructure/mongo/repositories/sampling_repository.py`
- `forward-bot/src/forward_bot/api/dependencies/providers.py`
- `forward-bot/src/forward_bot/application/pipeline/engine.py`
- `forward-bot/src/forward_bot/application/pipeline/steps/__init__.py`
- `forward-bot/src/forward_bot/application/pipeline/steps/time_window.py`
- `forward-bot/src/forward_bot/application/pipeline/steps/sampling.py`
- `forward-bot/src/forward_bot/application/pipeline/steps/media_type_filter.py`
- `forward-bot/src/forward_bot/application/pipeline/steps/block_keyword.py`
- `forward-bot/src/forward_bot/application/pipeline/steps/allow_keyword.py`
- `forward-bot/tests/infrastructure/mongo/test_sampling_repository.py`
- `forward-bot/tests/application/pipeline/steps/test_time_window.py`
- `forward-bot/tests/application/pipeline/steps/test_sampling.py`
- `forward-bot/tests/application/pipeline/steps/test_media_type_filter.py`
- `forward-bot/tests/application/pipeline/steps/test_block_keyword.py`
- `forward-bot/tests/application/pipeline/steps/test_allow_keyword.py`
- `forward-bot/tests/application/pipeline/test_engine.py`

### Change Log

- **2026-06-20**: Implemented filter pipeline steps 1 to 5, database persistence for sampling, and automated unit/integration test suites. Update story status to `review` and sprint-status to `review`.

### Review Findings

- [x] [Review][Patch] Silent exception swallowing during regex compilation [allow_keyword.py & block_keyword.py]
- [x] [Review][Patch] Empty string in `allow_keywords` regex will match all text [allow_keyword.py]
- [x] [Review][Defer] Dynamic regex compilation not cached locally when global cache is missing [allow_keyword.py & block_keyword.py] — deferred, pre-existing

