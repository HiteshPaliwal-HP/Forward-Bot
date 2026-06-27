---
baseline_commit: f76ee90d1996024b709c6c78e3c1b50e25acccd7
---
# Story 6.4: Forwards List (S2) & Forward Edit (S3) Screens

Status: done

## Story

As a **Channel Operator**,
I want to view all forwarding rules in a filterable table, enable/disable them individually or in bulk, and edit every aspect of a rule through a multi-panel form,
so that I can manage my forwarding configuration efficiently without using the raw API.

## Acceptance Criteria

1. **Forwards List Page — Rule Table (S2):**
   - **Given** the operator navigates to `/forwards` (S2).
   - **When** the page loads.
   - **Then** `GET /api/v1/rules?page=1&page_size=50` is fetched with `staleTime: 30_000`.
   - **And** the table renders columns: Source (display_name resolved from source_id), Destination (`destination_channel`), Status (`StatusPill` — `active` or `inactive`), FilterIconRow (active filters including timezone, sampling, media type filters, and keywords), Actions (Edit button → navigates to `/forwards/{id}/edit`, Enable/Disable toggle button).
   - **And** pagination controls appear when `total > 50` (Previous / Next buttons or page number indicators).

2. **Forwards List — Optimistic Toggle (S2):**
   - **Given** the operator clicks the Enable/Disable toggle on a rule row.
   - **When** the toggle fires.
   - **Then** an optimistic update immediately flips the `is_active` state in the UI (row shows the new status without waiting for network).
   - **And** `POST /api/v1/rules/{id}/enable` or `POST /api/v1/rules/{id}/disable` is called based on the current state.
   - **And** on success the TanStack Query cache for `queryKeys.rules.list()` is invalidated to refetch fresh data.
   - **And** on failure (4xx/5xx) the optimistic update is rolled back to the original state and a destructive toast appears: `"Toggle failed: <reason>."`.

3. **Forwards List — Bulk Action Bar (S2):**
   - **Given** the operator checks one or more rule checkboxes.
   - **When** any checkbox is checked.
   - **Then** a sticky bulk action bar slides in at the bottom of the page with: selected count indicator, "Enable selected" button, "Disable selected" button, "Delete selected" button.
   - **And** clicking "Delete selected" shows a confirmation dialog (shadcn `AlertDialog`) listing the count of rules to be deleted before proceeding.
   - **And** clicking "Disable selected" shows a confirmation dialog (shadcn `AlertDialog`) listing the count of rules to be disabled ONLY when 5 or more rules are selected.
   - **And** bulk operations execute sequentially (one-by-one API calls) with a progress toast tracking completion (e.g., "3 of 5 complete").
   - **And** when all bulk operations complete, a summary toast appears. If any operations failed, the toast is destructive and persists until dismissed, with the count of failures shown and a "[Show errors]" action that expands an inline sub-panel displaying the specific errors.

4. **Forward Create / Edit Form — Page Shell (S3):**
   - **Given** the operator navigates to `/forwards/new` or `/forwards/:id/edit` (S3).
   - **When** the form renders.
   - **Then** for the edit route, `GET /api/v1/rules/{id}` is fetched with `staleTime: 0` (always fresh on mount).
   - **And** the page title shows "Create Forward" for new rules and "Edit Forward" for existing ones.
   - **And** if `is_active=false` on an existing rule, the `ActivationBanner` from `components/shared` is rendered at the top of the form with `isActive={false}` and `onActivate()` wired to call `POST /api/v1/rules/{id}/enable` + invalidate rules cache.
   - **And** `Cmd/Ctrl+Enter` keyboard shortcut saves the form (submits as if the Save button was clicked).
   - **And** `Esc` closes any open sub-modal / dropdown within the form, and exits inline replacement rule edit mode.

