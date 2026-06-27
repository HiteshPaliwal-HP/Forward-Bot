---
baseline_commit: f76ee90d1996024b709c6c78e3c1b50e25acccd7
---

# Story 6.6: Logs Screen (S7), SSE Client & First-Run Wizard

Status: done

## Story

As a **Channel Operator**,
I want a live log tail with filter chips, correlation-ID tracing, and a first-run setup wizard that guides me through initial configuration,
So that I can diagnose forwarding issues in real time and get the bot configured correctly on first use.

## Acceptance Criteria

1. **Logs Screen — SSE Live Tail (S7):**
   - **Given** the operator navigates to `/logs` (S7).
   - **When** the page mounts.
   - **Then** `GET /api/v1/logs/recent?limit=200` is fetched first (historical batch); the last 200 entries are displayed as `LogRow` components in chronological order (oldest at top).
   - **And** after the historical batch loads, an `EventSource` connection opens to `GET /api/v1/logs/stream`; incoming SSE events are appended to the bottom of the log list and rendered as `LogRow` components — without duplicating the historical batch.
   - **And** auto-scroll is enabled by default: new entries scroll into view automatically when the user is near the bottom (within ~100px of the bottom).
   - **And** a **"Pause"** toggle button stops auto-scroll (but does NOT close the `EventSource` connection); pausing shows a floating "Jump to latest ↓" button that resumes auto-scroll and scrolls to the bottom.

2. **Logs Screen — SSE Disconnect Handling:**
   - **Given** the `EventSource` connection drops (network interruption, server restart).
   - **When** the `EventSource` `onerror` event fires.
   - **Then** the `DegradedBanner` component appears above the log list with message `"Live log stream disconnected — reconnecting…"`.
   - **And** the `EventSource` reconnects automatically via its built-in browser retry mechanism.
   - **And** the `DegradedBanner` dismisses when the connection re-establishes (the `EventSource` `onopen` fires after reconnect).

3. **Logs Screen — Filter Chips & URL Persistence:**
   - **Given** the operator is on `/logs`.
   - **When** they click severity filter chips (info / warning / error / success) or type a `correlation_id` in the filter bar.
   - **Then** the active filters are reflected in the URL query string (e.g., `?severity=error&correlation_id=abc12345`).
   - **And** on page load, the URL query string is read and filter chips are pre-selected accordingly.
   - **And** the log list filters **client-side** (from the in-memory buffer) — no new API call is made when filters change.
   - **And** a "Clear filters" button resets all chips and removes the query params.

4. **Logs Screen — Correlation ID Tracing:**
   - **Given** a log entry includes a `correlation_id`.
   - **When** the operator clicks the correlation ID badge (copy button) inside the expanded `LogRow` details panel.
   - **Then** the `correlation_id` is copied to the clipboard (existing LogRow behaviour).
   - **And** a "Filter by this ID" button (separate from Copy) appears next to the `correlation_id` in the expanded panel; clicking it sets `?correlation_id=<id>` in the URL and activates the correlation_id filter chip, showing only entries with that correlation_id.
   - **And** if the log entry also has a `rule_id`, a "Jump to rule →" link appears in the filter bar (below the chips) navigating to `/forwards/{rule_id}/edit`.

5. **First-Run Wizard:**
   - **Given** the operator's first visit after installation (no forwarding rules exist).
   - **When** the Dashboard mounts and `GET /api/v1/rules?page_size=1` returns `{ items: [], total: 0, ... }`.
   - **Then** the First-Run Wizard `Dialog` opens automatically, unless `localStorage.getItem("fb-first-run-dismissed")` is `"true"`.
   - **And** the wizard has 3 steps:
     - Step 1 — "Register a Source": description text + "Go to Sources →" button that navigates to `/sources/new`.
     - Step 2 — "Create a Forwarding Rule": description text + "Go to Forwards →" button that navigates to `/forwards/new`.
     - Step 3 — "Verify Live Logs": description text + "Go to Logs →" button that navigates to `/logs`.
   - **And** the wizard has "Next" / "Back" navigation between steps and a "Skip setup" link that dismisses the wizard permanently.
   - **And** on dismissal (Skip or close), `localStorage.setItem("fb-first-run-dismissed", "true")` is called; the wizard never reopens once dismissed.
   - **And** the wizard also does not open if at least 1 forwarding rule exists (even if `localStorage` is not set).

