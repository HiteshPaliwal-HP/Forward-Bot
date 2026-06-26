---
baseline_commit: 17d34587beab0220c32f0ceafc5e247a8a9e5060
---
# Story 6.3: Dashboard (S1) & Settings (S8) Screens

Status: done

## Story

As a **Channel Operator**,
I want a dashboard showing system health and recent activity, and a settings page for system configuration,
so that I can assess bot status at a glance and adjust operational settings without editing config files.

## Acceptance Criteria

1. **Dashboard Health Cards (S1):**
   - **Given** the operator navigates to `/` (Dashboard, S1).
   - **When** the page loads.
   - **Then** TanStack Query fetches `GET /health` with `staleTime: 30_000` and `GET /api/v1/stats/summary` with `staleTime: 60_000`.
   - **And** the health card displays: Telegram connectivity status (visual green/red indicator), MongoDB status (visual green/red indicator), active rule count.
   - **And** the stats panel displays `forwarded_24h`, `failed_24h`, `blocked_24h` counts from the stats summary response.
   - **And** loading states for these cards render premium loading skeletons (using Tailwind `animate-pulse` boxes) rather than raw loading text.

2. **Dashboard Degraded State (S1):**
   - **Given** the health endpoint returns `telegram_status: "degraded"` (i.e., Telegram is `disconnected` or `reconnecting`).
   - **When** the Dashboard renders.
   - **Then** the `DegradedBanner` component (from `components/layout/`) mounts — it already self-manages and renders itself; no duplication needed.
   - **And** clicking "Reconnect" in the banner calls `POST /api/v1/admin/reconnect` and shows a toast "Reconnect initiated".
   - **Note**: The layout's `DegradedBanner` from `components/layout/DegradedBanner.tsx` handles this globally in the `Layout` shell. The Dashboard page itself does NOT need to render a second DegradedBanner.

3. **Dashboard Recent Activity Panel (S1):**
   - **Given** the Recent Activity panel is on the Dashboard.
   - **When** the panel renders.
   - **Then** it fetches `GET /api/v1/logs/recent?limit=20` with `staleTime: 10_000` (mapped to `queryKeys.logs.recent()`).
   - **And** each entry renders as a `LogRow` component from `components/shared/` with its appropriate severity variant.
   - **And** a "View all logs →" link navigates to `/logs` using React Router `Link`.

4. **Dashboard First-Run Activation Banner (S1):**
   - **Given** no forwarding rules exist (rule list is empty).
   - **When** the Dashboard loads and `GET /api/v1/rules?page_size=1` returns an empty result.
   - **Then** the `ActivationBanner` is rendered with `isFirstRun={true}` showing a "Create your first rule" CTA that navigates to `/forwards/new`.
   - **And** `ActivationBanner` is NOT shown when at least one rule exists.

5. **Settings Page Core Display (S8):**
   - **Given** the operator navigates to `/settings` (S8).
   - **When** the page loads.
   - **Then** it fetches `GET /health` (reused from TanStack Query cache with `staleTime: 30_000`) and displays: service version (from health response or fallback `"0.1.0"` if missing), client-session uptime display (active duration elapsed since page load or `"N/A"`), MongoDB connection status (visual "up" / "down" badge), and static session TTL information (`"24 Hours (HttpOnly)"`).
   - **And** a "Logout" button calls `POST /api/v1/auth/logout` and on success redirects to `/login`.