5. **Forward Form — Seven CollapsiblePanel Sections (S3):**
   - **Given** the form renders.
   - **When** the user views the panels.
   - **Then** exactly 7 `CollapsiblePanel` sections appear, all collapsed by default unless specified by the URL query parameters (e.g., `?panels=basic,transforms` which restores their expanded state, allowing multiple panels to be open simultaneously):
     1. **Basic Config** — `source_id` selector (dropdown populated from sources list), `destination_channel` text input, `media_type_filter` checkboxes (allowing selection of `text` and/or `photo`), and `is_active` toggle switch.
     2. **Time Window** — `timezone` text input (IANA name), `days_of_week` checkboxes (MON–SUN), `start_time` and `end_time` time inputs; entire block optional (null = no restriction).
     3. **Sampling** — `sampling.n` numeric input (≥1); label shows "Forward every Nth message"; value 1 = forward all.
     4. **Keyword Filters** — `keyword_match_mode` radio (literal | regex), `block_keywords` textarea (one per line), `allow_keywords` textarea (one per line).
     5. **Content Transforms** —
        - **Text Simplification:** `remove_links` toggle, `remove_hashtags` toggle, `remove_mentions` toggle.
        - **Media Handling:** `forward_media` radio (forward | ignore | caption_only).
        - **Media Replacement (Shown only if `forward_media` is `forward` or `caption_only`):** `media_replacement.enabled` toggle. When enabled, displays a text input for `media_replacement.replacement_image_path` with a "Browse" button, and a radio for `media_replacement.replacement_caption_mode` (use_replacement | use_source | none). Clicking "Browse" opens a modal gallery listing files from `GET /api/v1/media/replacement-images` which populates the path on selection.
        - **Source References Auto-Replacement:** `auto_replace_source_refs.enabled` toggle. When enabled, displays `auto_replace_source_refs.replacement` text input (for destination handle/link) and `auto_replace_source_refs.replace_display_name` checkbox.
     6. **Attribution** — `attribution.enabled` toggle, `attribution.position` radio (prefix | suffix), `attribution.format` text input; live preview below the input showing rendered attribution line with sample source name substituted. Token chips (`{source_name}` and `{source_username}`) are clickable to insert at the current cursor position in the format field.
     7. **Replacement Rules** —
        - In **new rule** mode: displays "Save the forwarding rule first to configure text replacement rules."
        - In **edit rule** mode: inline CRUD table for child `replacement_rules` for this rule: columns (search_text, replacement_text, match_mode, is_active), Add / Edit / Delete actions; editing uses an inline row form; saved via `POST/PUT/DELETE /api/v1/rules/{id}/replacement-rules`.
   - **And** each panel header `summary` prop shows a brief human-readable config state (e.g., "Mon–Fri 09:00–17:00 Europe/Warsaw" for time window, "Every 2nd message" for sampling, "3 blocked / 2 allowed" for keywords, "Inactive" when the sub-config is unconfigured / default).

