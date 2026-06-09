---
status: 'ready-for-dev'
---

# Story 2.2: Source Listing & Updates

Status: ready-for-dev

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
   - **And** `page_size` must default to 50, with a validated maximum limit of 200. Any requested `page_size` greater than 200 must be capped at 200.

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
   - **When** `GET /api/v1/sources?folder_id=null` is called.
   - **Then** only Sources with no folder assignment (`folder_id` is null) are returned.
   - **When** `GET /api/v1/sources?folder_id=invalid_hex_string` is called.
   - **Then** HTTP 422 Unprocessable Entity is returned (due to invalid ObjectId format).

4. **Update Source (PUT Endpoint):**
   - **Given** a registered Source exists with ID `{source_id}`.
   - **When** `PUT /api/v1/sources/{source_id}` is called with a complete payload containing `display_name`, `type`, and `folder_id` (which can be a hex string or null).
   - **Then** HTTP 200 OK is returned with the updated Source serialized.
   - **And** the database record is updated: `display_name`, `type`, and `folder_id` are modified, and `updated_at` is set to the current UTC timestamp (ISO 8601 string with `Z` suffix).
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

- [ ] **Domain & Exceptions**
  - [ ] Add `FolderNotFoundException` in [exceptions.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/domain/exceptions.py) (AC: 5)
  - [ ] Update `domain_exception_handler` in [app.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py) to map `FolderNotFoundException` to HTTP 422 with `"code": "folder_not_found"` (AC: 5)
- [ ] **Infrastructure / Repository**
  - [ ] Extend `SourceRepository` in [source_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/source_repository.py) to add a method for listing sources with pagination and filters (`type` and `folder_id`) (AC: 1, 2, 3)
  - [ ] Add update method in `SourceRepository` that updates specific fields or replaces the entity document (AC: 4, 6)
  - [ ] Add helper inside `SourceRepository` to check folder existence directly using `self.db[SOURCE_FOLDERS].find_one({"_id": ObjectId(folder_id)})` to bypass the need for a full `FolderRepository` since it's not yet created (AC: 5)
- [ ] **Use Cases**
  - [ ] Implement `ListSources` use case in `application/sources/list_sources.py` (AC: 1, 2, 3)
  - [ ] Implement `UpdateSource` use case in `application/sources/update_source.py` to handle both PUT (replace) and PATCH (partial) updates, including checks for folder existence and unique usernames (AC: 4, 5, 6, 7)
- [ ] **API Schemas & Router**
  - [ ] Add schemas in [source.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/schemas/source.py):
    - `SourcesPagedResponse` (with fields `items`, `total`, `page`, `page_size`)
    - `SourceUpdateRequest` (required `display_name`, `type`, optional `folder_id`)
    - `SourcePatchRequest` (all fields optional: `display_name`, `telegram_username`, `folder_id`)
  - [ ] Implement `GET /` router in [sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py) using `ListSources` (AC: 1, 2, 3, 8)
  - [ ] Implement `PUT /{source_id}` router in [sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py) using `UpdateSource` (AC: 4, 5, 8)
  - [ ] Implement `PATCH /{source_id}` router in [sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/sources.py) using `UpdateSource` (AC: 5, 6, 7, 8)
- [ ] **Verification & Testing**
  - [ ] Add repository tests in [test_source_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/test_source_repository.py) for filtering, pagination, and updates (AC: 1, 2, 3)
  - [ ] Add router tests in [test_sources.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py) verifying success, pagination capping, validation, folder/username errors, and security protection (AC: 1-8)

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
- **Pagination Capping:**
  - Enforce max limit for `page_size` inside the schema or routing parameters: `page_size = min(page_size, 200)`.
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

### Completion Notes List

### File List