6. **Settings Theme Toggle (S8):**
   - **Given** the operator is on the Settings page.
   - **When** the theme toggle renders.
   - **Then** it shows a three-state toggle: System / Light / Dark with the currently-active option highlighted.
   - **And** selecting a theme option calls `setTheme()` from `useTheme()` (ThemeContext).
   - **And** the chosen theme is saved to `localStorage` under key `fb-theme` (handled by ThemeContext, no extra code needed).
   - **And** on next page load the persisted theme is applied before first render (no flash — handled by ThemeContext's initializer reading from localStorage).

7. **API Modules:**
   - **Given** the Dashboard and Settings screens require data.
   - **When** the API modules are inspected.
   - **Then** `web/src/api/health.ts` exports `fetchHealth` function (currently has `fetchTelegramStatus` and `fetchCacheStatus` — extend it with a proper `fetchHealth` for `GET /health` using raw `axios`).
   - **And** `web/src/api/stats.ts` is created and exports `fetchStats` function calling `GET /api/v1/stats/summary`.
   - **And** `web/src/api/logs.ts` is created and exports `fetchRecentLogs(limit?: number)` calling `GET /api/v1/logs/recent?limit={limit}`.
   - **And** `web/src/api/rules.ts` is created and exports at minimum `fetchRules(params?: {...})` calling `GET /api/v1/rules` (stub for Stories 6-4 to flesh out, but needed for first-run detection).

8. **Query Keys:**
   - **Given** new query calls are added.
   - **When** `web/src/lib/queryKeys.ts` is inspected.
   - **Then** the following key entries exist (some already exist — add only missing ones):
     - `queryKeys.health.status()` → `["health", "status"]` (for `GET /health`)
     - `queryKeys.stats.summary()` → `["stats", "summary"]` ✅ already exists
     - `queryKeys.logs.recent()` → `["logs", "recent"]` ✅ already exists
     - `queryKeys.rules.list()` → `["rules", "list"]` ✅ already exists

9. **Build Verification:**
   - **Given** all screens are implemented.
   - **When** `npm run build` is executed in `web/`.
   - **Then** the build completes with zero TypeScript errors.

---

## Tasks / Subtasks

- [x] **1. Create `web/src/api/stats.ts`** (AC: 7)
  - [x] Export `fetchStats()` calling `apiClient.get("/stats/summary")` and returning `{ forwarded_24h, failed_24h, blocked_24h }`

- [x] **2. Create `web/src/api/logs.ts`** (AC: 7)
  - [x] Export `fetchRecentLogs(limit = 20)` calling `apiClient.get("/logs/recent", { params: { limit } })`

- [x] **3. Create `web/src/api/rules.ts`** (AC: 7)
  - [x] Export `fetchRules(params?)` calling `apiClient.get("/rules", { params })` — minimal stub for first-run detection

- [x] **4. Extend `web/src/api/health.ts`** (AC: 7)
  - [x] Add `fetchHealth()` calling raw `axios.get("/health")` returning raw health response (version, status, etc.)

- [x] **5. Update `web/src/lib/queryKeys.ts`** (AC: 8)
  - [x] Add `health.status: () => ["health", "status"] as const`

- [x] **6. Implement `web/src/pages/Dashboard.tsx`** (AC: 1, 2, 3, 4)
  - [x] Use `useQuery` for health (`queryKeys.health.status()`, staleTime 30s), stats (`queryKeys.stats.summary()`, staleTime 60s), logs (`queryKeys.logs.recent()`, staleTime 10s), and rules-list (`queryKeys.rules.list()` with `page_size=1`, staleTime 30s)
  - [x] Implement premium skeleton loading states for stats/health cards using Tailwind `animate-pulse` boxes
  - [x] Render health card: Telegram status dot + label, MongoDB status, active rule count from stats
  - [x] Render stats panel: forwarded_24h, failed_24h, blocked_24h with icon + label
  - [x] Render recent activity panel with `LogRow` components + "View all logs →" link
  - [x] Conditionally render `ActivationBanner` with `isFirstRun={true}` + `onCreateRule` when rules list is empty

- [x] **7. Implement `web/src/pages/Settings.tsx`** (AC: 5, 6)
  - [x] Use `useQuery` for health data (reuse `queryKeys.health.status()`, staleTime 30s)
  - [x] Display service info section: service version (from health or fallback "0.1.0"), client-session uptime duration timer (elapsed since page load), MongoDB connection status (stylized "up" / "down" badge), static session TTL info ("24 Hours (HttpOnly)")
  - [x] Implement three-state theme toggle (System/Light/Dark) using `useTheme()`
  - [x] Implement Logout button using `useMutation` → `authApi.logout()` → redirect to `/login` on success
  - [x] Handle logout errors with a toast

- [x] **8. Verify Build** (AC: 9)
  - [x] Run `npm run build` in `web/` — must complete with zero TypeScript errors

---

## Dev Notes

### Critical: Do NOT Add a Second DegradedBanner on Dashboard

The `Layout` shell (`components/layout/Layout.tsx`) already renders `DegradedBanner` globally:
```tsx
<DegradedBanner />  // inside Layout.tsx, already monitors Telegram + MongoDB
```
This self-contained banner from `components/layout/DegradedBanner.tsx` already polls `/health/telegram` and `/health/ready` every 10 seconds, displays when degraded, and provides the Reconnect button. **Do NOT render it again in Dashboard.tsx.** The acceptance criterion about "DegradedBanner mounts" is fulfilled by the existing Layout shell.

The **shared** `DegradedBanner` in `components/shared/DegradedBanner.tsx` is a _presentational-only_ component (no internal data fetching). It is intended for Logs screen SSE disconnection (Story 6-6), NOT for the Dashboard.

### Health Endpoints are Route-Mounted (No Prefix)

**CRITICAL**: The backend health endpoints are mounted directly at the root, NOT under `/api/v1`.
- Use raw `axios` to query them directly at `/health`, `/health/ready`, and `/health/telegram`.
- Do NOT use `apiClient` for health routes, as it appends `/api/v1` and will return `404 Not Found`.

### API Endpoint Reference

| Endpoint | Method | Description | Response Shape |
|---|---|---|---|
| `/health` | GET | Overall health (liveness) | `{ status: "ok" }` |
| `/health/ready` | GET | MongoDB readiness | `{ mongodb: "up" | "down", cache: { version: number, refreshed_at: string } }` |
| `/health/telegram` | GET | Telegram status | `{ telegram: "connected" | "disconnected" | "reconnecting", last_event: string | null }` |
| `/api/v1/stats/summary` | GET | 24h stats from ring buffer | `{ forwarded_24h: N, failed_24h: N, blocked_24h: N }` |
| `/api/v1/logs/recent` | GET | Last N log entries | `{ items: LogEntry[] }` |
| `/api/v1/rules` | GET | Rules list (paged) | `{ items: [...], total: N, page: N, page_size: N }` |
| `/api/v1/auth/logout` | POST | Clear session cookie | `{}` |

### Settings Info Rendering

- **Service Version**: Query `/health/ready` to display the cache version, or use `0.1.0` as the default fallback.
- **MongoDB Connection Status**: Displays a stylized "up" / "down" badge mapped to the status from `/health/ready` (e.g. `up` -> green badge, `down` -> red badge). Do not attempt to query or display credentials/URIs directly.
- **Session TTL & Uptime**: The backend session max-age is 24 hours. Display a static indicator `"24 Hours (HttpOnly)"`. For uptime, render the elapsed active session duration on the client side since the application was loaded, or fallback to `"N/A"`.

### Recommended Dashboard Data Approach & Loading States

Rather than adding yet another health query, re-use the data already in cache from the TopBar's existing queries:

```tsx
// Already cached by TopBar, refetch every 10s
const { data: telegramData } = useQuery({
  queryKey: queryKeys.health.telegram(),
  queryFn: healthApi.fetchTelegramStatus,
  staleTime: 30_000, // Use 30s stale for Dashboard card (TopBar uses 0)
});

const { data: cacheData } = useQuery({
  queryKey: queryKeys.health.cache(),
  queryFn: healthApi.fetchCacheStatus,
  staleTime: 30_000,
});
```

Always display visual loading skeletons using Tailwind's `animate-pulse` boxes for a premium, non-flashing layout structure.

### Stats Summary API Module

Create `web/src/api/stats.ts`:
```typescript
import { apiClient } from "./client";

export interface StatsSummary {
  forwarded_24h: number;
  failed_24h: number;
  blocked_24h: number;
}

export const statsApi = {
  fetchSummary: async (): Promise<StatsSummary> => {
    const { data } = await apiClient.get<StatsSummary>("/stats/summary");
    return data;
  },
};
```

### Logs Recent API Module

Create `web/src/api/logs.ts`:
```typescript
import { apiClient } from "./client";
import type { LogEntry } from "@/types/ui";

export interface LogsRecentResponse {
  items: LogEntry[];
}

export const logsApi = {
  fetchRecent: async (limit = 20): Promise<LogsRecentResponse> => {
    const { data } = await apiClient.get<LogsRecentResponse>("/logs/recent", {
      params: { limit },
    });
    return data;
  },
};
```

### Rules API Module (Stub)

Create `web/src/api/rules.ts` — minimal stub to enable first-run detection. Story 6-4 will extend this substantially:
```typescript
import { apiClient } from "./client";

export interface RulesListResponse {
  items: unknown[];
  total: number;
  page: number;
  page_size: number;
}

export const rulesApi = {
  fetchRules: async (params?: { page?: number; page_size?: number }): Promise<RulesListResponse> => {
    const { data } = await apiClient.get<RulesListResponse>("/rules", { params });
    return data;
  },
};
```

> **Important for Story 6-4**: When that story implements the full Forward List screen, it should extend `web/src/api/rules.ts` without breaking this stub's `fetchRules` signature.

### Dashboard Component Structure (Recommended)

```tsx
// web/src/pages/Dashboard.tsx
import { useQuery } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import { healthApi } from "@/api/health";
import { statsApi } from "@/api/stats";
import { logsApi } from "@/api/logs";
import { rulesApi } from "@/api/rules";
import { queryKeys } from "@/lib/queryKeys";
import { LogRow } from "@/components/shared";
import { ActivationBanner } from "@/components/shared";
// ... other imports

export default function Dashboard() {
  const navigate = useNavigate();
  
  const { data: telegramData, isLoading: isTelegramLoading } = useQuery({...});
  const { data: cacheData, isLoading: isCacheLoading } = useQuery({...});
  const { data: statsData, isLoading: isStatsLoading } = useQuery({
    queryKey: queryKeys.stats.summary(),
    queryFn: statsApi.fetchSummary,
    staleTime: 60_000,
  });
  const { data: logsData, isLoading: isLogsLoading } = useQuery({
    queryKey: queryKeys.logs.recent(),
    queryFn: () => logsApi.fetchRecent(20),
    staleTime: 10_000,
  });
  const { data: rulesData } = useQuery({
    queryKey: queryKeys.rules.list(),
    queryFn: () => rulesApi.fetchRules({ page_size: 1 }),
    staleTime: 30_000,
  });

  const isFirstRun = rulesData?.total === 0;

  return (
    <div>
      {isFirstRun && (
        <ActivationBanner isActive={false} onActivate={() => {}} isFirstRun={true} onCreateRule={() => navigate("/forwards/new")} />
      )}
      {/* health cards, stats panel, activity panel with loading skeletons */}
    </div>
  );
}
```

### Settings Component Structure (Recommended)

```tsx
// web/src/pages/Settings.tsx
import { useTheme } from "@/contexts/ThemeContext";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { healthApi } from "@/api/health";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "sonner";
import { useEffect, useState } from "react";

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [sessionUptime, setSessionUptime] = useState<string>("0s");

  useEffect(() => {
    const startTime = Date.now();
    const timer = setInterval(() => {
      const diff = Math.floor((Date.now() - startTime) / 1000);
      const hours = Math.floor(diff / 3600);
      const minutes = Math.floor((diff % 3600) / 60);
      const seconds = diff % 60;
      setSessionUptime(`${hours}h ${minutes}m ${seconds}s`);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const { data: healthData } = useQuery({
    queryKey: queryKeys.health.status(),
    queryFn: healthApi.fetchHealth,
    staleTime: 30_000,
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => navigate("/login"),
    onError: () => toast.error("Logout failed — please try again."),
  });

  return (
    <div>
      {/* Theme toggle: System / Light / Dark */}
      {/* Service info: version, sessionUptime (client uptime), MongoDB connection status badge */}
      {/* Logout button */}
    </div>
  );
}
```

### Tailwind v4 Color Utilities

**CRITICAL**: This project uses Tailwind v4. The `color-` prefix is stripped from CSS variable names in utility classes:
- `text-active` → uses `var(--color-active)` ✅
- `bg-success-bg` → uses `var(--color-success-bg)` ✅
- `bg-error-bg` → uses `var(--color-error-bg)` ✅
- `text-warning-foreground` → uses `var(--color-warning-foreground)` ✅
- `text-muted-foreground` → Tailwind built-in uses `var(--muted-foreground)` = `var(--color-text-secondary)` ✅

Do NOT use: `text-color-active`, `bg-color-success-bg`, etc.

### Reusing Shared Components

Import from the barrel file:
```tsx
import { LogRow, ActivationBanner, StatusPill } from "@/components/shared";
```

All 7 shared components (+ Button, Sheet) are exported from `web/src/components/shared/index.ts`.

### LogEntry Type

```typescript
// Already defined in web/src/types/ui.ts (from Story 6-2)
export interface LogEntry {
  event: string;
  level: "debug" | "info" | "warning" | "error" | "critical";
  timestamp: string;
  correlation_id?: string;
  rule_id?: string;
  [key: string]: unknown;
}
```

Use `logsApi.fetchRecent()` which returns `{ items: LogEntry[] }`. Pass each item directly to `<LogRow entry={item} />`.

### Loading and Error States

Always handle `isLoading` and `error` states for each `useQuery` call:
- For `isLoading`: render skeleton/spinner placeholders (use `animate-pulse` Tailwind class on placeholder divs)
- For errors: render a simple error card with a retry button (use `refetch()` from the query result)
- Do not crash the entire page on partial data failures — each card/panel should degrade independently

### TypeScript Strict Mode

This project has TypeScript strict mode enabled. Avoid `any` types. Define explicit interfaces for all API response shapes. The `npm run build` final verification gate must pass with zero errors.

---

## Previous Story Intelligence

From Story 6-2 (done, commit `17d3458`):
- **7 shared components implemented** in `web/src/components/shared/`: `Tooltip`, `DegradedBanner` (presentational), `LogRow`, `FilterIconRow`, `StatusPill`, `CollapsiblePanel`, `ActivationBanner`.
- **Barrel export** at `web/src/components/shared/index.ts` — import from here.
- **TypeScript interfaces** defined in `web/src/types/ui.ts`: `LogEntry`, `FilterConfig`, `StatusPillStatus`.
- **ActivationBanner** props: `isActive: boolean`, `onActivate: () => void`, optional `isFirstRun?: boolean`, optional `onCreateRule?: () => void`.
- **LogRow** uses the `LogEntry` interface and maps event names to visual variants automatically.
- **CollapsiblePanel** accepts `title`, `summary`, `children`, optional `defaultOpen?: boolean`.
- **Tailwind v4 naming confirmed**: `text-active`, `bg-error-bg`, `border-warning-border` — no `color-` prefix in utility classes.
- **Sonner toast** (`import { toast } from "sonner"`) is the toast library.
- **`cn()` utility** from `@/lib/utils` for conditional class composition.
- **No Redux/Zustand** — only `ThemeContext` + (future) `SseContext` are global contexts.

From Story 6-1 (done, commit `38a29fe`):
- **`useTheme()`** from `@/contexts/ThemeContext` provides `theme: "light" | "dark" | "system"` and `setTheme()`.
- **`useAuth()`** from `@/hooks/useAuth` provides `isAuthenticated`, `isLoading`.
- **`apiClient`** from `@/api/client` — Axios instance with `baseURL: "/api/v1"` and `withCredentials: true`.
- **`queryKeys`** from `@/lib/queryKeys` — centralized key factory; `stats.summary()`, `logs.recent()`, `rules.list()` keys already defined.
- **`useNavigate()`** from `react-router-dom` is available in any component rendered within `BrowserRouter`.
- **Layout shell** (`components/layout/Layout.tsx`) renders `DegradedBanner` globally — no duplicate needed in Dashboard.

### Files Created/Modified in Story 6-2

```
web/src/
├── types/ui.ts                         ← LogEntry, FilterConfig, StatusPillStatus interfaces
└── components/
    └── shared/
        ├── index.ts                    ← Barrel export for all shared components
        ├── Tooltip.tsx
        ├── DegradedBanner.tsx          ← Presentational, props-driven (DISTINCT from layout version)
        ├── LogRow.tsx
        ├── FilterIconRow.tsx
        ├── StatusPill.tsx
        ├── CollapsiblePanel.tsx
        └── ActivationBanner.tsx
```

---

## Git Intelligence

```
17d3458  story 6-2 done  (Shared UI Component Library — 7 new components in components/shared/)
38a29fe  6-1 story done  (React SPA foundation, brand tokens, auth, layout)
424cecd  epic 5 completed
abe83bc  story 5-3 done  (SSE log broadcaster + stats/log API endpoints)
b534983  story 5-2 done  (Full structlog chain, ring buffer, event catalog)
```

---

## Project Structure Notes

- Backend project root: `forward-bot/` (contains `pyproject.toml`, `src/`)
- Frontend project root: `web/` (contains `package.json`, `src/`)
- Story files: `_bmad-output/implementation-artifacts/`
- Planning artifacts: `_bmad-output/planning-artifacts/`

### Files to Create

```
web/src/
├── api/
│   ├── stats.ts      ← NEW: fetchStats() → GET /stats/summary
│   ├── logs.ts       ← NEW: fetchRecentLogs(limit) → GET /logs/recent
│   └── rules.ts      ← NEW: fetchRules(params?) → GET /rules (minimal stub)
└── pages/
    ├── Dashboard.tsx  ← REPLACE stub: full S1 implementation
    └── Settings.tsx   ← REPLACE stub: full S8 implementation
```

### Files to Modify

```
web/src/
├── api/health.ts         ← EXTEND: add fetchHealth() → GET /health
└── lib/queryKeys.ts      ← EXTEND: add health.status() key
```

No backend changes are required for this story. All work is frontend-only. The required backend API endpoints are all implemented in previous epics.

### References

- [Story 6.3 Acceptance Criteria in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L1086-L1116)
- [UX-DR3 (DegradedBanner)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L191-L193)
- [UX-DR22 (Theme Toggle)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L229-L230)
- [FR-44 (SSE + Logs endpoints)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L105-L106)
- [Existing Layout (global DegradedBanner)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/layout/Layout.tsx)
- [Existing ThemeContext](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/contexts/ThemeContext.tsx)
- [Existing queryKeys.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/lib/queryKeys.ts)
- [Existing health.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/health.ts)
- [Existing tokens.css](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/styles/tokens.css)
- [Story 6-2 implementation](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/implementation-artifacts/6-2-shared-ui-component-library.md)

---

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Flash)

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created.
- Implemented frontend API files: `stats.ts`, `logs.ts`, and `rules.ts`.
- Extended `health.ts` and `queryKeys.ts` with `/health` route query support.
- Fully implemented S1 Dashboard screen with live status indicators, pulse skeleton loaders, 24h summary stats, and recent activity log stream.
- Fully implemented S8 Settings screen with theme selector (system/light/dark), live client-uptime timer, versioning details, DB status badges, session TTL, and logout mutation.
- Verified successful production build of the frontend package with zero compilation/TS errors.

