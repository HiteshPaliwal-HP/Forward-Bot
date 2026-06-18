---
status: 'done'
baseline_commit: '57848c6e377c8a087419ba5f23ff93b6c46e006b'
---

# Story 2.3: Folder CRUD

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want **to create, rename, and delete Folders to organize my Sources into logical groups**,
so that **I can manage 40+ sources without visual clutter and filter forwarding rules by folder**.

## Acceptance Criteria

1. **Create Folder (`POST /api/v1/folders`):**
   - **Given** a unique folder name is provided in the payload.
   - **When** `POST /api/v1/folders` is called with `{"name": "Crypto Signals"}`.
   - **Then** HTTP 201 Created is returned with the created Folder containing `id` (24-character hex ObjectId string), `name`, `created_at`, and `updated_at` (ISO 8601 UTC strings with `Z` suffix).
   - **And** a structured log event `folder_created` is emitted containing the folder's `id` and `name`.

2. **Reject Duplicate Folder Name (Case-Insensitive):**
   - **Given** a folder name that already exists in the database `source_folders` collection (checked case-insensitively).
   - **When** `POST /api/v1/folders` is called with that duplicate name (e.g., `"crypto signals"` when `"Crypto Signals"` exists).
   - **Then** HTTP 422 Unprocessable Entity is returned with standard error envelope:
     ```json
     {
       "error": {
         "code": "folder_name_in_use",
         "message": "Folder name in use: crypto signals."
       }
     }
     ```

