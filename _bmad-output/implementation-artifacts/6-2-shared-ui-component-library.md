---
baseline_commit: 38a29fe57a82ebb69bc7a2f1a0d5ef1c94c5710a
---
# Story 6.2: Shared UI Component Library

Status: done

## Story

As a **Channel Operator**,
I want all recurring UI elements — degraded banners, log rows, filter icon rows, status pills, collapsible panels, and activation banners — implemented as reusable components with full accessibility support,
so that every screen is visually consistent and usable with keyboard and screen readers.

## Acceptance Criteria

1. **DegradedBanner Component (UX-DR3):**
   - **Given** the component library exists in `web/src/components/shared/`.
   - **When** `DegradedBanner` is rendered with `message` and `onReconnect` props.
   - **Then** it renders with `--color-degraded-bg` background (`bg-degraded-bg`), `--color-degraded-border` border (`border-degraded-border`), `--color-degraded-foreground` text (`text-degraded-foreground`); full-width, `border-radius: 0`; non-dismissible.
   - **And** it renders with `role="alert"` and `aria-live="assertive"`.
   - **And** it accepts and renders `message: string` prop and `onReconnect: () => void` prop for the `[Reconnect]` button.
   - **And** this standalone `DegradedBanner` in `components/shared/` is distinct from the existing `components/layout/DegradedBanner.tsx` which is a self-contained, data-fetching banner — the shared version is a pure presentational component accepting props.

2. **LogRow Component (UX-DR4):**
   - **Given** `LogRow` is rendered with a `LogEntry` prop.
   - **When** the `event` type maps to a known variant.
   - **Then** the row renders: 4px left accent stripe, lucide icon (matching the variant), bold event label, monospace payload preview, right-aligned timestamp.
   - **And** eight variants are implemented based on event name matching:
     - `forwarded` → success stripe + `ArrowUpRight` icon (green)
     - `filter_blocked` → muted stripe + `CircleSlash` icon (muted)
     - `telegram_rejected` → error stripe + `AlertTriangle` icon (red)
     - `destination_unreachable` → error stripe + `Ban` icon (red)
     - `flood_wait` → warning stripe + `Clock` icon (amber)
     - `edit_propagated` → success stripe + `Pencil` icon (green)
     - `delete_propagated` → success stripe + `Trash2` icon (green)
     - `reply_orphaned` → warning stripe + `CornerDownRight` icon with strikethrough modifier (amber)
     - All other events → default neutral stripe + `Info` icon
   - **And** `LogRow` supports an expandable inline detail panel: clicking the row toggles display of the full raw JSON payload + a `correlation_id` copy button; if `rule_id` is present, a "Jump to rule →" link appears (clicking this link must use `e.stopPropagation()` to prevent toggling the panel).

3. **FilterIconRow Component (UX-DR5):**
   - **Given** `FilterIconRow` is rendered with a rule's filter configuration object.
   - **When** filters are active.
   - **Then** four lucide icons render in order: `Clock` (time_window), `Shuffle` (sampling), `Image` (media_type_filter), `Key` (keyword filters — block_keywords or allow_keywords).
   - **And** active filters render icon in `--color-active` (green, class `text-active`) at full opacity; inactive filters render in `--color-text-secondary` at 40% opacity (class `text-secondary opacity-40`).
   - **And** each icon has a hover Tooltip describing the configured value (e.g., `"Mon–Fri 09:00–17:00 Europe/Warsaw"` for time_window, `"Every 3rd message"` for sampling) using a custom `Tooltip` component built in `web/src/components/shared/Tooltip.tsx`.
   - **And** each icon hit area is a minimum of `24×24px`.

4. **StatusPill Component (UX-DR6):**
   - **Given** `StatusPill` is rendered with a `status` prop.
   - **When** `status` is `"active"`.
   - **Then** it renders pill-success: tinted green background (`bg-success-bg`), green border (`border-success-border`), green foreground (`text-success-foreground`), `CheckCircle2` icon + "Active" label.
   - **And** `status="inactive"` renders neutral pill: muted background, muted border, muted foreground, `Circle` icon + "Inactive" label.
   - **And** `status="error"` renders error pill: `bg-error-bg`, `border-error-border`, `text-error` foreground, `AlertCircle` icon + "Error" label.
   - **And** `status="stale"` renders cache-stale pill: `bg-warning-bg`, `border-warning-border`, `text-warning-foreground`, `Clock` icon + "Stale" label.
   - **And** every variant always shows icon + label, never color alone (accessibility requirement).

