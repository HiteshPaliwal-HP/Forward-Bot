---
baseline_commit: f76ee90d1996024b709c6c78e3c1b50e25acccd7
---
# Story 6.5: Sources List (S4), Source Edit (S5) & Folder Modals (S6)

Status: done

## Story

As a **Channel Operator**,
I want to register and manage Telegram sources with folder organization, with clear feedback when a source is already in use by rules,
So that I can maintain an organized source catalog and understand the impact of removing a source.

## Acceptance Criteria

1. **Sources List Page — Left Rail + Table (S4):**
   - **Given** the operator navigates to `/sources` (S4).
   - **When** the page loads.
   - **Then** `GET /api/v1/sources?page=1&page_size=50` and `GET /api/v1/folders` are fetched with `staleTime: 60_000`.
   - **And** the left rail renders folder tabs: "All" (default), then one tab per folder (showing `source_count`), then an "Ungrouped" bucket (sources with `folder_id = null`).
   - **And** clicking a folder tab re-fetches sources filtered by that folder (use `folder_id=<id>` param); clicking "Ungrouped" uses `folder_id=null`; clicking "All" fetches without folder filter.
   - **And** each source row in the table shows: `display_name`, Telegram ID/username (`telegram_username` or `telegram_id`), folder badge (folder name or "–"), active rule count, Edit action (→ `/sources/{id}/edit`), Delete action (triggers delete flow).
   - **And** the active rule count is read from the `rules.list()` TanStack Query cache if available (otherwise displayed as `–`), without triggering separate API queries.
   - **And** pagination controls appear when `total > 50`.

2. **Sources List — Folder Management in Left Rail (S4/S6):**
   - **Given** the left rail is rendered.
   - **When** the operator clicks "+ New Folder".
   - **Then** the FolderModal opens in "create" mode.
   - **And** each folder tab in the left rail has a rename icon (pencil) and a delete icon (trash) that open the FolderModal in "rename" or "delete" mode respectively.

3. **Sources List — Source Delete with 409 Guard (S4/S5):**
   - **Given** the operator clicks Delete on a source row.
   - **When** `DELETE /api/v1/sources/{id}` is called.
   - **Then** on HTTP 204, the source row is removed and the sources list cache is invalidated.
   - **And** on HTTP 409 (source in use), a shadcn `AlertDialog` appears listing the conflicting rule IDs with "Jump to rule" links that navigate to `/forwards/{rule_id}/edit`; the delete is not performed.
   - **And** the rule details (ID and destination channel name) shown in the dialog are fetched via `GET /api/v1/rules?source_id={source_id}` upon receiving the 409 error.
   - **And** the 409 error body format is: `{"error": {"code": "source_in_use", "message": "Source {id} is referenced by {n} rules."}}` — parse message or look up rules dynamically.

4. **Source Create / Edit Form (S5):**
   - **Given** the operator navigates to `/sources/new` or `/sources/{id}/edit`.
   - **When** the form renders.
   - **Then** for edit mode, `GET /api/v1/sources/{id}` is fetched with `staleTime: 0` (always fresh).
   - **And** for new mode, all fields are blank with defaults.
   - **And** the page title shows "Register Source" for new and "Edit Source" for existing.
   - **And** fields shown: `telegram_reference` (Telegram username or numeric ID input — new mode only; hidden/read-only in edit mode since the ID is resolved at creation), `display_name` (text input), `type` (radio: `channel` | `group` — edit mode only; auto-resolved on create), `folder_id` (dropdown populated from `GET /api/v1/folders`).

5. **Source Form — Resolved-ID Echo (S5, UX-DR16):**
   - **Given** the operator is in source edit mode OR has just successfully saved a new source.
   - **When** the page renders or save completes.
   - **Then** a read-only line appears below the Display Name field showing the resolved numeric Telegram ID: `"Resolved ID: {telegram_id}"` in `text-muted-foreground`.
   - **Note**: The `/resolve` endpoint does NOT exist on the backend. For creation, register first via POST, then echo the resolved numeric ID from the creation response.

