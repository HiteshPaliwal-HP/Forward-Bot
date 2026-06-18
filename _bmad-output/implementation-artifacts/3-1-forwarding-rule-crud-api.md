---
baseline_commit: 57848c6e377c8a087419ba5f23ff93b6c46e006b
---

# Story 3.1: Forwarding Rule CRUD API

Status: done

## Story

As a **Channel Operator**,
I want to **create, read, update, delete, enable, and disable Forwarding Rules via the REST API with complete filter and transform configuration**,
so that **I can precisely control what gets forwarded and how, without restarting the service**.

---

## Acceptance Criteria

1. **Create Rule — Happy Path (`POST /api/v1/rules`):**
   - **Given** a valid payload with `source_id` (existing Source ObjectId hex), `destination_channel` (Telegram username or numeric ID), and any combination of optional config fields.
   - **When** `POST /api/v1/rules` is called.
   - **Then** HTTP 201 is returned with the fully persisted rule containing all fields at their defaults:
     - `is_active=false`
     - `keyword_match_mode="literal"`
     - `block_keywords=[]`
     - `allow_keywords=[]`
     - `media_type_filter=["text","photo"]`
     - `remove_links=false`, `remove_hashtags=false`, `remove_mentions=false`
     - `forward_media="forward"` (values: `forward | ignore | caption_only`)
     - `sampling={"n": 1}`
     - `time_window=null`
     - `attribution={"enabled": false, "position": "prefix", "format": "From {source_name}"}`
     - `auto_replace_source_refs={"enabled": false, "replacement": null, "replace_display_name": false}`
     - `media_replacement={"enabled": false, "replacement_image_path": null, "replacement_caption_mode": "use_source"}`
     - `created_at`, `updated_at` (ISO 8601 UTC with `Z` suffix)
     - `id` (24-char hex ObjectId string)
   - **And** duplicate `(source_id, destination_channel)` pairs ARE permitted — no uniqueness constraint on this combination.

2. **Reject Non-Existent `source_id`:**
   - **Given** `source_id` references an ObjectId that does not exist in the `sources` collection.
   - **When** `POST /api/v1/rules` is called.
   - **Then** HTTP **422** is returned with `{"error": {"code": "source_not_found", "message": "..."}}`
   - **Note:** This returns **422** (not 404). Use `RuleSourceNotFoundException` (see Dev Notes §Exception Mapping) — **not** `SourceNotFoundException` which maps to 404.