6. **Forward Form — Submission (S3):**
   - **Given** the operator fills the form and clicks Save.
   - **When** validation passes (all required fields present).
   - **Then** for a **new** rule: `POST /api/v1/rules` is called with the form payload; on HTTP 201 the operator is redirected to `/forwards` and the rules list cache is invalidated.
   - **And** for an **existing** rule: `PUT /api/v1/rules/{id}` is called; on HTTP 200 the operator is redirected to `/forwards` and the rules cache is invalidated.
   - **And** on HTTP 422, field-level validation errors from the API are displayed inline next to the offending fields (using the `error.response.data.detail` array from FastAPI's Pydantic validation format).
   - **And** on any other error, a destructive toast appears: `"Save failed — please try again."`.

7. **API Modules:**
   - **Given** the Forwards screens require data.
   - **When** `web/src/api/rules.ts` is inspected.
   - **Then** it is extended from the Story 6-3 stub to export all rule CRUD operations:
     - `fetchRules(params?)` — already exists, keep backward-compatible.
     - `fetchRule(id: string)` — `GET /api/v1/rules/{id}`.
     - `createRule(payload: RuleCreatePayload)` — `POST /api/v1/rules`.
     - `updateRule(id: string, payload: RuleUpdatePayload)` — `PUT /api/v1/rules/{id}`.
     - `deleteRule(id: string)` — `DELETE /api/v1/rules/{id}`.
     - `enableRule(id: string)` — `POST /api/v1/rules/{id}/enable`.
     - `disableRule(id: string)` — `POST /api/v1/rules/{id}/disable`.
   - **And** `web/src/api/rules.ts` also exports replacement rule operations:
     - `fetchReplacementRules(ruleId: string)` — `GET /api/v1/rules/{ruleId}/replacement-rules`.
     - `createReplacementRule(ruleId: string, payload)` — `POST /api/v1/rules/{ruleId}/replacement-rules`.
     - `updateReplacementRule(ruleId: string, replacementId: string, payload)` — `PUT /api/v1/rules/{ruleId}/replacement-rules/{replacementId}`.
     - `deleteReplacementRule(ruleId: string, replacementId: string)` — `DELETE /api/v1/rules/{ruleId}/replacement-rules/{replacementId}`.
   - **And** `web/src/api/sources.ts` exists and exports at minimum `fetchSources(params?)` for populating the source_id dropdown.
   - **And** `web/src/api/media.ts` already exists with `fetchReplacementImages()` — no changes needed.

8. **Query Keys:**
   - **Given** new query calls are added.
   - **When** `web/src/lib/queryKeys.ts` is inspected.
   - **Then** the following key entries exist (add only missing ones):
     - `queryKeys.rules.list()` → `["rules", "list"]`
     - `queryKeys.rules.detail(id)` → `["rules", "detail", id]`
     - `queryKeys.sources.list()` → `["sources", "list"]`
     - `queryKeys.rules.replacements(ruleId)` → `["rules", "replacements", ruleId]` — **ADD this**

9. **Route Update:**
   - **Given** the user navigates to `/forwards/new`.
   - **When** the router processes the path.
   - **Then** the `ForwardEdit` component renders (new rule mode, no `id` param).
   - **And** the route `forwards/:id` must match both `/forwards/new` AND `/forwards/{objectId}/edit`; use a query param `?new=true` OR split into two routes: `forwards/new` and `forwards/:id/edit`.
   - **Note**: The existing route `forwards/:id` must be updated to `forwards/:id/edit` and a separate `forwards/new` route added to avoid `:id` matching the literal string "new".

10. **Build Verification:**
    - **Given** all screens are implemented.
    - **When** `npm run build` is executed in `web/`.
    - **Then** the build completes with zero TypeScript errors.

---

## Tasks / Subtasks

- [x] **1. Extend `web/src/api/rules.ts`** (AC: 7)
  - [x] Add TypeScript interfaces: `ForwardingRule`, `RuleCreatePayload`, `RuleUpdatePayload`, `ReplacementRule`, `ReplacementRulePayload`
  - [x] Add `fetchRule(id)`, `createRule(payload)`, `updateRule(id, payload)`, `deleteRule(id)`, `enableRule(id)`, `disableRule(id)`
  - [x] Add replacement rule operations: `fetchReplacementRules`, `createReplacementRule`, `updateReplacementRule`, `deleteReplacementRule`

- [x] **2. Create `web/src/api/sources.ts`** (AC: 7)
  - [x] Export `SourceItem` interface (id, display_name, telegram_username, type, folder_id)
  - [x] Export `sourcesApi.fetchSources(params?)` → `GET /api/v1/sources`

- [x] **3. Update `web/src/lib/queryKeys.ts`** (AC: 8)
  - [x] Add `rules.replacements: (ruleId: string) => ["rules", "replacements", ruleId] as const`

- [x] **4. Update `web/src/routes/index.tsx`** (AC: 9)
  - [x] Add route `<Route path="forwards/new" element={<ForwardEdit />} />` BEFORE `<Route path="forwards/:id/edit" ...>`
  - [x] Rename existing `forwards/:id` route to `forwards/:id/edit`
  - [x] Update any navigation links from `/forwards/:id` to `/forwards/:id/edit`

- [x] **5. Implement `web/src/pages/ForwardsList.tsx`** (AC: 1, 2, 3)
  - [x] Fetch sources list for display_name resolution (map source_id → display_name)
  - [x] Render rule table with columns: Source, Destination, StatusPill, FilterIconRow, Actions
  - [x] Implement optimistic enable/disable toggle with rollback on error
  - [x] Implement checkbox selection state
  - [x] Implement bulk action bar (slides in when ≥1 checked)
  - [x] Implement bulk delete confirmation with shadcn AlertDialog
  - [x] Implement bulk disable confirmation with shadcn AlertDialog (when ≥5 selected)
  - [x] Implement bulk enable/disable with progress toast
  - [x] Implement bulk action summary toast with failure expander panel `[Show errors]`
  - [x] Implement pagination controls

- [x] **6. Implement `web/src/pages/ForwardEdit.tsx`** (AC: 4, 5, 6)
  - [x] Detect new vs. edit mode from route params (no `id` = new, `id` present = edit)
  - [x] Sync open collapsible panels state to URL query parameters (`?panels=...`)
  - [x] Fetch rule data for edit mode; show loading skeleton while fetching
  - [x] Render ActivationBanner for inactive existing rules
  - [x] Implement Cmd/Ctrl+Enter keyboard shortcut to submit form
  - [x] Implement Esc keyboard shortcut to close modals/popovers and exit inline rule edit mode
  - [x] Implement 7 CollapsiblePanel sections with all their fields
  - [x] Implement media type filter checkboxes in Panel 1
  - [x] Implement media replacement config & Combobox browse gallery in Panel 5
  - [x] Implement auto replace source refs config in Panel 5
  - [x] Implement attribution live preview with clickable tokens in Panel 6
  - [x] Implement replacement rules inline CRUD table in Panel 7 (conditional read-only guard in create mode)
  - [x] Wire form submission (POST for new, PUT for edit)
  - [x] Handle FastAPI 422 errors mapped to specific nested fields inline
  - [x] Handle other errors with toast

- [x] **7. Verify Build** (AC: 10)
  - [x] Run `npm run build` in `web/` — must complete with zero TypeScript errors

---

## Dev Notes

### Route Order — `/forwards/new` Must Come Before `/forwards/:id/edit`

React Router matches routes in order. The literal path `forwards/new` MUST be registered **before** `forwards/:id/edit`, otherwise the string `"new"` will be captured as the `:id` param:

```tsx
// web/src/routes/index.tsx — CORRECT order:
<Route path="forwards/new" element={<ForwardEdit />} />     {/* literal "new" first */}
<Route path="forwards/:id/edit" element={<ForwardEdit />} /> {/* then param-based */}
```

In `ForwardEdit.tsx`, detect the mode with:
```tsx
const { id } = useParams<{ id: string }>();
const isNewRule = !id;  // id is undefined on the /forwards/new route
```

### API Endpoint Reference

| Endpoint | Method | Description | Response Shape |
|---|---|---|---|
| `GET /api/v1/rules` | GET | List rules (paged) | `{ items: ForwardingRule[], total: N, page: N, page_size: N }` |
| `GET /api/v1/rules/{id}` | GET | Get single rule | `ForwardingRule` |
| `POST /api/v1/rules` | POST | Create rule | `ForwardingRule` (HTTP 201) |
| `PUT /api/v1/rules/{id}` | PUT | Full update rule | `ForwardingRule` (HTTP 200) |
| `DELETE /api/v1/rules/{id}` | DELETE | Delete rule | HTTP 204 No Content |
| `POST /api/v1/rules/{id}/enable` | POST | Enable rule | `{ ok: true }` |
| `POST /api/v1/rules/{id}/disable` | POST | Disable rule | `{ ok: true }` |
| `GET /api/v1/rules/{id}/replacement-rules` | GET | List replacement rules | `{ items: ReplacementRule[] }` |
| `POST /api/v1/rules/{id}/replacement-rules` | POST | Create replacement rule | `ReplacementRule` (HTTP 201) |
| `PUT /api/v1/rules/{id}/replacement-rules/{repId}` | PUT | Update replacement rule | `ReplacementRule` (HTTP 200) |
| `DELETE /api/v1/rules/{id}/replacement-rules/{repId}` | DELETE | Delete replacement rule | HTTP 204 |
| `GET /api/v1/sources` | GET | List sources | `{ items: SourceItem[], total: N, page: N, page_size: N }` |
| `GET /api/v1/media/replacement-images` | GET | List image filenames | `string[]` |

### ForwardingRule TypeScript Interface

Map the backend `ForwardingRuleResponse` schema exactly (snake_case, matches JSON):

```typescript
// In web/src/api/rules.ts

export interface SamplingConfig {
  n: number;
}

export interface TimeWindowConfig {
  timezone: string;
  days_of_week: string[];
  start_time: string;
  end_time: string;
}

export interface AttributionConfig {
  enabled: boolean;
  position: "prefix" | "suffix";
  format: string;
}

export interface AutoReplaceSourceRefsConfig {
  enabled: boolean;
  replacement: string | null;
  replace_display_name: boolean;
}

export interface MediaReplacementConfig {
  enabled: boolean;
  replacement_image_path: string | null;
  replacement_caption_mode: "use_replacement" | "use_source" | "none";
}

export interface ForwardingRule {
  id: string;
  source_id: string;
  destination_channel: string;
  is_active: boolean;
  keyword_match_mode: "literal" | "regex";
  block_keywords: string[];
  allow_keywords: string[];
  media_type_filter: string[];
  remove_links: boolean;
  remove_hashtags: boolean;
  remove_mentions: boolean;
  forward_media: "forward" | "ignore" | "caption_only";
  sampling: SamplingConfig;
  time_window: TimeWindowConfig | null;
  attribution: AttributionConfig;
  auto_replace_source_refs: AutoReplaceSourceRefsConfig;
  media_replacement: MediaReplacementConfig;
  created_at: string;
  updated_at: string;
}

export type RuleCreatePayload = Omit<ForwardingRule, "id" | "created_at" | "updated_at">;
export type RuleUpdatePayload = RuleCreatePayload;

export interface ReplacementRule {
  id: string;
  forwarding_rule_id: string;
  search_text: string;
  replacement_text: string;
  match_mode: "literal" | "regex";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ReplacementRulePayload = Omit<ReplacementRule, "id" | "forwarding_rule_id" | "created_at" | "updated_at">;
```

### Source Interface (for source_id dropdown)

```typescript
// In web/src/api/sources.ts
export interface SourceItem {
  id: string;
  telegram_id: number;
  telegram_username: string | null;
  display_name: string;
  type: "channel" | "group";
  folder_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourcesListResponse {
  items: SourceItem[];
  total: number;
  page: number;
  page_size: number;
}

export const sourcesApi = {
  fetchSources: async (params?: { page?: number; page_size?: number; folder_id?: string }): Promise<SourcesListResponse> => {
    const { data } = await apiClient.get<SourcesListResponse>("/sources", { params });
    return data;
  },
};
```

### ForwardsList: Optimistic Toggle Pattern

Use TanStack Query's `useMutation` with `onMutate` for optimistic updates:

```tsx
const queryClient = useQueryClient();

const toggleMutation = useMutation({
  mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
    isActive ? rulesApi.disableRule(id) : rulesApi.enableRule(id),

  onMutate: async ({ id, isActive }) => {
    await queryClient.cancelQueries({ queryKey: queryKeys.rules.list() });
    const previousData = queryClient.getQueryData(queryKeys.rules.list());

    queryClient.setQueryData(queryKeys.rules.list(), (old: RulesListResponse | undefined) => {
      if (!old) return old;
      return {
        ...old,
        items: old.items.map((rule: ForwardingRule) =>
          rule.id === id ? { ...rule, is_active: !isActive } : rule
        ),
      };
    });

    return { previousData };
  },

  onError: (_err, _vars, context) => {
    queryClient.setQueryData(queryKeys.rules.list(), context?.previousData);
    toast.error("Toggle failed — please try again.");
  },

  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
  },
});
```

### ForwardsList: Bulk Action Pattern

Handle checkbox selections and sequential bulk actions with customizable dialog triggers, live counters, and failure listings:

```tsx
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
const [bulkActionType, setBulkActionType] = useState<"enable" | "disable" | "delete" | null>(null);

const handleBulkAction = async (action: "enable" | "disable" | "delete") => {
  const ids = Array.from(selectedIds);
  let completed = 0;
  let failed = 0;
  const errors: string[] = [];

  const toastId = toast.loading(`0 of ${ids.length} complete`);

  for (const id of ids) {
    try {
      if (action === "enable") await rulesApi.enableRule(id);
      else if (action === "disable") await rulesApi.disableRule(id);
      else if (action === "delete") await rulesApi.deleteRule(id);
      completed++;
    } catch (err: any) {
      failed++;
      errors.push(`Rule ${id}: ${err.response?.data?.message || err.message}`);
    }
    toast.loading(`${completed + failed} of ${ids.length} complete`, { id: toastId });
  }

  if (failed === 0) {
    toast.success(`${completed} rules ${action}d successfully.`, { id: toastId });
  } else {
    toast.error(`${completed} succeeded, ${failed} failed.`, {
      id: toastId,
      duration: Infinity,
      description: (
        <div className="mt-2">
          <p className="font-semibold text-xs">Errors details:</p>
          <details className="cursor-pointer text-[10px] max-h-32 overflow-y-auto mt-1">
            <summary className="text-muted-foreground hover:text-foreground">Show errors</summary>
            <ul className="list-disc pl-3 mt-1 space-y-1">
              {errors.map((e, idx) => (
                <li key={idx}>{e}</li>
              ))}
            </ul>
          </details>
        </div>
      )
    });
  }

  queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
  setSelectedIds(new Set());
  setBulkActionType(null);
};
```

### ForwardEdit: Form State & Default Values

Use controlled component states (`useState` or a parent record state object) since `react-hook-form` is not installed.

Default values for a **new rule** form:
```typescript
const DEFAULT_RULE: RuleCreatePayload = {
  source_id: "",
  destination_channel: "",
  is_active: false,
  keyword_match_mode: "literal",
  block_keywords: [],
  allow_keywords: [],
  media_type_filter: ["text", "photo"],
  remove_links: false,
  remove_hashtags: false,
  remove_mentions: false,
  forward_media: "forward",
  sampling: { n: 1 },
  time_window: null,
  attribution: { enabled: false, position: "prefix", format: "From {source_name}" },
  auto_replace_source_refs: { enabled: false, replacement: null, replace_display_name: false },
  media_replacement: { enabled: false, replacement_image_path: null, replacement_caption_mode: "use_source" },
};
```

### ForwardEdit: Panel Summary Strings

Generate the summary string for each panel header dynamically:

| Panel | Summary (configured) | Summary (unconfigured/default) |
|---|---|---|
| Basic Config | `"{source_display_name} → {destination_channel} ({media_filters})"` | `"Not configured"` |
| Time Window | `"{days} {start}–{end} {tz}"` | `"Inactive"` |
| Sampling | `"Every {n}th message"` | `"Inactive (forward all)"` |
| Keyword Filters | `"{N} blocked / {M} allowed"` | `"Inactive"` |
| Content Transforms | List active transforms e.g. `"Remove links, replacement image"` | `"No transforms"` |
| Attribution | `"Prefix: {format}"` | `"Inactive"` |
| Replacement Rules | `"{N} rule(s) configured"` | `"None"` |

### ForwardEdit: Attribution Live Preview & Clicking Tokens

Render live prefix or suffix previews. Wire click handlers to token chips to append them to the current text input:

```tsx
const handleInsertToken = (token: string) => {
  // Append token to attribution format string or insert at current cursor selection
  setAttributionFormat(prev => prev + token);
};
```

### ForwardEdit: URL Panel State Synchronization

Manage the collapsible panels' open state and synchronize it with the URL parameter `?panels=basic,keywords` utilizing `useSearchParams`:

```tsx
const [searchParams, setSearchParams] = useSearchParams();
const activePanels = searchParams.get("panels")?.split(",") || [];

const togglePanel = (panelKey: string) => {
  const current = new Set(activePanels);
  if (current.has(panelKey)) {
    current.delete(panelKey);
  } else {
    current.add(panelKey);
  }
  const next = Array.from(current).join(",");
  setSearchParams(next ? { panels: next } : {}, { replace: true });
};
```

### ForwardEdit: Keyboard Shortcuts & Escape Cancellations

Listen globally for `Cmd/Ctrl+Enter` to trigger submission. Ensure `Esc` closes any active subform edit states:

```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      // Close overlay or exit inline edit row
      if (isEditingReplacementRow) {
        setIsEditingReplacementRow(false);
      }
    } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };
  document.addEventListener("keydown", handleKeyDown);
  return () => document.removeEventListener("keydown", handleKeyDown);
}, [isEditingReplacementRow, handleSubmit]);
```

### 422 Field-Level Error Handling & Nested Mapping Helper

FastAPI nested schema errors return with arrays like `["body", "sampling", "n"]`. Resolve paths to map directly to nested states:

```typescript
type ApiValidationError = { loc: string[]; msg: string; type: string };

const mapApiErrors = (detail: ApiValidationError[]): Record<string, string> => {
  const errors: Record<string, string> = {};
  for (const err of detail) {
    // Reconstruct the path skipping "body"
    const path = err.loc.filter(l => l !== "body").join(".");
    errors[path] = err.msg;
  }
  return errors;
};

// Use errors["sampling.n"] or errors["media_replacement.replacement_image_path"] in form UI
```

### Tailwind v4 Color Utilities (CRITICAL — Same as 6-3)

This project uses **Tailwind v4**. The `color-` prefix is stripped from CSS variable names in utility classes:
- `text-active` → uses `var(--color-active)` ✅
- `bg-success-bg` → uses `var(--color-success-bg)` ✅
- `bg-error-bg` → uses `var(--color-error-bg)` ✅
- `text-warning-foreground` → uses `var(--color-warning-foreground)` ✅
- `text-muted-foreground` → Tailwind built-in uses `var(--muted-foreground)` ✅

Do NOT use: `text-color-active`, `bg-color-success-bg`, etc.

### Shared Component Imports

Always import from the barrel file:
```tsx
import { CollapsiblePanel, StatusPill, FilterIconRow, ActivationBanner } from "@/components/shared";
```

### TypeScript Strict Mode

TypeScript strict mode is enabled. Rules:
- No `any` types — use `unknown` or explicit interfaces.
- `RulesListResponse.items` is currently `unknown[]` in the stub — upgrade it to `ForwardingRule[]` when extending rules.ts.
- Define explicit return types on API functions.
- The `npm run build` final verification gate must pass with zero errors.

### Sonner Toast

The project uses `sonner` for toasts:
```tsx
import { toast } from "sonner";

toast.success("Message");
toast.error("Error message");
toast.loading("In progress...");
// With ID for update:
const id = toast.loading("Starting...");
toast.success("Done!", { id });
```

### shadcn AlertDialog for Bulk Actions

Use the pre-existing shadcn `AlertDialog` component (from `components/ui/`):
```tsx
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
```

### Checking Available Packages

Before using `react-hook-form` or any other package, check `web/package.json`. If it's not installed, implement form state with controlled `useState`/inputs. Do NOT install new packages.

---

## Previous Story Intelligence

From Story 6-3 (done, commit `f76ee90`):
- **Dashboard.tsx** and **Settings.tsx** fully implemented. Pattern: `useQuery` + loading skeletons with `animate-pulse`.
- **`web/src/api/stats.ts`** created with `statsApi.fetchSummary()`.
- **`web/src/api/logs.ts`** created with `logsApi.fetchRecent(limit)`.
- **`web/src/api/rules.ts`** stub created with `rulesApi.fetchRules(params?)` → Story 6-4 extends this substantially.
- **`web/src/api/health.ts`** extended with `fetchHealth()` using raw `axios` (no `/api/v1` prefix).
- **`web/src/lib/queryKeys.ts`** extended with `health.status()`.
- **Review findings from 6-3**: Dashboard first-run flash fixed with `isLoading` guard; raw axios confirmed for health endpoints; stats interface extended with active_rules.

From Story 6-2 (done, commit `17d3458`):
- **7 shared components** in `web/src/components/shared/`: `Tooltip`, `DegradedBanner`, `LogRow`, `FilterIconRow`, `StatusPill`, `CollapsiblePanel`, `ActivationBanner`.
- **`CollapsiblePanel`** props: `title: string`, `summary: string`, `children: React.ReactNode`, `defaultOpen?: boolean`, `className?: string`.
- **`StatusPill`** props: `status: StatusPillStatus` → `"active" | "inactive" | "error" | "stale"`.
- **`FilterIconRow`** props: `config: FilterConfig` → maps from `FilterConfig` in `types/ui.ts`.
- **`ActivationBanner`** props: `isActive: boolean`, `onActivate: () => void`, optional `isFirstRun?: boolean`, optional `onCreateRule?: () => void`.

From Story 6-1 (done, commit `38a29fe`):
- **`apiClient`** in `@/api/client` — Axios instance with `baseURL: "/api/v1"` and `withCredentials: true`.
- **`queryKeys`** in `@/lib/queryKeys` — centralized factory; `rules.detail(id)` and `sources.list()` already defined.
- **`useNavigate()`** available in any component.
- Layout shell (`components/layout/Layout.tsx`) renders `DegradedBanner` globally.

---

## Git Intelligence

```
f76ee90  6-3 story completed  (Dashboard S1 + Settings S8 screens; added stats.ts, logs.ts, rules.ts stubs)
17d3458  story 6-2 done  (Shared UI component library — 7 components in components/shared/)
38a29fe  6-1 story done  (React SPA foundation, brand tokens, auth, layout)
424cecd  epic 5 completed
abe83bc  story 5-3 done  (SSE log broadcaster + stats/log API endpoints)
```

---

## Project Structure Notes

- Backend project root: `forward-bot/` (contains `pyproject.toml`, `src/forward_bot/`)
- Frontend project root: `web/` (contains `package.json`, `vite.config.ts`, `src/`)
- Story files: `_bmad-output/implementation-artifacts/`
- Planning artifacts: `_bmad-output/planning-artifacts/`

### Files to Create

```
web/src/
└── api/
    └── sources.ts   ← NEW: sourcesApi.fetchSources() → GET /api/v1/sources
```

### Files to Modify

```
web/src/
├── api/
│   └── rules.ts          ← EXTEND: add full CRUD + replacement rule operations; upgrade RulesListResponse.items type
├── lib/
│   └── queryKeys.ts      ← EXTEND: add rules.replacements(ruleId) key
├── routes/
│   └── index.tsx         ← MODIFY: split forwards/:id into forwards/new + forwards/:id/edit
└── pages/
    ├── ForwardsList.tsx  ← REPLACE stub: full S2 implementation
    └── ForwardEdit.tsx   ← REPLACE stub: full S3 implementation
```

No backend changes are required for this story. All required backend API endpoints are fully implemented from previous epics (Epic 3 + Epic 5). The `GET /api/v1/media/replacement-images` endpoint is also already live.

---

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Flash (High))

### Completion Notes List

- Applied comprehensive quality verification checks to fully incorporate missing S3 sub-configs (media replacement Combobox browse, auto-replace refs config, media type checkboxes).
- Enabled open panel URL query parameters state preservation (`?panels=...`).
- Added sequential bulk operations error details modal and 5+ row bulk-disable `AlertDialog` triggers.
- Handled nested FastAPI error parameter mapping helper for complex field levels.
- Pre-allocated a read-only message guard in creation mode for the inline replacement rules table.

### File List

- [NEW] [sources.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/sources.ts)
- [MODIFY] [rules.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/rules.ts)
- [MODIFY] [queryKeys.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/lib/queryKeys.ts)
- [MODIFY] [index.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/routes/index.tsx)
- [MODIFY] [ForwardsList.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/ForwardsList.tsx)
- [MODIFY] [ForwardEdit.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/ForwardEdit.tsx)

### Review Findings

- [x] [Review][Patch] Incorrect Tailwind color utility classes used [ForwardEdit.tsx, ForwardsList.tsx]
- [x] [Review][Patch] selectedIds state is not cleared after single rule deletion [ForwardsList.tsx]
- [x] [Review][Defer] handleSelectAll only selects current page items [ForwardsList.tsx] — deferred, pre-existing