5. **CollapsiblePanel Component (UX-DR7):**
   - **Given** `CollapsiblePanel` is rendered with `title`, `summary`, and `children` props.
   - **When** the component mounts.
   - **Then** it renders collapsed by default; the header shows `title` + `summary` string in `--color-text-secondary`.
   - **And** clicking the panel header or pressing `Enter`/`Space` on it toggles the panel body open/closed.
   - **And** the chevron icon animates (rotates 180°) on open/close.
   - **And** the trigger element has `aria-expanded` toggled between `true`/`false` and `aria-controls` pointing to the panel body ID; the panel body has a matching `id`.
   - **And** the expand/collapse transition uses a CSS Grid row template height transition (`grid-template-rows` transitioning between `0fr` and `1fr`, with the inner content wrapped in an `overflow-hidden` container).
   - **And** multiple `CollapsiblePanel` instances can be open simultaneously (no accordion behavior).
   - **And** `CollapsiblePanel` accepts an optional `defaultOpen?: boolean` prop (defaults to `false`).

6. **ActivationBanner Component (UX-DR8):**
   - **Given** `ActivationBanner` is rendered with `isActive: boolean` and `onActivate: () => void` props.
   - **When** `isActive` is `false`.
   - **Then** the banner renders using a warning-tinted layout container with custom CSS classes (`bg-warning-bg`, `border-warning-border`, `text-warning-foreground`); copy reads `"This forward is inactive. Activate to begin processing."`; an `[Activate]` button calls `onActivate`.
   - **When** `isActive` is `true`.
   - **Then** the banner does not render (returns `null`).
   - **And** the `ActivationBanner` is also used on the Dashboard to show first-run guidance when `isFirstRun={true}` — when no forwarding rules exist, it renders with a "Create your first rule" CTA that navigates to `/forwards/new`; `isFirstRun` prop overrides the `isActive` variant rendering.

7. **Accessibility Floor (UX-DR21):**
   - **Given** all shared components are reviewed.
   - **When** each component is rendered.
   - **Then** minimum 4.5:1 contrast ratio for all text/background color pairs.
   - **And** `aria-label` is present on all icon-only interactive elements.
   - **And** keyboard focus rings are visible in both `data-theme="light"` and `data-theme="dark"` using the CSS `--ring` token via `focus-visible:ring-2 focus-visible:ring-ring`.
   - **And** semantic HTML is used: `<button>` for all interactive triggers, `role="alert"` + `aria-live="assertive"` on `DegradedBanner`, `aria-expanded` + `aria-controls` on `CollapsiblePanel`.

8. **Component Exports:**
   - **Given** all components are implemented.
   - **When** `web/src/components/shared/index.ts` is reviewed.
   - **Then** all shared components are exported from a single barrel file: `DegradedBanner`, `LogRow`, `FilterIconRow`, `StatusPill`, `CollapsiblePanel`, `ActivationBanner`, `Tooltip`.
   - **And** TypeScript interfaces for all component props are defined and exported from the same barrel or a `web/src/types/ui.ts` file.

9. **Build Verification:**
   - **Given** all components are implemented.
   - **When** `npm run build` is executed in `web/`.
   - **Then** the build completes with zero TypeScript errors.

---

## Tasks / Subtasks

- [x] **1. Tooltip Component**
  - [x] Create `web/src/components/shared/Tooltip.tsx` implementing a lightweight React tooltip wrapper (e.g., hover/focus triggered overlay using React state or absolute positioning) for descriptive hovers
  - [x] Ensure full screen-reader and keyboard focus accessibility