6. **Source Form — Submission (S5):**
   - **Given** the operator fills the form and clicks Save.
   - **When** validation passes (all required fields present).
   - **Then** for **new** source: `POST /api/v1/sources` is called with `{ telegram_reference, display_name }`. If a `folder_id` is selected in the UI, a subsequent `PATCH /api/v1/sources/{id}` with `{ folder_id }` is immediately sent. On success, redirect to `/sources` and show `sonner` toast containing the resolved Telegram ID.
   - **And** for **existing** source: `PUT /api/v1/sources/{id}` is called with `{ display_name, type, folder_id, telegram_username }` payload; on HTTP 200 redirect to `/sources` and invalidate sources list and detail caches.
   - **And** on HTTP 422, field-level errors from the API are displayed inline next to the offending fields.
   - **And** on any other error, a destructive toast appears: `"Save failed — please try again."`.

7. **Folder Modal — Create (S6, UX-DR18):**
   - **Given** the operator clicks "+ New Folder" in the left rail.
   - **When** the modal opens.
   - **Then** a custom `Dialog` renders with a single `folder_name` text input, "Cancel" and "Create" buttons.
   - **And** as the operator types (debounced 300ms), `GET /api/v1/folders?name={typed_name}` is called; if any result has `name` matching exactly (case-insensitive) and is not the current folder, inline error: `"Folder name in use: {name}."` below the input; "Create" button disabled while error present.
   - **And** on submit, `POST /api/v1/folders` is called with `{ name: folder_name }`; on HTTP 201 the modal closes and folders list cache is invalidated.
   - **And** on HTTP 422 (folder name in use from API), the inline error is shown.

8. **Folder Modal — Rename (S6, UX-DR18):**
   - **Given** the operator clicks the rename icon on a folder tab.
   - **When** the modal opens.
   - **Then** the `folder_name` field is pre-populated with the current folder name; the title is "Rename Folder".
   - **And** same debounced duplicate-name validation as create, but the current folder's own name does NOT trigger the duplicate error (self-rename allowed).
   - **And** on submit, `PUT /api/v1/folders/{id}` is called with `{ name: new_name }`; on success the modal closes and folders cache is invalidated.

9. **Folder Modal — Delete (S6):**
   - **Given** the operator clicks the delete icon on a folder tab.
   - **When** the action fires.
   - **Then** a custom `AlertDialog` confirmation appears listing the count of sources that will be unassigned: `"Delete folder '{name}'? {N} source(s) will be moved to Ungrouped."` (where `N` is the `source_count` of the folder).
   - **And** on confirm, `DELETE /api/v1/folders/{id}` is called; on HTTP 204 the folders and sources list caches are invalidated.

10. **API Modules:**
    - **Given** the sources and folders screens require data.
    - **When** `web/src/api/sources.ts` and `web/src/api/folders.ts` are inspected.
    - **Then** `sources.ts` is extended from the Story 6-4 stub to export:
      - `fetchSources(params?)` — already exists, keep backward-compatible.
      - `fetchSource(id: string)` — `GET /api/v1/sources/{id}`.
      - `createSource(payload: SourceCreatePayload)` — `POST /api/v1/sources`.
      - `updateSource(id: string, payload: SourceUpdatePayload)` — `PUT /api/v1/sources/{id}`.
      - `patchSource(id: string, payload: SourcePatchPayload)` — `PATCH /api/v1/sources/{id}`.
      - `deleteSource(id: string)` — `DELETE /api/v1/sources/{id}`.
    - **And** `web/src/api/folders.ts` [NEW] exports:
      - `fetchFolders(params?)` — `GET /api/v1/folders`.
      - `fetchFolder(id: string, params?)` — `GET /api/v1/folders/{id}`.
      - `createFolder(payload: { name: string })` — `POST /api/v1/folders`.
      - `renameFolder(id: string, payload: { name: string })` — `PUT /api/v1/folders/{id}`.
      - `deleteFolder(id: string)` — `DELETE /api/v1/folders/{id}`.
    - **And** `web/src/api/rules.ts` is extended to support filtering by `source_id?: string` and `folder_id?: string` in `fetchRules`.

