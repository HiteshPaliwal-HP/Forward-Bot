---
baseline_commit: 0838a33a62b81c669346ccaecddab270bf7d26f6
---
Created At: 2026-06-19T17:40:30Z
Completed At: 2026-06-19T17:40:30Z
File Path: `file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/implementation-artifacts/4-1-pipeline-infrastructure-context-protocol-engine-message-mapping.md`

# Story 4.1: Pipeline Infrastructure — Context, Protocol, Engine & Message Mapping

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want the forwarding pipeline to have a well-defined structure so that each processing step can be built, tested, and replaced independently,
so that the system is maintainable as new filter and transform steps are added.

---

## Acceptance Criteria

1. **PipelineStep Protocol Definition:**
   - **Given** the pipeline infrastructure is implemented.
   - **When** `application/pipeline/protocol.py` is inspected.
   - **Then** it defines the `PipelineStep` protocol using Python 3.13 standard typing library:
     ```python
     from typing import Protocol

     class PipelineStep(Protocol):
         name: str
         async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome: ...
     ```

2. **PipelineContext & BlockedOutcome Domain Models:**
   - **Given** a message is received from a source and matched against a rule.
   - **When** `PipelineContext` is initialized.
   - **Then** it carries:
     - `text` (str): The current message text.
     - `caption` (str | None): The current media caption text.
     - `media` (Any | None): The MTProto media object (or None).
     - `attribution_decided` (bool): Flag indicating if attribution has been applied.
     - `reply_target_destination_id` (int | None): The message ID in the destination channel that this message replies to.
     - `correlation_id` (str): An 8-character hex string correlation ID (caller-provided; generation is deferred to the Telegram Worker in Story 4.5, e.g. using `secrets.token_hex(4)`).
     - `rule` (ForwardingRule): A copy-on-write snapshot of the active ForwardingRule. (Since rule and source are mutable, the caller must pass `copy.copy(rule)` / `copy.copy(source)` to prevent steps from modifying cached rule or source properties).
     - `source` (Source): A copy-on-write snapshot of the registered Source.
     - `metadata` (dict): A mutable dictionary for runtime step coordination (serves as the primary data flow channel for mapping step execution inputs/outputs).
   - **And** `BlockedOutcome` carries:
     - `reason` (str): A string reason that must belong to the canonical `BLOCK_REASONS` set: `{"outside_time_window", "sampled_out", "media_type_filtered", "blocked_keyword", "no_allow_keyword_matched", "empty_after_processing", "unsupported_media_type", "step_error"}`.
     - `matched_keyword` (str | None): The keyword that triggered the block (if applicable).
     - `details` (str | None): Additional human-readable context or error traceback for debugging.

3. **Pipeline Engine Orchestration & Exception Isolation (FR-24):**
   - **Given** a `PipelineContext` is executed by the pipeline engine in `application/pipeline/engine.py`.
   - **When** the engine runs through the 18-step canonical sequence in exact order.
   - **Then** it returns either the final `PipelineContext` (on success) or a `BlockedOutcome` (on filter or empty check block).
   - **And** if any pipeline step raises an unexpected exception during `apply()`, it is caught inside `engine.py` (engine-level exception isolation is the chosen design to avoid per-step try/except duplication). The engine wrapper catches the exception, logs it as an ERROR with the `correlation_id`, uses `traceback.format_exc()` to extract the traceback details, and returns a `BlockedOutcome(reason="step_error", details=traceback_str)`. The exception must not escape the engine or abort execution for other active rules.

4. **Message Mapping Domain Model & Schema (FR-19):**
   - **Given** a successfully forwarded message.
   - **When** mapping info is persisted.
   - **Then** it writes to the `message_mappings` collection using the `MappingRepository` matching the schema:
     - `forwarding_rule_id` (ObjectId string hex)
     - `source_channel_id` (int64)
     - `source_message_id` (int32)
     - `destination_channel_id` (int64)
     - `destination_message_id` (int32)
     - `forwarded_at` (UTC datetime generated using `datetime.now(timezone.utc)`)
   - **And** the mapping details are communicated via `PipelineContext.metadata`:
     - `source_message_id` is initialized in `ctx.metadata["source_message_id"]` by the caller (Telegram Worker, Story 4.5).
     - `destination_message_id` is set in `ctx.metadata["destination_message_id"]` by the delivery step.
     - `destination_channel_id` is set in `ctx.metadata["destination_channel_id"]` by the delivery step.
     - `PersistMappingStep` reads these fields from `ctx.metadata` to build the mapping document.
   - **And** the collection maintains a compound background index on `(forwarding_rule_id, source_channel_id, source_message_id)` which has been pre-created at startup.