3. **Reject Self-Referential Rule:**
   - **Given** `source_id` and `destination_channel` refer to the same Telegram entity (i.e., the Source's `telegram_username` or `telegram_id` matches `destination_channel`).
   - **When** `POST /api/v1/rules` is called.
   - **Then** HTTP 422 is returned with `{"error": {"code": "self_referential_rule", "message": "Cannot create rule: source equals destination."}}`

4. **Reject Invalid Regex Keywords:**
   - **Given** `keyword_match_mode` is `"regex"` and a `block_keywords` or `allow_keywords` entry contains an invalid regex pattern.
   - **When** `POST` or `PUT /api/v1/rules/{id}` is called.
   - **Then** HTTP 422 is returned with `{"error": {"code": "invalid_regex", "message": "Invalid regex /{pattern}/: {reason}."}}`

5. **Accept Cross-Midnight Time Windows:**
   - **Given** `time_window.end_time` < `time_window.start_time` (e.g., `22:00` → `06:00`).
   - **When** `POST` or `PUT` is called.
   - **Then** HTTP 201/200 is returned (cross-midnight windows are valid per FR-32).

6. **Reject Invalid IANA Timezone:**
   - **Given** `time_window.timezone` is not a valid IANA timezone name (e.g., `"Not/AZone"`).
   - **When** `POST` or `PUT` is called.
   - **Then** HTTP 422 is returned with `{"error": {"code": "invalid_timezone", "message": "..."}}`

7. **Reject Media Replacement Without Path:**
   - **Given** `media_replacement.enabled=true` and `replacement_image_path` is `null`.
   - **When** `POST` or `PUT` is called.
   - **Then** HTTP 422 is returned with `{"error": {"code": "media_replacement_path_required", "message": "..."}}`

8. **Enable Rule (`POST /api/v1/rules/{id}/enable`):**
   - **Given** a rule exists with `is_active=false`.
   - **When** `POST /api/v1/rules/{id}/enable` is called.
   - **Then** HTTP 200 is returned with `{"ok": true}`.
   - **And** `is_active` becomes `true` in MongoDB immediately.
   - **Given** `{id}` does not exist or is invalid.
   - **When** `POST /api/v1/rules/{id}/enable` is called.
   - **Then** HTTP 404 with `{"error": {"code": "rule_not_found", "message": "Rule {id} not found."}}`

9. **Disable Rule (`POST /api/v1/rules/{id}/disable`):**
   - **Given** a rule exists.
   - **When** `POST /api/v1/rules/{id}/disable` is called.
   - **Then** HTTP 200 is returned with `{"ok": true}`.
   - **And** `is_active` becomes `false` in MongoDB immediately.
   - **Given** `{id}` does not exist or is invalid.
   - **When** `POST /api/v1/rules/{id}/disable` is called.
   - **Then** HTTP 404 with `{"error": {"code": "rule_not_found", "message": "Rule {id} not found."}}`

10. **List Rules (`GET /api/v1/rules`) — Pagination & Filters:**
    - **Given** rules exist in the database.
    - **When** `GET /api/v1/rules` is called (optionally with `?source_id=`, `?destination_channel=`, `?is_active=true|false`, `?folder_id=`, `?page=`, `?page_size=`).
    - **Then** paginated response `{"items": [...], "total": N, "page": N, "page_size": 50}` is returned, sorted by `created_at` descending (newest first — consistent with sources list).
    - **And** `folder_id` filter joins via the Source's `folder_id` field — only rules whose source has `folder_id` matching the given value are returned.
    - **And** default `page_size` is 50; max is 200.

11. **Get Single Rule (`GET /api/v1/rules/{id}`):**
    - **Given** a rule exists.
    - **When** `GET /api/v1/rules/{id}` is called.
    - **Then** HTTP 200 with the full rule document.
    - **Given** `{id}` does not exist or is invalid.
    - **When** `GET /api/v1/rules/{id}` is called.
    - **Then** HTTP 404 with `{"error": {"code": "rule_not_found", "message": "Rule {id} not found."}}`

12. **Update Rule (`PUT /api/v1/rules/{id}`):**
    - **Given** a rule exists.
    - **When** `PUT /api/v1/rules/{id}` is called with updated config (all fields provided, full replacement).
    - **Then** HTTP 200 with the updated rule; `updated_at` refreshed to current UTC.
    - **And** the same validation rules apply on PUT as on POST: source_id must exist (→ 422), self-referential check, invalid regex, invalid timezone, media_replacement path required.
    - **Note:** PUT re-validates that `source_id` still references an existing Source (same check as POST). If the source was deleted after rule creation, PUT returns 422.

13. **Delete Rule (`DELETE /api/v1/rules/{id}`):**
    - **Given** a rule exists.
    - **When** `DELETE /api/v1/rules/{id}` is called.
    - **Then** HTTP 204 is returned.
    - **And** all associated Replacement Rules for this rule are cascade-deleted from `replacement_rules` collection.
    - **Given** `{id}` does not exist.
    - **When** `DELETE /api/v1/rules/{id}` is called.
    - **Then** HTTP 404 with `{"error": {"code": "rule_not_found", ...}}`

14. **Auth Gate / Security:**
    - **Given** any request is made to any rules endpoint.
    - **Then** the dual-auth gate (`Depends(get_current_operator)`) must be in effect (X-API-Key header or signed session cookie).

---

## Tasks / Subtasks

- [x] **Domain Entity**
  - [x] Create `ForwardingRule` domain entity in `domain/entities/forwarding_rule.py` as a `@dataclass` with all fields and sub-config dataclasses (`TimeWindowConfig`, `SamplingConfig`, `AttributionConfig`, `AutoReplaceConfig`, `MediaReplacementConfig`)
  - [x] Add all new domain exceptions to `domain/exceptions.py`:
    - `RuleNotFoundException`
    - `RuleInvalidRegexException`
    - `RuleSelfReferentialException`
    - `RuleInvalidTimezoneException`
    - `RuleMediaReplacementPathRequiredException`

- [x] **Infrastructure / Repository**
  - [x] Create `ForwardingRuleRepository` in `infrastructure/mongo/repositories/rule_repository.py` extending `BaseRepository`
  - [x] Implement `get_rule_by_id(id: str)` returning document or `None`
  - [x] Implement `add_rule(rule_doc: dict)` returning inserted `id` string
  - [x] Implement `update_rule(id: str, rule_doc: dict)` returning `bool`
  - [x] Implement `delete_rule(id: str)` deleting the rule AND cascading `replacement_rules` for that `forwarding_rule_id`
  - [x] Implement `enable_rule(id: str)` / `disable_rule(id: str)` using `$set is_active`
  - [x] Implement `list_rules(filters: dict, page: int, page_size: int)` with optional `source_id`, `destination_channel`, `is_active`, `folder_id` filters — `folder_id` filter requires a join through `sources` collection

- [x] **Use Cases**
  - [x] `application/rules/create_rule.py` — `CreateRule` use case: validate source exists, validate self-ref, validate regex if `keyword_match_mode=regex`, validate timezone if `time_window` set, validate media_replacement path required, persist
  - [x] `application/rules/list_rules.py` — `ListRules` use case
  - [x] `application/rules/get_rule.py` — `GetRule` use case
  - [x] `application/rules/update_rule.py` — `UpdateRule` use case (same validations as create)
  - [x] `application/rules/delete_rule.py` — `DeleteRule` use case (cascade)
  - [x] `application/rules/enable_rule.py` — `EnableRule` use case
  - [x] `application/rules/disable_rule.py` — `DisableRule` use case

- [x] **API Schemas**
  - [x] Create `api/schemas/rule.py` with all schemas:
    - Sub-config Pydantic models: `TimeWindowConfig`, `SamplingConfig`, `AttributionConfig`, `AutoReplaceSourceRefsConfig`, `MediaReplacementConfig`
    - `ForwardingRuleCreateRequest` (required: `source_id`, `destination_channel`; all others optional with defaults)
    - `ForwardingRuleUpdateRequest` (full replacement — all fields with defaults)
    - `ForwardingRuleResponse` (extends `MongoBaseModel`, includes all fields)

- [x] **API Router**
  - [x] Create `api/routers/rules.py` with all endpoints:
    - `POST /api/v1/rules` → 201
    - `GET /api/v1/rules` → 200 paginated
    - `GET /api/v1/rules/{id}` → 200 or 404
    - `PUT /api/v1/rules/{id}` → 200 or 404
    - `DELETE /api/v1/rules/{id}` → 204 or 404
    - `POST /api/v1/rules/{id}/enable` → 200 `{"ok": true}`
    - `POST /api/v1/rules/{id}/disable` → 200 `{"ok": true}`
  - [x] Inject `ForwardingRuleRepository`, `SourceRepository` via `Depends()`
  - [x] All endpoints declare `Depends(get_current_operator)`

- [x] **Dependency Provider Update**
  - [x] Add `get_rule_repository` to `api/dependencies/providers.py`

- [x] **App Wiring**
  - [x] Register `ForwardingRuleRepository`-related MongoDB indexes in `app.py` lifespan:
    - Compound index: `(source_id, is_active)` on `forwarding_rules`
    - Index: `(is_active,)` on `forwarding_rules`
  - [x] Register new exception handlers in `domain_exception_handler` for all new exceptions
  - [x] Register `rules_router` via `app.include_router(rules_router)`

- [x] **Verification & Testing**
  - [x] Write unit tests in `tests/infrastructure/mongo/test_rule_repository.py`
  - [x] Write API integration tests in `tests/api/test_rules.py` covering all ACs:
    - Happy path create with all defaults
    - Self-referential rejection
    - Non-existent source_id rejection
    - Invalid regex rejection (both block_keywords and allow_keywords)
    - Cross-midnight time window accepted
    - Invalid timezone rejected
    - media_replacement enabled + null path rejected
    - Enable / disable actions
    - List with each filter: source_id, destination_channel, is_active, folder_id
    - Get 200 / 404
    - Delete cascade (verify replacement_rules also removed)
    - Auth rejection (no key → 401)

### Review Findings

- [x] [Review][Patch] Invalid `source_id` query parameter is silently ignored in listing [rule_repository.py:1387]
- [x] [Review][Patch] `created_at` and `updated_at` response schema annotations are typed as Any [rule.py:344]

---

## Dev Notes

### Architecture & Implementation Guardrails

#### Clean Architecture Rules

- `ForwardingRule` domain entity lives in `domain/entities/forwarding_rule.py` — a **pure Python dataclass** with no imports from `infrastructure/`, `api/`, FastAPI, or Motor.
- Use cases in `application/rules/` receive injected repositories; they never import from `api/`.
- `ForwardingRuleRepository` in `infrastructure/mongo/repositories/rule_repository.py` extends `BaseRepository` — follow the same pattern as [`source_repository.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/source_repository.py) and [`folder_repository.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py).
- The API router in `api/routers/rules.py` is the translation layer: map exceptions to HTTP responses via `domain_exception_handler` in `app.py`.
- **Read [`app.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py) before modifying** — the exception handler chain and lifespan structure must be understood.

#### Domain Entity Structure

See Tasks section for the full entity definition. Key types: sub-configs are `@dataclass` — `TimeWindowConfig`, `SamplingConfig`, `AttributionConfig`, `AutoReplaceSourceRefsConfig`, `MediaReplacementConfig`. Root entity is `ForwardingRule` dataclass. All live in `domain/entities/forwarding_rule.py` with **only stdlib imports** (`dataclasses`, `datetime`).

#### Exception to HTTP Mapping

**All 6 new exceptions must be added as `elif` blocks inside the existing `domain_exception_handler` in `app.py`.** The handler uses an `elif` chain — missing any block causes a silent fallback to HTTP 400. Add them **before** the final `return JSONResponse(status_code=400, ...)` fallback.

| Exception | HTTP Status | Error Code | Notes |
|-----------|-------------|------------|-------|
| `RuleNotFoundException` | 404 | `rule_not_found` | Used by GET/PUT/DELETE/enable/disable |
| `RuleSourceNotFoundException` | 422 | `source_not_found` | **NEW** — raised by CreateRule/UpdateRule use cases when source_id not found. Distinct from existing `SourceNotFoundException` (→ 404). |
| `RuleInvalidRegexException` | 422 | `invalid_regex` | |
| `RuleSelfReferentialException` | 422 | `self_referential_rule` | |
| `RuleInvalidTimezoneException` | 422 | `invalid_timezone` | |
| `RuleMediaReplacementPathRequiredException` | 422 | `media_replacement_path_required` | |

**Why `RuleSourceNotFoundException` not `SourceNotFoundException`?** AC2 specifies HTTP 422 for missing `source_id` on rule create/update. The existing `SourceNotFoundException` is already mapped to **HTTP 404** in `app.py` (line 186–195). Using it here would return 404, violating the AC. Add `RuleSourceNotFoundException` to `domain/exceptions.py` as a new class extending `DomainException`.

```python
# In domain/exceptions.py — add:
class RuleNotFoundException(DomainException):
    def __init__(self, rule_id: str):
        self.rule_id = rule_id
        super().__init__(f"Rule {rule_id} not found.")

class RuleSourceNotFoundException(DomainException):
    """Raised by rule use cases when source_id is not found (returns 422, not 404)."""
    def __init__(self, source_id: str):
        self.source_id = source_id
        super().__init__(f"Source {source_id} not found.")

class RuleInvalidRegexException(DomainException):
    def __init__(self, pattern: str, reason: str):
        self.pattern = pattern
        self.reason = reason
        super().__init__(f"Invalid regex /{pattern}/: {reason}.")

class RuleSelfReferentialException(DomainException):
    pass

class RuleInvalidTimezoneException(DomainException):
    def __init__(self, timezone: str):
        self.timezone = timezone
        super().__init__(f"Invalid timezone: {timezone}.")

class RuleMediaReplacementPathRequiredException(DomainException):
    pass
```

#### Regex Validation Pattern (use in `CreateRule` and `UpdateRule` use cases)

```python
import re
from zoneinfo import ZoneInfo
from forward_bot.domain.exceptions import RuleInvalidRegexException, RuleInvalidTimezoneException

def validate_keyword_regex(keywords: list[str], mode: str) -> None:
    """Validate keywords are valid Python regex if mode is 'regex'."""
    if mode != "regex":
        return
    for pattern in keywords:
        try:
            re.compile(pattern)
        except re.error as e:
            raise RuleInvalidRegexException(pattern=pattern, reason=str(e))

def validate_timezone(tz_name: str) -> None:
    """Validate IANA timezone name using zoneinfo."""
    try:
        ZoneInfo(tz_name)
    except Exception:
        raise RuleInvalidTimezoneException(timezone=tz_name)
```

> **Why `zoneinfo`?** The architecture decision (addendum §6) selected `zoneinfo` (stdlib, Python 3.9+) over `pytz` for timezone resolution. It is already used in `config.py`.

#### Self-Referential Rule Check

```python
# In CreateRule AND UpdateRule use cases:
# Use source_repo.get_source_by_id() (returns a Source entity, not raw dict)
source = await source_repo.get_source_by_id(payload.source_id)
if source is None:
    raise RuleSourceNotFoundException(payload.source_id)  # 422, NOT SourceNotFoundException (which → 404)

# Compare destination_channel to source's telegram_username and telegram_id
dest = payload.destination_channel.lstrip("@").lower()
if source.telegram_username and source.telegram_username.lower() == dest:
    raise RuleSelfReferentialException()
if str(source.telegram_id) == dest:
    raise RuleSelfReferentialException()
```

> **Important:** Use `source_repo.get_source_by_id()` (returns `Source | None` entity), not the raw `BaseRepository.get_by_id()` (returns `dict | None`). This is consistent with how all other use cases access the SourceRepository.

#### MongoDB Indexes (add to `lifespan` in `app.py`)

Add inside the existing `try` block in `default_lifespan`, **after** the `mongodb_indexes_created` log line (after line 44 in current `app.py`):

```python
from forward_bot.api.schemas.base import FORWARDING_RULES
await mongo_client.db[FORWARDING_RULES].create_index(
    [("source_id", 1), ("is_active", 1)], background=True
)
await mongo_client.db[FORWARDING_RULES].create_index(
    [("is_active", 1)], background=True
)
```

#### ⚠️ CRITICAL: `source_id` Storage Format — Conflict Resolution

**Store `source_id` in `forwarding_rules` as a BSON `ObjectId`**, NOT as a plain string.

**Why:** The existing `SourceRepository.get_referencing_rules_count()` (line 78 of `source_repository.py`) already queries `forwarding_rules` using:
```python
count = await self.db[FORWARDING_RULES].count_documents({"source_id": ObjectId(source_id)})
```
If you store `source_id` as a string, this query will always return 0, silently breaking the guard that prevents deleting sources with active rules.

**Implementation in `ForwardingRuleRepository`:**
- On insert/update: convert `source_id` hex string → `ObjectId(source_id)` before storing
- On read (`_to_document` / `_to_entity`): convert back to `str(doc["source_id"])` in the entity
- In `list_rules` filter: query `{"source_id": ObjectId(source_id)}` (validate with `ObjectId.is_valid()` first)

**In `ForwardingRuleResponse` Pydantic schema:** add a `@field_validator("source_id", mode="before")` to coerce ObjectId → str (same pattern as `MongoBaseModel.coerce_object_id` for `_id`).

#### `folder_id` Filter Join Strategy

`GET /api/v1/rules?folder_id=X` must filter rules whose Source has `folder_id=X`. Because `forwarding_rules` only stores `source_id` (not `folder_id`), this requires a two-step approach:

```python
# 1. Get all sources in that folder using the EXISTING SourceRepository method:
sources = await source_repo.get_sources_by_folder_id(folder_id)  # method exists at line 94 of source_repository.py
source_ids = [ObjectId(s.id) for s in sources]  # convert to ObjectId for query
# 2. Filter rules by source_id IN (source_ids)
query["source_id"] = {"$in": source_ids}
```

> **Note:** The method is `get_sources_by_folder_id()` on `SourceRepository` — NOT `find_by_folder_id()` (that method does not exist).

Do NOT attempt a MongoDB `$lookup` join at the rules collection level — the extra complexity is not warranted at this scale (100 active sources).

#### Cascade Delete Pattern

When `DELETE /api/v1/rules/{id}` is called, the repository must also delete all `replacement_rules` with `forwarding_rule_id = rule_id`:

```python
# In ForwardingRuleRepository.delete_rule():
from forward_bot.api.schemas.base import FORWARDING_RULES, REPLACEMENT_RULES  # both exist in base.py

async def delete_rule(self, rule_id: str) -> bool:
    # Delete child replacement rules first (REPLACEMENT_RULES constant is in base.py line 9)
    await self.db[REPLACEMENT_RULES].delete_many(
        {"forwarding_rule_id": rule_id}  # stored as string, not ObjectId
    )
    # Delete the rule itself
    return await self.delete(rule_id)
```

> Pattern mirrors `FolderRepository.delete_folder()` which uses `self.db[SOURCES]` for cross-collection ops.

#### Pydantic Schema Design

```python
# api/schemas/rule.py (excerpt)
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal
from bson import ObjectId

class SamplingConfigSchema(BaseModel):
    n: int = Field(default=1, ge=1)

class TimeWindowConfigSchema(BaseModel):
    timezone: str
    days_of_week: list[Literal["MON","TUE","WED","THU","FRI","SAT","SUN"]]
    start_time: str   # "HH:MM" format
    end_time: str     # "HH:MM" format

class AttributionConfigSchema(BaseModel):
    enabled: bool = False
    position: Literal["prefix", "suffix"] = "prefix"
    format: str = "From {source_name}"

class AutoReplaceSourceRefsConfigSchema(BaseModel):
    enabled: bool = False
    replacement: str | None = None
    replace_display_name: bool = False

class MediaReplacementConfigSchema(BaseModel):
    enabled: bool = False
    replacement_image_path: str | None = None
    replacement_caption_mode: Literal["use_replacement", "use_source", "none"] = "use_source"

class ForwardingRuleCreateRequest(BaseModel):
    source_id: str = Field(min_length=1)        # validated as ObjectId hex in use case
    destination_channel: str = Field(min_length=1)  # prevent empty-string records (Epic 2 retro)
    is_active: bool = False
    keyword_match_mode: Literal["literal", "regex"] = "literal"
    block_keywords: list[str] = Field(default_factory=list)
    allow_keywords: list[str] = Field(default_factory=list)
    media_type_filter: list[str] = Field(default=["text", "photo"])
    remove_links: bool = False
    remove_hashtags: bool = False
    remove_mentions: bool = False
    forward_media: Literal["forward", "ignore", "caption_only"] = "forward"
    sampling: SamplingConfigSchema = Field(default_factory=SamplingConfigSchema)
    time_window: TimeWindowConfigSchema | None = None
    attribution: AttributionConfigSchema = Field(default_factory=AttributionConfigSchema)
    auto_replace_source_refs: AutoReplaceSourceRefsConfigSchema = Field(default_factory=AutoReplaceSourceRefsConfigSchema)
    media_replacement: MediaReplacementConfigSchema = Field(default_factory=MediaReplacementConfigSchema)

class ForwardingRuleResponse(MongoBaseModel):
    # source_id stored as ObjectId in MongoDB — must coerce to string on read
    source_id: str

    @field_validator("source_id", mode="before")
    @classmethod
    def coerce_source_id(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        return str(v)
    # ... remaining fields with defaults matching domain entity
```

**Schema Rules:**
- Pydantic validates `Literal` types and `ge=1` constraints automatically.
- Invalid regex and invalid timezones are **domain-level** validations in the use case (not Pydantic), mapped to 422 via `domain_exception_handler`.
- `ObjectId` path params (`{id}`): `BaseRepository.get_by_id()` returns `None` for invalid ObjectIds — the use case raises `RuleNotFoundException` → 404. No extra path validation needed.
- `SAMPLING_COUNTERS` collection (already in `base.py`) is **out of scope** for this story — do not read or write it.

#### Pagination Response Pattern (established in Epic 2)

```python
# Consistent with SourceRepository list pattern
return {
    "items": [...],
    "total": total_count,
    "page": page,
    "page_size": page_size
}
```

#### Data Storage Format

- `source_id`: stored as **BSON `ObjectId`** in MongoDB (queried as `ObjectId`); serialized as 24-char hex string in API responses via `ForwardingRuleResponse.coerce_source_id`
- `destination_channel`: stored as-is (string — username or numeric ID string)
- `time_window.start_time` / `end_time`: stored as `"HH:MM"` strings in MongoDB; parse to `datetime.time` in domain entity when needed
- `sampling.n`: stored as integer
- All timestamps: UTC `datetime` in MongoDB, serialized as `"2026-06-17T18:30:00Z"` in API responses via `MongoBaseModel.serialize_dt`
- `is_active`: stored as boolean (not int)

### Previous Story Intelligence (Epic 2 Learnings)

**From Epic 2 Retrospective — apply directly to this story:**

1. **Motor `.aggregate()` mock pattern:** `collection.aggregate()` returns a cursor synchronously (not an async call). In unit tests, mock it with `MagicMock()` (not `AsyncMock()`), then mock the cursor's `to_list()` as an `AsyncMock`.
   ```python
   mock_collection.aggregate.return_value = MagicMock()
   mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=[...])
   ```

2. **`min_length=1` on ALL string fields:** `source_id` and `destination_channel` both need `min_length=1` in the Pydantic schema — already included in schema design above.

3. **`BaseRepository` pattern:** Use `self.collection` for primary collection. For cascade cross-collection ops, use `self.db[COLLECTION_NAME]` directly — same as `FolderRepository.delete_folder` using `self.db[SOURCES]`.

4. **MongoDB index creation in lifespan:** Add inside the existing `try` block in `app.py`'s `default_lifespan`, after the `mongodb_indexes_created` log line (line 44).

5. **Auth on every endpoint:** Every `@router.*()` function must include `_: str = Depends(get_current_operator)` in its signature. Without this, the endpoint is unprotected.

6. **Enable/Disable 404 handling:** `$set is_active` on a nonexistent doc returns `modified_count=0`. Check for this: if `modified_count == 0`, raise `RuleNotFoundException`. Otherwise `{"ok": true}` is returned falsely.

7. **Epic status promotion:** This is the first story in Epic 3. After implementation, update `epic-3: in-progress` in `sprint-status.yaml` (already set to `in-progress` — verify it is not `backlog`).

### Git Intelligence (Recent Commits)

| Commit | What It Did |
|--------|------------|
| `57848c6` | Story 2.3 — Folder CRUD complete (FolderRepository, use cases, router, tests) |
| `64187b5` | Story 2.1 — Source registration with Telegram resolve |
| `514a259` | Story 1.4 — Telegram auth + session management |
| `db15da0` | Story 1.3 — FastAPI shell, health, Docker |

**Current file inventory established by Epic 2:**

```
src/forward_bot/
  domain/entities/
    source.py          ✅ exists
    source_folder.py   ✅ exists
  domain/exceptions.py ✅ exists (FolderNotFoundException, SourceNotFoundException etc.)
  application/
    folders/           ✅ complete (5 use cases)
    sources/           ✅ complete (5 use cases)
    rules/             🚧 empty — needs CREATE this story
    replacements/      🚧 empty — needs Story 3.2
    pipeline/          🚧 empty — needs Epic 4
  infrastructure/mongo/repositories/
    base.py            ✅ BaseRepository
    source_repository.py ✅ exists
    folder_repository.py ✅ exists
    rule_repository.py 🚧 NEW — create this story
  api/
    dependencies/
      auth.py          ✅ get_current_operator (X-API-Key + session cookie)
      providers.py     ✅ get_db, get_source_repository, get_folder_repository
    routers/
      folders.py       ✅ exists
      sources.py       ✅ exists
      rules.py         🚧 NEW — create this story
    schemas/
      base.py          ✅ MongoBaseModel + collection constants
      folder.py        ✅ exists
      rule.py          🚧 NEW — create this story
  app.py               ✅ exists (lifespan, exception handlers — UPDATE this story)
  tasks.py             ✅ stubs for cache_refresher, mapping_sweeper, worker
```

### Technical References

- Error response envelope: [architecture.md#A1](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L348-L354)
- `get_current_operator` dual-auth: [architecture.md#S1](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L298-L315)
- Clean Architecture structure: [architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L621-L648)
- API URL naming (plural `snake_case`): [architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L560-L571)
- MongoDB collection naming: [architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L553-L558)
- FR-4–7, FR-31a, FR-32–37, FR-39, FR-41: [epics.md#Story 3.1](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L580-L634)

### What This Story Must NOT Do

- ❌ Do **not** implement the `RuleCache` or `CacheHolder` — that is Story 3.3.
- ❌ Do **not** implement `ReplacementRule` CRUD — that is Story 3.2.
- ❌ Do **not** read or write the `SAMPLING_COUNTERS` collection — that is a pipeline execution concern (Epic 4).
- ❌ Do **not** validate `replacement_image_path` against the filesystem — that is a pipeline execution concern (Story 4.3). Only validate that path is non-null when `enabled=true`.
- ❌ Do **not** add a uniqueness constraint on `(source_id, destination_channel)` — duplicates are intentionally permitted (FR-4).
- ❌ Do **not** add a Telegram resolve call for `destination_channel` at rule-creation time — it is stored as-is (username or numeric string). Resolution happens in the worker at dispatch time.
- ❌ Do **not** store `source_id` as a plain hex string — store as BSON `ObjectId` (see Critical: `source_id` Storage Format above). Violating this breaks `SourceRepository.get_referencing_rules_count()`.

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (Thinking)

### Debug Log References

- None.

### Completion Notes List

- Implemented pure Python domain entities and dataclasses for `ForwardingRule`.
- Created MongoDB-backed `ForwardingRuleRepository` supporting cascade deletes, folder two-step join, enable/disable operations.
- Developed all 7 clean-architecture use cases (create, update, get, delete, enable, disable, list).
- Designed rules Pydantic request/response schemas. Fixed schema inheritance mapping for the `id` field using validation/serialization aliases, matching other existing models.
- Built rules API router with 7 endpoints fully wired up to dual operator authentication.
- Configured indexes for `forwarding_rules` in application lifespan startup.
- Implemented and verified comprehensive repository and API integration tests (all 145 suite tests passing).

### Review Findings

- Validated that `id` is properly serialized as `"id"` rather than `"_id"` to ensure seamless API contract compatibility.

### File List

_New files to create:_
- `forward-bot/src/forward_bot/domain/entities/forwarding_rule.py`
- `forward-bot/src/forward_bot/infrastructure/mongo/repositories/rule_repository.py`
- `forward-bot/src/forward_bot/application/rules/create_rule.py`
- `forward-bot/src/forward_bot/application/rules/list_rules.py`
- `forward-bot/src/forward_bot/application/rules/get_rule.py`
- `forward-bot/src/forward_bot/application/rules/update_rule.py`
- `forward-bot/src/forward_bot/application/rules/delete_rule.py`
- `forward-bot/src/forward_bot/application/rules/enable_rule.py`
- `forward-bot/src/forward_bot/application/rules/disable_rule.py`
- `forward-bot/src/forward_bot/api/schemas/rule.py`
- `forward-bot/src/forward_bot/api/routers/rules.py`
- `forward-bot/tests/infrastructure/mongo/test_rule_repository.py`
- `forward-bot/tests/api/test_rules.py`

_Files to modify:_
- `forward-bot/src/forward_bot/domain/exceptions.py` — add new rule exceptions
- `forward-bot/src/forward_bot/api/dependencies/providers.py` — add `get_rule_repository`
- `forward-bot/src/forward_bot/app.py` — add router, exception handlers, indexes