11. **Route Update:**
    - **Given** the current routes for sources exist.
    - **When** the routes are inspected.
    - **Then** the route `sources/:id` (currently `/sources/:id`) must be updated to `/sources/new` (literal) + `/sources/:id/edit` pattern — following the exact same pattern as `forwards/new` + `forwards/:id/edit` in Story 6-4.
    - **And** the `folders/:id` route is removed from routes; FolderModal is rendered as a component within `SourcesList.tsx` via state.

12. **Build Verification:**
    - **Given** all screens are implemented.
    - **When** `npm run build` is executed in `web/`.
    - **Then** the build completes with zero TypeScript errors.

---

## Tasks / Subtasks

- [x] **1. Extend `web/src/api/sources.ts`** (AC: 10)
  - [x] Add TypeScript interfaces: `SourceCreatePayload`, `SourceUpdatePayload`, `SourcePatchPayload`
  - [x] Add `fetchSource(id)`, `createSource(payload)`, `updateSource(id, payload)`, `patchSource(id, payload)`, `deleteSource(id)`

- [x] **2. Create `web/src/api/folders.ts`** (AC: 10)
  - [x] Add TypeScript interfaces: `FolderItem`, `FolderDetailsResponse`
  - [x] Export `foldersApi.fetchFolders(params?)`, `foldersApi.fetchFolder(id, params?)`, `createFolder(payload)`, `renameFolder(id, payload)`, `deleteFolder(id)`

- [x] **3. Update `web/src/api/rules.ts`** (AC: 10)
  - [x] Extend query params interface for `fetchRules` to accept `source_id?: string` and `folder_id?: string`

- [x] **4. Create custom `web/src/components/ui/dialog.tsx`** (AC: 7, 8, 9)
  - [x] Build a lightweight custom `Dialog` overlay component with backdrop and close button, exporting `Dialog`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, and `DialogDescription`

- [x] **5. Update `web/src/lib/queryKeys.ts`** (AC: 10)
  - [x] Add `folders.detail: (id: string) => ["folders", "detail", id] as const`

- [x] **6. Update `web/src/routes/index.tsx`** (AC: 11)
  - [x] Add `<Route path="sources/new" element={<SourceEdit />} />` BEFORE `<Route path="sources/:id/edit" ...>`
  - [x] Rename existing `sources/:id` route to `sources/:id/edit`
  - [x] Remove `folders/:id` route (FolderModal is now a component within SourcesList)

- [x] **7. Implement `web/src/pages/SourcesList.tsx`** (AC: 1, 2, 3)
  - [x] Fetch sources list + folders list
  - [x] Render left rail with folder tabs (All, named folders with source_count, Ungrouped)
  - [x] Folder tab click updates source filter
  - [x] "+ New Folder" button opens FolderModal (create mode)
  - [x] Rename + Delete icons on each folder tab open FolderModal (rename/delete modes)
  - [x] Render source table with columns: display_name, telegram ID/username, folder badge, active rule count, Edit, Delete actions
  - [x] Read active rule count from cached rules list or show `–`
  - [x] Implement delete source with 409 guard: call `rulesApi.fetchRules({ source_id })` to find conflicting rules and display their IDs and names with links in an AlertDialog
  - [x] Implement pagination controls
  - [x] Handle redirect resolved-ID echo toast message on mount if passed in router state

- [x] **8. Implement `web/src/pages/SourceEdit.tsx`** (AC: 4, 5, 6)
  - [x] Detect new vs. edit mode from route params
  - [x] Fetch source data for edit mode; show loading skeleton
  - [x] Render form fields: telegram_reference (new only), display_name, type radio (edit only), folder_id dropdown
  - [x] Display resolved numeric Telegram ID below display name (read-only)
  - [x] Wire form submission:
    - [x] New mode: `POST /api/v1/sources` first. If successful and a folder was selected, `PATCH /api/v1/sources/{id}` with `folder_id`.
    - [x] Edit mode: `PUT /api/v1/sources/{id}`
  - [x] Redirect to `/sources` with resolved Telegram ID passed in router state upon creation
  - [x] Handle FastAPI 422 errors inline
  - [x] Handle other errors with toast