### File List

- [NEW] [stats.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/stats.ts)
- [NEW] [logs.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/logs.ts)
- [NEW] [rules.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/rules.ts)
- [MODIFY] [health.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/api/health.ts)
- [MODIFY] [queryKeys.ts](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/lib/queryKeys.ts)
- [MODIFY] [Dashboard.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/Dashboard.tsx)
- [MODIFY] [Settings.tsx](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/pages/Settings.tsx)

### Change Log

- Addressed story 6.3 implementation. Added new Dashboard and Settings screens along with backend API client layers. Build compiles successfully.

### Review Findings
- [x] [Review][Patch] Missing `active_rules` in StatsSummary / Dashboard — Dashboard expects active rule count from stats, but interface and usage are missing it [web/src/api/stats.ts]
- [x] [Review][Patch] Dashboard First-Run Flash — `isFirstRun` calculation does not explicitly account for `isLoading`, causing a potential flash of content [web/src/pages/Dashboard.tsx]
- [x] [Review][Patch] Verify raw axios in health.ts — AC requires raw axios for /health to avoid /api/v1 prefix mapping errors [web/src/api/health.ts]
- [x] [Review][Defer] ServiceVersion Fallback UX — "0.1.0" fallback masks missing version data [web/src/pages/Settings.tsx] — deferred, pre-existing
- [x] [Review][Defer] Client Session Timer Resets — Timer tracks component mount time rather than true session uptime [web/src/pages/Settings.tsx] — deferred, pre-existing