- [x] **2. DegradedBanner (presentational, props-driven)** (AC: 1)
  - [x] Create `web/src/components/shared/DegradedBanner.tsx` as a pure presentational component with `message: string` and `onReconnect: () => void` props
  - [x] Apply `bg-degraded-bg`, `border-degraded-border`, `text-degraded-foreground` classes; `role="alert"`; `aria-live="assertive"` full-width, no border-radius

- [x] **3. LogRow Component** (AC: 2)
  - [x] Define `LogEntry` TypeScript interface in `web/src/types/ui.ts` (fields: `event`, `level`, `timestamp`, `correlation_id?`, `rule_id?`, `payload?: Record<string, unknown>`)
  - [x] Create `web/src/components/shared/LogRow.tsx` with variant → icon/stripe mapping for all 8 event types + default
  - [x] Implement expandable detail panel: click toggles full JSON payload view + correlation_id copy button + "Jump to rule →" link if rule_id present
  - [x] Call `e.stopPropagation()` on the rule link click to prevent row expansion toggling

- [x] **4. FilterIconRow Component** (AC: 3)
  - [x] Define `FilterConfig` TypeScript interface (fields: `time_window?`, `sampling?`, `media_type_filter?`, `block_keywords?`, `allow_keywords?`)
  - [x] Create `web/src/components/shared/FilterIconRow.tsx` with Clock/Shuffle/Image/Key icons; active = `text-active`, inactive = `text-secondary opacity-40`
  - [x] Wrap each filter icon in the custom `Tooltip` component with descriptive configuration hover text; ensure 24×24px minimum hit area

- [x] **5. StatusPill Component** (AC: 4)
  - [x] Create `web/src/components/shared/StatusPill.tsx` with `status: "active" | "inactive" | "error" | "stale"` prop
  - [x] Implement 4 pill variants using exact state token utility classes; always include icon + label

- [x] **6. CollapsiblePanel Component** (AC: 5)
  - [x] Create `web/src/components/shared/CollapsiblePanel.tsx` with `title`, `summary`, `children`, and optional `defaultOpen` props
  - [x] Implement smooth CSS height transition utilizing Tailwind grid template rows (`grid-rows-[0fr]` to `grid-rows-[1fr]`); transition the chevron icon rotation (`rotate-180` when open); wire `aria-expanded` and `aria-controls`
  - [x] Use a stable `id` (derived from `title` or passed as prop) for `aria-controls` → `id` linkage

- [x] **7. ActivationBanner Component** (AC: 6)
  - [x] Create `web/src/components/shared/ActivationBanner.tsx` with `isActive`, `onActivate`, and optional `isFirstRun` + `onCreateRule` props
  - [x] Render `null` when `isActive=true` and `isFirstRun` is not set; render warning alert using custom Tailwind utility classes (`bg-warning-bg`, `border-warning-border`, `text-warning-foreground`) when `isActive=false`; render first-run CTA when `isFirstRun=true`

- [x] **8. Barrel Export + Types** (AC: 8)
  - [x] Create/update `web/src/components/shared/index.ts` to export all 7 components (including `Tooltip`)
  - [x] Create `web/src/types/ui.ts` with exported TypeScript interfaces: `LogEntry`, `FilterConfig`, `StatusPillStatus`

- [x] **9. Verify Build** (AC: 9)
  - [x] Run `npm run build` in `web/` — must complete with zero TypeScript errors

### Review Findings

- [x] [Review][Patch] Missing disabled/loading state for banner actions — Both DegradedBanner's [Reconnect] and ActivationBanner's [Activate] lack disabled state to prevent multi-clicking.
- [x] [Review][Patch] LogRow Expansion Keyboard Accessibility Missing [web/src/components/shared/LogRow.tsx:179]
- [x] [Review][Patch] CollapsiblePanel content not strictly hidden from screen readers [web/src/components/shared/CollapsiblePanel.tsx:43]
- [x] [Review][Patch] formatTimestamp gracefully failing on invalid dates [web/src/components/shared/LogRow.tsx:116]

---

## Dev Notes

### Critical: Shared vs. Layout DegradedBanner — DO NOT CONFUSE