6. **`useSseLog` Hook:**
   - **Given** `web/src/hooks/useSseLog.ts` is implemented.
   - **When** the hook is mounted or its parameters change.
   - **Then** it supports an `enabled` parameter (default `true`) and only opens an `EventSource` to `/api/v1/logs/stream` if `enabled` is `true`.
   - **And** it accepts a `startAfterTimestamp` option to filter out any incoming events with a timestamp less than or equal to the starting timestamp.
   - **And** it returns: `{ entries: LogEntry[], isConnected: boolean, isError: boolean }`.
   - **And** on unmount or when `enabled` becomes `false`, `eventSource.close()` is called to prevent memory leaks.
   - **And** the hook maintains a capped in-memory buffer (max 1000 entries) appending new SSE events — oldest at top, newest at bottom.
   - **And** the hook updates its internal timestamp cutoff when new messages arrive to prevent duplicates when automatic reconnects replay events.

7. **`FirstRunWizard` Component:**
   - **Given** `web/src/components/FirstRunWizard.tsx` is implemented (replacing the stub page).
   - **When** the component renders.
   - **Then** it uses the existing custom `Dialog` from `web/src/components/ui/dialog.tsx`.
   - **And** it is **not** a routed page — it is a modal component rendered inside `Dashboard.tsx`.
   - **And** the route `wizard` in `routes/index.tsx` is removed (the stub page at `pages/FirstRunWizard.tsx` is converted to the component at `components/FirstRunWizard.tsx`).

8. **API — `logsApi` Extension:**
   - **Given** `web/src/api/logs.ts` currently has only `fetchRecent`.
   - **When** this story is complete.
   - **Then** `logsApi` is extended to also export:
     - `fetchRecent(limit?: number, params?: { event?: string; correlation_id?: string })` — extended to accept optional filter params: `GET /api/v1/logs/recent`.
     - `searchLogs(params: { correlation_id: string; since?: string })` — `GET /api/v1/logs/search`.
   - **And** `SSE_STREAM_URL = "/api/v1/logs/stream"` is exported as a constant for use in `useSseLog`.

9. **Build Verification:**
   - **Given** all screens and components are implemented.
   - **When** `npm run build` is executed in `web/`.
   - **Then** the build completes with zero TypeScript errors.

---

## Tasks / Subtasks

- [x] **1. Extend `web/src/api/logs.ts`** (AC: 8)
  - [x] Add `searchLogs(params)` function — `GET /api/v1/logs/search`
  - [x] Extend `fetchRecent` to accept optional `event` and `correlation_id` filter params
  - [x] Export `SSE_STREAM_URL` constant

- [x] **2. Create `web/src/hooks/useSseLog.ts`** (AC: 6)
  - [x] Support `enabled` option, only connecting when `enabled` is true
  - [x] Open `EventSource` to `SSE_STREAM_URL` when active
  - [x] Append incoming `message` events to internal state buffer (max 1000 entries)
  - [x] Track `isConnected` (true on `onopen`) and `isError` (true on `onerror`, reset on `onopen`)
  - [x] Update internal timestamp cutoff with each received event to prevent duplication upon automatic reconnect
  - [x] Close `EventSource` on unmount or when `enabled` becomes `false`
  - [x] Return `{ entries, isConnected, isError }`

- [x] **3. Implement `web/src/components/FirstRunWizard.tsx`** (AC: 5, 7)
  - [x] Move from stub page `pages/FirstRunWizard.tsx` → component `components/FirstRunWizard.tsx`
  - [x] Accept props: `open: boolean`, `onDismiss: () => void`
  - [x] Implement 3-step dialog using custom `Dialog` from `components/ui/dialog.tsx`
  - [x] Implement "Next" / "Back" step navigation
  - [x] Implement "Skip setup" dismiss with `localStorage.setItem("fb-first-run-dismissed", "true")`
  - [x] Step navigation buttons use `useNavigate()` for routing to respective pages