5. **Mapping Repository Lookup for Replies (FR-40):**
   - **Given** a source channel message that is a reply to another source message.
   - **When** the pipeline looks up the parent mapping via `MappingRepository.get_by_source_message(source_channel_id, source_message_id, forwarding_rule_id)`.
   - **Then** it returns the matching `MessageMapping` entity containing `destination_message_id` (or None if no mapping exists).

---

## Tasks / Subtasks

- [x] **Domain Entities & Packages Definition**
  - [x] Ensure `src/forward_bot/application/pipeline/__init__.py` and `src/forward_bot/application/pipeline/steps/__init__.py` exist.
  - [x] Ensure test package directories have `__init__.py` files:
    - `tests/domain/__init__.py`
    - `tests/domain/entities/__init__.py`
    - `tests/application/__init__.py`
    - `tests/application/pipeline/__init__.py`
  - [x] Create `forward_bot/domain/entities/pipeline_context.py` containing `PipelineContext`, `BlockedOutcome`, and `BLOCK_REASONS` set constant.
  - [x] Create `forward_bot/domain/entities/message_mapping.py` containing the `MessageMapping` dataclass.
- [x] **Pipeline Protocol & Engine Implementation**
  - [x] Create `forward_bot/application/pipeline/protocol.py` defining the `PipelineStep` Protocol.
  - [x] Create `forward_bot/application/pipeline/engine.py` orchestrating the 18 steps in the following canonical sequence:
    1. `TimeWindowStep` (pass-through placeholder)
    2. `SamplingStep` (pass-through placeholder)
    3. `MediaTypeFilterStep` (pass-through placeholder)
    4. `BlockKeywordStep` (pass-through placeholder)
    5. `AllowKeywordStep` (pass-through placeholder)
    6. `MediaDecisionStep` (pass-through placeholder)
    7. `ReplyLookupStep` (pass-through placeholder)
    8. `SourceRefReplaceStep` (pass-through placeholder)
    9. `TextReplacementStep` (pass-through placeholder)
    10. `LinkRemovalStep` (pass-through placeholder)
    11. `HashtagRemovalStep` (pass-through placeholder)
    12. `MentionRemovalStep` (pass-through placeholder)
    13. `MediaReplacementStep` (pass-through placeholder)
    14. `WhitespaceStep` (pass-through placeholder)
    15. `AttributionStep` (pass-through placeholder)
    16. `EmptyCheckStep` (pass-through placeholder)
    17. `DeliverStep` (stub class that simulates message delivery by setting `ctx.metadata["destination_message_id"] = 99999` and `ctx.metadata["destination_channel_id"] = 99999`)
    18. `PersistMappingStep` (implemented step that retrieves metadata, maps, and persists via `MappingRepository`)
    - [x] Implement steps 1-16 as placeholder steps in `src/forward_bot/application/pipeline/steps/` that inherit/implement `PipelineStep` and pass the context through unchanged.
    - [x] Implement the step iterator wrapping step executions in a try/except block to catch unexpected exceptions, logging them at ERROR level with `correlation_id`, importing `traceback` to extract details via `traceback.format_exc()`, and returning a `BlockedOutcome` with `step_error` and the traceback in `details`.
- [x] **MongoDB Mapping Repository**
  - [x] Create `forward_bot/infrastructure/mongo/repositories/mapping_repository.py` subclassing `BaseRepository`.
  - [x] Import `MESSAGE_MAPPINGS` constant from `forward_bot.api.schemas.base` and initialize with `super().__init__(db, MESSAGE_MAPPINGS)`.
  - [x] Implement `_to_entity` mapping BSON document to `MessageMapping`, converting BSON ObjectId `_id` to string and mapping datetimes.
  - [x] Implement `_to_document` converting entity fields back to BSON-compatible dict.
  - [x] Implement mapping persistence using the inherited `await self.insert(doc)` method (do not use `self.collection.insert_one` directly).
  - [x] Implement `get_by_source_message(source_channel_id, source_message_id, forwarding_rule_id)` returning `MessageMapping | None`.
- [x] **Unit Tests**
  - [x] Verify that all existing 219 tests pass successfully.
  - [x] Write unit tests in `tests/domain/entities/test_pipeline_context.py` and `tests/domain/entities/test_message_mapping.py`.
  - [x] Write unit tests in `tests/application/pipeline/test_engine.py` verifying the sequential execution of steps, early exit on `BlockedOutcome`, and engine-level exception isolation.
  - [x] Write repository tests in `tests/infrastructure/mongo/repositories/test_mapping_repository.py` verifying insertion, retrieval, and mapping. Use `unittest.mock`'s `MagicMock` / `AsyncMock` to mock `self.collection.find_one` and `self.collection.insert_one` to avoid external MongoDB service dependency, following existing mock patterns.

---

## Dev Notes

### Architecture & Implementation Guardrails
- **Clean Architecture Boundaries:**
  - Keep domain entities in `domain/entities/` free of Motor, Telethon, or FastAPI dependencies.
  - Repositories in `infrastructure/mongo/repositories/` inherit from `BaseRepository`.
  - Placeholders for pipeline steps should be implemented under `application/pipeline/steps/` as clean modular classes.