The existing `web/src/components/layout/DegradedBanner.tsx` is a **self-contained data-fetching component** that calls the health APIs internally and conditionally renders itself. **Do NOT modify it.**

Story 6-2 requires a **separate, presentational** `DegradedBanner` in `web/src/components/shared/DegradedBanner.tsx` that:
- Accepts `message: string` and `onReconnect: () => void` props
- Is always rendered when mounted (no internal condition based on fetched data)
- Is intended for use in specific contexts like the Logs screen SSE disconnection state (Story 6-6) and the Settings screen

### Tailwind v4 Color Utility Naming

**CRITICAL**: This project uses Tailwind v4. In Tailwind v4, the `color-` prefix is stripped from CSS variable names when generating utility classes. The tokens are defined as `--color-active`, `--color-error`, etc.

- Use `text-active` NOT `text-color-active`
- Use `bg-error-bg` NOT `bg-color-error-bg`
- Use `border-warning-border` NOT `border-color-warning-border`
- Use `text-degraded-foreground` NOT `text-color-degraded-foreground`

This is confirmed by the existing `DegradedBanner.tsx` which uses `bg-degraded-bg`, `border-degraded-border`, `text-degraded-foreground`, `text-error`.

### LogRow Event-to-Variant Mapping

Map event names from the catalog (FR-27) to visual variants:

```typescript
const VARIANT_MAP: Record<string, LogRowVariant> = {
  // Success (green) variants
  forward_succeeded: "forwarded",
  edit_propagated: "edit_propagated",
  delete_propagated: "delete_propagated",
  
  // Filter blocked (muted) variants
  pipeline_blocked: "filter_blocked",
  outside_time_window: "filter_blocked",
  sampled_out: "filter_blocked",
  media_type_filtered: "filter_blocked",
  blocked_keyword: "filter_blocked",
  no_allow_keyword_matched: "filter_blocked",
  empty_after_processing: "filter_blocked",
  unsupported_media_type: "filter_blocked",
  
  // Error variants
  forward_failed: "telegram_rejected",
  media_replacement_failed: "telegram_rejected",
  telegram_session_invalidated: "telegram_rejected",
  
  // Warning variants
  flood_wait: "flood_wait",
  reply_parent_not_found: "reply_orphaned",
  reply_target_missing: "reply_orphaned",
};
```

Each variant maps to:
| Variant | Stripe Color | Icon | Icon Color |
|---|---|---|---|
| `forwarded` | `--color-success` | `ArrowUpRight` | success |
| `filter_blocked` | `--color-muted` | `CircleSlash` | muted |
| `telegram_rejected` | `--color-error` | `AlertTriangle` | error |
| `destination_unreachable` | `--color-error` | `Ban` | error |
| `flood_wait` | `--color-warning` | `Clock` | warning |
| `edit_propagated` | `--color-success` | `Pencil` | success |
| `delete_propagated` | `--color-success` | `Trash2` | success |
| `reply_orphaned` | `--color-warning` | `CornerDownRight` | warning (with `line-through` on label) |
| `default` | `--color-border` | `Info` | muted |

### LogRow Data Shape

The backend log events from the ring buffer (Story 5.2) are structured JSON. A typical entry looks like:
```json
{
  "event": "forward_succeeded",
  "level": "info",
  "timestamp": "2026-06-25T10:32:11Z",
  "correlation_id": "a3f9b2c1",
  "rule_id": "6831f4e2a3b1c4d5e6f7a8b9",
  "source_message_id": 12345,
  "destination_message_id": 67890
}
```

The `LogEntry` TypeScript interface should be flexible enough to accommodate `unknown` extra fields via an index signature:
```typescript
export interface LogEntry {
  event: string;
  level: "debug" | "info" | "warning" | "error" | "critical";
  timestamp: string;
  correlation_id?: string;
  rule_id?: string;
  [key: string]: unknown; // for extra fields like source_message_id, etc.
}
```

### FilterIconRow Config Shape

Filter icons map to forwarding rule fields from the API. The `FilterConfig` interface:
```typescript
export interface FilterConfig {
  time_window?: {
    timezone: string;
    days_of_week: string[];
    start_time: string;
    end_time: string;
  };
  sampling?: {
    n: number;
  };
  media_type_filter?: string[];
  block_keywords?: string[];
  allow_keywords?: string[];
}
```