- [x] **4. Update `web/src/pages/Dashboard.tsx`** (AC: 5)
  - [x] Import and render `FirstRunWizard` as a modal overlay
  - [x] Add `useQuery` for `GET /api/v1/rules?page_size=1` to detect zero-rule state
  - [x] Read `localStorage.getItem("fb-first-run-dismissed")` to decide auto-open
  - [x] Control `wizardOpen` state: open if `total === 0` AND not dismissed
  - [x] Pass `onDismiss` handler that sets `localStorage` and closes wizard

- [x] **5. Implement `web/src/pages/Logs.tsx`** (AC: 1, 2, 3, 4)
  - [x] Fetch historical batch via `logsApi.fetchRecent(200)` on mount using TanStack Query with `staleTime: 0`
  - [x] Use `useSseLog` hook, passing `enabled: !isLoading` and the last historical event's timestamp as `startAfterTimestamp` to cleanly gate stream connection
  - [x] Merge historical + live entries chronologically (oldest at top), deduplicating by timestamp + event
  - [x] Implement client-side filtering using the `getDisplaySeverity` helper to map `LogEntry` to display chips ("info", "warning", "error", "success")
  - [x] When a correlation ID is clicked, filter by that correlation ID, and extract the first non-null `rule_id` from matching entries to render a "Jump to rule →" link in the filter bar
  - [x] Inside the `DegradedBanner` `onReconnect` callback, fetch `healthApi.fetchTelegramStatus` to verify authentication before recreating the EventSource connection
  - [x] Render entries as `LogRow` components in a scrollable container
  - [x] Implement auto-scroll logic: scroll to bottom when `isAutoScroll` is true and new entries arrive
  - [x] Implement "Pause" toggle button — toggles `isAutoScroll` without closing SSE
  - [x] Show floating "Jump to latest ↓" button when paused and scrolled up
  - [x] Show `DegradedBanner` when `isError` is true from `useSseLog`
  - [x] Implement filter chips: severity (info / warning / error / success) and correlation_id text input
  - [x] Sync active filters to/from URL query params (`useSearchParams`)
  - [x] Filter entries client-side based on active filters
  - [x] Add "Clear filters" button
  - [x] Add "Filter by this ID" logic — intercept correlation_id click from expanded LogRow detail panel via a prop callback or URL state

- [x] **6. Update `web/src/pages/FirstRunWizard.tsx`** (AC: 7)
  - [x] Replace stub content with a redirect to `/` or a plain `null` render (the real wizard is now in `components/FirstRunWizard.tsx`)
  - [x] OR simply remove the page file and the `wizard` route from `routes/index.tsx`

- [x] **7. Update `web/src/routes/index.tsx`** (AC: 7)
  - [x] Remove `import FirstRunWizard from "@/pages/FirstRunWizard"` and `<Route path="wizard" ...>`

- [x] **8. Verify Build** (AC: 9)
  - [x] Run `npm run build` in `web/` — must complete with zero TypeScript errors

---

## Dev Notes

### ⚠️ CRITICAL: SSE + Historical Batch Merge — No Duplicates & Enabled Gating

The Logs screen loads two data sources:
1. **Historical batch** via `logsApi.fetchRecent(200)` — this gives entries that already exist in the ring buffer.
2. **Live SSE stream** via `useSseLog` — replays the ring buffer on connect THEN pushes new events.

The SSE endpoint (`GET /api/v1/logs/stream`) **replays the ring buffer on connect** (see Story 5.3 AC). This means the SSE stream will deliver the same ~200 recent events again on connect. 

**Strategy to avoid duplicates:**
- Fetch historical batch first (via TanStack Query).
- Only enable and open the `EventSource` connection in `useSseLog` after the historical batch has successfully loaded (i.e. by passing `enabled: !isLoading`).
- Pass the timestamp of the last historical log entry as `startAfterTimestamp` to act as the initial cutoff.
- Inside the hook, update the cutoff `ref` value with the timestamp of every newly received event that passes the cutoff check. This is crucial: since standard EventSource automatically reconnects on connection drops and prompts the backend to replay the ring buffer, updating the cutoff to the latest received timestamp prevents replayed historical events from causing duplicates.
- Ensure proper deduplication of combined entries keying on `timestamp + event` in `Logs.tsx`.

