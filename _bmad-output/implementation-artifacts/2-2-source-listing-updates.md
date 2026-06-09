---
status: 'done'
baseline_commit: 64187b52447dd96a8c0f0602e04f5ead9b8d427a
---

# Story 2.2: Source Listing & Updates

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want **to list all my registered Sources filtered by type or folder, and update a Source's display name or folder assignment**,
so that **I can manage a large source catalog efficiently**.

## Acceptance Criteria

1. **List Registered Sources (Pagination):**
   - **Given** registered Sources exist in the database.
   - **When** `GET /api/v1/sources` is called without pagination parameters.
   - **Then** HTTP 200 OK is returned with a default paginated JSON envelope:
     ```json
     {
       "items": [...],
       "total": N,
       "page": 1,
       "page_size": 50
     }
     ```
   - **Given** specific pagination parameters `page` and `page_size` are provided.
   - **When** `GET /api/v1/sources?page=2&page_size=10` is called.
   - **Then** HTTP 200 OK is returned with the items corresponding to the second page of size 10, showing the accurate `total`, `page`, and `page_size`.
   - **And** the items must be sorted by `created_at` descending by default to ensure deterministic pagination.
   - **And** `page_size` must default to 50, with a validated maximum limit of 200. Any requested `page_size` greater than 200 must be capped at 200. `page` and `page_size` must be validated to be >= 1.

2. **Filter Sources by Type:**
   - **Given** Sources of both `type="channel"` and `type="group"` exist.
   - **When** `GET /api/v1/sources?type=channel` is called.
   - **Then** only sources where `type` is `"channel"` are returned in the `items` array.
   - **When** `GET /api/v1/sources?type=group` is called.
   - **Then** only sources where `type` is `"group"` are returned.
   - **When** `GET /api/v1/sources?type=invalid_type` is called.
   - **Then** HTTP 422 Unprocessable Entity is returned (as type must be strictly `"channel"` or `"group"`).