Tooltip text examples:
- `time_window` active: `"Mon–Fri 09:00–17:00 Europe/Warsaw"` (format days + time + timezone)
- `sampling` active: `"Every 3rd message"` (format "Every Nth message")
- `media_type_filter` active: `"photo, video"` (join array)
- keywords (block or allow): `"Keywords: 3 blocked, 2 allowed"` (count)

### CollapsiblePanel Animation (Tailwind CSS Grid Row Transition)

For a smooth transition without specifying fixed heights or max-heights, use:
```tsx
<div className={cn(
  "grid transition-all duration-300 ease-in-out",
  isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
)}>
  <div className="overflow-hidden">
    {children}
  </div>
</div>
```

### Tooltip Implementation

Since the project does not configure shadcn, implement a custom, highly reusable `Tooltip.tsx` inside `components/shared/` to support hover and focus states for filter config indicators:
```tsx
import React, { useState } from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div 
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div 
          className={cn(
            "absolute bottom-full left-1/2 z-50 mb-2 w-max max-w-xs -translate-x-1/2 rounded bg-black/90 px-2.5 py-1.5 text-xs text-white shadow-md animate-in fade-in duration-100",
            className
          )}
          role="tooltip"
        >
          {content}
        </div>
      )}
    </div>
  );
}
```

### Components Already in `components/shared/`

From Story 6-1, the following shared components already exist:
- `web/src/components/shared/Button.tsx` — custom Button
- `web/src/components/shared/Sheet.tsx` — mobile nav drawer

These are the only existing shared components. The new 7 components from this story should be added alongside them.

### Export Barrel Convention

The existing `components/shared/` directory does NOT yet have an `index.ts` barrel file. Create it as part of this story. After this story, it should export:
```typescript
export { DegradedBanner } from "./DegradedBanner";
export { LogRow } from "./LogRow";
export { FilterIconRow } from "./FilterIconRow";
export { StatusPill } from "./StatusPill";
export { CollapsiblePanel } from "./CollapsiblePanel";
export { ActivationBanner } from "./ActivationBanner";
export { Tooltip } from "./Tooltip";
// Existing ones:
export { Button } from "./Button";
export { Sheet } from "./Sheet";
```

### TypeScript Strict Mode

The project has TypeScript strict mode enabled (`web/tsconfig.json`). All component props must be typed explicitly — no `any`. The build verification (`npm run build`) is the final gating check.

### Existing Token Classes to Reuse

From the review findings of Story 6-1, Tailwind v4 utility classes in this project work as:
- `bg-success-bg` → `background-color: var(--color-success-bg)`
- `text-success-foreground` → `color: var(--color-success-foreground)`
- `border-success-border` → `border-color: var(--color-success-border)`
- `bg-warning-bg`, `text-warning-foreground`, `border-warning-border`
- `bg-error-bg`, `text-error`, `border-error-border`
- `text-muted-foreground` → Tailwind's built-in which maps to `--muted-foreground` (which is `--color-text-secondary`)
- `text-active` → maps to `--color-active`

Look at `Sidebar.tsx` for real usage examples of these classes.

---

## Previous Story Intelligence

From Story 6-1 (done, commit `38a29fe`):

- **Tailwind v4 class naming confirmed**: `text-error` (not `text-color-error`), `bg-error-bg` (not `bg-color-error-bg`). This is the #1 most critical thing to get right.
- **`DegradedBanner` in layout** already self-manages health polling — do NOT modify `components/layout/DegradedBanner.tsx`.
- **`useNavigate()`** from `react-router-dom` is available in any component rendered within `BrowserRouter`.
- **Sonner** (`import { toast } from "sonner"`) is the toast library — already installed.
- **lucide-react** is installed and provides all needed icons.
- **`cn()` utility** from `@/lib/utils` is available and should be used for conditional class composition.
- **`@/` path alias** is configured in `tsconfig.json` and resolves to `web/src/`.
- **No Redux/Zustand** — only `ThemeContext` and (future) `SseContext` are global contexts per architecture F3. Do not introduce any new global state.