```typescript
// useSseLog.ts onmessage handler approach:
es.onmessage = (event: MessageEvent) => {
  try {
    const entry: LogEntry = JSON.parse(event.data as string);
    if (entry.timestamp >= cutoff.current) {
      setEntries(prev => [...prev.slice(-(MAX_BUFFER - 1)), entry]);
      cutoff.current = entry.timestamp; // update to prevent replay duplicates on auto-reconnect
    }
  } catch {
    // ignore malformed lines
  }
};
```

### ⚠️ CRITICAL: `EventSource` Does Not Support Custom Headers

The SSE endpoint `GET /api/v1/logs/stream` uses the same cookie-based auth that the rest of the app uses. Since the app uses `HttpOnly` cookies with `SameSite=Strict` and `withCredentials: true` (already set on `apiClient`), the `EventSource` will automatically send cookies:

```typescript
// useSseLog.ts — correct EventSource creation:
const es = new EventSource("/api/v1/logs/stream", { withCredentials: true });
```

Do NOT try to pass an `Authorization` header — `EventSource` doesn't support custom headers. Cookie auth handles it.

### ⚠️ CRITICAL: SSE Event Format

The backend SSE broadcaster (Story 5.3) sends events as:
```
data: {"event": "forward_succeeded", "level": "info", "timestamp": "2026-06-27T...", "correlation_id": "a3f9b2c1", ...}\n\n
```

Parse with:
```typescript
es.onmessage = (event: MessageEvent) => {
  try {
    const entry: LogEntry = JSON.parse(event.data);
    // process entry
  } catch {
    // ignore malformed lines
  }
};
```

### ⚠️ CRITICAL: Auto-Scroll Implementation

Use a `ref` on the scrollable container and check scroll position:

```typescript
const scrollRef = useRef<HTMLDivElement>(null);
const isNearBottom = () => {
  const el = scrollRef.current;
  if (!el) return false;
  return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
};

// After new entries are appended:
useEffect(() => {
  if (isAutoScroll && scrollRef.current) {
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }
}, [entries, isAutoScroll]);

// Detect manual scroll-up to pause auto-scroll:
const handleScroll = () => {
  if (!isNearBottom()) {
    setIsAutoScroll(false);
  }
};
```

### ⚠️ CRITICAL: `FirstRunWizard` Is a Modal Component, Not a Page

The stub at `web/src/pages/FirstRunWizard.tsx` was a placeholder page. This story converts it to a **component** at `web/src/components/FirstRunWizard.tsx` rendered as an overlay inside `Dashboard.tsx`.

Steps:
1. Create `web/src/components/FirstRunWizard.tsx` with the real wizard UI.
2. Remove the stub `pages/FirstRunWizard.tsx` file.
3. Remove the `wizard` route and its import from `routes/index.tsx`.
4. Import and use `FirstRunWizard` in `Dashboard.tsx`.

### ⚡ ENHANCEMENT: Filter Chips — Client-Side Only

All filtering on the Logs screen is **client-side** only. The URL stores the active filter state for shareability/refresh persistence. The filter logic should:

```typescript
// In Logs.tsx
const [searchParams, setSearchParams] = useSearchParams();
const activeSeverities = searchParams.getAll("severity");  // can have multiple
const activeCorrelationId = searchParams.get("correlation_id") ?? "";

const filteredEntries = useMemo(() => {
  return allEntries.filter(entry => {
    const severityMatch = activeSeverities.length === 0 || activeSeverities.includes(getDisplaySeverity(entry));
    const correlationMatch = !activeCorrelationId || entry.correlation_id === activeCorrelationId;
    return severityMatch && correlationMatch;
  });
}, [allEntries, activeSeverities, activeCorrelationId]);
```

### ⚡ ENHANCEMENT: "Filter by Correlation ID" Integration with `LogRow`

The existing `LogRow` already has a "Copy Correlation ID" button. This story needs to **also** surface a "Filter by this ID" action. There are two clean approaches:

**Option A (Recommended): Pass a callback prop to `LogRow`**
```tsx
// LogRow.tsx — add optional prop:
interface LogRowProps {
  entry: LogEntry;
  onFilterByCorrelationId?: (id: string) => void;
}

// In the expanded detail panel, next to the existing Copy button:
{entry.correlation_id && onFilterByCorrelationId && (
  <button onClick={() => onFilterByCorrelationId(entry.correlation_id!)}>
    Filter by this ID
  </button>
)}
```

**Option B: Use URL navigation directly in LogRow**

Option A is preferred because it keeps `LogRow` testable and not coupled to router state.

### API Endpoint Reference

| Endpoint | Method | Description | Response Shape |
|---|---|---|---|
| `GET /api/v1/logs/recent` | GET | Last N log entries from ring buffer | `{ items: LogEntry[] }` |
| `GET /api/v1/logs/stream` | GET (SSE) | Live log stream; replays ring buffer on connect | SSE stream of JSON log events |
| `GET /api/v1/logs/search` | GET | Filter ring buffer by correlation_id | `{ items: LogEntry[] }` |
| `GET /api/v1/rules` | GET | Used to detect zero-rule state for wizard | `{ items: [], total: 0, ... }` |

Query params for `GET /api/v1/logs/recent`:
- `limit` (int, default 50, max 500)
- `event` (string, optional filter)
- `correlation_id` (string, optional filter)

Query params for `GET /api/v1/logs/stream`:
- `event` (string, optional SSE-level filter)
- `correlation_id` (string, optional SSE-level filter)

### TypeScript Interfaces / Additions

```typescript
// web/src/api/logs.ts — ADDITIONS

export const SSE_STREAM_URL = "/api/v1/logs/stream";

export interface LogsSearchResponse {
  items: LogEntry[];
}

export const logsApi = {
  // Extended from existing — add optional params:
  fetchRecent: async (
    limit = 20,
    params?: { event?: string; correlation_id?: string }
  ): Promise<LogsRecentResponse> => {
    const { data } = await apiClient.get<LogsRecentResponse>("/logs/recent", {
      params: { limit, ...params },
    });
    return data;
  },

  // NEW:
  searchLogs: async (params: {
    correlation_id: string;
    since?: string;
  }): Promise<LogsSearchResponse> => {
    const { data } = await apiClient.get<LogsSearchResponse>("/logs/search", {
      params,
    });
    return data;
  },
};
```

```typescript
// web/src/hooks/useSseLog.ts — NEW FILE

import { useState, useEffect, useRef } from "react";
import type { LogEntry } from "@/types/ui";
import { SSE_STREAM_URL } from "@/api/logs";

const MAX_BUFFER = 1000;

interface UseSseLogOptions {
  enabled?: boolean;
  startAfterTimestamp?: string;
}

interface UseSseLogResult {
  entries: LogEntry[];
  isConnected: boolean;
  isError: boolean;
}

export function useSseLog({ enabled = true, startAfterTimestamp }: UseSseLogOptions = {}): UseSseLogResult {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isError, setIsError] = useState(false);
  const cutoff = useRef<string>(startAfterTimestamp ?? new Date().toISOString());

  useEffect(() => {
    if (startAfterTimestamp) {
      cutoff.current = startAfterTimestamp;
    }
  }, [startAfterTimestamp]);

  useEffect(() => {
    if (!enabled) {
      setIsConnected(false);
      return;
    }

    const es = new EventSource(SSE_STREAM_URL, { withCredentials: true });

    es.onopen = () => {
      setIsConnected(true);
      setIsError(false);
    };

    es.onmessage = (event: MessageEvent) => {
      try {
        const entry: LogEntry = JSON.parse(event.data as string);
        // Only add entries newer than the cutoff (avoids duplicates)
        if (entry.timestamp >= cutoff.current) {
          setEntries(prev => [...prev.slice(-(MAX_BUFFER - 1)), entry]);
          // Update the cutoff to prevent duplicates on automatic EventSource reconnects
          cutoff.current = entry.timestamp;
        }
      } catch {
        // ignore malformed SSE lines
      }
    };

    es.onerror = () => {
      setIsConnected(false);
      setIsError(true);
    };

    return () => {
      es.close();
    };
  }, [enabled]);

  return { entries, isConnected, isError };
}
```