- [x] **9. Implement `web/src/components/FolderModal.tsx`** (AC: 7, 8, 9)
  - [x] Create `FolderModal` dialog component accepting props: `mode: "create" | "rename" | "delete"`, `folder?: FolderItem`, `onClose: () => void`, `onSuccess: () => void`
  - [x] Implement create form with debounced 300ms duplicate-name validation
  - [x] Implement rename form with same validation (exclude current folder from duplicate check)
  - [x] Implement delete confirmation (custom AlertDialog showing source count of folder)

- [x] **10. Verify Build** (AC: 12)
  - [x] Run `npm run build` in `web/` — must complete with zero TypeScript errors

---

## Dev Notes

### ⚠️ CRITICAL: `/sources/resolve/{identifier}` Backend Endpoint Does NOT Exist

The epics spec mentions a `GET /api/v1/sources/resolve/{identifier}` endpoint for live resolution during source creation. **This endpoint is NOT implemented** in the backend.

**Correct approach:** Display the resolved `telegram_id` only **after a successful `POST /api/v1/sources`** — the API response includes `telegram_id`. Show this on the redirect success toast, and below the display name in edit mode.

### ⚠️ CRITICAL: Source Registration Inline Folder Assignment (Two-step flow)

Because the backend `POST /api/v1/sources` accepts only `{ telegram_reference, display_name }`, assigning a folder at creation requires a two-step flow in `SourceEdit.tsx`:
1. Submit POST request to `/api/v1/sources` to register the source.
2. If successful and the user selected a folder, immediately send a `PATCH /api/v1/sources/{id}` containing `{ folder_id }`.
3. If the PATCH fails, handle it gracefully by showing a warning toast and continuing with the redirect.

### ⚠️ CRITICAL: Route Pattern — `/sources/new` Must Come Before `/sources/:id/edit`

Follow the exact same pattern established in Story 6-4 for forwards:

```tsx
// web/src/routes/index.tsx — CORRECT order:
<Route path="sources/new" element={<SourceEdit />} />       {/* literal "new" first */}
<Route path="sources/:id/edit" element={<SourceEdit />} /> {/* then param-based */}
```

In `SourceEdit.tsx`:
```tsx
const { id } = useParams<{ id: string }>();
const isNewSource = !id;  // id is undefined on the /sources/new route
```

### ⚠️ CRITICAL: FolderModal Location — Component, Not Page

`FolderModal` must be implemented as a component at `web/src/components/FolderModal.tsx` and opened inside `SourcesList.tsx` via state. Remove the old route and stub at `pages/FolderModal.tsx`.

### ⚡ ENHANCEMENT: Active Rule Count Client-Side Cache Counting

To display the active rule count without making separate API requests:
```typescript
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";

const queryClient = useQueryClient();
const rulesCache = queryClient.getQueryData<RulesListResponse>(queryKeys.rules.list());

// For a given source in the table:
const getActiveRuleCount = (sourceId: string) => {
  if (!rulesCache) return "–";
  const count = rulesCache.items.filter(
    (rule) => rule.source_id === sourceId && rule.is_active
  ).length;
  return count.toString();
};
```

### ⚡ ENHANCEMENT: Querying Conflicting Rules on 409 Delete Conflict

If a delete call returns a 409 error:
1. Make an API call to `rulesApi.fetchRules({ source_id: sourceId })` to fetch all rules referencing this source.
2. Store the rule items in state.
3. Show the `AlertDialog` rendering "Jump to rule" links for each of these rules using `/forwards/${rule.id}/edit`.

### API Endpoint Reference

