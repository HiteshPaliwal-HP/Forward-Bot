---
baseline_commit: 'NO_VCS'
status: 'done'
completedAt: '2026-06-06'
---

# Story 1.2: Configure Application Settings & Database Client

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,  
I want **the application to read all configuration from environment variables and connect to MongoDB on startup**,  
so that **I can configure the service by editing `.env` without touching code, and the service fails fast if required vars are missing**.

## Developer Context

This story lays the foundation for how the application reads its configuration and interfaces with the database. The developer MUST adhere to the exact architecture guidelines specified here to prevent deviations in data serialization and project structure.

## Technical Requirements

1. **Fail-fast on Missing Environment Variables:**
   - **Given** a required env var (`MONGO_URI`, `API_KEY`, or `SECRET_KEY`) is missing or blank
   - **Then** startup fails immediately with a clear error message naming the missing variable before any server port is bound.

2. **Pydantic Settings Parsing and Defaults:**
   - Use `pydantic-settings` to map environment variables.
   - Configure case-insensitivity: `SettingsConfigDict(env_file=".env", case_sensitive=False)`.
   - Implement the following defaults: `TELEGRAM_SESSION_PATH` ("./data/telegram.session"), `MEDIA_REPLACEMENT_BASE_DIR` ("./data/replacement-images"), `SAMPLING_PERSIST` (false), `UI_ENABLED` (true), `MAPPING_RETENTION_DAYS` (30), `LOG_RING_BUFFER_HOURS` (1), `HOT_RELOAD_INTERVAL` (30), `BIND_HOST` ("127.0.0.1").
   - `MONGO_URI`, `API_KEY`, and `SECRET_KEY` are required.

3. **MongoDB Client and Serialization:**
   - Create `MongoBaseModel` in `src/forward_bot/api/schemas/base.py` as the base for all response schemas.
   - Set up the MongoDB Motor client singleton inside `src/forward_bot/infrastructure/mongo/client.py` using `lifespan` database connection.
   - Define all six collection names as constants: `forwarding_rules`, `replacement_rules`, `message_mappings`, `sources`, `source_folders`, `sampling_counters`.

4. **Structured Logging and Secret Secrecy:**
   - Implement structured JSON logging using `structlog`.
   - Setup `SecretRedactor` to replace plaintext values of `API_KEY`, `SECRET_KEY`, and any session bytes with `"[REDACTED]"`.
   - The `structlog` configuration must use the processor chain: `merge_contextvars` -> `add_log_level` -> `TimeStamper(fmt="iso")` -> `JSONRenderer`.

## Architecture Compliance

- **MongoBaseModel Constraints:** Inherit from `BaseModel`. Implement `ConfigDict(populate_by_name=True)`. `ObjectId` fields MUST be serialized as 24-character hex strings (using `@field_validator("id", mode="before")`). Datetime fields MUST be serialized as ISO 8601 UTC strings with a `Z` suffix (using `@field_serializer`).
- **Explicit API JSON Naming Rule:** No camelCase conversion at the API boundary. The entire stack uses `snake_case` in JSON exactly as in MongoDB.

## File Structure Requirements

Must follow the Clean Architecture directory structure:
- **Settings:** `src/forward_bot/config.py` (Do not use `settings.py` for standard config per architecture doc)
- **Base Schema:** `src/forward_bot/api/schemas/base.py`
- **Mongo Client:** `src/forward_bot/infrastructure/mongo/client.py`
- **Logging Setup:** `src/forward_bot/infrastructure/logging/__init__.py`

## Testing Requirements

- Write unit/integration tests for Pydantic Settings parsing and defaults.
- Write tests for MongoDB Motor client connection establishment and the `MongoBaseModel` serialization format.
- Test files MUST mirror the `src/` directory structure exactly under `tests/` (e.g. `tests/infrastructure/mongo/test_client.py`, `tests/test_config.py`). No co-located test files in `src/`.

## References

- [Epics and Stories](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/epics.md#Story-1.2)
- [Architecture Document](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/architecture.md)

## Tasks/Subtasks
- [x] Fail-fast on Missing Environment Variables
  - [x] Enforce required `API_KEY`, `SECRET_KEY`, and `MONGO_URI`
  - [x] Validate against empty/whitespace values
  - [x] Handle ValidationError and ValueError gracefully during startup
- [x] Pydantic Settings Parsing and Defaults
  - [x] Implement SettingsConfigDict with `env_file=".env"` and `case_sensitive=False`
  - [x] Configure defaults for session paths, media, sampling, UI, and retention
  - [x] Validate timezone using zoneinfo and hot_reload_interval > 0
- [x] MongoDB Client and Serialization
  - [x] Create `MongoBaseModel` in base schemas with ObjectId coercing and ISO 8601 UTC datetime serializers
  - [x] Setup MongoDB Motor client singleton using connection lifespans
  - [x] Define collection names constants
- [x] Structured Logging and Secret Secrecy
  - [x] Setup `SecretRedactor` to mask `API_KEY`, `SECRET_KEY` and session bytes
  - [x] Configure `structlog` with requested processor chain

## File List
- [NEW] [config.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/config.py)
- [MODIFY] [settings.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/settings.py)
- [MODIFY] [__main__.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/__main__.py)
- [MODIFY] [client.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/client.py)
- [MODIFY] [__init__.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/infrastructure/logging/__init__.py)
- [MODIFY] [app.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/app.py)
- [NEW] [test_config.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/tests/test_config.py)
- [NEW] [test_client.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/tests/infrastructure/mongo/test_client.py)
- [MODIFY] [test_settings.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/test_settings.py)

## Change Log
- **2026-06-06**: Completed implementation of Story 1.2. Created config.py, deprecated settings.py, updated imports, and added comprehensive unit tests for configuration and serialization.

## Dev Agent Record

### Agent Model Used
Gemini 3.5 Flash (Medium)

### Completion Notes List
- Ultimate context engine analysis completed - comprehensive developer guide created.
- Created `config.py` using `SettingsConfigDict` and `pydantic-settings` to enforce required variables (`MONGO_URI`, `API_KEY`, `SECRET_KEY`) and defaults.
- Deprecated `settings.py` to point to `config.py` for backward compatibility.
- Added validation for timezone defaults via `ZoneInfo` and clamped `hot_reload_interval` to > 0.
- Implemented `MongoBaseModel` base schema inside `api/schemas/base.py` with custom validators and serializers ensuring `ObjectId` is coerced to `str` and `datetime` is formatted as ISO 8601 UTC with a `Z` suffix.
- Defined all six collection names as constants in `api/schemas/base.py`.
- Wrote extensive unit tests under `tests/test_config.py` and `tests/infrastructure/mongo/test_client.py`.

### Review Findings
- [x] [Review][Patch] Fragile MongoDB URI parsing [client.py:21]
- [x] [Review][Defer] SecretRedactor risk of over-scrubbing [logging/__init__.py:30] — deferred, pre-existing