3. **Filter Sources by Folder:**
   - **Given** Sources are assigned to folders (using valid `folder_id` ObjectId hex strings) or are unassigned (`folder_id: null` in MongoDB).
   - **When** `GET /api/v1/sources?folder_id={folder_id}` is called (where `{folder_id}` is a valid folder's hex string ID).
   - **Then** only Sources assigned to that specific folder are returned.
   - **When** `GET /api/v1/sources?folder_id=null` is called (passing the string `"null"`).
   - **Then** only Sources with no folder assignment (`folder_id` is null) are returned.
   - **When** `GET /api/v1/sources?folder_id=invalid_hex_string` is called.
   - **Then** HTTP 422 Unprocessable Entity is returned (due to invalid ObjectId format).

4. **Update Source (PUT Endpoint):**
   - **Given** a registered Source exists with ID `{source_id}`.
   - **When** `PUT /api/v1/sources/{source_id}` is called with a complete payload containing `display_name`, `type`, `folder_id` (which can be a hex string or null), and optionally `telegram_username`.
   - **Then** HTTP 200 OK is returned with the updated Source serialized.
   - **And** the database record is updated: `display_name`, `type`, `folder_id`, and `telegram_username` are modified, and `updated_at` is set to the current UTC timestamp (ISO 8601 string with `Z` suffix).
   - **And** if `telegram_username` is updated, the duplicate username check (AC 7) is enforced.
   - **Given** `{source_id}` does not exist.
   - **When** `PUT /api/v1/sources/{source_id}` is called.
   - **Then** HTTP 404 Not Found is returned with the standard error envelope:
     ```json
     {
       "error": {
         "code": "source_not_found",
         "message": "Source {source_id} not found."
       }
     }
     ```

5. **Folder Existence Validation on Update:**
   - **Given** the update or patch payload contains a non-null `folder_id`.
   - **When** `PUT` or `PATCH` is called on `/api/v1/sources/{source_id}`.
   - **Then** the service verifies if the folder exists in the `source_folders` collection.
   - **And** if the folder does not exist, the request is rejected with HTTP 422 Unprocessable Entity and:
     ```json
     {
       "error": {
         "code": "folder_not_found",
         "message": "Folder with ID {folder_id} does not exist."
       }
     }
     ```

6. **Partial Update (PATCH Endpoint):**
   - **Given** a registered Source exists.
   - **When** `PATCH /api/v1/sources/{source_id}` is called with a partial payload containing any subset of `display_name`, `telegram_username`, or `folder_id`.
   - **Then** HTTP 200 OK is returned with the updated Source.
   - **And** only the fields provided in the payload are updated in the database; other fields remain unchanged; `updated_at` is set to the current UTC timestamp.
   - **And** the folder existence check (AC 5) is enforced if `folder_id` is updated.
   - **Given** `{source_id}` does not exist.
   - **When** `PATCH /api/v1/sources/{source_id}` is called.
   - **Then** HTTP 404 Not Found is returned.

7. **Duplicate Username Check on Partial Update:**
   - **Given** `telegram_username` is updated via `PATCH`.
   - **When** the new username is already in use by *another* registered Source.
   - **Then** the request is rejected with HTTP 422 Unprocessable Entity:
     ```json
     {
       "error": {
         "code": "source_already_exists",
         "message": "Source with username {username} already exists."
       }
     }
     ```

8. **Auth Gate / Security:**
   - **Given** any request is made to `GET /api/v1/sources`, `PUT /api/v1/sources/{source_id}`, or `PATCH /api/v1/sources/{source_id}`.
   - **Then** it must go through the dual-auth security gate (`Depends(get_current_operator)`).

## Tasks / Subtasks

- [x] **Domain & Exceptions**
  - [x] Add `FolderNotFoundException` in [exceptions.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/domain/exceptions.py) (AC: 5)
  - [x] Update `domain_exception_handler` in [app.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py) to map `FolderNotFoundException` to HTTP 422 with `"code": "folder_not_found"` (AC: 5)
- [x] **Infrastructure / Repository**
  - [x] Extend `SourceRepository` in [source_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/source_repository.py) to add a method for listing sources with pagination and filters (`type` and `folder_id`) (AC: 1, 2, 3)
  - [x] Add update method in `SourceRepository` that updates specific fields or replaces the entity document (AC: 4, 6)
  - [x] Add helper inside `SourceRepository` to check folder existence directly using `self.db[SOURCE_FOLDERS].find_one({"_id": ObjectId(folder_id)})` to bypass the need for a full `FolderRepository` since it's not yet created (AC: 5)
- [x] **Use Cases**
  - [x] Implement `ListSources` use case in `application/sources/list_sources.py` (AC: 1, 2, 3)
  - [x] Implement `UpdateSource` use case in `application/sources/update_source.py` to handle both PUT (replace) and PATCH (partial) updates, including checks for folder existence and unique usernames (AC: 4, 5, 6, 7)
- [x] **API Schemas & Router**
  - [x] Add schemas in [source.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/schemas/source.py):
    - `SourcesPagedResponse` (with fields `items`, `total`, `page`, `page_size`)
    - `SourceUpdateRequest` (required `display_name`, `type`, optional `folder_id`, optional `telegram_username`)
    - `SourcePatchRequest` (all fields optional: `display_name`, `telegram_username`, `folder_id`)
  - [x] Implement `GET /` router in [sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py) using `ListSources` (AC: 1, 2, 3, 8)
  - [x] Implement `PUT /{source_id}` router in [sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py) using `UpdateSource` (AC: 4, 5, 8)
  - [x] Implement `PATCH /{source_id}` router in [sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py) using `UpdateSource` (AC: 5, 6, 7, 8)
- [x] **Verification & Testing**
  - [x] Add repository tests in [test_source_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/test_source_repository.py) for filtering, pagination, and updates (AC: 1, 2, 3)
  - [x] Add router tests in [test_sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py) verifying success, pagination capping, validation, folder/username errors, and security protection (AC: 1-8)

## Dev Notes

### Architecture & Implementation Guardrails

- **Clean Architecture:**
  - Keep domain entities pure. Use case execution should expect injected repositories and raise custom domain exceptions.
  - Router maps domain exceptions to HTTP codes and serializes outputs.
- **Folder Validation Trick:**
  - Since folders are fully implemented in Story 2.3 and `FolderRepository` is not yet available, verify if `folder_id` exists by querying MongoDB's `source_folders` collection directly:
    ```python
    from forward_bot.api.schemas.base import SOURCE_FOLDERS
    folder = await self.db[SOURCE_FOLDERS].find_one({"_id": ObjectId(folder_id)})
    ```
    This prevents dependency-block issues between Story 2.2 and 2.3.
- **Pagination Capping & Sorting:**
  - Enforce max limit for `page_size` inside the schema or routing parameters: `page_size = min(page_size, 200)`. Ensure `page >= 1` and `page_size >= 1`.
  - Apply a default sort order (`created_at` descending) in the repository list method.
- **Folder `null` String parsing:**
  - The `folder_id` query parameter might receive the literal string `"null"`. Handle this in the endpoint before validation (or define the parameter correctly) so that `"null"` is translated to `None` and doesn't fail standard hex string regex validations.
- **Username Normalization:**
  - Normalize any updated username (`telegram_username`) to strip `@` and check if it already exists in another source. If so, raise `SourceAlreadyExistsException`.
- **Dual-Auth Gate:**
  - Do not forget to wire `Depends(get_current_operator)` to all three endpoints.
- **ObjectId Conversion:**
  - Ensure any incoming `folder_id` string is checked for ObjectId validity:
    ```python
    from bson import ObjectId
    if folder_id and not ObjectId.is_valid(folder_id):
        raise ...
    ```

### References

- Cite: plural resource paths mapping standard [architecture.md:L560-571](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L560-L571)
- Cite: error response envelope format [architecture.md:L348-354](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L348-L354)
- Cite: Clean Architecture backend structure [architecture.md:L621-648](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L621-L648)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Debug Log References

- Fully verified unit test suite run successfully: `.venv\Scripts\pytest` passed all 93 tests.

### Completion Notes List

- Implemented `FolderNotFoundException` and `SourceUsernameAlreadyExistsException` to represent specific error constraints.
- Integrated mapping for domain exceptions in `app.py` exception handlers.
- Extended `SourceRepository` with helper methods `folder_exists`, `update_source`, and `list_sources` supporting type and folder filtering.
- Implemented use cases `ListSources` and `UpdateSource` to orchestrate pagination capping, type checks, and folder/username validation.
- Defined API routers for listing sources (GET), fully replacing sources (PUT), and partially updating sources (PATCH).
- Fully tested all acceptance criteria, verifying HTTP 200, 404, and 422 conditions.

### File List

- `forward-bot/src/forward_bot/domain/exceptions.py` (modified)
- `forward-bot/src/forward_bot/app.py` (modified)
- `forward-bot/src/forward_bot/infrastructure/mongo/repositories/source_repository.py` (modified)
- `forward-bot/src/forward_bot/application/sources/list_sources.py` (new)
- `forward-bot/src/forward_bot/application/sources/update_source.py` (new)
- `forward-bot/src/forward_bot/api/schemas/source.py` (modified)
- `forward-bot/src/forward_bot/api/routers/sources.py` (modified)
- `forward-bot/tests/infrastructure/mongo/test_source_repository.py` (modified)
- `forward-bot/tests/api/test_sources.py` (modified)