3. **List Folders with Source Count (Single-Trip Aggregation):**
   - **Given** registered folders exist in the database.
   - **When** `GET /api/v1/folders` is called.
   - **Then** HTTP 200 OK is returned with a JSON array of all folders.
   - **And** each folder object in the list includes a `source_count` integer showing how many Sources are currently assigned to it (`folder_id` matching this folder's ID).
   - **And** the folders are sorted alphabetically by `name` ascending.
   - **And** this count is fetched efficiently in a single aggregate database query to prevent N+1 query patterns.

4. **Verify Folder Name Availability (Debounce support):**
   - **Given** the operator wants to verify if a folder name is already in use (checked case-insensitively).
   - **When** `GET /api/v1/folders?name={name}` is called.
   - **Then** HTTP 200 OK is returned with a JSON list of matching folders (if name taken, returns the matching folder; if not, returns `[]`).
   - **And** this supports debounced check GET requests from the UI.

5. **Get Folder Details (With embedded sources or Not Found 404):**
   - **Given** a folder exists with ID `{folder_id}`.
   - **When** `GET /api/v1/folders/{folder_id}` is called.
   - **Then** HTTP 200 OK is returned with the folder details.
   - **When** `GET /api/v1/folders/{folder_id}?include=sources` is called.
   - **Then** the response includes the folder fields plus an embedded `sources` array containing all Source objects assigned to it.
   - **Given** `{folder_id}` does not exist or has an invalid ID format.
   - **When** `GET /api/v1/folders/{folder_id}` is called.
   - **Then** HTTP 404 Not Found is returned with standard error envelope:
     ```json
     {
       "error": {
         "code": "folder_not_found",
         "message": "Folder with ID {folder_id} does not exist."
       }
     }
     ```

6. **Rename Folder (Self-Rename and Conflict checks):**
   - **Given** a folder exists with ID `{folder_id}`.
   - **When** `PUT /api/v1/folders/{folder_id}` is called with a payload `{"name": "New Folder Name"}`.
   - **Then** HTTP 200 OK is returned with the updated Folder object, and `updated_at` is set to the current UTC timestamp.
   - **And** a structured log event `folder_renamed` is emitted.
   - **Given** the name is already in use by *another* folder (checked case-insensitively).
   - **When** `PUT /api/v1/folders/{folder_id}` is called.
   - **Then** HTTP 422 Unprocessable Entity is returned with `folder_name_in_use`.
   - **Given** the name matches the folder's *own* current name.
   - **When** `PUT /api/v1/folders/{folder_id}` is called.
   - **Then** the operation succeeds successfully (self-rename allowed).
   - **Given** `{folder_id}` does not exist.
   - **When** `PUT /api/v1/folders/{folder_id}` is called.
   - **Then** HTTP 404 Not Found is returned with `folder_not_found`.

7. **Delete Folder & Disassociate Sources:**
   - **Given** a folder exists with ID `{folder_id}`.
   - **When** `DELETE /api/v1/folders/{folder_id}` is called.
   - **Then** HTTP 204 No Content is returned.
   - **And** the folder document is permanently deleted from MongoDB `source_folders` collection.
   - **And** all Sources assigned to this folder have their `folder_id` updated to `null` in the `sources` collection.
   - **And** the Sources themselves are NOT deleted.
   - **And** a structured log event `folder_deleted` is emitted.
   - **Given** `{folder_id}` does not exist.
   - **When** `DELETE /api/v1/folders/{folder_id}` is called.
   - **Then** HTTP 404 Not Found is returned with `folder_not_found`.

8. **Auth Gate / Security:**
   - **Given** any request is made to the folders endpoints (`POST`, `GET`, `PUT`, `DELETE`).
   - **Then** it must go through the dual-auth security gate (`Depends(get_current_operator)`).

## Tasks / Subtasks

- [x] **Domain Entity & Exceptions**
  - [x] Create `SourceFolder` domain entity in [source_folder.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/domain/entities/source_folder.py) (AC: 1)
  - [x] Add `FolderNameInUseException` in [exceptions.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/domain/exceptions.py) (AC: 2, 6)
  - [x] Add `FolderReferenceNotFoundException` (when referenced folder is missing, mapped to HTTP 422) in [exceptions.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/domain/exceptions.py) (AC: 5)
  - [x] Update `domain_exception_handler` in [app.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py):
    - [x] Map `FolderNameInUseException` to HTTP 422 with `"code": "folder_name_in_use"` (AC: 2, 6)
    - [x] Map `FolderNotFoundException` to HTTP 404 with `"code": "folder_not_found"` (AC: 5, 6, 7)
    - [x] Map `FolderReferenceNotFoundException` to HTTP 422 with `"code": "folder_not_found"` (AC: 5)
- [x] **Infrastructure / Repository**
  - [x] Create `FolderRepository` inside [folder_repository.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py) inheriting from `BaseRepository` (AC: 1)
  - [x] Implement `get_folder_by_id(id)` returning folder domain entity (AC: 5)
  - [x] Implement `get_folder_by_name(name)` supporting case-insensitive checks (AC: 2, 4, 6)
  - [x] Implement `add_folder(folder)` saving a new folder mapped to document (AC: 1)
  - [x] Implement `update_folder(folder)` replacing the folder document (AC: 6)
  - [x] Implement `delete_folder(id)` deleting the folder and updating all referencing sources' `folder_id` to `None` in the `sources` collection (AC: 7)
  - [x] Implement `list_folders_with_source_count(name_filter)` using a MongoDB aggregation pipeline (`$lookup` and `$size`) to fetch folders with pre-calculated `source_count`, sorted by name ascending (AC: 3, 4)
- [x] **Use Cases**
  - [x] Implement `CreateFolder` use case in `application/folders/create_folder.py` checking case-insensitive name uniqueness and logging `folder_created` (AC: 1, 2)
  - [x] Implement `ListFolders` use case in `application/folders/list_folders.py` aggregating folder list with `source_count` (AC: 3, 4)
  - [x] Implement `GetFolder` use case in `application/folders/get_folder.py` supporting optional sources list loading (AC: 5)
  - [x] Implement `RenameFolder` (or `UpdateFolder`) use case in `application/folders/rename_folder.py` checking name uniqueness (excluding the current folder ID) and logging `folder_renamed` (AC: 6)
  - [x] Implement `DeleteFolder` use case in `application/folders/delete_folder.py` executing folder removal, source disassociation, and logging `folder_deleted` (AC: 7)
- [x] **API Schemas & Routers**
  - [x] Create schemas in [folder.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/schemas/folder.py):
    - [x] `FolderCreateRequest` (required `name`)
    - [x] `FolderUpdateRequest` (required `name`)
    - [x] `FolderResponse` (inheriting `MongoBaseModel`, with fields `name`, `created_at`, `updated_at`, `source_count`)
    - [x] `FolderDetailsResponse` (inheriting `FolderResponse`, with optional `sources` list)
  - [x] Implement `POST /api/v1/folders` in [folders.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py) (AC: 1, 2, 8)
  - [x] Implement `GET /api/v1/folders` in [folders.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py) (AC: 3, 4, 8)
  - [x] Implement `GET /api/v1/folders/{id}` in [folders.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py) (AC: 5, 8)
  - [x] Implement `PUT /api/v1/folders/{id}` in [folders.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py) (AC: 6, 8)
  - [x] Implement `DELETE /api/v1/folders/{id}` in [folders.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/api/routers/folders.py) (AC: 7, 8)
  - [x] Register the new router in [app.py](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py) (AC: 1-8)
- [x] **Verification & Testing**
  - [x] Write unit tests for `FolderRepository` under `tests/infrastructure/mongo/test_folder_repository.py` (AC: 1-7)
  - [x] Write integration router tests under `tests/api/test_folders.py` verifying all success, duplication, disassociation, self-rename, 404, 422 and security scenarios (AC: 1-8)

## Dev Notes

### Architecture & Implementation Guardrails

- **Clean Architecture & Separation of Concerns:**
  - `SourceFolder` domain entity must be a pure Python dataclass in `domain/entities/source_folder.py`, importing nothing from MongoDB or FastAPI frameworks.
  - Keep use cases focused on domain logic. Inject the `FolderRepository` (and `SourceRepository` if needed) into use cases via FastAPI dependencies.
  - The API router is the translation boundary. Map custom exceptions (`FolderNameInUseException`, `FolderNotFoundException`, `FolderReferenceNotFoundException`) to standard HTTP responses in the FastAPI app error handler (`app.py`).
- **Data Consistency Rules & Serializations:**
  - Use collection constant `SOURCE_FOLDERS` from `api/schemas/base.py`.
  - Save folders with timestamps as UTC ISO 8601 strings (e.g., `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`).
  - Use `MongoBaseModel` as the Pydantic schema base to serialize `_id` into a 24-character string `id`.
- **Database Index Dependency:**
  - Verify that the unique index on `name` exists for `SOURCE_FOLDERS` as declared in `app.py` lifespan (`await mongo_client.db[SOURCE_FOLDERS].create_index("name", unique=True, background=True)`).
- **Disassociation Handling on Delete:**
  - When a folder is deleted, all sources referencing it must be disassociated. In the delete use case or repository method, execute:
    ```python
    await self.db[SOURCES].update_many(
        {"folder_id": ObjectId(folder_id)},
        {"$set": {"folder_id": None}}
    )
    ```
    This ensures that when a folder is removed, its sources have `folder_id` set to `null` instead of dangling.
- **Double Name Check:**
  - When renaming a folder via PUT, ensure that if the name matches another existing folder, the `FolderNameInUseException` is raised. Allow renaming a folder to its *own* current name without triggering a name-in-use error. Exclude the current ID: `{"name": name, "_id": {"$ne": ObjectId(folder_id)}}`.
- **Case-Insensitive Uniqueness Enforced:**
  - To prevent duplicates like `"crypto"` and `"Crypto"`, the name existence checks must query MongoDB case-insensitively using collation or regular expressions, i.e. `{"name": {"$regex": f"^{name}$", "$options": "i"}}` or case-insensitive query matching.
- **Efficient N+1 Queries Prevention:**
  - When listing folders, use a MongoDB aggregate pipeline on `source_folders` collection with `$lookup` to join `sources` collection matching `folder_id` with `_id`, projecting `$size` of matches as `source_count`.
- **API Security:**
  - All router endpoints in `folders.py` must declare a dependency on `get_current_operator` to protect folders CRUD.

### References

- Cite: plural resource paths mapping standard [architecture.md:L560-571](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L560-L571)
- Cite: error response envelope format [architecture.md:L348-354](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L348-L354)
- Cite: Clean Architecture backend structure [architecture.md:L621-648](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L621-L648)
- Cite: Folder rename duplicate-name decision [architecture.md:L105](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L105)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Debug Log References

- Fixed aggregate pipeline unit test mock: collection.aggregate returns cursor synchronously in Motor, so we replaced AsyncMock return value with MagicMock.

### Completion Notes List

- Implemented SourceFolder domain entity.
- Implemented FolderRepository with aggregate queries for source counts.
- Implemented CreateFolder, ListFolders, GetFolder, RenameFolder, and DeleteFolder use cases.
- Implemented API schemas for folders.
- Implemented folders.py API router with standard security and exception handling.
- Registered folder.py schemas, providers, and registered folders router in app.py.
- Wrote extensive Unit and Integration API test suites. All 105 tests pass successfully.

### File List

- forward-bot/src/forward_bot/domain/entities/source_folder.py
- forward-bot/src/forward_bot/domain/exceptions.py
- forward-bot/src/forward_bot/infrastructure/mongo/repositories/source_repository.py
- forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
- forward-bot/src/forward_bot/application/folders/create_folder.py
- forward-bot/src/forward_bot/application/folders/get_folder.py
- forward-bot/src/forward_bot/application/folders/list_folders.py
- forward-bot/src/forward_bot/application/folders/rename_folder.py
- forward-bot/src/forward_bot/application/folders/delete_folder.py
- forward-bot/src/forward_bot/api/schemas/folder.py
- forward-bot/src/forward_bot/api/dependencies/providers.py
- forward-bot/src/forward_bot/api/routers/folders.py
- forward-bot/src/forward_bot/app.py
- forward-bot/src/forward_bot/application/sources/update_source.py
- forward-bot/tests/infrastructure/mongo/test_folder_repository.py
- forward-bot/tests/api/test_folders.py