```typescript
// web/src/components/FirstRunWizard.tsx — NEW COMPONENT (not a page)

interface FirstRunWizardProps {
  open: boolean;
  onDismiss: () => void;
}

// 3 steps: Register Source → Create Forward → Verify Logs
// Uses Dialog from web/src/components/ui/dialog.tsx
// Step navigation via useState<number> (0-indexed)
// "Skip setup" calls onDismiss
// Step action buttons use useNavigate() then call onDismiss
```

### Severity Filter → LogEntry Level Mapping

The severity filter chips map to `LogEntry.level`:
- "info" chip → `level === "info"`
- "warning" chip → `level === "warning"`
- "error" chip → `level === "error" || level === "critical"`
- "success" chip → derived from event name (`forward_succeeded`, `edit_propagated`, `delete_propagated`)

Since `LogEntry` doesn't have a dedicated `severity` field, derive it:
```typescript
const getDisplaySeverity = (entry: LogEntry): "info" | "warning" | "error" | "success" => {
  const successEvents = ["forward_succeeded", "edit_propagated", "delete_propagated", "mapping_sweep_completed"];
  if (successEvents.includes(entry.event)) return "success";
  if (entry.level === "critical" || entry.level === "error") return "error";
  if (entry.level === "warning") return "warning";
  return "info";
};
```

### Form State & Toast Patterns (Consistent with Previous Stories)

Use the same patterns established in Story 6-4 and 6-5:
```typescript
import { toast } from "sonner";
toast.success("Message here.");
toast.error("Error message here.");
```

Use `useNavigate()` from `react-router-dom` for programmatic navigation.

### TypeScript Strict Mode Checklist

- No `any` types — use `LogEntry` from `@/types/ui` for all log entries.
- `EventSource` type is available natively in TypeScript's `lib.dom.d.ts` — no import needed.
- `MessageEvent` is a DOM type — no import needed.
- All hook return types must be explicitly typed.
- `npm run build` must compile clean with zero warnings.

---

## Previous Story Learnings

- **Custom `Dialog` component** is at `web/src/components/ui/dialog.tsx` — use it (do NOT import from shadcn directly). Exports: `Dialog`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription`.
- **`AlertDialog`** is at `web/src/components/ui/alert-dialog.tsx` — also a custom implementation. Only needed for destructive confirmations. The First-Run Wizard uses the regular `Dialog`.
- **`DegradedBanner`** is at `web/src/components/shared/DegradedBanner.tsx` — props: `message: string`, `onReconnect: () => void`, `isLoading?: boolean`. For the SSE disconnect case, `onReconnect` can be a no-op or trigger `EventSource` recreation (browser retries automatically).
- **`LogRow`** is at `web/src/components/shared/LogRow.tsx` — already fully implemented with expand/collapse, copy correlation_id, jump to rule. The `onFilterByCorrelationId` prop will need to be added as an **optional** prop so existing usages (Dashboard recent activity) are not broken.
- **Axios `apiClient`** is at `@/api/client` with `baseURL: '/api/v1'` and `withCredentials: true`. SSE `EventSource` does NOT go through `apiClient` — it connects directly to `/api/v1/logs/stream`.
- **`useSearchParams`** from `react-router-dom` for URL query param management — the existing routes use React Router v7 declarative mode (`BrowserRouter + Routes`).
- **Tailwind v4** color tokens: use `text-muted-foreground`, `bg-card`, `border-border`, `text-foreground`, `bg-muted`, `text-error`, `text-success`, `text-warning-foreground`, etc. — these map to CSS custom properties defined in `web/src/styles/tokens.css`.
- **Route ordering**: the `wizard` route must be removed; no new page routes are added in this story.
- **`sonner` toast**: import `{ toast } from "sonner"`. Already installed.
- **`lucide-react`**: icons are already installed. Relevant icons for this story: `Play`, `Pause`, `ArrowDown`, `Filter`, `X`, `ChevronRight`, `ChevronLeft`.

---

## Git Intelligence

```
f76ee90  6-3 story completed  (ForwardsList + ForwardEdit full S2/S3 screens; sources.ts stub created)
17d3458  story 6-2 done  (Shared UI component library — 7 components in components/shared/)
38a29fe  6-1 story done  (React SPA foundation, brand tokens, auth, layout)
424cecd  epic 5 completed
abe83bc  story 5-3 done  (SSE log broadcaster + stats/log API endpoints)
b534983  story 5-2 completed  (Full structlog chain + ring buffer + event catalog)
```

Note: Git log shows commits through story 6-3; Stories 6-4 and 6-5 are complete (done) per sprint-status.yaml but not yet in the git log — changes are in working tree.

---

## Architecture Notes

- **Logs screen uses full-width layout** (per UX-DR2: "Logs screen uses full-width layout"). The existing `Layout.tsx` must accommodate this — check if it already has a mechanism (e.g., a context or prop to switch to full-width). If not, the Logs page container should use `max-w-none` or `w-full` instead of the standard `max-w-6xl`.
- **TanStack Query stale times** (from architecture F1):
  - `logs recent` = `staleTime: 0` — refetch every 5s (but SSE replaces polling here; just use `staleTime: 0` with no `refetchInterval` since SSE handles live updates).
  - `rules list` (for wizard detection) = `staleTime: 30_000` (already cached from Dashboard).
- **SSE endpoint registered before SPA catch-all** in FastAPI `main.py` — this is already done per Story 5.3.
- **Ring buffer default**: 1 hour of logs (`LOG_RING_BUFFER_HOURS=1`), configurable up to 24h. The `GET /api/v1/logs/recent?limit=200` returns up to the last 200 entries from the ring buffer (not necessarily 1h of entries).

---

## Project Structure Notes

- Frontend project root: `web/`
- Story files: `_bmad-output/implementation-artifacts/`

### Files to Create

```
web/src/
├── hooks/
│   └── useSseLog.ts            ← NEW: SSE EventSource lifecycle hook
└── components/
    └── FirstRunWizard.tsx      ← NEW: 3-step modal wizard component (replaces page stub)