| Endpoint | Method | Description | Response Shape |
|---|---|---|---|
| `GET /api/v1/sources` | GET | List sources (paged) | `{ items: SourceItem[], total: N, page: N, page_size: N }` |
| `GET /api/v1/sources/{id}` | GET | Get single source | `SourceItem` |
| `POST /api/v1/sources` | POST | Register source | `SourceItem` (HTTP 201) — body: `{ telegram_reference, display_name }` |
| `PUT /api/v1/sources/{id}` | PUT | Full update source | `SourceItem` (HTTP 200) — body: `{ display_name, type, folder_id, telegram_username }` |
| `PATCH /api/v1/sources/{id}` | PATCH | Partial update source | `SourceItem` (HTTP 200) |
| `DELETE /api/v1/sources/{id}` | DELETE | Delete source | HTTP 204 No Content OR HTTP 409 if in use |
| `GET /api/v1/folders` | GET | List folders (optionally `?name=` for dup check) | `FolderItem[]` |
| `GET /api/v1/folders/{id}` | GET | Get folder details | `FolderDetailsResponse` (with sources if `?include=sources`) |
| `POST /api/v1/folders` | POST | Create folder | `FolderItem` (HTTP 201) — body: `{ name }` |
| `PUT /api/v1/folders/{id}` | PUT | Rename folder | `FolderItem` (HTTP 200) — body: `{ name }` |
| `DELETE /api/v1/folders/{id}` | DELETE | Delete folder | HTTP 204 No Content |

### TypeScript Interfaces

```typescript
// web/src/api/sources.ts — ADDITIONS to existing file

export interface SourceCreatePayload {
  telegram_reference: string;  // Telegram username (@handle) or numeric ID
  display_name: string;
}

export interface SourceUpdatePayload {
  display_name: string;
  type: "channel" | "group";
  folder_id: string | null;
  telegram_username: string | null;
}

export interface SourcePatchPayload {
  display_name?: string;
  type?: "channel" | "group";
  folder_id?: string | null;
  telegram_username?: string | null;
}
```

```typescript
// web/src/api/folders.ts — NEW FILE

import { apiClient } from "./client";
import { SourceItem } from "./sources";

export interface FolderItem {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  source_count: number;
}

export interface FolderDetailsResponse extends FolderItem {
  sources: SourceItem[] | null;
}

export const foldersApi = {
  fetchFolders: async (params?: { name?: string }): Promise<FolderItem[]> => {
    const { data } = await apiClient.get<FolderItem[]>("/folders", { params });
    return data;
  },

  fetchFolder: async (id: string, params?: { include?: string }): Promise<FolderDetailsResponse> => {
    const { data } = await apiClient.get<FolderDetailsResponse>(`/folders/${id}`, { params });
    return data;
  },

  createFolder: async (payload: { name: string }): Promise<FolderItem> => {
    const { data } = await apiClient.post<FolderItem>("/folders", payload);
    return data;
  },

  renameFolder: async (id: string, payload: { name: string }): Promise<FolderItem> => {
    const { data } = await apiClient.put<FolderItem>(`/folders/${id}`, payload);
    return data;
  },

  deleteFolder: async (id: string): Promise<void> => {
    await apiClient.delete(`/folders/${id}`);
  },
};
```

```typescript
// web/src/api/rules.ts — UPDATE fetchRules signature to accept optional filters
  fetchRules: async (params?: { 
    page?: number; 
    page_size?: number; 
    is_active?: boolean;
    source_id?: string;
    folder_id?: string;
  }): Promise<RulesListResponse> => {
    const { data } = await apiClient.get<RulesListResponse>("/rules", { params });
    return data;
  },
```

```tsx
// web/src/components/ui/dialog.tsx — NEW FILE
import React, { useEffect } from "react";
import { X } from "lucide-react";

interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div 
        className="fixed inset-0 bg-black/55 backdrop-blur-xs transition-opacity duration-200" 
        onClick={() => onOpenChange?.(false)} 
      />
      <div className="relative bg-card border border-border rounded-lg shadow-lg max-w-lg w-full p-6 animate-in fade-in zoom-in-95 duration-200 z-10 flex flex-col">
        <button
          onClick={() => onOpenChange?.(false)}
          className="absolute right-4 top-4 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>
        {children}
      </div>
    </div>
  );
}

export function DialogContent({ children }: { children: React.ReactNode }) {
  return <div className="space-y-4">{children}</div>;
}

export function DialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col space-y-1.5 text-center sm:text-left">{children}</div>;
}

export function DialogFooter({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 space-y-2 space-y-reverse sm:space-y-0 mt-4">{children}</div>;
}

export function DialogTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-semibold text-foreground">{children}</h2>;
}

export function DialogDescription({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}
```

### Form State — No react-hook-form

