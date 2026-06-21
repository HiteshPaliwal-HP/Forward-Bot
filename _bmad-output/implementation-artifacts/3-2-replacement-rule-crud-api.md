---
baseline_commit: 57848c6e377c8a087419ba5f23ff93b6c46e006b
---

# Story 3.2: Replacement Rule CRUD API

Status: done

## Story

As a **Channel Operator**,
I want to create, list, update, and delete Replacement Rules scoped to a Forwarding Rule supporting both literal and regex substitutions,
so that **I can rewrite forwarded text — removing competitor names, swapping links, or applying regex patterns — without touching code**.

---

## Acceptance Criteria

1. **Create Replacement Rule — Happy Path (`POST /api/v1/rules/{rule_id}/replacement-rules`):**
   - **Given** a parent Forwarding Rule exists with `{rule_id}` and valid `search_text`, `replacement_text`, and `match_mode` are provided.
   - **When** `POST /api/v1/rules/{rule_id}/replacement-rules` is called.
   - **Then** HTTP 201 is returned with:
     - `id` (24-char hex ObjectId string)
     - `forwarding_rule_id` (the parent rule's id as a string)
     - `search_text` (as provided)
     - `replacement_text` (as provided)
     - `match_mode` (`literal` | `regex`)
     - `is_active` (default `true`)
     - `created_at` (ISO 8601 UTC string with Z suffix)
     - `updated_at` (ISO 8601 UTC string with Z suffix)

2. **Reject Invalid Regex Pattern (`POST` or `PUT`):**
   - **Given** `match_mode` is `"regex"` and `search_text` is an invalid regex pattern (e.g., `"[invalid("`).
   - **When** `POST /api/v1/rules/{rule_id}/replacement-rules` or `PUT /api/v1/rules/{rule_id}/replacement-rules/{id}` is called.
   - **Then** HTTP 422 is returned with:
     ```json
     {"error": {"code": "invalid_regex", "message": "Invalid regex /[invalid(/: {reason}."}}
     ```
   - **Note:** Reuses the existing `RuleInvalidRegexException` which is already mapped to HTTP 422 in `app.py`.

3. **Reject Non-Existent Parent Rule:**
   - **Given** `{rule_id}` does not exist in the `forwarding_rules` collection.
   - **When** `POST /api/v1/rules/{rule_id}/replacement-rules` is called.
   - **Then** HTTP 404 is returned with `{"error": {"code": "rule_not_found", "message": "Rule {id} not found."}}`.
   - **Note:** Reuses existing `RuleNotFoundException` mapped to 404 in `app.py`.

4. **List Replacement Rules (`GET /api/v1/rules/{rule_id}/replacement-rules`):**
   - **Given** replacement rules exist for a parent rule.
   - **When** `GET /api/v1/rules/{rule_id}/replacement-rules` is called.
   - **Then** HTTP 200 is returned with all replacement rules for that parent, ordered by `created_at` ascending (this is the pipeline application order per FR-7).
   - **And** The response is a flat list `{"items": [...]}` (not paginated — replacement rules per rule are bounded in practice).
   - **Given** `{rule_id}` does not exist.
   - **When** `GET /api/v1/rules/{rule_id}/replacement-rules` is called.
   - **Then** HTTP 404 with `{"error": {"code": "rule_not_found", ...}}`.

5. **Update Replacement Rule (`PUT /api/v1/rules/{rule_id}/replacement-rules/{id}`):**
   - **Given** a replacement rule exists.
   - **When** `PUT` is called with updated fields (`search_text`, `replacement_text`, `match_mode`, `is_active`).
   - **Then** HTTP 200 is returned with the updated replacement rule; `updated_at` is refreshed to current UTC.
   - **And** same regex validation applies as on POST.
   - **Given** `{id}` does not exist.
   - **When** `PUT` is called.
   - **Then** HTTP 404 with `{"error": {"code": "replacement_rule_not_found", ...}}`.

6. **Delete Replacement Rule (`DELETE /api/v1/rules/{rule_id}/replacement-rules/{id}`):**
   - **Given** a replacement rule exists.
   - **When** `DELETE /api/v1/rules/{rule_id}/replacement-rules/{id}` is called.
   - **Then** HTTP 204 is returned; the document is removed from `replacement_rules` collection.
   - **Given** `{id}` does not exist.
   - **When** `DELETE` is called.
   - **Then** HTTP 404 with `{"error": {"code": "replacement_rule_not_found", ...}}`.

7. **Cascade Delete with Parent Forwarding Rule:**
   - **Given** a Forwarding Rule has associated Replacement Rules.
   - **When** `DELETE /api/v1/rules/{rule_id}` is called (parent delete — already implemented in Story 3.1).
   - **Then** all child Replacement Rules for that parent are cascade-deleted from `replacement_rules`.
   - **Note:** This is already implemented in `ForwardingRuleRepository.delete_rule()` from Story 3.1. No new work needed here — just verify it works correctly with the real `replacement_rules` collection.

8. **Auth Gate:**
   - **Given** any request is made to any replacement-rules endpoint.
   - **Then** `Depends(get_current_operator)` must be in effect (X-API-Key header or signed session cookie). Missing auth → 401.

9. **Literal vs Regex Semantics (FR-8):**
   - **Given** `match_mode="literal"`.
   - **Then** literal match performs case-insensitive substring replacement (not enforced at storage — enforced at pipeline execution in Epic 4).
   - **Given** `match_mode="regex"`.
   - **Then** `search_text` must compile as a valid Python `re` pattern; `replacement_text` may include capture-group backreferences (e.g., `\1`).

---

## Tasks / Subtasks

- [x] **Domain Entity**
  - [x] Create `ReplacementRule` domain entity in `domain/entities/replacement_rule.py` as a `@dataclass`
  - [x] Add `ReplacementRuleNotFoundException` to `domain/exceptions.py`

- [x] **Infrastructure / Repository**
  - [x] Create `ReplacementRuleRepository` in `infrastructure/mongo/repositories/replacement_repository.py` extending `BaseRepository`
  - [x] Implement `get_replacement_by_id(id: str)` returning `ReplacementRule | None`
  - [x] Implement `add_replacement(replacement: ReplacementRule)` returning inserted `id` string
  - [x] Implement `update_replacement(id: str, replacement: ReplacementRule)` returning `bool`
  - [x] Implement `delete_replacement(id: str)` returning `bool`
  - [x] Implement `list_replacements_for_rule(rule_id: str)` returning `list[ReplacementRule]` ordered by `created_at` ASC

- [x] **Use Cases**
  - [x] `application/replacements/create_replacement.py` — `CreateReplacement` use case: validate parent rule exists, validate regex if `match_mode=regex`, persist
  - [x] `application/replacements/list_replacements.py` — `ListReplacements` use case: validate parent rule exists, fetch ordered list
  - [x] `application/replacements/update_replacement.py` — `UpdateReplacement` use case: validate replacement exists, validate regex if mode=regex, update
  - [x] `application/replacements/delete_replacement.py` — `DeleteReplacement` use case: validate replacement exists, delete

- [x] **API Schemas**
  - [x] Create `api/schemas/replacement_rule.py` with:
    - `ReplacementRuleCreateRequest` (required: `search_text`, `replacement_text`, `match_mode`; optional: `is_active=true`)
    - `ReplacementRuleUpdateRequest` (same fields, all required for full replacement)
    - `ReplacementRuleResponse` (extends `MongoBaseModel`)
    - `ReplacementRulesListResponse` (`items: list[ReplacementRuleResponse]`)

- [x] **API Router**
  - [x] Add replacement-rules sub-routes **inside** `api/routers/rules.py` (same file, not a new router file):
    - `POST /api/v1/rules/{rule_id}/replacement-rules` → 201
    - `GET /api/v1/rules/{rule_id}/replacement-rules` → 200
    - `PUT /api/v1/rules/{rule_id}/replacement-rules/{id}` → 200 or 404
    - `DELETE /api/v1/rules/{rule_id}/replacement-rules/{id}` → 204 or 404

- [x] **Dependency Provider Update**
  - [x] Add `get_replacement_repository` to `api/dependencies/providers.py`

- [x] **App Wiring**
  - [x] Register `ReplacementRuleRepository`-related MongoDB index in `app.py` lifespan:
    - Compound index: `(forwarding_rule_id, is_active, created_at)` on `replacement_rules`
  - [x] Register new exception handler for `ReplacementRuleNotFoundException` in `domain_exception_handler` in `app.py`
  - [x] Import `ReplacementRuleNotFoundException` in `app.py`

- [x] **Verification & Testing**
  - [x] Write unit tests in `tests/infrastructure/mongo/test_replacement_repository.py`
  - [x] Write API integration tests in `tests/api/test_replacement_rules.py` covering all ACs:
    - Happy path create with all required fields
    - Invalid regex rejection on `match_mode=regex` (POST and PUT)
    - Parent rule not found → 404 (POST and GET)
    - Replacement rule not found → 404 (PUT and DELETE)
    - List returns ordered by `created_at` ASC
    - Update refreshes `updated_at`
    - Delete 204 and removes document
    - Auth rejection (no key → 401)
    - Cascade delete verified (parent delete removes children — integration test)
  - [x] All 182 tests pass (35 new + 147 regression — 0 failures)

### Review Findings

- [x] [Review][Patch] Microsecond timestamp collision in pipeline sorting [forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py:70-81]
- [x] [Review][Patch] Missing `created_at` and `updated_at` optionality in response schema [forward-bot/src/forward_bot/api/schemas/replacement_rule.py:50-51]

---

## Dev Notes

### Architecture & Implementation Guardrails

#### Clean Architecture Rules

- `ReplacementRule` domain entity lives in `domain/entities/replacement_rule.py` — a **pure Python dataclass** with **only stdlib imports** (`dataclasses`, `datetime`).
- Use cases in `application/replacements/` receive injected repositories; they never import from `api/`.
- `ReplacementRuleRepository` in `infrastructure/mongo/repositories/replacement_repository.py` extends `BaseRepository` — follow the exact same pattern as `rule_repository.py`.
- The replacement-rules endpoints are added **to the existing `api/routers/rules.py`** file (not a new router), since they are sub-resources of rules and share the same URL prefix `api/v1/rules`.
- **Read [`app.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py) before modifying** — the exception handler chain and lifespan structure must be understood.

#### Domain Entity

```python
# domain/entities/replacement_rule.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ReplacementRule:
    """Domain entity for a text replacement rule scoped to a Forwarding Rule."""
    forwarding_rule_id: str        # Parent ForwardingRule ID (hex string)
    search_text: str               # Text to search for
    replacement_text: str          # Text to replace with (supports regex backrefs when match_mode=regex)
    match_mode: str                # "literal" | "regex"

    is_active: bool = True         # Default active (per FR-7)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

> **Key difference from ForwardingRule:** `is_active` **defaults to `True`** for replacement rules (per FR-7 and AC1 above), unlike forwarding rules which default to `False`.

#### New Exception — Add to `domain/exceptions.py`

```python
# In domain/exceptions.py — add after the existing Rule exceptions section:
class ReplacementRuleNotFoundException(DomainException):
    """Raised when a requested replacement rule is not found."""
    def __init__(self, replacement_id: str):
        self.replacement_id = replacement_id
        super().__init__(f"Replacement rule {replacement_id} not found.")
```

#### Exception to HTTP Mapping (add to `app.py`)

Add one `elif` block **before** the final `return JSONResponse(status_code=400, ...)` fallback in `domain_exception_handler`. Also add the import to the import block at line 132:

| Exception | HTTP Status | Error Code | Notes |
|-----------|-------------|------------|-------|
| `ReplacementRuleNotFoundException` | 404 | `replacement_rule_not_found` | Used by PUT and DELETE on replacement rules |

```python
# In app.py domain_exception_handler — add after the RuleMediaReplacementPathRequiredException block:
elif isinstance(exc, ReplacementRuleNotFoundException):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "replacement_rule_not_found",
                "message": f"Replacement rule {exc.replacement_id} not found."
            }
        }
    )
```

Also update the import block in `app.py` at line 132 to include `ReplacementRuleNotFoundException`:

```python
from forward_bot.domain.exceptions import (
    ...,  # existing imports
    ReplacementRuleNotFoundException,  # ADD THIS
)
```

#### `forwarding_rule_id` Storage Format (Critical)

`forwarding_rule_id` in `replacement_rules` documents is stored as a **plain hex string**, NOT as a BSON `ObjectId`. This is already established by Story 3.1's cascade delete in `ForwardingRuleRepository.delete_rule()`:

```python
# From rule_repository.py — already uses string comparison:
await self.db[REPLACEMENT_RULES].delete_many({"forwarding_rule_id": rule_id})
```

This means:
- On insert: store `forwarding_rule_id` as `str(rule_id)` (plain string, not `ObjectId`)
- On query: filter with `{"forwarding_rule_id": rule_id}` (plain string comparison)
- **Do NOT** convert `forwarding_rule_id` to `ObjectId` when querying — it is intentionally stored as a string

#### ReplacementRuleRepository Pattern

Follow `rule_repository.py` exactly. Key methods:

```python
# infrastructure/mongo/repositories/replacement_repository.py
from forward_bot.api.schemas.base import REPLACEMENT_RULES
from forward_bot.infrastructure.mongo.repositories.base import BaseRepository
from forward_bot.domain.entities.replacement_rule import ReplacementRule

class ReplacementRuleRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, REPLACEMENT_RULES)

    def _to_entity(self, doc: dict) -> ReplacementRule:
        return ReplacementRule(
            id=str(doc["_id"]),
            forwarding_rule_id=doc["forwarding_rule_id"],  # already stored as string
            search_text=doc["search_text"],
            replacement_text=doc["replacement_text"],
            match_mode=doc["match_mode"],
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    def _to_document(self, entity: ReplacementRule) -> dict:
        doc = {
            "forwarding_rule_id": entity.forwarding_rule_id,  # store as string
            "search_text": entity.search_text,
            "replacement_text": entity.replacement_text,
            "match_mode": entity.match_mode,
            "is_active": entity.is_active,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }
        if entity.id:
            from bson import ObjectId
            doc["_id"] = ObjectId(entity.id)
        return doc

    async def get_replacement_by_id(self, id: str) -> ReplacementRule | None:
        doc = await self.get_by_id(id)
        return self._to_entity(doc) if doc else None

    async def add_replacement(self, replacement: ReplacementRule) -> str:
        doc = self._to_document(replacement)
        inserted_id = await self.insert(doc)
        replacement.id = inserted_id
        return inserted_id

    async def update_replacement(self, id: str, replacement: ReplacementRule) -> bool:
        doc = self._to_document(replacement)
        return await self.update(id, doc)

    async def delete_replacement(self, id: str) -> bool:
        return await self.delete(id)

    async def list_replacements_for_rule(self, rule_id: str) -> list[ReplacementRule]:
        """List all replacement rules for a parent, ordered by created_at ASC (pipeline order)."""
        cursor = (
            self.collection.find({"forwarding_rule_id": rule_id})
            .sort("created_at", 1)  # ASC — pipeline application order (FR-7)
        )
        docs = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in docs]
```

> **Why `to_list(length=None)`?** Replacement rules per forwarding rule are bounded (tens, not thousands). No pagination needed.

#### Regex Validation (Reuse Existing Validators)

The `validate_keyword_regex()` function in `application/rules/validators.py` already handles regex validation and raises `RuleInvalidRegexException`. **Reuse it** for replacement rule `search_text` validation:

```python
# In application/replacements/create_replacement.py:
from forward_bot.application.rules.validators import validate_keyword_regex

# ⚠️ CRITICAL: search_text MUST be wrapped in a list.
# validate_keyword_regex iterates over the list. Passing a bare string
# would iterate its characters — each single char compiles as a valid regex,
# making the validation silently a no-op for invalid patterns like "[invalid(".
validate_keyword_regex([payload["search_text"]], payload["match_mode"])
```

This reuses `RuleInvalidRegexException` → HTTP 422 `invalid_regex` — exactly what the AC specifies and what `app.py` already handles.

#### Use Case Pattern — CreateReplacement

```python
# application/replacements/create_replacement.py
from datetime import datetime, timezone
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.application.rules.validators import validate_keyword_regex
from forward_bot.domain.exceptions import RuleNotFoundException


class CreateReplacement:
    def __init__(self, replacement_repo, rule_repo) -> None:
        self.replacement_repo = replacement_repo
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str, payload: dict) -> ReplacementRule:
        # 1. Validate parent rule exists
        parent_rule = await self.rule_repo.get_rule_by_id(rule_id)
        if parent_rule is None:
            raise RuleNotFoundException(rule_id)  # → 404

        # 2. Validate regex if match_mode=regex
        validate_keyword_regex([payload["search_text"]], payload["match_mode"])

        # 3. Build entity
        now = datetime.now(timezone.utc)
        replacement = ReplacementRule(
            forwarding_rule_id=rule_id,  # store as string
            search_text=payload["search_text"],
            replacement_text=payload["replacement_text"],
            match_mode=payload["match_mode"],
            is_active=payload.get("is_active", True),  # default True (FR-7)
            created_at=now,
            updated_at=now,
        )

        # 4. Persist
        await self.replacement_repo.add_replacement(replacement)
        return replacement
```

#### Use Case Pattern — ListReplacements

```python
# application/replacements/list_replacements.py
from forward_bot.domain.exceptions import RuleNotFoundException


class ListReplacements:
    def __init__(self, replacement_repo, rule_repo) -> None:
        self.replacement_repo = replacement_repo
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str) -> list:
        # Validate parent rule exists
        parent_rule = await self.rule_repo.get_rule_by_id(rule_id)
        if parent_rule is None:
            raise RuleNotFoundException(rule_id)  # → 404

        return await self.replacement_repo.list_replacements_for_rule(rule_id)
```

#### Use Case Pattern — UpdateReplacement

```python
# application/replacements/update_replacement.py
from datetime import datetime, timezone
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.application.rules.validators import validate_keyword_regex
from forward_bot.domain.exceptions import ReplacementRuleNotFoundException


class UpdateReplacement:
    def __init__(self, replacement_repo) -> None:
        self.replacement_repo = replacement_repo

    async def execute(self, replacement_id: str, payload: dict) -> ReplacementRule:
        # 1. Check replacement exists
        existing = await self.replacement_repo.get_replacement_by_id(replacement_id)
        if existing is None:
            raise ReplacementRuleNotFoundException(replacement_id)  # → 404

        # 2. Validate regex if match_mode=regex
        validate_keyword_regex([payload["search_text"]], payload["match_mode"])

        # 3. Update entity (preserve forwarding_rule_id and created_at)
        existing.search_text = payload["search_text"]
        existing.replacement_text = payload["replacement_text"]
        existing.match_mode = payload["match_mode"]
        existing.is_active = payload.get("is_active", existing.is_active)
        existing.updated_at = datetime.now(timezone.utc)

        await self.replacement_repo.update_replacement(replacement_id, existing)
        return existing
```

#### Use Case Pattern — DeleteReplacement

```python
# application/replacements/delete_replacement.py
from forward_bot.domain.exceptions import ReplacementRuleNotFoundException


class DeleteReplacement:
    def __init__(self, replacement_repo) -> None:
        self.replacement_repo = replacement_repo

    async def execute(self, replacement_id: str) -> None:
        existing = await self.replacement_repo.get_replacement_by_id(replacement_id)
        if existing is None:
            raise ReplacementRuleNotFoundException(replacement_id)  # → 404
        await self.replacement_repo.delete_replacement(replacement_id)
```

#### Pydantic Schema Design

```python
# api/schemas/replacement_rule.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from forward_bot.api.schemas.base import MongoBaseModel


class ReplacementRuleCreateRequest(BaseModel):
    """Request body for POST /api/v1/rules/{rule_id}/replacement-rules."""
    search_text: str = Field(min_length=1)         # prevent empty-string records
    replacement_text: str                           # may be empty (to delete matches)
    match_mode: Literal["literal", "regex"] = "literal"
    is_active: bool = True                          # default True per FR-7


class ReplacementRuleUpdateRequest(BaseModel):
    """Request body for PUT /api/v1/rules/{rule_id}/replacement-rules/{id}.
    Full replacement semantics — all fields required.
    """
    search_text: str = Field(min_length=1)
    replacement_text: str
    match_mode: Literal["literal", "regex"] = "literal"
    is_active: bool = True
    # ⚠️ NOTE: is_active defaults True (replacement rules default active).
    # This differs from ForwardingRuleUpdateRequest which defaults is_active=False.
    # This asymmetry is INTENTIONAL — do NOT change this default.


class ReplacementRuleResponse(MongoBaseModel):
    """API response for a single Replacement Rule document.

    ⚠️ CRITICAL — id field: Do NOT redeclare `id` here. MongoBaseModel already declares
    `id: str = Field(alias="_id")` with a coerce_object_id validator. Redeclaring with
    validation_alias/serialization_alias in a subclass causes Pydantic v2 field conflicts.
    The inherited `id` field + `from_entity()` passing `_id` key is the correct pattern.
    """
    forwarding_rule_id: str
    search_text: str
    replacement_text: str
    match_mode: str
    is_active: bool
    created_at: datetime  # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
    updated_at: datetime
    # ⚠️ created_at and updated_at are non-Optional here. The domain entity uses
    # Optional[datetime] for flexibility, but use cases MUST always set both to
    # datetime.now(timezone.utc) before persisting. A None value here will cause
    # a Pydantic validation error at response serialization time.

    @classmethod
    def from_entity(cls, r) -> "ReplacementRuleResponse":
        return cls.model_validate({
            "_id": r.id,        # MongoBaseModel.coerce_object_id handles str→str
            "forwarding_rule_id": r.forwarding_rule_id,
            "search_text": r.search_text,
            "replacement_text": r.replacement_text,
            "match_mode": r.match_mode,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        })


class ReplacementRulesListResponse(BaseModel):
    """List response for GET /api/v1/rules/{rule_id}/replacement-rules."""
    items: list[ReplacementRuleResponse]
```

> **`replacement_text` may be an empty string** — this is valid for use cases like "delete all occurrences of X". Do NOT add `min_length=1` to `replacement_text`.

#### Router Pattern — Add to Existing `api/routers/rules.py`

Add the following **new endpoints to the existing `rules.py` router** (same `APIRouter` instance, same file). Add necessary imports at the top of the file:

```python
# Additional imports to add to api/routers/rules.py:
from forward_bot.api.dependencies.providers import get_replacement_repository
from forward_bot.api.schemas.replacement_rule import (
    ReplacementRuleCreateRequest,
    ReplacementRuleUpdateRequest,
    ReplacementRuleResponse,
    ReplacementRulesListResponse,
)
from forward_bot.application.replacements.create_replacement import CreateReplacement
from forward_bot.application.replacements.list_replacements import ListReplacements
from forward_bot.application.replacements.update_replacement import UpdateReplacement
from forward_bot.application.replacements.delete_replacement import DeleteReplacement
from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository


@router.post(
    "/{rule_id}/replacement-rules",
    response_model=ReplacementRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a replacement rule scoped to a forwarding rule.",
)
async def create_replacement_rule(
    rule_id: str,
    payload: ReplacementRuleCreateRequest,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> ReplacementRuleResponse:
    use_case = CreateReplacement(replacement_repo, rule_repo)
    replacement = await use_case.execute(rule_id, payload.model_dump())
    return ReplacementRuleResponse.from_entity(replacement)


@router.get(
    "/{rule_id}/replacement-rules",
    response_model=ReplacementRulesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List replacement rules for a forwarding rule, ordered by created_at ASC.",
)
async def list_replacement_rules(
    rule_id: str,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> ReplacementRulesListResponse:
    use_case = ListReplacements(replacement_repo, rule_repo)
    replacements = await use_case.execute(rule_id)
    return ReplacementRulesListResponse(items=[ReplacementRuleResponse.from_entity(r) for r in replacements])


@router.put(
    "/{rule_id}/replacement-rules/{replacement_id}",
    response_model=ReplacementRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Full replacement update of a replacement rule.",
)
async def update_replacement_rule(
    rule_id: str,
    replacement_id: str,
    payload: ReplacementRuleUpdateRequest,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    _: str = Depends(get_current_operator),
) -> ReplacementRuleResponse:
    use_case = UpdateReplacement(replacement_repo)
    replacement = await use_case.execute(replacement_id, payload.model_dump())
    return ReplacementRuleResponse.from_entity(replacement)


@router.delete(
    "/{rule_id}/replacement-rules/{replacement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a replacement rule.",
)
async def delete_replacement_rule(
    rule_id: str,
    replacement_id: str,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    _: str = Depends(get_current_operator),
) -> None:
    use_case = DeleteReplacement(replacement_repo)
    await use_case.execute(replacement_id)
```

> **`rule_id` in PUT and DELETE:** The `rule_id` path param is accepted for URL consistency but is NOT validated against the replacement's `forwarding_rule_id` in these operations. The replacement's own `id` uniquely identifies it. This is an accepted MVP simplification.
>
> **Edge case (intentional, document in tests):** A `PUT /{wrong_rule_id}/replacement-rules/{id}` or `DELETE /{wrong_rule_id}/replacement-rules/{id}` where `id` exists but belongs to a *different* `rule_id` will succeed with HTTP 200/204. This cross-ownership scenario is **not validated** — do NOT add a cross-ownership check unless explicitly asked. Test stubs should note this edge case with a comment.

#### Dependency Provider Update (`api/dependencies/providers.py`)

Add the following after the existing `get_rule_repository` function:

```python
from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository

def get_replacement_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> ReplacementRuleRepository:
    """Injects the ReplacementRuleRepository."""
    return ReplacementRuleRepository(db)
```

#### MongoDB Index (`app.py` lifespan)

Add inside the existing `try` block in `default_lifespan`, after the FORWARDING_RULES indexes (around line 51):

```python
# Replacement rule index (Story 3.2)
from forward_bot.api.schemas.base import REPLACEMENT_RULES
await mongo_client.db[REPLACEMENT_RULES].create_index(
    [("forwarding_rule_id", 1), ("is_active", 1), ("created_at", 1)], background=True
)
```

#### ⚠️ CRITICAL: Route Ordering in `rules.py`

FastAPI matches routes top-to-bottom. The new replacement-rule routes (`/{rule_id}/replacement-rules`) must be added **AFTER** the `/{rule_id}` GET/PUT/DELETE routes for single rule operations, to avoid path ambiguity. The `/{rule_id}/replacement-rules` path will NOT conflict with `/{rule_id}` because of the additional `/replacement-rules` segment.

However, the `/{rule_id}/enable` and `/{rule_id}/disable` routes (added in Story 3.1) already demonstrate this pattern works correctly. Place replacement-rule routes after enable/disable routes.

#### Unit Test Pattern (Motor mock — from Epic 2 retrospective)

`collection.find()` returns a cursor synchronously (not an async call). In unit tests, mock with `MagicMock()`, then mock the cursor's `to_list()` as `AsyncMock`:

```python
# For list_replacements_for_rule:
mock_collection.find.return_value = MagicMock()
mock_collection.find.return_value.sort.return_value = MagicMock()
mock_collection.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[...])
```

For `insert`, `update`, `delete`, use `AsyncMock` directly (they are coroutines):

```python
mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
mock_collection.find_one = AsyncMock(return_value={...})
mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
```

#### API Integration Test Imports (for `tests/api/test_replacement_rules.py`)

Follow the same structure as `tests/api/test_rules.py`. Required imports:

```python
"""API integration tests for /api/v1/rules/{rule_id}/replacement-rules — covers all ACs for Story 3.2."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule, SamplingConfig, AttributionConfig,
    AutoReplaceSourceRefsConfig, MediaReplacementConfig,
)
from forward_bot.api.dependencies.providers import (
    get_rule_repository,
    get_replacement_repository,   # ← new provider added in this story
)
```

> **Both repos needed for POST/GET:** Endpoints that validate the parent rule (`POST`, `GET`) need **both** `get_rule_repository` AND `get_replacement_repository` overridden. Endpoints that operate on an existing replacement (`PUT`, `DELETE`) only need `get_replacement_repository` overridden (no parent rule lookup).

### Previous Story Intelligence (Story 3.1 Learnings)

1. **`id` field — do NOT redeclare in `ReplacementRuleResponse`:** `ForwardingRuleResponse` redeclares `id` with `validation_alias`/`serialization_alias` because it also needs a `@field_validator("source_id")`. For `ReplacementRuleResponse`, the `id` field is already fully handled by `MongoBaseModel` (`Field(alias="_id")` + `coerce_object_id` validator). Redeclaring `id` in the subclass causes a Pydantic v2 field conflict. The `from_entity()` classmethod passing `"_id": r.id` is sufficient — do NOT copy `ForwardingRuleResponse`'s `id` field declaration.

2. **`from_entity` class method:** Story 3.1 introduced the `from_entity()` classmethod pattern on response models. Replicate the classmethod structure — but see item 1 above regarding the `id` field difference.

3. **`min_length=1` on string fields:** `search_text` must have `min_length=1`. `replacement_text` must NOT — empty replacement strings are valid (to delete text occurrences).

4. **`BaseRepository.get_by_id()` returns `None` for invalid ObjectIds:** Do not add extra ObjectId format validation in the router — the use case raises `ReplacementRuleNotFoundException` → 404 when repo returns None.

5. **Auth on every endpoint:** Every `@router.*()` must include `_: str = Depends(get_current_operator)`.

6. **Cascade delete already implemented:** Story 3.1's `ForwardingRuleRepository.delete_rule()` already does `delete_many({"forwarding_rule_id": rule_id})` on the `REPLACEMENT_RULES` collection. Since `forwarding_rule_id` is stored as a string there, and the cascade delete uses the string `rule_id`, this will work correctly without any changes.

7. **Validators reuse:** The `application/rules/validators.py` module has `validate_keyword_regex()`. Import and reuse it directly rather than duplicating the logic.

### 🚀 Before You Start — Required First Actions

1. **Verify sprint status:**
   ```bash
   grep -A2 "3-2" _bmad-output/implementation-artifacts/sprint-status.yaml
   ```
   Expected: `status: ready-for-dev`. If `done` or `in-progress`, reconcile before proceeding.

2. **Check current git HEAD** (the git snapshot below may be stale):
   ```bash
   git log --oneline -5
   ```
   Story 3.1 was `done` at story-file creation time but may not have been committed yet. Identify the actual HEAD commit before assuming file states.

### Git Intelligence (Snapshot at Story File Creation)

| Commit | What It Did |
|--------|-------------|
| `57848c6` | Story 2.3 — Folder CRUD (establishes cross-collection ops pattern in `delete_folder`) |
| `64187b5` | Story 2.1 — Source registration + Telegram ID resolve |

> **Note:** This snapshot was captured before Story 3.1 commits landed. Run `git log --oneline -5` as the first action (see section above) to get the current state.

### Current File Inventory (After Story 3.1)

```
src/forward_bot/
  domain/entities/
    source.py                    ✅ exists
    source_folder.py             ✅ exists
    forwarding_rule.py           ✅ exists (Story 3.1)
    replacement_rule.py          🚧 NEW — create this story
  domain/exceptions.py           ✅ exists — ADD ReplacementRuleNotFoundException
  application/
    folders/                     ✅ complete
    sources/                     ✅ complete
    rules/                       ✅ complete (7 use cases from Story 3.1)
      validators.py              ✅ exists — REUSE validate_keyword_regex
    replacements/                ✅ package exists (__init__.py present, empty)
                                 🚧 4 use case files needed — create inside this package
                                 ⚠️ Do NOT modify __init__.py — leave empty, no exports needed
    pipeline/                    🚧 empty — needs Epic 4
  infrastructure/mongo/repositories/
    base.py                      ✅ BaseRepository
    source_repository.py         ✅ exists
    folder_repository.py         ✅ exists
    rule_repository.py           ✅ exists (Story 3.1) — VERIFY cascade delete works
    replacement_repository.py    🚧 NEW — create this story
  api/
    dependencies/
      auth.py                    ✅ get_current_operator
      providers.py               ✅ has get_rule_repository — ADD get_replacement_repository
    routers/
      folders.py                 ✅ exists
      sources.py                 ✅ exists
      rules.py                   ✅ exists (Story 3.1) — ADD replacement-rule endpoints
    schemas/
      base.py                    ✅ MongoBaseModel + collection constants
      folder.py                  ✅ exists
      rule.py                    ✅ exists (Story 3.1)
      replacement_rule.py        🚧 NEW — create this story
  app.py                         ✅ exists — ADD exception handler + import + MongoDB index
  tasks.py                       ✅ stubs
```

### Technical References

- Error response envelope (A1): [architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md)
- `get_current_operator` dual-auth: `api/dependencies/auth.py`
- FR-7 (Replacement Rule CRUD): [epics.md#Story 3.2](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L636-L670)
- FR-8 (Literal + regex semantics): applied at pipeline execution time (Epic 4), not at storage time
- `BaseRepository` pattern: [base.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/base.py)
- `ForwardingRuleRepository` pattern to mirror: [rule_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/rule_repository.py)
- `validators.py` (reuse `validate_keyword_regex`): [validators.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/application/rules/validators.py)
- Existing `REPLACEMENT_RULES` constant: [base.py#L9](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/schemas/base.py#L9)

### What This Story Must NOT Do

- ❌ Do **not** implement literal or regex replacement logic — that is a pipeline execution concern (Epic 4, Story 4.3 `TextReplacementStep`). This story only stores configuration.
- ❌ Do **not** add pagination to the replacement rules list endpoint — replacement rules per parent are bounded (no cursor/page needed).
- ❌ Do **not** implement the `RuleCache` or `CacheHolder` — that is Story 3.3.
- ❌ Do **not** validate that `replacement_text` is a valid regex — only `search_text` is compiled as a pattern.
- ❌ Do **not** store `forwarding_rule_id` as a BSON `ObjectId` — it is intentionally stored as a plain string to be consistent with the existing cascade delete in `ForwardingRuleRepository.delete_rule()`.
- ❌ Do **not** create a new `APIRouter` for replacement-rules — add endpoints to the existing `api/routers/rules.py`.

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (Thinking)

### Debug Log References

1. `ReplacementRuleResponse.id` serialization fix: Initially inherited `id: str = Field(alias="_id")` from `MongoBaseModel`, which serializes as `_id` when FastAPI calls `model_dump(by_alias=True)`. Fixed by redeclaring `id: str = Field(validation_alias="_id", serialization_alias="id")` in `ReplacementRuleResponse`, matching the `ForwardingRuleResponse` pattern.

### Completion Notes List

✅ All 9 Acceptance Criteria implemented and verified:
- AC1: POST creates replacement rule with all fields, is_active defaults True (FR-7).
- AC2: Invalid regex on POST/PUT returns 422 `invalid_regex` — reuses `validate_keyword_regex()` with list wrapping.
- AC3: Non-existent parent rule returns 404 `rule_not_found`.
- AC4: GET lists replacement rules ordered by `created_at` ASC (pipeline order FR-7), returns 404 for missing parent.
- AC5: PUT updates replacement rule, refreshes `updated_at`, returns 404 for missing replacement.
- AC6: DELETE returns 204 for found, 404 for missing replacement.
- AC7: Cascade delete of replacement_rules when parent forwarding rule is deleted — verified via existing `ForwardingRuleRepository.delete_rule()` using string `forwarding_rule_id`.
- AC8: Auth gate — all 4 replacement-rule endpoints require X-API-Key (→ 401 without it).
- AC9: Literal vs regex semantics — literal mode skips pattern compilation; regex validates `search_text` at write time.

✅ Key implementation decisions:
- `forwarding_rule_id` stored as plain string (not BSON ObjectId) — consistent with cascade delete in Story 3.1.
- `search_text` wrapped in list when passed to `validate_keyword_regex()` to prevent character-by-character iteration.
- Replacement-rule endpoints added to existing `rules.py` router (not a new file) as sub-resources.
- `ReplacementRuleResponse.id` requires `serialization_alias="id"` override to ensure JSON response uses `id` key.
- Cross-ownership on PUT/DELETE is intentionally not validated (MVP simplification, documented in tests).

✅ Tests: 35 new tests (14 unit + 21 API integration) — 182 total suite, 0 failures, 0 regressions.

### File List

### File List

_New files created:_
- `forward-bot/src/forward_bot/domain/entities/replacement_rule.py`
- `forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py`
- `forward-bot/src/forward_bot/application/replacements/create_replacement.py`
- `forward-bot/src/forward_bot/application/replacements/list_replacements.py`
- `forward-bot/src/forward_bot/application/replacements/update_replacement.py`
- `forward-bot/src/forward_bot/application/replacements/delete_replacement.py`
- `forward-bot/src/forward_bot/api/schemas/replacement_rule.py`
- `forward-bot/tests/infrastructure/mongo/test_replacement_repository.py`
- `forward-bot/tests/api/test_replacement_rules.py`

_Files modified:_
- `forward-bot/src/forward_bot/domain/exceptions.py` — added `ReplacementRuleNotFoundException`
- `forward-bot/src/forward_bot/api/dependencies/providers.py` — added `get_replacement_repository`
- `forward-bot/src/forward_bot/api/routers/rules.py` — added 4 replacement-rule endpoints + imports
- `forward-bot/src/forward_bot/app.py` — added exception handler, import, and MongoDB index

---

## Change Log

- Story 3.2 implemented: Replacement Rule CRUD API (4 endpoints, 7 files created, 4 modified). All 9 ACs verified. 35 new tests added. 182 total suite green. (Date: 2026-06-18)