```

### Files to Modify

```
web/src/
├── api/
│   └── logs.ts                 ← EXTEND: searchLogs(), SSE_STREAM_URL, extend fetchRecent params
├── pages/
│   ├── Logs.tsx                ← REPLACE: full S7 implementation
│   ├── Dashboard.tsx           ← MODIFY: integrate FirstRunWizard overlay
│   └── FirstRunWizard.tsx      ← DELETE: stub page (wizard moved to components/)
├── components/
│   └── shared/
│       └── LogRow.tsx          ← MODIFY: add optional onFilterByCorrelationId prop
└── routes/
    └── index.tsx               ← MODIFY: remove wizard route + import
```

---

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Completion Notes List

- Extended logs API to support `searchLogs` and filter params in `fetchRecent`.
- Implemented custom `useSseLog` hook to stream logs with duplicate prevention and automatic reconnect handling.
- Implemented the 3-step `FirstRunWizard` modal component matching design system tokens.
- Integrated `FirstRunWizard` in `Dashboard.tsx` with zero-rule detection and persistent dismissal setting.
- Replaced the stub `Logs.tsx` with the complete Logs page featuring SSE streaming, client-side filtering, trace ID filtering, and auto-scroll control.
- Modified the stub `FirstRunWizard.tsx` page to redirect to dashboard and removed the `/wizard` route.
- Updated `LogRow.tsx` to support trace filtering via a callback prop.
- Configured conditional layout width wrapper in `Layout.tsx` for a full-width experience on the Logs page.
- Ran clean verification build with `npm run build`.

### File List

- `web/src/api/logs.ts`
- `web/src/hooks/useSseLog.ts`
- `web/src/components/FirstRunWizard.tsx`
- `web/src/pages/Dashboard.tsx`
- `web/src/pages/Logs.tsx`
- `web/src/pages/FirstRunWizard.tsx`
- `web/src/components/shared/LogRow.tsx`
- `web/src/components/layout/Layout.tsx`
- `web/src/routes/index.tsx`

### Review Findings

- [x] [Review][Patch] Deduplicate by Correlation ID [web/src/pages/Logs.tsx:80]
- [x] [Review][Patch] Fix Auto-scroll scroll-smooth animation conflict [web/src/pages/Logs.tsx:345]
- [x] [Review][Patch] Strictly filter startAfterTimestamp [web/src/hooks/useSseLog.ts:47]