- **Serialization & Datetime Conventions:**
  - Datetime fields must be generated with `datetime.now(timezone.utc)`. Never use naive `datetime.utcnow()` as it is deprecated.
  - Datetime fields must be stored as UTC and serialized as ISO 8601 strings with a `Z` suffix.
  - MongoDB ObjectIds must be serialized as 24-character hex strings in response schemas.
- **Step Data Flow:**
  - `PipelineContext.metadata` serves as the communication bridge.
  - Caller sets `ctx.metadata["source_message_id"]`.
  - `DeliverStep` sets `ctx.metadata["destination_message_id"]` and `ctx.metadata["destination_channel_id"]`.
  - `PersistMappingStep` retrieves these keys to write a mapping document.
- **Background Task Startup:**
  - Verify that the background index on `message_mappings` is correctly setup in `app.py` lifespan (this index was pre-created in Story 3.3).

### Source Tree Components to Touch
- `src/forward_bot/domain/entities/pipeline_context.py` [NEW]
- `src/forward_bot/domain/entities/message_mapping.py` [NEW]
- `src/forward_bot/application/pipeline/protocol.py` [NEW]
- `src/forward_bot/application/pipeline/engine.py` [NEW]
- `src/forward_bot/application/pipeline/__init__.py` [NEW]
- `src/forward_bot/application/pipeline/steps/__init__.py` [NEW]
- `src/forward_bot/infrastructure/mongo/repositories/mapping_repository.py` [NEW]
- `tests/domain/__init__.py` [NEW]
- `tests/domain/entities/__init__.py` [NEW]
- `tests/application/__init__.py` [NEW]
- `tests/application/pipeline/__init__.py` [NEW]

---

### Project Structure Notes
- The folder skeleton maps directly to the architectural boundary layout:
  - `domain/entities/`
  - `application/pipeline/`
  - `infrastructure/mongo/repositories/`

---

### References
- [Pipeline Step Order & Block Reasons: epics.md#FR-11](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L41)
- [Message Mapping Retention & Index: architecture.md#Data Architecture](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L287)
- [Exception Isolation: epics.md#FR-24](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L63)

## Dev Agent Record

### Agent Model Used
Gemini 3.5 Flash (High)

### Debug Log References
None

### Completion Notes List
- Defined `PipelineStep` protocol.
- Implemented `PipelineContext` and `BlockedOutcome` domain entities with copy-on-write snapshots for `ForwardingRule` and `Source`.
- Implemented `PipelineEngine` to orchestrate execution of all 18 pipeline steps sequentially with exception isolation and structured logging.
- Created placeholder classes for steps 1-16, and stub implementation for `DeliverStep`.
- Implemented `MappingRepository` subclassing `BaseRepository` for CRUD and reply lookup queries against `message_mappings` collection, using standard BSON mapping conversions.
- Implemented `PersistMappingStep` which reads metadata properties and persists forwarded message mapping records via `MappingRepository`.
- Wrote extensive unit tests covering the entities, pipeline engine execution sequence, early-exit filter logic, exception isolation, and repository BSON mappings.
- Confirmed all new and existing 239 tests pass successfully.

### File List
- `src/forward_bot/domain/entities/pipeline_context.py`
- `src/forward_bot/domain/entities/message_mapping.py`
- `src/forward_bot/application/pipeline/protocol.py`
- `src/forward_bot/application/pipeline/engine.py`
- `src/forward_bot/application/pipeline/__init__.py`
- `src/forward_bot/application/pipeline/steps/__init__.py`
- `src/forward_bot/application/pipeline/steps/placeholders.py`
- `src/forward_bot/application/pipeline/steps/deliver.py`
- `src/forward_bot/application/pipeline/steps/persist_mapping.py`
- `src/forward_bot/infrastructure/mongo/repositories/mapping_repository.py`
- `tests/domain/__init__.py`
- `tests/domain/entities/__init__.py`
- `tests/domain/entities/test_pipeline_context.py`
- `tests/domain/entities/test_message_mapping.py`
- `tests/application/__init__.py`
- `tests/application/pipeline/__init__.py`
- `tests/application/pipeline/test_engine.py`
- `tests/infrastructure/mongo/test_mapping_repository.py`

### Review Findings

- [x] [Review][Patch] Shallow copy used for `rule` and `source` in `PipelineContext` [forward-bot/src/forward_bot/domain/entities/pipeline_context.py:48-49]
- [x] [Review][Defer] Pagination missing in `list_sources` and `list_rules` during cache refresh [forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py:152] — deferred, pre-existing
- [x] [Review][Defer] BSON limit risk for `$in` query in `list_all_replacements_for_rules` [forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py:853] — deferred, pre-existing