Use controlled component states (`useState`) for all form fields. Use `sonner` `toast` library directly:
```typescript
import { toast } from "sonner";
toast.success("Source saved.");
toast.error("Save failed.");
```

### TypeScript Strict Mode

- No `any` types — use explicit interfaces or `unknown`.
- All API and helper functions must have explicit return types.
- `npm run build` must compile clean with zero warnings.

---

## Previous Story Learnings

- **Route pattern hierarchy:** Route literals like `sources/new` must be declared before parameterized routes like `sources/:id/edit` in `AppRoutes`.
- **Axios `apiClient`:** Always import `apiClient` from `@/api/client` (preset with `/api/v1` prefix).
- **Tailwind v4 color styles:** Colors map to CSS variables natively (e.g. `text-muted-foreground` maps to `var(--muted-foreground)`). Avoid referencing raw color names or old utility prefixes in Tailwind class definitions.

---

## Git Intelligence

```
f76ee90  6-3 story completed  (ForwardsList + ForwardEdit full S2/S3 screens; sources.ts stub created)
17d3458  story 6-2 done  (Shared UI component library — 7 components in components/shared/)
38a29fe  6-1 story done  (React SPA foundation, brand tokens, auth, layout)
```

---

## Architecture Notes

- Sources and Folders lists `staleTime: 60_000` (60 seconds).
- Source Edit mode details query `staleTime: 0` (always fresh).
- `GET /api/v1/folders` returns a flat array of folders (`FolderItem[]`), not a paginated list.

---

## Project Structure Notes

- Frontend project root: `web/`
- Story files: `_bmad-output/implementation-artifacts/`

### Files to Create

```
web/src/
├── api/
│   └── folders.ts       ← NEW: foldersApi functions
└── components/
    ├── FolderModal.tsx  ← NEW: Dialog component for folder CRUD
    └── ui/
        └── dialog.tsx   ← NEW: custom Dialog UI primitives
```

### Files to Modify

```
web/src/
├── api/
│   ├── sources.ts       ← EXTEND: CRUD payloads and methods
│   └── rules.ts         ← EXTEND: fetchRules parameters
├── lib/
│   └── queryKeys.ts     ← EXTEND: add folders.detail key
├── routes/
│   └── index.tsx        ← MODIFY: route changes for sources and folders
└── pages/
    ├── SourcesList.tsx  ← REPLACE: S4 list view + left rail folders
    ├── SourceEdit.tsx   ← REPLACE: S5 creation and modification form
    └── FolderModal.tsx  ← DELETE: replaced by component
```

---

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Completion Notes List

- Implemented the core components for S4 (Sources List), S5 (Source Edit Form), and S6 (Folder Management Modals).
- Extended `/sources` layout to include a dynamic left rail displaying folders (including source counts) and an "Ungrouped" bucket.
- Wrote lightweight, accessible `Dialog` and updated `AlertDialog` UI primitives under `web/src/components/ui/`.
- Created a modular `FolderModal` component that handles creation, renaming (with debounced duplicate name check), and deletion (warning the user with actual source counts to be moved).
- Configured registration flow for sources to resolve numeric IDs and perform a two-step post-then-patch folder assignment when necessary.
- Enhanced the sources table to display active rule count reactively read from the TanStack Query rules cache without sending duplicate requests.
- Integrated a 409 conflict check on source deletion, querying rules matching the source ID and displaying rule details with "Jump to rule" configuration links.
- Verified build and compilation: `npm run build` completes successfully with zero TypeScript compilation errors.

### File List

- [web/src/api/sources.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/sources.ts)
- [web/src/api/folders.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/folders.ts)
- [web/src/api/rules.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/rules.ts)
- [web/src/lib/queryKeys.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/lib/queryKeys.ts)
- [web/src/routes/index.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/routes/index.tsx)
- [web/src/components/ui/dialog.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/ui/dialog.tsx)
- [web/src/components/ui/alert-dialog.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/ui/alert-dialog.tsx)
- [web/src/components/FolderModal.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/FolderModal.tsx)
- [web/src/pages/SourcesList.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/SourcesList.tsx)
- [web/src/pages/SourceEdit.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/SourceEdit.tsx)

### Review Findings

✅ Clean review — all layers passed.