### Files Created in Story 6-1

 the following files exist and should be imported/referenced by Story 6-2 components:
- `web/src/lib/queryKeys.ts` — centralized key factory
- `web/src/lib/queryClient.ts` — TanStack QueryClient instance
- `web/src/api/client.ts` — Axios instance (use `apiClient` named export)
- `web/src/contexts/ThemeContext.tsx` — `useTheme()` hook
- `web/src/hooks/useAuth.ts` — `useAuth()` hook for session checks
- `web/src/components/layout/DegradedBanner.tsx` — LEAVE UNTOUCHED

---

## Git Intelligence

```
38a29fe  6-1 story done  (Epic 6 Story 6.1 complete — React SPA foundation, brand tokens, auth, layout)
424cecd  epic 5 completed
abe83bc  story 5-3 done
b534983  story 5-2 completed
cdb0812  story 5-1 completed
```

Epic 6 Story 6.1 is the only Epic 6 story committed. The shared component library is the next logical step before building any data-driven screens, because all subsequent stories (6-3 through 6-6) will import from this library.

---

## Project Structure Notes

- Backend project root: `forward-bot/` (contains `pyproject.toml`, `src/`)
- Frontend project root: `web/` (contains `package.json`, `src/`)
- Implementations: `forward-bot/src/forward_bot/`
- Tests: `forward-bot/tests/`
- Planning artifacts: `_bmad-output/planning-artifacts/`
- Story files: `_bmad-output/implementation-artifacts/`

### New Files to Create

```
web/src/
├── types/
│   └── ui.ts                           ← NEW: LogEntry, FilterConfig, StatusPillStatus interfaces
├── components/
│   └── shared/
│       ├── index.ts                    ← NEW: barrel export for all shared components
│       ├── Tooltip.tsx                 ← NEW: custom Tooltip component
│       ├── DegradedBanner.tsx          ← NEW: presentational (props-driven), distinct from layout/DegradedBanner
│       ├── LogRow.tsx                  ← NEW: log event row with 8 variants + expandable detail
│       ├── FilterIconRow.tsx           ← NEW: 4-icon filter status row with custom Tooltips
│       ├── StatusPill.tsx              ← NEW: active/inactive/error/stale pill with icon+label
│       ├── CollapsiblePanel.tsx        ← NEW: accordion panel with animated chevron + ARIA + Grid height transition
│       └── ActivationBanner.tsx        ← NEW: rule-inactive warning + first-run CTA variant
```

No backend changes are required for this story. All work is frontend only.

### References

- [Story 6.2 Acceptance Criteria in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L1050-L1084)
- [UX-DR3 (DegradedBanner)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L191-L193)
- [UX-DR4 (LogRow)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L193-L194)
- [UX-DR5 (FilterIconRow)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L195-L196)
- [UX-DR6 (StatusPill)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L197-L198)
- [UX-DR7 (CollapsiblePanel)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L199-L200)
- [UX-DR8 (ActivationBanner)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L201-L202)
- [UX-DR21 (Accessibility Floor)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L227-L228)
- [FR-27 Event Catalog](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L69)
- [Existing DegradedBanner (layout)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/layout/DegradedBanner.tsx)
- [Existing tokens.css](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/styles/tokens.css)
- [Story 6-1 implementation](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/implementation-artifacts/6-1-react-spa-foundation-brand-tokens-app-layout-authentication.md)

---

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Flash)

### Completion Notes List

- Implemented 7 new shared presentational components: Tooltip, DegradedBanner, LogRow, FilterIconRow, StatusPill, CollapsiblePanel, and ActivationBanner in `web/src/components/shared/`.
- Created types definitions in `web/src/types/ui.ts`.
- Integrated all components in barrel export `web/src/components/shared/index.ts`.
- Validated build success via `npm run build` inside the `web` folder.
- Fully adhered to accessibility requirements (aria roles, aria labels, keyboard focus rings, semantic markup).
- Checked out and compiled production package with zero errors.
