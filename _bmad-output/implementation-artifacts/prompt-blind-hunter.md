Run the bmad-review-adversarial-general skill on this diff:

<diff>
diff --git a/_bmad-output/implementation-artifacts/6-2-shared-ui-component-library.md b/_bmad-output/implementation-artifacts/6-2-shared-ui-component-library.md
new file mode 100644
index 0000000..f345e0a
--- /dev/null
+++ b/_bmad-output/implementation-artifacts/6-2-shared-ui-component-library.md
@@ -0,0 +1,457 @@
+---
+baseline_commit: 38a29fe57a82ebb69bc7a2f1a0d5ef1c94c5710a
+---
+# Story 6.2: Shared UI Component Library
+
+Status: review
+
+## Story
+
+As a **Channel Operator**,
+I want all recurring UI elements ΓÇö degraded banners, log rows, filter icon rows, status pills, collapsible panels, and activation banners ΓÇö implemented as reusable components with full accessibility support,
+so that every screen is visually consistent and usable with keyboard and screen readers.
+
+## Acceptance Criteria
+
+1. **DegradedBanner Component (UX-DR3):**
+   - **Given** the component library exists in `web/src/components/shared/`.
+   - **When** `DegradedBanner` is rendered with `message` and `onReconnect` props.
+   - **Then** it renders with `--color-degraded-bg` background (`bg-degraded-bg`), `--color-degraded-border` border (`border-degraded-border`), `--color-degraded-foreground` text (`text-degraded-foreground`); full-width, `border-radius: 0`; non-dismissible.
+   - **And** it renders with `role="alert"` and `aria-live="assertive"`.
+   - **And** it accepts and renders `message: string` prop and `onReconnect: () => void` prop for the `[Reconnect]` button.
+   - **And** this standalone `DegradedBanner` in `components/shared/` is distinct from the existing `components/layout/DegradedBanner.tsx` which is a self-contained, data-fetching banner ΓÇö the shared version is a pure presentational component accepting props.
+
+2. **LogRow Component (UX-DR4):**
+   - **Given** `LogRow` is rendered with a `LogEntry` prop.
+   - **When** the `event` type maps to a known variant.
+   - **Then** the row renders: 4px left accent stripe, lucide icon (matching the variant), bold event label, monospace payload preview, right-aligned timestamp.
+   - **And** eight variants are implemented based on event name matching:
+     - `forwarded` ΓåÆ success stripe + `ArrowUpRight` icon (green)
+     - `filter_blocked` ΓåÆ muted stripe + `CircleSlash` icon (muted)
+     - `telegram_rejected` ΓåÆ error stripe + `AlertTriangle` icon (red)
+     - `destination_unreachable` ΓåÆ error stripe + `Ban` icon (red)
+     - `flood_wait` ΓåÆ warning stripe + `Clock` icon (amber)
+     - `edit_propagated` ΓåÆ success stripe + `Pencil` icon (green)
+     - `delete_propagated` ΓåÆ success stripe + `Trash2` icon (green)
+     - `reply_orphaned` ΓåÆ warning stripe + `CornerDownRight` icon with strikethrough modifier (amber)
+     - All other events ΓåÆ default neutral stripe + `Info` icon
+   - **And** `LogRow` supports an expandable inline detail panel: clicking the row toggles display of the full raw JSON payload + a `correlation_id` copy button; if `rule_id` is present, a "Jump to rule ΓåÆ" link appears (clicking this link must use `e.stopPropagation()` to prevent toggling the panel).
+
+3. **FilterIconRow Component (UX-DR5):**
+   - **Given** `FilterIconRow` is rendered with a rule's filter configuration object.
+   - **When** filters are active.
+   - **Then** four lucide icons render in order: `Clock` (time_window), `Shuffle` (sampling), `Image` (media_type_filter), `Key` (keyword filters ΓÇö block_keywords or allow_keywords).
+   - **And** active filters render icon in `--color-active` (green, class `text-active`) at full opacity; inactive filters render in `--color-text-secondary` at 40% opacity (class `text-secondary opacity-40`).
+   - **And** each icon has a hover Tooltip describing the configured value (e.g., `"MonΓÇôFri 09:00ΓÇô17:00 Europe/Warsaw"` for time_window, `"Every 3rd message"` for sampling) using a custom `Tooltip` component built in `web/src/components/shared/Tooltip.tsx`.
+   - **And** each icon hit area is a minimum of `24├ù24px`.
+
+4. **StatusPill Component (UX-DR6):**
+   - **Given** `StatusPill` is rendered with a `status` prop.
+   - **When** `status` is `"active"`.
+   - **Then** it renders pill-success: tinted green background (`bg-success-bg`), green border (`border-success-border`), green foreground (`text-success-foreground`), `CheckCircle2` icon + "Active" label.
+   - **And** `status="inactive"` renders neutral pill: muted background, muted border, muted foreground, `Circle` icon + "Inactive" label.
+   - **And** `status="error"` renders error pill: `bg-error-bg`, `border-error-border`, `text-error` foreground, `AlertCircle` icon + "Error" label.
+   - **And** `status="stale"` renders cache-stale pill: `bg-warning-bg`, `border-warning-border`, `text-warning-foreground`, `Clock` icon + "Stale" label.
+   - **And** every variant always shows icon + label, never color alone (accessibility requirement).
+
+5. **CollapsiblePanel Component (UX-DR7):**
+   - **Given** `CollapsiblePanel` is rendered with `title`, `summary`, and `children` props.
+   - **When** the component mounts.
+   - **Then** it renders collapsed by default; the header shows `title` + `summary` string in `--color-text-secondary`.
+   - **And** clicking the panel header or pressing `Enter`/`Space` on it toggles the panel body open/closed.
+   - **And** the chevron icon animates (rotates 180┬░) on open/close.
+   - **And** the trigger element has `aria-expanded` toggled between `true`/`false` and `aria-controls` pointing to the panel body ID; the panel body has a matching `id`.
+   - **And** the expand/collapse transition uses a CSS Grid row template height transition (`grid-template-rows` transitioning between `0fr` and `1fr`, with the inner content wrapped in an `overflow-hidden` container).
+   - **And** multiple `CollapsiblePanel` instances can be open simultaneously (no accordion behavior).
+   - **And** `CollapsiblePanel` accepts an optional `defaultOpen?: boolean` prop (defaults to `false`).
+
+6. **ActivationBanner Component (UX-DR8):**
+   - **Given** `ActivationBanner` is rendered with `isActive: boolean` and `onActivate: () => void` props.
+   - **When** `isActive` is `false`.
+   - **Then** the banner renders using a warning-tinted layout container with custom CSS classes (`bg-warning-bg`, `border-warning-border`, `text-warning-foreground`); copy reads `"This forward is inactive. Activate to begin processing."`; an `[Activate]` button calls `onActivate`.
+   - **When** `isActive` is `true`.
+   - **Then** the banner does not render (returns `null`).
+   - **And** the `ActivationBanner` is also used on the Dashboard to show first-run guidance when `isFirstRun={true}` ΓÇö when no forwarding rules exist, it renders with a "Create your first rule" CTA that navigates to `/forwards/new`; `isFirstRun` prop overrides the `isActive` variant rendering.
+
+7. **Accessibility Floor (UX-DR21):**
+   - **Given** all shared components are reviewed.
+   - **When** each component is rendered.
+   - **Then** minimum 4.5:1 contrast ratio for all text/background color pairs.
+   - **And** `aria-label` is present on all icon-only interactive elements.
+   - **And** keyboard focus rings are visible in both `data-theme="light"` and `data-theme="dark"` using the CSS `--ring` token via `focus-visible:ring-2 focus-visible:ring-ring`.
+   - **And** semantic HTML is used: `<button>` for all interactive triggers, `role="alert"` + `aria-live="assertive"` on `DegradedBanner`, `aria-expanded` + `aria-controls` on `CollapsiblePanel`.
+
+8. **Component Exports:**
+   - **Given** all components are implemented.
+   - **When** `web/src/components/shared/index.ts` is reviewed.
+   - **Then** all shared components are exported from a single barrel file: `DegradedBanner`, `LogRow`, `FilterIconRow`, `StatusPill`, `CollapsiblePanel`, `ActivationBanner`, `Tooltip`.
+   - **And** TypeScript interfaces for all component props are defined and exported from the same barrel or a `web/src/types/ui.ts` file.
+
+9. **Build Verification:**
+   - **Given** all components are implemented.
+   - **When** `npm run build` is executed in `web/`.
+   - **Then** the build completes with zero TypeScript errors.
+
+---
+
+## Tasks / Subtasks
+
+- [x] **1. Tooltip Component**
+  - [x] Create `web/src/components/shared/Tooltip.tsx` implementing a lightweight React tooltip wrapper (e.g., hover/focus triggered overlay using React state or absolute positioning) for descriptive hovers
+  - [x] Ensure full screen-reader and keyboard focus accessibility
+
+- [x] **2. DegradedBanner (presentational, props-driven)** (AC: 1)
+  - [x] Create `web/src/components/shared/DegradedBanner.tsx` as a pure presentational component with `message: string` and `onReconnect: () => void` props
+  - [x] Apply `bg-degraded-bg`, `border-degraded-border`, `text-degraded-foreground` classes; `role="alert"`; `aria-live="assertive"` full-width, no border-radius
+
+- [x] **3. LogRow Component** (AC: 2)
+  - [x] Define `LogEntry` TypeScript interface in `web/src/types/ui.ts` (fields: `event`, `level`, `timestamp`, `correlation_id?`, `rule_id?`, `payload?: Record<string, unknown>`)
+  - [x] Create `web/src/components/shared/LogRow.tsx` with variant ΓåÆ icon/stripe mapping for all 8 event types + default
+  - [x] Implement expandable detail panel: click toggles full JSON payload view + correlation_id copy button + "Jump to rule ΓåÆ" link if rule_id present
+  - [x] Call `e.stopPropagation()` on the rule link click to prevent row expansion toggling
+
+- [x] **4. FilterIconRow Component** (AC: 3)
+  - [x] Define `FilterConfig` TypeScript interface (fields: `time_window?`, `sampling?`, `media_type_filter?`, `block_keywords?`, `allow_keywords?`)
+  - [x] Create `web/src/components/shared/FilterIconRow.tsx` with Clock/Shuffle/Image/Key icons; active = `text-active`, inactive = `text-secondary opacity-40`
+  - [x] Wrap each filter icon in the custom `Tooltip` component with descriptive configuration hover text; ensure 24├ù24px minimum hit area
+
+- [x] **5. StatusPill Component** (AC: 4)
+  - [x] Create `web/src/components/shared/StatusPill.tsx` with `status: "active" | "inactive" | "error" | "stale"` prop
+  - [x] Implement 4 pill variants using exact state token utility classes; always include icon + label
+
+- [x] **6. CollapsiblePanel Component** (AC: 5)
+  - [x] Create `web/src/components/shared/CollapsiblePanel.tsx` with `title`, `summary`, `children`, and optional `defaultOpen` props
+  - [x] Implement smooth CSS height transition utilizing Tailwind grid template rows (`grid-rows-[0fr]` to `grid-rows-[1fr]`); transition the chevron icon rotation (`rotate-180` when open); wire `aria-expanded` and `aria-controls`
+  - [x] Use a stable `id` (derived from `title` or passed as prop) for `aria-controls` ΓåÆ `id` linkage
+
+- [x] **7. ActivationBanner Component** (AC: 6)
+  - [x] Create `web/src/components/shared/ActivationBanner.tsx` with `isActive`, `onActivate`, and optional `isFirstRun` + `onCreateRule` props
+  - [x] Render `null` when `isActive=true` and `isFirstRun` is not set; render warning alert using custom Tailwind utility classes (`bg-warning-bg`, `border-warning-border`, `text-warning-foreground`) when `isActive=false`; render first-run CTA when `isFirstRun=true`
+
+- [x] **8. Barrel Export + Types** (AC: 8)
+  - [x] Create/update `web/src/components/shared/index.ts` to export all 7 components (including `Tooltip`)
+  - [x] Create `web/src/types/ui.ts` with exported TypeScript interfaces: `LogEntry`, `FilterConfig`, `StatusPillStatus`
+
+- [x] **9. Verify Build** (AC: 9)
+  - [x] Run `npm run build` in `web/` ΓÇö must complete with zero TypeScript errors
+
+---
+
+## Dev Notes
+
+### Critical: Shared vs. Layout DegradedBanner ΓÇö DO NOT CONFUSE
+
+The existing `web/src/components/layout/DegradedBanner.tsx` is a **self-contained data-fetching component** that calls the health APIs internally and conditionally renders itself. **Do NOT modify it.**
+
+Story 6-2 requires a **separate, presentational** `DegradedBanner` in `web/src/components/shared/DegradedBanner.tsx` that:
+- Accepts `message: string` and `onReconnect: () => void` props
+- Is always rendered when mounted (no internal condition based on fetched data)
+- Is intended for use in specific contexts like the Logs screen SSE disconnection state (Story 6-6) and the Settings screen
+
+### Tailwind v4 Color Utility Naming
+
+**CRITICAL**: This project uses Tailwind v4. In Tailwind v4, the `color-` prefix is stripped from CSS variable names when generating utility classes. The tokens are defined as `--color-active`, `--color-error`, etc.
+
+- Use `text-active` NOT `text-color-active`
+- Use `bg-error-bg` NOT `bg-color-error-bg`
+- Use `border-warning-border` NOT `border-color-warning-border`
+- Use `text-degraded-foreground` NOT `text-color-degraded-foreground`
+
+This is confirmed by the existing `DegradedBanner.tsx` which uses `bg-degraded-bg`, `border-degraded-border`, `text-degraded-foreground`, `text-error`.
+
+### LogRow Event-to-Variant Mapping
+
+Map event names from the catalog (FR-27) to visual variants:
+
+```typescript
+const VARIANT_MAP: Record<string, LogRowVariant> = {
+  // Success (green) variants
+  forward_succeeded: "forwarded",
+  edit_propagated: "edit_propagated",
+  delete_propagated: "delete_propagated",
+  
+  // Filter blocked (muted) variants
+  pipeline_blocked: "filter_blocked",
+  outside_time_window: "filter_blocked",
+  sampled_out: "filter_blocked",
+  media_type_filtered: "filter_blocked",
+  blocked_keyword: "filter_blocked",
+  no_allow_keyword_matched: "filter_blocked",
+  empty_after_processing: "filter_blocked",
+  unsupported_media_type: "filter_blocked",
+  
+  // Error variants
+  forward_failed: "telegram_rejected",
+  media_replacement_failed: "telegram_rejected",
+  telegram_session_invalidated: "telegram_rejected",
+  
+  // Warning variants
+  flood_wait: "flood_wait",
+  reply_parent_not_found: "reply_orphaned",
+  reply_target_missing: "reply_orphaned",
+};
+```
+
+Each variant maps to:
+| Variant | Stripe Color | Icon | Icon Color |
+|---|---|---|---|
+| `forwarded` | `--color-success` | `ArrowUpRight` | success |
+| `filter_blocked` | `--color-muted` | `CircleSlash` | muted |
+| `telegram_rejected` | `--color-error` | `AlertTriangle` | error |
+| `destination_unreachable` | `--color-error` | `Ban` | error |
+| `flood_wait` | `--color-warning` | `Clock` | warning |
+| `edit_propagated` | `--color-success` | `Pencil` | success |
+| `delete_propagated` | `--color-success` | `Trash2` | success |
+| `reply_orphaned` | `--color-warning` | `CornerDownRight` | warning (with `line-through` on label) |
+| `default` | `--color-border` | `Info` | muted |
+
+### LogRow Data Shape
+
+The backend log events from the ring buffer (Story 5.2) are structured JSON. A typical entry looks like:
+```json
+{
+  "event": "forward_succeeded",
+  "level": "info",
+  "timestamp": "2026-06-25T10:32:11Z",
+  "correlation_id": "a3f9b2c1",
+  "rule_id": "6831f4e2a3b1c4d5e6f7a8b9",
+  "source_message_id": 12345,
+  "destination_message_id": 67890
+}
+```
+
+The `LogEntry` TypeScript interface should be flexible enough to accommodate `unknown` extra fields via an index signature:
+```typescript
+export interface LogEntry {
+  event: string;
+  level: "debug" | "info" | "warning" | "error" | "critical";
+  timestamp: string;
+  correlation_id?: string;
+  rule_id?: string;
+  [key: string]: unknown; // for extra fields like source_message_id, etc.
+}
+```
+
+### FilterIconRow Config Shape
+
+Filter icons map to forwarding rule fields from the API. The `FilterConfig` interface:
+```typescript
+export interface FilterConfig {
+  time_window?: {
+    timezone: string;
+    days_of_week: string[];
+    start_time: string;
+    end_time: string;
+  };
+  sampling?: {
+    n: number;
+  };
+  media_type_filter?: string[];
+  block_keywords?: string[];
+  allow_keywords?: string[];
+}
+```
+
+Tooltip text examples:
+- `time_window` active: `"MonΓÇôFri 09:00ΓÇô17:00 Europe/Warsaw"` (format days + time + timezone)
+- `sampling` active: `"Every 3rd message"` (format "Every Nth message")
+- `media_type_filter` active: `"photo, video"` (join array)
+- keywords (block or allow): `"Keywords: 3 blocked, 2 allowed"` (count)
+
+### CollapsiblePanel Animation (Tailwind CSS Grid Row Transition)
+
+For a smooth transition without specifying fixed heights or max-heights, use:
+```tsx
+<div className={cn(
+  "grid transition-all duration-300 ease-in-out",
+  isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
+)}>
+  <div className="overflow-hidden">
+    {children}
+  </div>
+</div>
+```
+
+### Tooltip Implementation
+
+Since the project does not configure shadcn, implement a custom, highly reusable `Tooltip.tsx` inside `components/shared/` to support hover and focus states for filter config indicators:
+```tsx
+import React, { useState } from "react";
+import { cn } from "@/lib/utils";
+
+interface TooltipProps {
+  content: React.ReactNode;
+  children: React.ReactElement;
+  className?: string;
+}
+
+export function Tooltip({ content, children, className }: TooltipProps) {
+  const [visible, setVisible] = useState(false);
+
+  return (
+    <div 
+      className="relative inline-block"
+      onMouseEnter={() => setVisible(true)}
+      onMouseLeave={() => setVisible(false)}
+      onFocus={() => setVisible(true)}
+      onBlur={() => setVisible(false)}
+    >
+      {children}
+      {visible && (
+        <div 
+          className={cn(
+            "absolute bottom-full left-1/2 z-50 mb-2 w-max max-w-xs -translate-x-1/2 rounded bg-black/90 px-2.5 py-1.5 text-xs text-white shadow-md animate-in fade-in duration-100",
+            className
+          )}
+          role="tooltip"
+        >
+          {content}
+        </div>
+      )}
+    </div>
+  );
+}
+```
+
+### Components Already in `components/shared/`
+
+From Story 6-1, the following shared components already exist:
+- `web/src/components/shared/Button.tsx` ΓÇö custom Button
+- `web/src/components/shared/Sheet.tsx` ΓÇö mobile nav drawer
+
+These are the only existing shared components. The new 7 components from this story should be added alongside them.
+
+### Export Barrel Convention
+
+The existing `components/shared/` directory does NOT yet have an `index.ts` barrel file. Create it as part of this story. After this story, it should export:
+```typescript
+export { DegradedBanner } from "./DegradedBanner";
+export { LogRow } from "./LogRow";
+export { FilterIconRow } from "./FilterIconRow";
+export { StatusPill } from "./StatusPill";
+export { CollapsiblePanel } from "./CollapsiblePanel";
+export { ActivationBanner } from "./ActivationBanner";
+export { Tooltip } from "./Tooltip";
+// Existing ones:
+export { Button } from "./Button";
+export { Sheet } from "./Sheet";
+```
+
+### TypeScript Strict Mode
+
+The project has TypeScript strict mode enabled (`web/tsconfig.json`). All component props must be typed explicitly ΓÇö no `any`. The build verification (`npm run build`) is the final gating check.
+
+### Existing Token Classes to Reuse
+
+From the review findings of Story 6-1, Tailwind v4 utility classes in this project work as:
+- `bg-success-bg` ΓåÆ `background-color: var(--color-success-bg)`
+- `text-success-foreground` ΓåÆ `color: var(--color-success-foreground)`
+- `border-success-border` ΓåÆ `border-color: var(--color-success-border)`
+- `bg-warning-bg`, `text-warning-foreground`, `border-warning-border`
+- `bg-error-bg`, `text-error`, `border-error-border`
+- `text-muted-foreground` ΓåÆ Tailwind's built-in which maps to `--muted-foreground` (which is `--color-text-secondary`)
+- `text-active` ΓåÆ maps to `--color-active`
+
+Look at `Sidebar.tsx` for real usage examples of these classes.
+
+---
+
+## Previous Story Intelligence
+
+From Story 6-1 (done, commit `38a29fe`):
+
+- **Tailwind v4 class naming confirmed**: `text-error` (not `text-color-error`), `bg-error-bg` (not `bg-color-error-bg`). This is the #1 most critical thing to get right.
+- **`DegradedBanner` in layout** already self-manages health polling ΓÇö do NOT modify `components/layout/DegradedBanner.tsx`.
+- **`useNavigate()`** from `react-router-dom` is available in any component rendered within `BrowserRouter`.
+- **Sonner** (`import { toast } from "sonner"`) is the toast library ΓÇö already installed.
+- **lucide-react** is installed and provides all needed icons.
+- **`cn()` utility** from `@/lib/utils` is available and should be used for conditional class composition.
+- **`@/` path alias** is configured in `tsconfig.json` and resolves to `web/src/`.
+- **No Redux/Zustand** ΓÇö only `ThemeContext` and (future) `SseContext` are global contexts per architecture F3. Do not introduce any new global state.
+
+### Files Created in Story 6-1
+
+ the following files exist and should be imported/referenced by Story 6-2 components:
+- `web/src/lib/queryKeys.ts` ΓÇö centralized key factory
+- `web/src/lib/queryClient.ts` ΓÇö TanStack QueryClient instance
+- `web/src/api/client.ts` ΓÇö Axios instance (use `apiClient` named export)
+- `web/src/contexts/ThemeContext.tsx` ΓÇö `useTheme()` hook
+- `web/src/hooks/useAuth.ts` ΓÇö `useAuth()` hook for session checks
+- `web/src/components/layout/DegradedBanner.tsx` ΓÇö LEAVE UNTOUCHED
+
+---
+
+## Git Intelligence
+
+```
+38a29fe  6-1 story done  (Epic 6 Story 6.1 complete ΓÇö React SPA foundation, brand tokens, auth, layout)
+424cecd  epic 5 completed
+abe83bc  story 5-3 done
+b534983  story 5-2 completed
+cdb0812  story 5-1 completed
+```
+
+Epic 6 Story 6.1 is the only Epic 6 story committed. The shared component library is the next logical step before building any data-driven screens, because all subsequent stories (6-3 through 6-6) will import from this library.
+
+---
+
+## Project Structure Notes
+
+- Backend project root: `forward-bot/` (contains `pyproject.toml`, `src/`)
+- Frontend project root: `web/` (contains `package.json`, `src/`)
+- Implementations: `forward-bot/src/forward_bot/`
+- Tests: `forward-bot/tests/`
+- Planning artifacts: `_bmad-output/planning-artifacts/`
+- Story files: `_bmad-output/implementation-artifacts/`
+
+### New Files to Create
+
+```
+web/src/
+Γö£ΓöÇΓöÇ types/
+Γöé   ΓööΓöÇΓöÇ ui.ts                           ΓåÉ NEW: LogEntry, FilterConfig, StatusPillStatus interfaces
+Γö£ΓöÇΓöÇ components/
+Γöé   ΓööΓöÇΓöÇ shared/
+Γöé       Γö£ΓöÇΓöÇ index.ts                    ΓåÉ NEW: barrel export for all shared components
+Γöé       Γö£ΓöÇΓöÇ Tooltip.tsx                 ΓåÉ NEW: custom Tooltip component
+Γöé       Γö£ΓöÇΓöÇ DegradedBanner.tsx          ΓåÉ NEW: presentational (props-driven), distinct from layout/DegradedBanner
+Γöé       Γö£ΓöÇΓöÇ LogRow.tsx                  ΓåÉ NEW: log event row with 8 variants + expandable detail
+Γöé       Γö£ΓöÇΓöÇ FilterIconRow.tsx           ΓåÉ NEW: 4-icon filter status row with custom Tooltips
+Γöé       Γö£ΓöÇΓöÇ StatusPill.tsx              ΓåÉ NEW: active/inactive/error/stale pill with icon+label
+Γöé       Γö£ΓöÇΓöÇ CollapsiblePanel.tsx        ΓåÉ NEW: accordion panel with animated chevron + ARIA + Grid height transition
+Γöé       ΓööΓöÇΓöÇ ActivationBanner.tsx        ΓåÉ NEW: rule-inactive warning + first-run CTA variant
+```
+
+No backend changes are required for this story. All work is frontend only.
+
+### References
+
+- [Story 6.2 Acceptance Criteria in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L1050-L1084)
+- [UX-DR3 (DegradedBanner)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L191-L193)
+- [UX-DR4 (LogRow)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L193-L194)
+- [UX-DR5 (FilterIconRow)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L195-L196)
+- [UX-DR6 (StatusPill)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L197-L198)
+- [UX-DR7 (CollapsiblePanel)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L199-L200)
+- [UX-DR8 (ActivationBanner)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L201-L202)
+- [UX-DR21 (Accessibility Floor)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L227-L228)
+- [FR-27 Event Catalog](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L69)
+- [Existing DegradedBanner (layout)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/components/layout/DegradedBanner.tsx)
+- [Existing tokens.css](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/web/src/styles/tokens.css)
+- [Story 6-1 implementation](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/implementation-artifacts/6-1-react-spa-foundation-brand-tokens-app-layout-authentication.md)
+
+---
+
+## Dev Agent Record
+
+### Agent Model Used
+
+Antigravity (Gemini 3.5 Flash)
+
+### Completion Notes List
+
+- Implemented 7 new shared presentational components: Tooltip, DegradedBanner, LogRow, FilterIconRow, StatusPill, CollapsiblePanel, and ActivationBanner in `web/src/components/shared/`.
+- Created types definitions in `web/src/types/ui.ts`.
+- Integrated all components in barrel export `web/src/components/shared/index.ts`.
+- Validated build success via `npm run build` inside the `web` folder.
+- Fully adhered to accessibility requirements (aria roles, aria labels, keyboard focus rings, semantic markup).
+- Checked out and compiled production package with zero errors.
diff --git a/_bmad-output/implementation-artifacts/sprint-status.yaml b/_bmad-output/implementation-artifacts/sprint-status.yaml
index e145684..3e10cc5 100644
--- a/_bmad-output/implementation-artifacts/sprint-status.yaml
+++ b/_bmad-output/implementation-artifacts/sprint-status.yaml
@@ -33,7 +33,7 @@
 # - Dev moves story to 'review', then runs code-review (fresh context, different LLM recommended)
 
 generated: "2026-06-02"
-last_updated: 2026-06-25T22:11:00+05:30
+last_updated: 2026-06-25T23:44:00+05:30
 work_started: "2026-06-02"
 work_completed: "2026-06-09"
 first_story_created: "2026-06-02"
@@ -98,7 +98,7 @@ development_status:
   epic-6: in-progress
 
   6-1-react-spa-foundation-brand-tokens-app-layout-authentication: done
-  6-2-shared-ui-component-library: backlog
+  6-2-shared-ui-component-library: review
   6-3-dashboard-s1-settings-s8-screens: backlog
   6-4-forwards-list-s2-forward-edit-s3-screens: backlog
   6-5-sources-list-s4-source-edit-s5-folder-modals-s6: backlog
@@ -117,10 +117,10 @@ summary:
   epics_in_progress: 1
   epics_done: 5
 
-  stories_backlog: 5
+  stories_backlog: 4
   stories_ready_for_dev: 0
   stories_in_progress: 0
-  stories_in_review: 0
+  stories_in_review: 1
   stories_done: 19
 
   retrospectives_optional: 1
diff --git a/diff.txt b/diff.txt
index 4508a49..0d6e6ac 100644
Binary files a/diff.txt and b/diff.txt differ
diff --git a/diff_utf8.txt b/diff_utf8.txt
index 6fe10ea..d46e7cc 100644
--- a/diff_utf8.txt
+++ b/diff_utf8.txt
@@ -1,1781 +0,0 @@
-∩╗┐diff --git a/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md b/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md
-index 162b2b7..a8df3b5 100644
---- a/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md
-+++ b/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md
-@@ -4,7 +4,7 @@ baseline_commit: 57848c6e377c8a087419ba5f23ff93b6c46e006b
- 
- # Story 3.2: Replacement Rule CRUD API
- 
--Status: review
-+Status: done
- 
- ## Story
- 
-@@ -145,6 +145,11 @@ so that **I can rewrite forwarded text ╬ô├ç├╢ removing competitor names, swapping l
-     - Cascade delete verified (parent delete removes children ╬ô├ç├╢ integration test)
-   - [x] All 182 tests pass (35 new + 147 regression ╬ô├ç├╢ 0 failures)
- 
-+### Review Findings
-+
-+- [x] [Review][Patch] Microsecond timestamp collision in pipeline sorting [forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py:70-81]
-+- [x] [Review][Patch] Missing `created_at` and `updated_at` optionality in response schema [forward-bot/src/forward_bot/api/schemas/replacement_rule.py:50-51]
-+
- ---
- 
- ## Dev Notes
-diff --git a/_bmad-output/implementation-artifacts/deferred-work.md b/_bmad-output/implementation-artifacts/deferred-work.md
-index 33a2081..27a964b 100644
---- a/_bmad-output/implementation-artifacts/deferred-work.md
-+++ b/_bmad-output/implementation-artifacts/deferred-work.md
-@@ -40,3 +40,12 @@ The epic spec does not cover what happens when `POST /api/v1/sources` is called
- - Raises `ValueError` for unknown references; `ChannelPrivateError` for private channels; `UsernameNotOccupiedError` for non-existent usernames ╬ô├ç├╢ all should map to `telegram_resolve_failed` (HTTP 422)
- - Rate limiting: Telegram allows ~30 resolve calls/second; safe for typical operator usage but document in dev notes
- 
-+## Deferred from: code review of 3-3-atomic-rule-cache-cache-refresher.md (2026-06-18)
-+
-+- ~~**Sequential O(N) database queries for replacement rules**~~: **RESOLVED** (2026-06-19, Epic 3 Retro)
-+  Added `ReplacementRuleRepository.list_all_replacements_for_rules(rule_ids)` ╬ô├ç├╢ a single `$in` query that fetches all replacement rules for all active rules in one MongoDB round-trip, then groups in-memory. `build_rule_cache` now performs exactly 4 DB queries regardless of rule count (was 4+N). `cache_refresher.py` updated; tests updated in `test_cache_refresher.py`.
-+
-+## Resolved during: Epic 3 Retrospective (2026-06-19)
-+
-+- **`_id`/`id` Pydantic v2 serialization-alias pattern documented**: `MongoBaseModel` docstring in `api/schemas/base.py` now contains the definitive two-pattern guide (Pattern A: alias-only subclass; Pattern B: subclass with extra `@field_validator`). Common mistakes listed. Prevents recurrence of the duplicate-validator Pydantic error in Epic 6 schemas.
-+
-diff --git a/_bmad-output/implementation-artifacts/diff-for-review.diff b/_bmad-output/implementation-artifacts/diff-for-review.diff
-index f9d423b..4e367da 100644
-Binary files a/_bmad-output/implementation-artifacts/diff-for-review.diff and b/_bmad-output/implementation-artifacts/diff-for-review.diff differ
-diff --git a/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md b/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md
-index e7143a1..c70cacd 100644
---- a/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md
-+++ b/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md
-@@ -1,9 +1,9 @@
- # Acceptance Auditor Review
- 
--You are an Acceptance Auditor. Review the diff in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\diff-for-review.diff` against the spec in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\3-1-forwarding-rule-crud-api.md`.
-+You are an Acceptance Auditor. Review the diff in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\diff-for-review.diff` against the spec in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\3-2-replacement-rule-crud-api.md`.
- 
- Check for:
--1. Violations of acceptance criteria (AC 1 through AC 14).
-+1. Violations of acceptance criteria (AC 1 through AC 9).
- 2. Deviations from spec intent.
- 3. Missing implementation of specified behavior.
- 4. Contradictions between spec constraints and actual code.
-diff --git a/_bmad-output/implementation-artifacts/sprint-status.yaml b/_bmad-output/implementation-artifacts/sprint-status.yaml
-index a1dff1a..a13c58b 100644
---- a/_bmad-output/implementation-artifacts/sprint-status.yaml
-+++ b/_bmad-output/implementation-artifacts/sprint-status.yaml
-@@ -1,7 +1,7 @@
- # Sprint Status Tracking for Forward Bot
- # =======================================
- # Generated: 2026-06-02
--# Last Updated: 2026-06-18
-+# Last Updated: 2026-06-19
- # Project: Forward Bot
- # Project Key: NOKEY
- # Tracking System: file-system
-@@ -33,7 +33,7 @@
- # - Dev moves story to 'review', then runs code-review (fresh context, different LLM recommended)
- 
- generated: "2026-06-02"
--last_updated: "2026-06-18"
-+last_updated: "2026-06-19"
- work_started: "2026-06-02"
- work_completed: "2026-06-09"
- first_story_created: "2026-06-02"
-@@ -66,18 +66,18 @@ development_status:
-   epic-2-retrospective: done
- 
-   # ===== EPIC 3: Forwarding Rule Configuration =====
--  epic-3: in-progress
-+  epic-3: done
- 
-   3-1-forwarding-rule-crud-api: done
--  3-2-replacement-rule-crud-api: review
--  3-3-atomic-rule-cache-cache-refresher: backlog
-+  3-2-replacement-rule-crud-api: done
-+  3-3-atomic-rule-cache-cache-refresher: done
- 
--  epic-3-retrospective: optional
-+  epic-3-retrospective: done
- 
-   # ===== EPIC 4: Core Message Forwarding Engine =====
--  epic-4: backlog
-+  epic-4: in-progress
- 
--  4-1-pipeline-infrastructure-context-protocol-engine-message-mapping: backlog
-+  4-1-pipeline-infrastructure-context-protocol-engine-message-mapping: review
-   4-2-filter-pipeline-steps-steps-1-5: backlog
-   4-3-transform-media-pipeline-steps-steps-6-16: backlog
-   4-4-telegram-delivery-reliability: backlog
-@@ -113,18 +113,18 @@ summary:
-   total_stories: 24
-   total_retrospectives: 6
- 
--  epics_backlog: 3
-+  epics_backlog: 2
-   epics_in_progress: 1
--  epics_done: 2
-+  epics_done: 3
- 
--  stories_backlog: 16
-+  stories_backlog: 14
-   stories_ready_for_dev: 0
-   stories_in_progress: 0
-   stories_in_review: 1
--  stories_done: 7
-+  stories_done: 9
- 
--  retrospectives_optional: 4
--  retrospectives_done: 2
-+  retrospectives_optional: 3
-+  retrospectives_done: 3
- 
- # STORY ORDERING & DEPENDENCIES
- # ==============================
-diff --git a/_bmad-output/implementation-artifacts/tests/test-summary.md b/_bmad-output/implementation-artifacts/tests/test-summary.md
-index 2c83813..b405724 100644
---- a/_bmad-output/implementation-artifacts/tests/test-summary.md
-+++ b/_bmad-output/implementation-artifacts/tests/test-summary.md
-@@ -2,9 +2,9 @@
- 
- **Framework:** pytest 9.0.3 + pytest-asyncio 1.4.0 (Python 3.13.3)  
- **Test Suites:**
--- E2E Tests: [`tests/e2e/test_epic1_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic1_e2e.py), [`tests/e2e/test_epic2_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic2_e2e.py)
--- API Tests: [`tests/api/test_folders.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_folders.py), [`tests/api/test_sources.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py), [`tests/api/test_health.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_health.py)
--- Repository & Client Tests: [`tests/infrastructure/mongo/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/)
-+- E2E Tests: [`tests/e2e/test_epic1_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic1_e2e.py), [`tests/e2e/test_epic2_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic2_e2e.py), [`tests/e2e/test_epic3_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic3_e2e.py)
-+- API Tests: [`tests/api/test_rules.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_rules.py), [`tests/api/test_replacement_rules.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_replacement_rules.py), [`tests/api/test_folders.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_folders.py), [`tests/api/test_sources.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py), [`tests/api/test_health.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_health.py)
-+- Repository & Client Tests: [`tests/infrastructure/mongo/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/), [`tests/infrastructure/cache/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/cache/)
- 
- ---
- 
-@@ -71,38 +71,108 @@
- 
- ---
- 
-+### Epic 3 ╬ô├ç├╢ Forwarding Rule Configuration
-+
-+#### E2E Workflow Test (`test_epic3_e2e_workflow`)
-+Single comprehensive test exercising the full HTTP ╬ô├Ñ├å use-case ╬ô├Ñ├å MockDatabase cycle:
-+
-+**Story 3.1 ╬ô├ç├╢ Forwarding Rule CRUD:**
-+- Auth gate enforcement (401 without API key).
-+- Create rule returns 201 with all 14 default fields verified.
-+- Duplicate `(source_id, destination_channel)` pairs permitted (no uniqueness constraint).
-+- Non-existent `source_id` ╬ô├Ñ├å 422 `source_not_found`.
-+- Self-referential rule by username ╬ô├Ñ├å 422 `self_referential_rule`.
-+- Self-referential rule by Telegram ID string ╬ô├Ñ├å 422 `self_referential_rule`.
-+- Invalid regex in `block_keywords` ╬ô├Ñ├å 422 `invalid_regex`.
-+- Invalid regex in `allow_keywords` ╬ô├Ñ├å 422 `invalid_regex`.
-+- Cross-midnight time window (`end_time < start_time`) accepted ╬ô├Ñ├å 201.
-+- Invalid IANA timezone ╬ô├Ñ├å 422 `invalid_timezone`.
-+- `media_replacement.enabled=true` + `null` path ╬ô├Ñ├å 422 `media_replacement_path_required`.
-+- Get single rule 200 / not-found 404 `rule_not_found`.
-+- Enable rule ╬ô├Ñ├å 200 `{ok: true}`; `is_active` becomes `true`.
-+- Disable rule ╬ô├Ñ├å 200 `{ok: true}`; enable/disable on non-existent ╬ô├Ñ├å 404.
-+- List rules with pagination (total, page, page_size).
-+- Filter by `source_id`, `is_active`, `destination_channel`.
-+- `page_size` capped at 200.
-+- PUT update with all validation rules (invalid source, invalid regex, invalid timezone, not-found).
-+- DELETE returns 204; cascade to replacement_rules; delete non-existent ╬ô├Ñ├å 404.
-+
-+**Story 3.2 ╬ô├ç├╢ Replacement Rule CRUD:**
-+- POST to non-existent parent rule ╬ô├Ñ├å 404 `rule_not_found`.
-+- Create replacement rule ╬ô├Ñ├å 201 with all fields including `is_active=true` default.
-+- Invalid regex in `search_text` ╬ô├Ñ├å 422 `invalid_regex`.
-+- List returns ordered by `created_at` ASC (pipeline order).
-+- List for non-existent parent ╬ô├Ñ├å 404 `rule_not_found`.
-+- PUT update refreshes fields; invalid regex ╬ô├Ñ├å 422; not-found ╬ô├Ñ├å 404 `replacement_rule_not_found`.
-+- DELETE ╬ô├Ñ├å 204; verify removal from listing; delete non-existent ╬ô├Ñ├å 404.
-+- Auth gate for replacement-rules endpoints (401 without API key).
-+- Cascade delete: deleting parent rule removes all child replacement rules.
-+
-+#### Story 3.3 ╬ô├ç├╢ Atomic Rule Cache & Cache Refresher
-+
-+##### RuleCache Unit Tests (`tests/e2e/test_epic3_e2e.py` + `tests/infrastructure/cache/test_rule_cache.py`)
-+- `test_rule_cache_is_frozen`: Mutation of frozen RuleCache raises `AttributeError`/`TypeError`.
-+- `test_rule_cache_empty_defaults`: `RuleCache()` with no args is version=0, all fields empty.
-+- `test_cache_holder_starts_with_empty_cache`: `CacheHolder.current` is empty at startup.
-+- `test_cache_holder_atomic_swap`: Assigning `CacheHolder.current` atomically replaces the snapshot.
-+- `test_compiled_patterns_empty_defaults`: `CompiledPatterns` defaults to empty lists/dict.
-+- `test_compiled_patterns_with_real_patterns`: `re.Pattern` objects stored and retrievable.
-+
-+##### Cache Refresher Tests (`tests/e2e/test_epic3_e2e.py` + `tests/infrastructure/cache/test_cache_refresher.py`)
-+- `test_build_rule_cache_happy_path`: Fetches all 4 collections, builds valid `RuleCache` with correct version.
-+- `test_build_rule_cache_compiles_regex_patterns`: Block/allow/replacement regex patterns are pre-compiled into `CompiledPatterns`.
-+- `test_build_rule_cache_skips_invalid_regex`: Invalid regex skipped ╬ô├ç├╢ `block_patterns` empty; refresh completes; version is set.
-+- `test_cache_refresher_retains_snapshot_on_mongodb_failure`: MongoDB failure ╬ô├Ñ├å `CacheHolder.current` retains last valid snapshot (version unchanged).
-+
-+#### API Integration Tests
-+
-+##### Rules Router (`tests/api/test_rules.py`)
-+All 14 ACs from Story 3.1 covered with 25 tests including: happy path create with defaults, duplicate pair permitted, source not found (422), self-referential (username + telegram_id), invalid regex (block + allow), cross-midnight time window, invalid timezone, media_replacement path required, enable/disable (success + not-found), list (pagination + 4 filters), get (200 + 404), PUT (success + validations + not-found), DELETE cascade (204 + 404), auth gate.
-+
-+##### Replacement Rules Router (`tests/api/test_replacement_rules.py`)
-+All 8 ACs from Story 3.2 covered with 10 tests including: happy path create, invalid regex rejection (POST + PUT), parent rule not found (POST + GET), list ordered ASC, update refreshes `updated_at`, delete 204, auth gate, cascade delete.
-+
-+---
-+
- ## Suite Summary & Coverage
- 
- | Test Suite | Total Passed | Description |
- |------------|--------------|-------------|
- | `test_epic1_e2e.py` | 52 | E2E foundation client tests |
--| `test_epic2_e2e.py` | 1 | E2E complete workflow test |
-+| `test_epic2_e2e.py` | 1 | E2E complete Epic 2 workflow |
-+| `test_epic3_e2e.py` | 11 | E2E Epic 3 workflow + cache unit/integration |
-+| `test_rules.py` | 25 | Forwarding Rules HTTP API integration tests |
-+| `test_replacement_rules.py` | 10 | Replacement Rules HTTP API integration tests |
- | `test_folders.py` | 10 | Folders HTTP API integration tests |
- | `test_sources.py` | 19 | Sources HTTP API integration tests |
- | `test_health.py` | 5 | Health endpoints unit tests |
- | `test_client.py` | 2 | MongoClientHolder unit tests |
--| `test_folder_repository.py` | 2 | Folder repository database mapper tests |
-+| `test_folder_repository.py` | 6 | Folder repository + `list_folders` tests |
- | `test_source_repository.py` | 3 | Source repository database mapper tests |
-+| `test_rule_repository.py` | 8 | Rule repository (cascade delete, filters, join) |
-+| `test_replacement_repository.py` | 14 | Replacement repository mapper + edge cases |
-+| `test_rule_cache.py` | 10 | RuleCache / CacheHolder / CompiledPatterns |
-+| `test_cache_refresher.py` | 11 | build_rule_cache + run_cache_refresher |
- | `test_telegram_client.py` | 5 | Telegram connection unit tests |
- | `test_config.py` | 7 | Settings validation unit tests |
- 
--**Total passing tests in project: 106**  
--**Execution duration: ~3.07 seconds**  
--**Warnings: 2 (FastAPI standard deprecation warning)**  
-+**Total passing tests in project: 230**  
-+**Execution duration: ~12.27 seconds**  
-+**Warnings: 4 (FastAPI standard deprecation warning ╬ô├ç├╢ `HTTP_422_UNPROCESSABLE_ENTITY`)**
- 
- ---
- 
- ## Test Run Results
- 
- ```
--======================= 106 passed, 2 warnings in 3.07s =======================
-+====================== 230 passed, 4 warnings in 12.27s =======================
- ```
- 
--All E2E and API integration tests pass with 100% success rate.
-+All E2E, API integration, repository, and unit tests pass with 100% success rate.
- 
- ---
- 
- ## Next Steps
- 
--- Integrate Epic 3 (Forwarding Rule Configuration) CRUD endpoints and verify cached rule operations.
--- Implement UI components for folder CRUD modals and source listings matching the new endpoint specs.
-+- Integrate Epic 4 (Core Message Forwarding Engine) pipeline steps ╬ô├ç├╢ the `RuleCache` and `CacheHolder` from Story 3.3 are ready.
-+- E2E test for Epic 4 will exercise the full pipeline dispatch cycle (filter + transform + delivery).
-diff --git a/_bmad_review_diff.txt b/_bmad_review_diff.txt
-index f781803..1202cb5 100644
-Binary files a/_bmad_review_diff.txt and b/_bmad_review_diff.txt differ
-diff --git a/forward-bot/src/forward_bot/api/schemas/base.py b/forward-bot/src/forward_bot/api/schemas/base.py
-index e4c39b9..a27bd67 100644
---- a/forward-bot/src/forward_bot/api/schemas/base.py
-+++ b/forward-bot/src/forward_bot/api/schemas/base.py
-@@ -15,9 +15,61 @@ SAMPLING_COUNTERS = "sampling_counters"
- 
- class MongoBaseModel(BaseModel):
-     """Base model for MongoDB documents returned by the API.
--    
--    Converts MongoDB _id to string id, serializes ObjectIds,
--    and formats datetimes as ISO 8601 UTC strings with Z suffix.
-+
-+    Converts MongoDB ``_id`` to a string ``id`` field, coerces BSON ObjectIds,
-+    and serializes datetimes as ISO 8601 UTC strings with a ``Z`` suffix.
-+
-+    ╬ô├╢├ç╬ô├╢├ç _id / id contract ╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç
-+    MongoDB stores the primary key as ``_id`` (BSON ObjectId).  The API must
-+    expose it as ``"id"`` (plain string) in JSON responses.  This base class
-+    handles the mapping via ``Field(alias="_id")``.
-+
-+    SUBCLASS RULES ╬ô├ç├╢ read before creating a new response schema:
-+
-+    Pattern A ╬ô├ç├╢ no extra field_validator needed on the subclass
-+    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-+    Use when the subclass does NOT need to validate any other field
-+    (e.g. ReplacementRuleResponse, SourceFolderResponse)::
-+
-+        class MyResponse(MongoBaseModel):
-+            # Redeclare only the aliases ╬ô├ç├╢ never re-add a @field_validator("id").
-+            id: str = Field(validation_alias="_id", serialization_alias="id")
-+            other_field: str
-+
-+        @classmethod
-+        def from_entity(cls, e) -> "MyResponse":
-+            # Always pass "_id" (not "id") as the key to model_validate.
-+            return cls.model_validate({"_id": e.id, "other_field": e.x})
-+
-+    Pattern B ╬ô├ç├╢ subclass also needs a field_validator on another BSON field
-+    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-+    Use when another field is stored as ObjectId in MongoDB (e.g. source_id
-+    in ForwardingRuleResponse)::
-+
-+        class MyResponse(MongoBaseModel):
-+            id: str = Field(validation_alias="_id", serialization_alias="id")
-+            foreign_id: str  # stored as ObjectId in Mongo
-+
-+            @field_validator("foreign_id", mode="before")
-+            @classmethod
-+            def coerce_foreign_id(cls, v: Any) -> str:
-+                return str(v)
-+
-+            @classmethod
-+            def from_entity(cls, e) -> "MyResponse":
-+                return cls.model_validate({"_id": e.id, "foreign_id": e.foreign_id})
-+
-+    Common mistakes to avoid
-+    ~~~~~~~~~~~~~~~~~~~~~~~~
-+    - Do NOT add ``@field_validator("id")`` in a subclass ╬ô├ç├╢ MongoBaseModel
-+      already has ``coerce_object_id``.  Pydantic v2 raises a duplicate-validator
-+      error at import time.
-+    - Do NOT pass ``"id": e.id`` to ``model_validate`` ╬ô├ç├╢ always use ``"_id"``
-+      so the alias chain resolves correctly.
-+    - Do NOT use ``Field(alias="_id")`` alone and expect ``"id"`` in the JSON
-+      output ╬ô├ç├╢ you also need ``serialization_alias="id"`` on the subclass field,
-+      because ``alias`` controls parsing only.
-+    ╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç╬ô├╢├ç
-     """
-     model_config = ConfigDict(
-         populate_by_name=True,
-@@ -29,7 +81,7 @@ class MongoBaseModel(BaseModel):
-     @field_validator("id", mode="before")
-     @classmethod
-     def coerce_object_id(cls, v: Any) -> str:
--        """Coerce ObjectId to string."""
-+        """Coerce BSON ObjectId to hex string. Safe to call on a plain string."""
-         if isinstance(v, ObjectId):
-             return str(v)
-         return str(v)
-diff --git a/forward-bot/src/forward_bot/api/schemas/replacement_rule.py b/forward-bot/src/forward_bot/api/schemas/replacement_rule.py
-index af0aea1..49b8420 100644
---- a/forward-bot/src/forward_bot/api/schemas/replacement_rule.py
-+++ b/forward-bot/src/forward_bot/api/schemas/replacement_rule.py
-@@ -1,6 +1,6 @@
- """Pydantic schemas for Replacement Rule API request/response models."""
- from datetime import datetime
--from typing import Literal
-+from typing import Literal, Optional
- 
- from pydantic import BaseModel, Field
- 
-@@ -47,12 +47,11 @@ class ReplacementRuleResponse(MongoBaseModel):
-     replacement_text: str
-     match_mode: str
-     is_active: bool
--    created_at: datetime   # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
--    updated_at: datetime
--    # ╬ô├£├íΓê⌐Γòò├à created_at and updated_at are non-Optional here. The domain entity uses
--    # Optional[datetime] for flexibility, but use cases MUST always set both to
--    # datetime.now(timezone.utc) before persisting. A None value here will cause
--    # a Pydantic validation error at response serialization time.
-+    created_at: Optional[datetime] = None   # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
-+    updated_at: Optional[datetime] = None
-+    # ╬ô├£├íΓê⌐Γòò├à created_at and updated_at are Optional[datetime] here to match the domain entity's
-+    # representation and allow flexibility in tests. In production, these should
-+    # be populated with datetime.now(timezone.utc) before persisting.
- 
-     @classmethod
-     def from_entity(cls, r) -> "ReplacementRuleResponse":
-diff --git a/forward-bot/src/forward_bot/app.py b/forward-bot/src/forward_bot/app.py
-index db75f33..9037640 100644
---- a/forward-bot/src/forward_bot/app.py
-+++ b/forward-bot/src/forward_bot/app.py
-@@ -54,6 +54,16 @@ async def default_lifespan(app: FastAPI):
-                 await mongo_client.db[REPLACEMENT_RULES].create_index(
-                     [("forwarding_rule_id", 1), ("is_active", 1), ("created_at", 1)], background=True
-                 )
-+                # Message mapping compound index (pre-created for Epic 4 Story 4.1)
-+                from forward_bot.api.schemas.base import MESSAGE_MAPPINGS
-+                await mongo_client.db[MESSAGE_MAPPINGS].create_index(
-+                    [
-+                        ("forwarding_rule_id", 1),
-+                        ("source_channel_id", 1),
-+                        ("source_message_id", 1),
-+                    ],
-+                    background=True
-+                )
-                 logger.info("mongodb_indexes_created", message="MongoDB indexes verified/created successfully")
-             except Exception as e:
-                 logger.error("mongodb_index_creation_failed", error=str(e), message="Failed to create MongoDB indexes")
-@@ -73,7 +83,7 @@ async def default_lifespan(app: FastAPI):
-         raise e
- 
-     # Start background task stubs
--    cache_task = asyncio.create_task(run_cache_refresher())
-+    cache_task = asyncio.create_task(run_cache_refresher(settings, mongo_client.db))
-     sweeper_task = asyncio.create_task(run_mapping_sweeper())
-     worker_task = asyncio.create_task(run_telegram_worker())
- 
-diff --git a/forward-bot/src/forward_bot/application/pipeline/__init__.py b/forward-bot/src/forward_bot/application/pipeline/__init__.py
-index e69de29..e344cb8 100644
---- a/forward-bot/src/forward_bot/application/pipeline/__init__.py
-+++ b/forward-bot/src/forward_bot/application/pipeline/__init__.py
-@@ -0,0 +1,8 @@
-+"""Pipeline application package."""
-+from forward_bot.application.pipeline.protocol import PipelineStep
-+from forward_bot.application.pipeline.engine import PipelineEngine
-+
-+__all__ = [
-+    "PipelineStep",
-+    "PipelineEngine",
-+]
-diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py b/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
-index e69de29..8521025 100644
---- a/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
-+++ b/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
-@@ -0,0 +1,42 @@
-+"""Pipeline steps application package."""
-+from forward_bot.application.pipeline.steps.placeholders import (
-+    TimeWindowStep,
-+    SamplingStep,
-+    MediaTypeFilterStep,
-+    BlockKeywordStep,
-+    AllowKeywordStep,
-+    MediaDecisionStep,
-+    ReplyLookupStep,
-+    SourceRefReplaceStep,
-+    TextReplacementStep,
-+    LinkRemovalStep,
-+    HashtagRemovalStep,
-+    MentionRemovalStep,
-+    MediaReplacementStep,
-+    WhitespaceStep,
-+    AttributionStep,
-+    EmptyCheckStep,
-+)
-+from forward_bot.application.pipeline.steps.deliver import DeliverStep
-+from forward_bot.application.pipeline.steps.persist_mapping import PersistMappingStep
-+
-+__all__ = [
-+    "TimeWindowStep",
-+    "SamplingStep",
-+    "MediaTypeFilterStep",
-+    "BlockKeywordStep",
-+    "AllowKeywordStep",
-+    "MediaDecisionStep",
-+    "ReplyLookupStep",
-+    "SourceRefReplaceStep",
-+    "TextReplacementStep",
-+    "LinkRemovalStep",
-+    "HashtagRemovalStep",
-+    "MentionRemovalStep",
-+    "MediaReplacementStep",
-+    "WhitespaceStep",
-+    "AttributionStep",
-+    "EmptyCheckStep",
-+    "DeliverStep",
-+    "PersistMappingStep",
-+]
-diff --git a/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py b/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py
-new file mode 100644
-index 0000000..191397c
---- /dev/null
-+++ b/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py
-@@ -0,0 +1,232 @@
-+"""Background cache refresher for the forwarding rule pipeline.
-+
-+Provides two public coroutines:
-+
-+  - ``build_rule_cache(db, version)``  ╬ô├ç├╢ fetches all four MongoDB collections,
-+    compiles regex patterns, and returns a frozen ``RuleCache`` snapshot.
-+  - ``run_cache_refresher(settings, db)`` ╬ô├ç├╢ long-running background loop that
-+    calls ``build_rule_cache`` every ``HOT_RELOAD_INTERVAL`` seconds and
-+    atomically replaces ``CacheHolder.current``.
-+
-+Design decisions
-+----------------
-+* **Sleep-first pattern**: the refresher sleeps *before* the first build so
-+  that the MongoDB connection pool and all startup tasks are fully established
-+  before the initial fetch.  The pipeline starts with the empty
-+  ``RuleCache()`` (version=0) until the first refresh completes ╬ô├ç├╢ Epic 4
-+  workers tolerate an empty ``rules`` list at startup.
-+* **Atomic swap**: ``CacheHolder.current = new_cache`` is a single Python
-+  reference assignment, which is atomic under the CPython GIL and the asyncio
-+  event loop.  No locking primitives are needed.
-+* **Retain last snapshot on failure**: if MongoDB is temporarily unreachable
-+  the ``WARNING`` is logged and ``CacheHolder.current`` is left unchanged so
-+  the pipeline continues with the last known-good snapshot.
-+* **Invalid regex ╬ô├ç├╢ skip and log**: a ``re.error`` during pattern compilation
-+  logs an ``ERROR`` for the offending rule/pattern and skips that pattern.
-+  The rest of the refresh completes normally (AC-3).
-+* **O(1) DB queries**: the refresh performs exactly 4 MongoDB round-trips
-+  (sources, folders, rules, all-replacements-in-one-``$in``-query),
-+  regardless of rule count. Previously replacement rules were fetched in an
-+  O(N) per-rule loop ╬ô├ç├╢ this is fixed as of the Epic 3 retrospective.
-+"""
-+import asyncio
-+import re
-+from datetime import datetime, timezone
-+
-+from forward_bot.infrastructure.logging import logger
-+from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
-+from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository
-+from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
-+from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository
-+from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository
-+
-+
-+async def build_rule_cache(db, version: int) -> RuleCache:
-+    """Fetch all four collections from MongoDB and build an atomic RuleCache snapshot.
-+
-+    Steps
-+    -----
-+    1. Fetch all Sources ╬ô├Ñ├å ``dict[id, Source]``
-+    2. Fetch all Folders ╬ô├Ñ├å ``dict[id, SourceFolder]``
-+    3. Fetch **active** ForwardingRules ╬ô├Ñ├å ``list[ForwardingRule]``
-+    4. Fetch ALL ReplacementRules for all active rules in one ``$in`` query ╬ô├Ñ├å
-+       ``dict[rule_id, list[ReplacementRule]]``  (O(1) DB round-trips)
-+    5. Compile regex patterns for each rule
-+       (``block_keywords``, ``allow_keywords``, replacement ``search_text``)
-+    6. Return a frozen ``RuleCache`` with the supplied ``version`` number.
-+
-+    Args:
-+        db:      Motor ``AsyncIOMotorDatabase`` instance.
-+        version: Version number to stamp on the returned cache snapshot.
-+
-+    Returns:
-+        A frozen ``RuleCache`` snapshot ready to be atomically assigned to
-+        ``CacheHolder.current``.
-+
-+    Raises:
-+        Any exception raised by MongoDB (network failures, etc.) ╬ô├ç├╢ callers
-+        should catch these and retain the last valid snapshot.
-+    """
-+    source_repo = SourceRepository(db)
-+    folder_repo = FolderRepository(db)
-+    rule_repo = ForwardingRuleRepository(db)
-+    replacement_repo = ReplacementRuleRepository(db)
-+
-+    # 1. Fetch all sources (not just active) ╬ô├ç├╢ page_size=10000 effectively fetches all
-+    #    (NFR-Scale target is 100 active sources, so this is well above the expected ceiling)
-+    all_sources_list, _ = await source_repo.list_sources(page_size=10000)
-+    sources = {s.id: s for s in all_sources_list if s.id}
-+
-+    # 2. Fetch all folders
-+    all_folders = await folder_repo.list_folders()
-+    folders = {f.id: f for f in all_folders if f.id}
-+
-+    # 3. Fetch only active forwarding rules
-+    #    source_repo=None is fine here because we are not filtering by folder_id
-+    active_rules, _ = await rule_repo.list_rules(
-+        source_repo=None,
-+        is_active=True,
-+        page_size=10000,
-+    )
-+
-+    # 4. Fetch ALL replacement rules for all active rules in ONE MongoDB query.
-+    #    ``list_all_replacements_for_rules`` uses a ``$in`` filter, reducing DB
-+    #    round-trips from O(N) per-rule to a fixed O(1) regardless of rule count.
-+    #    All replacement rules are loaded (not filtered by is_active) so that the
-+    #    pipeline TextReplacementStep can skip is_active=False at runtime ╬ô├ç├╢
-+    #    consistent with FR-7 and the Epic 4 design notes.
-+    rule_ids = [r.id for r in active_rules if r.id]
-+    replacements: dict[str, list] = await replacement_repo.list_all_replacements_for_rules(rule_ids)
-+
-+    # 5. Compile regex patterns for each active rule.
-+    #    Invalid patterns are logged as ERROR and skipped (no-op) for the
-+    #    lifetime of this snapshot ╬ô├ç├╢ the refresh continues normally (AC-3).
-+    compiled_patterns: dict[str, CompiledPatterns] = {}
-+    for rule in active_rules:
-+        if not rule.id:
-+            continue
-+
-+        patterns = CompiledPatterns()
-+
-+        if rule.keyword_match_mode == "regex":
-+            # Compile block_keywords
-+            for kw in rule.block_keywords:
-+                try:
-+                    patterns.block_patterns.append(re.compile(kw, re.IGNORECASE))
-+                except re.error as e:
-+                    logger.error(
-+                        "cache_pattern_compile_failed",
-+                        rule_id=rule.id,
-+                        pattern=kw,
-+                        field="block_keywords",
-+                        error=str(e),
-+                    )
-+                    # Skip this pattern ╬ô├ç├╢ no-op for this snapshot's lifetime
-+
-+            # Compile allow_keywords
-+            for kw in rule.allow_keywords:
-+                try:
-+                    patterns.allow_patterns.append(re.compile(kw, re.IGNORECASE))
-+                except re.error as e:
-+                    logger.error(
-+                        "cache_pattern_compile_failed",
-+                        rule_id=rule.id,
-+                        pattern=kw,
-+                        field="allow_keywords",
-+                        error=str(e),
-+                    )
-+                    # Skip this pattern ╬ô├ç├╢ no-op for this snapshot's lifetime
-+
-+        # Compile replacement rule search_text patterns (regex mode only)
-+        for rr in replacements.get(rule.id, []):
-+            if rr.match_mode == "regex" and rr.id:
-+                try:
-+                    patterns.replacement_patterns[rr.id] = re.compile(
-+                        rr.search_text, re.IGNORECASE
-+                    )
-+                except re.error as e:
-+                    logger.error(
-+                        "cache_pattern_compile_failed",
-+                        rule_id=rule.id,
-+                        replacement_rule_id=rr.id,
-+                        pattern=rr.search_text,
-+                        field="replacement_search_text",
-+                        error=str(e),
-+                    )
-+                    # Skip this pattern ╬ô├ç├╢ no-op for this snapshot's lifetime
-+
-+        compiled_patterns[rule.id] = patterns
-+
-+    return RuleCache(
-+        sources=sources,
-+        folders=folders,
-+        rules=active_rules,
-+        replacements=replacements,
-+        compiled_patterns=compiled_patterns,
-+        version=version,
-+        refreshed_at=datetime.now(timezone.utc),
-+    )
-+
-+
-+async def run_cache_refresher(settings, db) -> None:
-+    """Background coroutine: refreshes ``RuleCache`` every ``HOT_RELOAD_INTERVAL`` seconds.
-+
-+    Behaviour
-+    ---------
-+    * **Sleep-first**: waits one interval before the first build so that the
-+      rest of the application (MongoDB pool, Telegram client) has time to
-+      initialise.  The pipeline starts with the empty ``RuleCache()``
-+      (version=0, ``rules=[]``) until the first refresh completes.
-+    * **On success**: atomically replaces ``CacheHolder.current``; logs INFO
-+      with version, rule_count, source_count, folder_count.
-+    * **On failure**: logs WARNING with ``last_successful_refresh`` ISO
-+      timestamp; retains the current ``CacheHolder.current`` (last known-good
-+      snapshot); continues the loop on the next interval (AC-5).
-+    * **Graceful shutdown**: re-raises ``asyncio.CancelledError`` after logging
-+      so that the task can be awaited cleanly by the lifespan handler.
-+
-+    The ``version`` counter starts at 1 on the first successful build
-+    (``CacheHolder`` starts at version=0, the empty initial cache).
-+
-+    Args:
-+        settings: Application ``Settings`` instance with ``hot_reload_interval``.
-+        db:       Motor ``AsyncIOMotorDatabase`` instance.
-+    """
-+    version = 1
-+    last_successful_refresh: datetime | None = None
-+    logger.info("cache_refresher_started", hot_reload_interval=settings.hot_reload_interval)
-+
-+    while True:
-+        try:
-+            # Sleep first ╬ô├ç├╢ ensures MongoDB is ready before the initial fetch
-+            await asyncio.sleep(settings.hot_reload_interval)
-+
-+            new_cache = await build_rule_cache(db, version)
-+            CacheHolder.current = new_cache          # ╬ô├Ñ├ë atomic under asyncio event loop
-+            last_successful_refresh = new_cache.refreshed_at
-+            version += 1
-+
-+            logger.info(
-+                "cache_refreshed",
-+                version=new_cache.version,
-+                rule_count=len(new_cache.rules),
-+                source_count=len(new_cache.sources),
-+                folder_count=len(new_cache.folders),
-+            )
-+
-+        except asyncio.CancelledError:
-+            logger.info("cache_refresher_stopped")
-+            raise
-+
-+        except Exception as e:
-+            logger.warning(
-+                "cache_refresh_failed",
-+                error=str(e),
-+                last_successful_refresh=(
-+                    last_successful_refresh.strftime("%Y-%m-%dT%H:%M:%SZ")
-+                    if last_successful_refresh
-+                    else None
-+                ),
-+            )
-+            # Retain CacheHolder.current (last valid snapshot) ╬ô├ç├╢ do NOT clear it.
-+            # The loop continues on the next interval (AC-5).
-diff --git a/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py b/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py
-new file mode 100644
-index 0000000..1946c4b
---- /dev/null
-+++ b/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py
-@@ -0,0 +1,87 @@
-+"""Atomic cache snapshot types for the forwarding rule pipeline.
-+
-+This module defines the three types consumed by Epic 4 pipeline steps:
-+
-+  - CompiledPatterns  ╬ô├ç├╢ pre-compiled re.Pattern objects for a single ForwardingRule.
-+  - RuleCache         ╬ô├ç├╢ frozen, immutable snapshot of all four MongoDB collections.
-+  - CacheHolder       ╬ô├ç├╢ mutable singleton whose `.current` attribute is atomically
-+                        replaced by the cache refresher on each interval.
-+
-+Assignment of ``CacheHolder.current`` is a single Python reference swap, which is
-+atomic under both the CPython GIL and the asyncio event loop's single-threaded
-+execution model.  No locking primitives are required.
-+"""
-+import re
-+from dataclasses import dataclass, field
-+from datetime import datetime
-+from typing import Optional
-+
-+
-+@dataclass
-+class CompiledPatterns:
-+    """Pre-compiled regex patterns for a single ForwardingRule.
-+
-+    Keyed structures allow O(1) lookup by field name during pipeline execution.
-+    ``block_patterns`` and ``allow_patterns`` are lists of compiled ``re.Pattern``
-+    objects (one per keyword that uses regex mode).
-+    ``replacement_patterns`` maps each ``replacement_rule.id`` ╬ô├Ñ├å
-+    compiled ``re.Pattern`` for its ``search_text``.
-+    """
-+
-+    block_patterns: list[re.Pattern] = field(default_factory=list)
-+    allow_patterns: list[re.Pattern] = field(default_factory=list)
-+    replacement_patterns: dict[str, re.Pattern] = field(default_factory=dict)
-+    # Key: replacement_rule.id (str) ╬ô├Ñ├å compiled re.Pattern for search_text
-+
-+
-+@dataclass(frozen=True)
-+class RuleCache:
-+    """Atomic, immutable snapshot of all four MongoDB collections.
-+
-+    Built once per ``HOT_RELOAD_INTERVAL`` by the cache refresher and atomically
-+    assigned to ``CacheHolder.current``.  Pipeline steps read this snapshot for
-+    the full lifecycle of a single message dispatch ╬ô├ç├╢ no torn reads possible.
-+
-+    Fields:
-+        sources:           All sources keyed by their id (hex string).
-+        folders:           All folders keyed by their id (hex string).
-+        rules:             Active-only ForwardingRules (``is_active=True``),
-+                           fetched with ``page_size=10000`` (all active rules).
-+        replacements:      All replacement rules per parent rule_id.
-+                           Key: ``forwarding_rule_id`` (str) ╬ô├Ñ├å
-+                           ``list[ReplacementRule]`` (``created_at`` ASC order).
-+        compiled_patterns: Pre-compiled regex patterns per rule_id.
-+                           Key: ``rule_id`` (str) ╬ô├Ñ├å ``CompiledPatterns``.
-+        version:           Monotonically increasing integer.  Starts at 0
-+                           (initial empty cache), increments by 1 on each
-+                           successful build.  Useful for debugging staleness.
-+        refreshed_at:      UTC datetime of the last successful cache build.
-+                           ``None`` for the initial empty cache (version=0).
-+    """
-+
-+    sources: dict = field(default_factory=dict)           # dict[str, Source]
-+    folders: dict = field(default_factory=dict)           # dict[str, SourceFolder]
-+    rules: list = field(default_factory=list)             # list[ForwardingRule] (active only)
-+    replacements: dict = field(default_factory=dict)      # dict[str, list[ReplacementRule]]
-+    compiled_patterns: dict = field(default_factory=dict)  # dict[str, CompiledPatterns]
-+    version: int = 0
-+    refreshed_at: Optional[datetime] = None
-+
-+
-+class CacheHolder:
-+    """Singleton holder for the current ``RuleCache`` snapshot.
-+
-+    ``CacheHolder.current`` is the only write path for the cache refresher.
-+    All reads come from pipeline steps (Epic 4) which consume a local reference
-+    to the snapshot at the start of each dispatch.
-+
-+    Usage::
-+
-+        # Read in pipeline steps (capture once per dispatch):
-+        snapshot = CacheHolder.current
-+
-+        # Write in cache_refresher only (atomic reference swap):
-+        CacheHolder.current = new_cache
-+    """
-+
-+    current: RuleCache = RuleCache()  # Start with empty cache (version=0)
-diff --git a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
-index a0cf0ac..ee17c10 100644
---- a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
-+++ b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
-@@ -76,6 +76,15 @@ class FolderRepository(BaseRepository):
-             )
-         return deleted
- 
-+    async def list_folders(self) -> list[SourceFolder]:
-+        """Fetch all SourceFolders from the database mapped to domain entities.
-+
-+        Returns all folders in the collection with no filtering or pagination.
-+        Used by the cache refresher (Story 3.3) to populate ``RuleCache.folders``.
-+        """
-+        docs = await self.find({})
-+        return [self._to_entity(doc) for doc in docs]
-+
-     async def list_folders_with_source_count(self, name_filter: str | None = None) -> list[dict[str, Any]]:
-         """List folders with their source counts using a single aggregate query."""
-         pipeline: list[dict[str, Any]] = []
-diff --git a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py
-index 4fa7eb3..3c78408 100644
---- a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py
-+++ b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py
-@@ -67,6 +67,42 @@ class ReplacementRuleRepository(BaseRepository):
-         """Delete a replacement rule by ObjectId. Returns True if deleted."""
-         return await self.delete(id)
- 
-+    async def list_all_replacements_for_rules(
-+        self, rule_ids: list[str]
-+    ) -> dict[str, list[ReplacementRule]]:
-+        """Fetch ALL replacement rules for a set of forwarding rule IDs in ONE query.
-+
-+        Uses a ``$in`` filter to fetch all matching documents in a single MongoDB
-+        round-trip, then groups results in-memory by ``forwarding_rule_id``.
-+        Within each group the order is ``created_at ASC, _id ASC`` (pipeline order, FR-7).
-+
-+        This is the O(1) replacement for the O(N) per-rule sequential loop previously
-+        used in ``build_rule_cache``. At NFR-Scale (100 active rules) this reduces cache
-+        refresh DB round-trips from 101 to 4 (sources, folders, rules, replacements).
-+
-+        Args:
-+            rule_ids: List of forwarding rule ID hex strings whose replacement rules to fetch.
-+
-+        Returns:
-+            ``dict[forwarding_rule_id, list[ReplacementRule]]`` ╬ô├ç├╢ every requested rule_id
-+            appears as a key; missing ones map to ``[]``.
-+        """
-+        if not rule_ids:
-+            return {}
-+
-+        cursor = (
-+            self.collection.find({"forwarding_rule_id": {"$in": rule_ids}})
-+            .sort([("created_at", 1), ("_id", 1)])  # pipeline application order (FR-7)
-+        )
-+        docs = await cursor.to_list(length=None)
-+
-+        # Group in-memory; pre-seed all requested IDs so callers get [] for rules with no replacements
-+        grouped: dict[str, list[ReplacementRule]] = {rid: [] for rid in rule_ids}
-+        for doc in docs:
-+            entity = self._to_entity(doc)
-+            grouped.setdefault(entity.forwarding_rule_id, []).append(entity)
-+        return grouped
-+
-     async def list_replacements_for_rule(self, rule_id: str) -> list[ReplacementRule]:
-         """List all replacement rules for a parent forwarding rule, ordered by created_at ASC.
- 
-@@ -75,7 +111,7 @@ class ReplacementRuleRepository(BaseRepository):
-         """
-         cursor = (
-             self.collection.find({"forwarding_rule_id": rule_id})
--            .sort("created_at", 1)  # ASC ╬ô├ç├╢ pipeline application order (FR-7)
-+            .sort([("created_at", 1), ("_id", 1)])  # ASC with secondary _id sort to prevent collision
-         )
-         docs = await cursor.to_list(length=None)
-         return [self._to_entity(doc) for doc in docs]
-diff --git a/forward-bot/src/forward_bot/tasks.py b/forward-bot/src/forward_bot/tasks.py
-index 2a37c2b..2287b33 100644
---- a/forward-bot/src/forward_bot/tasks.py
-+++ b/forward-bot/src/forward_bot/tasks.py
-@@ -2,14 +2,32 @@
- import asyncio
- from forward_bot.infrastructure.logging import logger
- 
--async def run_cache_refresher() -> None:
--    """Stub for cache refresher task."""
--    logger.info("cache_refresher_started", status="stub")
--    try:
--        await asyncio.sleep(float('inf'))
--    except asyncio.CancelledError:
--        logger.info("cache_refresher_stopped")
--        raise
-+async def run_cache_refresher(settings=None, db=None) -> None:
-+    """Real cache refresher ╬ô├ç├╢ delegates to infrastructure/cache/cache_refresher.py.
-+
-+    When called without arguments (legacy / test scenarios) the function falls
-+    back to an infinite sleep so that task cancellation still works cleanly ╬ô├ç├╢
-+    preserving backward compatibility with existing E2E tests from Story 1.3.
-+
-+    Args:
-+        settings: Application ``Settings`` instance with ``hot_reload_interval``.
-+                  When ``None`` the function sleeps indefinitely (stub mode).
-+        db:       Motor ``AsyncIOMotorDatabase`` instance.
-+                  When ``None`` the function sleeps indefinitely (stub mode).
-+    """
-+    if settings is None or db is None:
-+        # Stub mode: sleep until cancelled (preserves cancellation semantics)
-+        logger.info("cache_refresher_started", status="stub-no-settings")
-+        try:
-+            await asyncio.sleep(float("inf"))
-+        except asyncio.CancelledError:
-+            logger.info("cache_refresher_stopped")
-+            raise
-+        return
-+
-+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher as _run
-+    await _run(settings, db)
-+
- 
- async def run_mapping_sweeper() -> None:
-     """Stub for mapping sweeper task."""
-diff --git a/forward-bot/tests/infrastructure/cache/__init__.py b/forward-bot/tests/infrastructure/cache/__init__.py
-new file mode 100644
-index 0000000..d0d1445
---- /dev/null
-+++ b/forward-bot/tests/infrastructure/cache/__init__.py
-@@ -0,0 +1 @@
-+# tests/infrastructure/cache/__init__.py
-diff --git a/forward-bot/tests/infrastructure/cache/test_cache_refresher.py b/forward-bot/tests/infrastructure/cache/test_cache_refresher.py
-new file mode 100644
-index 0000000..c0ab3fe
---- /dev/null
-+++ b/forward-bot/tests/infrastructure/cache/test_cache_refresher.py
-@@ -0,0 +1,583 @@
-+import asyncio
-+import contextlib
-+from datetime import datetime, timezone
-+from unittest.mock import AsyncMock, MagicMock, patch
-+
-+import pytest
-+
-+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
-+from forward_bot.domain.entities.replacement_rule import ReplacementRule
-+from forward_bot.domain.entities.source import Source
-+from forward_bot.domain.entities.source_folder import SourceFolder
-+from forward_bot.infrastructure.cache.rule_cache import CacheHolder, CompiledPatterns, RuleCache
-+
-+
-+# ---------------------------------------------------------------------------
-+# Helper factories
-+# ---------------------------------------------------------------------------
-+
-+
-+def _now() -> datetime:
-+    return datetime.now(timezone.utc)
-+
-+
-+def make_source(id_: str = "src1") -> Source:
-+    return Source(
-+        id=id_,
-+        telegram_id=1001,
-+        telegram_username="test_chan",
-+        display_name="Test Chan",
-+        type="channel",
-+        folder_id=None,
-+        created_at=_now(),
-+        updated_at=_now(),
-+    )
-+
-+
-+def make_folder(id_: str = "fol1") -> SourceFolder:
-+    return SourceFolder(id=id_, name="Test Folder", created_at=_now(), updated_at=_now())
-+
-+
-+def make_rule(
-+    id_: str = "rule1",
-+    match_mode: str = "literal",
-+    block: list[str] | None = None,
-+    allow: list[str] | None = None,
-+    active: bool = True,
-+) -> ForwardingRule:
-+    return ForwardingRule(
-+        id=id_,
-+        source_id="src1",
-+        destination_channel="@dest",
-+        is_active=active,
-+        keyword_match_mode=match_mode,
-+        block_keywords=block or [],
-+        allow_keywords=allow or [],
-+    )
-+
-+
-+def make_replacement(
-+    id_: str = "rr1",
-+    search: str = "old",
-+    mode: str = "literal",
-+    rule_id: str = "rule1",
-+) -> ReplacementRule:
-+    return ReplacementRule(
-+        id=id_,
-+        forwarding_rule_id=rule_id,
-+        search_text=search,
-+        replacement_text="new",
-+        match_mode=mode,
-+        is_active=True,
-+        created_at=_now(),
-+        updated_at=_now(),
-+    )
-+
-+
-+def _make_mock_repos(
-+    sources=None,
-+    folders=None,
-+    rules=None,
-+    replacements=None,
-+):
-+    """Return a dict of pre-configured mock repositories.
-+
-+    ``replacements`` should be a ``dict[rule_id, list[ReplacementRule]]``.
-+    The mock wires up ``list_all_replacements_for_rules`` (the O(1) batch method
-+    used by ``build_rule_cache``) to return the dict keyed by the requested IDs.
-+    The per-rule ``list_replacements_for_rule`` is NOT called by the cache refresher.
-+    """
-+    mock_source_repo = MagicMock()
-+    mock_source_repo.list_sources = AsyncMock(
-+        return_value=(sources or [], len(sources) if sources else 0)
-+    )
-+
-+    mock_folder_repo = MagicMock()
-+    mock_folder_repo.list_folders = AsyncMock(return_value=folders or [])
-+
-+    mock_rule_repo = MagicMock()
-+    mock_rule_repo.list_rules = AsyncMock(
-+        return_value=(rules or [], len(rules) if rules else 0)
-+    )
-+
-+    mock_replacement_repo = MagicMock()
-+    _replacements = replacements or {}
-+
-+    async def batch_list(rule_ids):
-+        """Simulate list_all_replacements_for_rules: pre-seed every requested id."""
-+        return {rid: _replacements.get(rid, []) for rid in rule_ids}
-+
-+    mock_replacement_repo.list_all_replacements_for_rules = batch_list
-+
-+    return mock_source_repo, mock_folder_repo, mock_rule_repo, mock_replacement_repo
-+
-+
-+@contextlib.contextmanager
-+def _patch_repos(source_repo, folder_repo, rule_repo, replacement_repo):
-+    """Context manager that patches all four repository classes simultaneously."""
-+    with (
-+        patch(
-+            "forward_bot.infrastructure.cache.cache_refresher.SourceRepository",
-+            return_value=source_repo,
-+        ),
-+        patch(
-+            "forward_bot.infrastructure.cache.cache_refresher.FolderRepository",
-+            return_value=folder_repo,
-+        ),
-+        patch(
-+            "forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository",
-+            return_value=rule_repo,
-+        ),
-+        patch(
-+            "forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository",
-+            return_value=replacement_repo,
-+        ),
-+    ):
-+        yield
-+
-+
-+
-+# ---------------------------------------------------------------------------
-+# build_rule_cache ╬ô├ç├╢ happy path
-+# ---------------------------------------------------------------------------
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_happy_path():
-+    """build_rule_cache fetches 4 collections and builds a valid RuleCache snapshot."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    source = make_source()
-+    folder = make_folder()
-+    rule = make_rule()
-+    replacement = make_replacement()
-+
-+    sr, fr, rr, rep = _make_mock_repos(
-+        sources=[source],
-+        folders=[folder],
-+        rules=[rule],
-+        replacements={"rule1": [replacement]},
-+    )
-+
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    assert isinstance(cache, RuleCache)
-+    assert cache.version == 1
-+    assert "src1" in cache.sources
-+    assert "fol1" in cache.folders
-+    assert len(cache.rules) == 1
-+    assert "rule1" in cache.replacements
-+    assert len(cache.replacements["rule1"]) == 1
-+    assert cache.refreshed_at is not None
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_version_stamped_correctly():
-+    """build_rule_cache stamps the provided version number into the snapshot."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    sr, fr, rr, rep = _make_mock_repos()
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=7)
-+
-+    assert cache.version == 7
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_refreshed_at_is_utc():
-+    """build_rule_cache sets refreshed_at to UTC datetime."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    sr, fr, rr, rep = _make_mock_repos()
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    assert cache.refreshed_at is not None
-+    assert cache.refreshed_at.tzinfo is not None  # timezone-aware
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_empty_db():
-+    """build_rule_cache with empty collections returns an empty but valid snapshot."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    sr, fr, rr, rep = _make_mock_repos()
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    assert cache.sources == {}
-+    assert cache.folders == {}
-+    assert cache.rules == []
-+    assert cache.replacements == {}
-+    assert cache.compiled_patterns == {}
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_multiple_sources_and_rules():
-+    """build_rule_cache correctly indexes multiple sources and rules."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    sources = [make_source(id_=f"src{i}") for i in range(3)]
-+    rules = [make_rule(id_=f"rule{i}") for i in range(2)]
-+
-+    sr, fr, rr, rep = _make_mock_repos(sources=sources, rules=rules)
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    assert len(cache.sources) == 3
-+    assert len(cache.rules) == 2
-+    assert all(f"src{i}" in cache.sources for i in range(3))
-+
-+
-+# ---------------------------------------------------------------------------
-+# build_rule_cache ╬ô├ç├╢ regex pattern compilation (AC-2)
-+# ---------------------------------------------------------------------------
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_compiles_block_and_allow_regex():
-+    """Regex block_keywords and allow_keywords are compiled into CompiledPatterns (AC-2)."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["BTC|ETH"])
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    assert "rule1" in cache.compiled_patterns
-+    cp = cache.compiled_patterns["rule1"]
-+    assert len(cp.block_patterns) == 1
-+    assert cp.block_patterns[0].pattern == "pump.*"
-+    assert len(cp.allow_patterns) == 1
-+    assert cp.allow_patterns[0].pattern == "BTC|ETH"
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_compiles_replacement_regex():
-+    """Regex replacement search_text is compiled into CompiledPatterns.replacement_patterns."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule(match_mode="literal")  # keyword mode doesn't matter for replacement regex
-+    replacement = make_replacement(search="old.+new", mode="regex")
-+
-+    sr, fr, rr, rep = _make_mock_repos(
-+        rules=[rule],
-+        replacements={"rule1": [replacement]},
-+    )
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    assert "rule1" in cache.compiled_patterns
-+    cp = cache.compiled_patterns["rule1"]
-+    assert "rr1" in cp.replacement_patterns
-+    assert cp.replacement_patterns["rr1"].pattern == "old.+new"
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_literal_keywords_not_compiled():
-+    """Literal-mode keywords do NOT populate block_patterns or allow_patterns."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule(match_mode="literal", block=["pump"], allow=["btc"])
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    cp = cache.compiled_patterns["rule1"]
-+    # Literal mode ╬ô├ç├╢ no compiled patterns for block/allow
-+    assert cp.block_patterns == []
-+    assert cp.allow_patterns == []
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_literal_replacement_not_compiled():
-+    """Literal-mode replacement rules do NOT populate replacement_patterns."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule()
-+    replacement = make_replacement(search="old", mode="literal")
-+
-+    sr, fr, rr, rep = _make_mock_repos(
-+        rules=[rule],
-+        replacements={"rule1": [replacement]},
-+    )
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    cp = cache.compiled_patterns["rule1"]
-+    assert cp.replacement_patterns == {}
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_patterns_compiled_with_ignorecase():
-+    """Compiled patterns use re.IGNORECASE flag (FR-36, FR-8 compliance)."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+    import re
-+
-+    rule = make_rule(match_mode="regex", block=["TestPATTERN"])
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    cp = cache.compiled_patterns["rule1"]
-+    assert cp.block_patterns[0].flags & re.IGNORECASE
-+
-+
-+# ---------------------------------------------------------------------------
-+# build_rule_cache ╬ô├ç├╢ invalid regex skip and log (AC-3)
-+# ---------------------------------------------------------------------------
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_skips_invalid_block_regex(caplog):
-+    """Invalid block_keywords regex is skipped and logged as ERROR ╬ô├ç├╢ refresh completes (AC-3)."""
-+    import logging
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule(match_mode="regex", block=["[invalid("])  # invalid regex
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
-+    with _patch_repos(sr, fr, rr, rep):
-+        with caplog.at_level(logging.ERROR):
-+            cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    # Refresh completes ╬ô├ç├╢ version stamped correctly
-+    assert cache.version == 1
-+    # Invalid pattern skipped ╬ô├ç├╢ CompiledPatterns exists but block_patterns is empty
-+    assert "rule1" in cache.compiled_patterns
-+    assert cache.compiled_patterns["rule1"].block_patterns == []
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_skips_invalid_allow_regex():
-+    """Invalid allow_keywords regex is skipped ╬ô├ç├╢ other valid patterns still compile."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["[bad("])
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    cp = cache.compiled_patterns["rule1"]
-+    # Valid block pattern compiled; invalid allow pattern skipped
-+    assert len(cp.block_patterns) == 1
-+    assert cp.allow_patterns == []
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_skips_invalid_replacement_regex():
-+    """Invalid replacement search_text regex is skipped ╬ô├ç├╢ refresh completes (AC-3)."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule()
-+    bad_replacement = make_replacement(search="[invalid(", mode="regex")
-+
-+    sr, fr, rr, rep = _make_mock_repos(
-+        rules=[rule],
-+        replacements={"rule1": [bad_replacement]},
-+    )
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    # Refresh completes; invalid replacement pattern absent from compiled_patterns
-+    assert cache.version == 1
-+    assert cache.compiled_patterns["rule1"].replacement_patterns == {}
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_valid_patterns_survive_invalid_one():
-+    """When one of multiple patterns is invalid, valid patterns still compile."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule = make_rule(match_mode="regex", block=["pump.*", "[invalid(", "dump.*"])
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    cp = cache.compiled_patterns["rule1"]
-+    # 2 valid patterns compiled; 1 invalid skipped
-+    assert len(cp.block_patterns) == 2
-+    compiled_texts = {p.pattern for p in cp.block_patterns}
-+    assert "pump.*" in compiled_texts
-+    assert "dump.*" in compiled_texts
-+
-+
-+@pytest.mark.asyncio
-+async def test_build_rule_cache_invalid_regex_other_rules_unaffected():
-+    """An invalid pattern in one rule does not affect compilation of other rules."""
-+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
-+
-+    rule_bad = make_rule(id_="rule_bad", match_mode="regex", block=["[invalid("])
-+    rule_good = make_rule(id_="rule_good", match_mode="regex", block=["pump.*"])
-+
-+    sr, fr, rr, rep = _make_mock_repos(rules=[rule_bad, rule_good])
-+    with _patch_repos(sr, fr, rr, rep):
-+        cache = await build_rule_cache(MagicMock(), version=1)
-+
-+    # Bad rule: empty block_patterns
-+    assert cache.compiled_patterns["rule_bad"].block_patterns == []
-+    # Good rule: compiled correctly
-+    assert len(cache.compiled_patterns["rule_good"].block_patterns) == 1
-+
-+
-+# ---------------------------------------------------------------------------
-+# run_cache_refresher ╬ô├ç├╢ MongoDB failure retains last snapshot (AC-5)
-+# ---------------------------------------------------------------------------
-+
-+
-+@pytest.mark.asyncio
-+async def test_run_cache_refresher_retains_snapshot_on_mongodb_failure():
-+    """On MongoDB error, CacheHolder.current retains the last valid snapshot (AC-5)."""
-+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
-+
-+    initial_cache = RuleCache(version=99)
-+    saved = CacheHolder.current
-+    CacheHolder.current = initial_cache
-+
-+    mock_settings = MagicMock()
-+    mock_settings.hot_reload_interval = 0.01  # very short for test speed
-+
-+    async def mock_build(db, version):
-+        raise Exception("MongoDB connection lost")
-+
-+    with patch(
-+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
-+        side_effect=mock_build,
-+    ):
-+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
-+        await asyncio.sleep(0.05)  # Let it fail at least once
-+        task.cancel()
-+        try:
-+            await task
-+        except asyncio.CancelledError:
-+            pass
-+
-+    # Snapshot retained ╬ô├ç├╢ not reset to empty
-+    assert CacheHolder.current.version == 99
-+    CacheHolder.current = saved
-+
-+
-+@pytest.mark.asyncio
-+async def test_run_cache_refresher_continues_after_failure():
-+    """After a MongoDB failure the refresher continues on the next interval (AC-5)."""
-+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
-+
-+    saved = CacheHolder.current
-+    CacheHolder.current = RuleCache(version=0)
-+
-+    call_count = 0
-+
-+    async def mock_build(db, version):
-+        nonlocal call_count
-+        call_count += 1
-+        raise Exception("transient error")
-+
-+    mock_settings = MagicMock()
-+    mock_settings.hot_reload_interval = 0.01
-+
-+    with patch(
-+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
-+        side_effect=mock_build,
-+    ):
-+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
-+        await asyncio.sleep(0.08)
-+        task.cancel()
-+        try:
-+            await task
-+        except asyncio.CancelledError:
-+            pass
-+
-+    # Refresher looped multiple times despite repeated failures
-+    assert call_count >= 2
-+    CacheHolder.current = saved
-+
-+
-+@pytest.mark.asyncio
-+async def test_run_cache_refresher_version_increments_on_success():
-+    """Version counter increments by 1 on each successful cache build."""
-+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
-+
-+    saved = CacheHolder.current
-+    version_log: list[int] = []
-+
-+    async def mock_build(db, version):
-+        version_log.append(version)
-+        return RuleCache(version=version, refreshed_at=datetime.now(timezone.utc))
-+
-+    mock_settings = MagicMock()
-+    mock_settings.hot_reload_interval = 0.01
-+
-+    with patch(
-+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
-+        side_effect=mock_build,
-+    ):
-+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
-+        await asyncio.sleep(0.08)
-+        task.cancel()
-+        try:
-+            await task
-+        except asyncio.CancelledError:
-+            pass
-+
-+    # Versions should be sequential starting at 1
-+    assert version_log[0] == 1
-+    for i in range(1, len(version_log)):
-+        assert version_log[i] == version_log[i - 1] + 1
-+
-+    CacheHolder.current = saved
-+
-+
-+@pytest.mark.asyncio
-+async def test_run_cache_refresher_swaps_cache_on_success():
-+    """run_cache_refresher atomically replaces CacheHolder.current on a successful build."""
-+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
-+
-+    saved = CacheHolder.current
-+    CacheHolder.current = RuleCache(version=0)
-+
-+    built_cache = RuleCache(version=1, refreshed_at=datetime.now(timezone.utc))
-+
-+    async def mock_build(db, version):
-+        return built_cache
-+
-+    mock_settings = MagicMock()
-+    mock_settings.hot_reload_interval = 0.01
-+
-+    with patch(
-+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
-+        side_effect=mock_build,
-+    ):
-+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
-+        await asyncio.sleep(0.05)
-+        task.cancel()
-+        try:
-+            await task
-+        except asyncio.CancelledError:
-+            pass
-+
-+    # CacheHolder.current was replaced
-+    assert CacheHolder.current.refreshed_at is not None
-+
-+    CacheHolder.current = saved
-+
-+
-+@pytest.mark.asyncio
-+async def test_run_cache_refresher_cancelled_error_propagates():
-+    """run_cache_refresher re-raises CancelledError for clean shutdown."""
-+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
-+
-+    mock_settings = MagicMock()
-+    mock_settings.hot_reload_interval = 10.0  # long sleep
-+
-+    task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
-+    await asyncio.sleep(0.01)
-+    task.cancel()
-+
-+    with pytest.raises(asyncio.CancelledError):
-+        await task
-diff --git a/forward-bot/tests/infrastructure/cache/test_rule_cache.py b/forward-bot/tests/infrastructure/cache/test_rule_cache.py
-new file mode 100644
-index 0000000..b17ae53
---- /dev/null
-+++ b/forward-bot/tests/infrastructure/cache/test_rule_cache.py
-@@ -0,0 +1,143 @@
-+"""Unit tests for RuleCache, CacheHolder, and CompiledPatterns.
-+
-+Tests the construction, frozen behaviour, and atomic swap semantics of the
-+cache types defined in ``infrastructure/cache/rule_cache.py``.
-+"""
-+import re
-+from datetime import datetime, timezone
-+
-+import pytest
-+
-+from forward_bot.infrastructure.cache.rule_cache import CacheHolder, CompiledPatterns, RuleCache
-+
-+
-+# ---------------------------------------------------------------------------
-+# RuleCache ╬ô├ç├╢ construction and frozen semantics
-+# ---------------------------------------------------------------------------
-+
-+
-+def test_rule_cache_defaults():
-+    """RuleCache() with no args produces a valid empty snapshot (version=0)."""
-+    cache = RuleCache()
-+    assert cache.sources == {}
-+    assert cache.folders == {}
-+    assert cache.rules == []
-+    assert cache.replacements == {}
-+    assert cache.compiled_patterns == {}
-+    assert cache.version == 0
-+    assert cache.refreshed_at is None
-+
-+
-+def test_rule_cache_with_version():
-+    """RuleCache stores the supplied version number."""
-+    cache = RuleCache(version=5)
-+    assert cache.version == 5
-+
-+
-+def test_rule_cache_with_refreshed_at():
-+    """RuleCache stores a non-None refreshed_at when explicitly supplied."""
-+    ts = datetime.now(timezone.utc)
-+    cache = RuleCache(version=1, refreshed_at=ts)
-+    assert cache.refreshed_at == ts
-+
-+
-+def test_rule_cache_frozen():
-+    """RuleCache is a frozen dataclass ╬ô├ç├╢ attributes cannot be mutated after creation."""
-+    cache = RuleCache(version=1)
-+    with pytest.raises((AttributeError, TypeError)):
-+        cache.version = 2  # type: ignore[misc]
-+
-+
-+def test_rule_cache_frozen_sources():
-+    """RuleCache.sources dict is NOT replaced after creation (frozen reference)."""
-+    cache = RuleCache(version=1, sources={"s1": object()})
-+    with pytest.raises((AttributeError, TypeError)):
-+        cache.sources = {}  # type: ignore[misc]
-+
-+
-+# ---------------------------------------------------------------------------
-+# CacheHolder ╬ô├ç├╢ singleton and atomic swap
-+# ---------------------------------------------------------------------------
-+
-+
-+def test_cache_holder_starts_with_empty_cache():
-+    """CacheHolder.current starts as an empty RuleCache (version=0).
-+
-+    Note: CacheHolder is module-level state ╬ô├ç├╢ we reset it before asserting to
-+    ensure isolation from other tests that mutate it.
-+    """
-+    CacheHolder.current = RuleCache()
-+    assert CacheHolder.current.version == 0
-+    assert CacheHolder.current.rules == []
-+    assert CacheHolder.current.refreshed_at is None
-+
-+
-+def test_cache_holder_atomic_swap():
-+    """Assigning CacheHolder.current replaces the snapshot reference atomically."""
-+    original = CacheHolder.current
-+    new_cache = RuleCache(version=42)
-+    CacheHolder.current = new_cache
-+    assert CacheHolder.current.version == 42
-+    # Restore to keep other tests clean
-+    CacheHolder.current = original
-+
-+
-+def test_cache_holder_multiple_swaps():
-+    """Multiple successive swaps always expose the latest cache."""
-+    saved = CacheHolder.current
-+    for v in range(1, 6):
-+        CacheHolder.current = RuleCache(version=v)
-+        assert CacheHolder.current.version == v
-+    CacheHolder.current = saved
-+
-+
-+def test_cache_holder_local_snapshot_not_affected_by_swap():
-+    """A local reference to the old snapshot is not changed by a later swap."""
-+    saved = CacheHolder.current
-+    snapshot_before = CacheHolder.current      # capture reference
-+    CacheHolder.current = RuleCache(version=99)
-+    # The local variable still points to the old snapshot
-+    assert snapshot_before is not CacheHolder.current
-+    CacheHolder.current = saved
-+
-+
-+# ---------------------------------------------------------------------------
-+# CompiledPatterns
-+# ---------------------------------------------------------------------------
-+
-+
-+def test_compiled_patterns_defaults():
-+    """CompiledPatterns has correct empty defaults."""
-+    p = CompiledPatterns()
-+    assert p.block_patterns == []
-+    assert p.allow_patterns == []
-+    assert p.replacement_patterns == {}
-+
-+
-+def test_compiled_patterns_with_real_patterns():
-+    """CompiledPatterns stores compiled re.Pattern objects correctly."""
-+    block = [re.compile("pump", re.IGNORECASE)]
-+    allow = [re.compile("btc", re.IGNORECASE)]
-+    repl = {"rr-id-1": re.compile("old", re.IGNORECASE)}
-+    p = CompiledPatterns(block_patterns=block, allow_patterns=allow, replacement_patterns=repl)
-+    assert len(p.block_patterns) == 1
-+    assert p.block_patterns[0].pattern == "pump"
-+    assert len(p.allow_patterns) == 1
-+    assert p.allow_patterns[0].pattern == "btc"
-+    assert "rr-id-1" in p.replacement_patterns
-+    assert p.replacement_patterns["rr-id-1"].pattern == "old"
-+
-+
-+def test_compiled_patterns_multiple_block_patterns():
-+    """CompiledPatterns can hold multiple block and allow patterns."""
-+    block = [re.compile(p, re.IGNORECASE) for p in ["pump.*", "dump.*", "scam"]]
-+    p = CompiledPatterns(block_patterns=block)
-+    assert len(p.block_patterns) == 3
-+    assert {pat.pattern for pat in p.block_patterns} == {"pump.*", "dump.*", "scam"}
-+
-+
-+def test_compiled_patterns_ignorecase_flag():
-+    """CompiledPatterns correctly stores patterns compiled with IGNORECASE."""
-+    pattern = re.compile("TestPattern", re.IGNORECASE)
-+    p = CompiledPatterns(block_patterns=[pattern])
-+    assert p.block_patterns[0].flags & re.IGNORECASE
-diff --git a/forward-bot/tests/infrastructure/mongo/test_folder_repository.py b/forward-bot/tests/infrastructure/mongo/test_folder_repository.py
-index 79edbdb..79f9d68 100644
---- a/forward-bot/tests/infrastructure/mongo/test_folder_repository.py
-+++ b/forward-bot/tests/infrastructure/mongo/test_folder_repository.py
-@@ -146,3 +146,97 @@ async def test_list_folders_with_source_count():
-     results_filtered = await repo.list_folders_with_source_count("crypto")
-     pipeline_filtered = mock_collection.aggregate.call_args[0][0]
-     assert any("$match" in step for step in pipeline_filtered)
-+
-+
-+# ---------------------------------------------------------------------------
-+# list_folders ╬ô├ç├╢ Story 3.3 addition
-+# ---------------------------------------------------------------------------
-+
-+
-+@pytest.mark.asyncio
-+async def test_list_folders_returns_all_folders():
-+    """list_folders() fetches all SourceFolders with no filtering (Story 3.3)."""
-+    mock_db = MagicMock()
-+    mock_collection = AsyncMock()
-+    mock_db.__getitem__.return_value = mock_collection
-+
-+    now = datetime.now(timezone.utc)
-+    mock_docs = [
-+        {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"), "name": "Folder A",
-+         "created_at": now, "updated_at": now},
-+        {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8f"), "name": "Folder B",
-+         "created_at": now, "updated_at": now},
-+    ]
-+
-+    mock_cursor = MagicMock()
-+    mock_cursor.to_list = AsyncMock(return_value=mock_docs)
-+    mock_collection.find = MagicMock(return_value=mock_cursor)
-+
-+    repo = FolderRepository(mock_db)
-+    folders = await repo.list_folders()
-+
-+    assert len(folders) == 2
-+    assert all(isinstance(f, SourceFolder) for f in folders)
-+    names = {f.name for f in folders}
-+    assert names == {"Folder A", "Folder B"}
-+
-+
-+@pytest.mark.asyncio
-+async def test_list_folders_called_with_empty_filter():
-+    """list_folders() queries the collection with an empty filter ({})."""
-+    mock_db = MagicMock()
-+    mock_collection = AsyncMock()
-+    mock_db.__getitem__.return_value = mock_collection
-+
-+    mock_cursor = MagicMock()
-+    mock_cursor.to_list = AsyncMock(return_value=[])
-+    mock_collection.find = MagicMock(return_value=mock_cursor)
-+
-+    repo = FolderRepository(mock_db)
-+    await repo.list_folders()
-+
-+    mock_collection.find.assert_called_once_with({})
-+
-+
-+@pytest.mark.asyncio
-+async def test_list_folders_empty_collection():
-+    """list_folders() returns an empty list when the collection is empty."""
-+    mock_db = MagicMock()
-+    mock_collection = AsyncMock()
-+    mock_db.__getitem__.return_value = mock_collection
-+
-+    mock_cursor = MagicMock()
-+    mock_cursor.to_list = AsyncMock(return_value=[])
-+    mock_collection.find = MagicMock(return_value=mock_cursor)
-+
-+    repo = FolderRepository(mock_db)
-+    folders = await repo.list_folders()
-+
-+    assert folders == []
-+
-+
-+@pytest.mark.asyncio
-+async def test_list_folders_maps_to_domain_entity():
-+    """list_folders() correctly maps MongoDB documents to SourceFolder entities."""
-+    mock_db = MagicMock()
-+    mock_collection = AsyncMock()
-+    mock_db.__getitem__.return_value = mock_collection
-+
-+    oid = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
-+    now = datetime.now(timezone.utc)
-+    mock_doc = {"_id": oid, "name": "My Folder", "created_at": now, "updated_at": now}
-+
-+    mock_cursor = MagicMock()
-+    mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
-+    mock_collection.find = MagicMock(return_value=mock_cursor)
-+
-+    repo = FolderRepository(mock_db)
-+    folders = await repo.list_folders()
-+
-+    assert len(folders) == 1
-+    folder = folders[0]
-+    assert folder.id == str(oid)
-+    assert folder.name == "My Folder"
-+    assert folder.created_at == now
-+    assert folder.updated_at == now
-+
-diff --git a/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py b/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py
-index 9474b9c..f9cd099 100644
---- a/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py
-+++ b/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py
-@@ -303,7 +303,7 @@ async def test_list_replacements_for_rule_returns_ordered_entities():
- 
-     # Verify query uses string comparison (not ObjectId)
-     mock_collection.find.assert_called_once_with({"forwarding_rule_id": PARENT_OID})
--    mock_cursor.sort.assert_called_once_with("created_at", 1)   # ASC ╬ô├ç├╢ pipeline order
-+    mock_cursor.sort.assert_called_once_with([("created_at", 1), ("_id", 1)])   # ASC with secondary sort
- 
- 
- @pytest.mark.asyncio
diff --git a/web/src/components/shared/ActivationBanner.tsx b/web/src/components/shared/ActivationBanner.tsx
new file mode 100644
index 0000000..e1bdc84
--- /dev/null
+++ b/web/src/components/shared/ActivationBanner.tsx
@@ -0,0 +1,71 @@
+import { Link } from "react-router-dom";
+import { AlertTriangle, Plus } from "lucide-react";
+import { cn } from "@/lib/utils";
+
+interface ActivationBannerProps {
+  isActive: boolean;
+  onActivate: () => void;
+  isFirstRun?: boolean;
+  className?: string;
+}
+
+export function ActivationBanner({
+  isActive,
+  onActivate,
+  isFirstRun = false,
+  className
+}: ActivationBannerProps) {
+  if (isFirstRun) {
+    return (
+      <div 
+        className={cn(
+          "w-full bg-warning-bg border border-warning-border rounded-lg p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 text-warning-foreground shadow-2xs select-none",
+          className
+        )}
+      >
+        <div className="flex items-start gap-3">
+          <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
+          <div>
+            <h3 className="font-bold text-sm">Welcome to Forward Bot!</h3>
+            <p className="text-xs mt-1 leading-normal opacity-90 font-medium">
+              There are no forwarding rules configured yet. Create a forwarding rule to begin routing messages between Telegram channels.
+            </p>
+          </div>
+        </div>
+        <Link 
+          to="/forwards/new"
+          className="inline-flex items-center gap-2 px-4 py-2 bg-warning-foreground text-white rounded-md text-xs font-bold hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer shadow-3xs self-start md:self-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
+        >
+          <Plus className="w-4 h-4" />
+          <span>Create your first rule</span>
+        </Link>
+      </div>
+    );
+  }
+
+  if (isActive) {
+    return null;
+  }
+
+  return (
+    <div 
+      className={cn(
+        "w-full bg-warning-bg border border-warning-border rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-warning-foreground shadow-2xs select-none",
+        className
+      )}
+    >
+      <div className="flex items-center gap-2">
+        <AlertTriangle className="w-5 h-5 flex-shrink-0" />
+        <span className="text-sm font-bold tracking-tight leading-normal">
+          This forward is inactive. Activate to begin processing.
+        </span>
+      </div>
+      <button
+        onClick={onActivate}
+        className="px-4 py-1.5 bg-warning-foreground text-white rounded-md text-xs font-bold hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer shadow-3xs self-start sm:self-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
+      >
+        Activate
+      </button>
+    </div>
+  );
+}
diff --git a/web/src/components/shared/CollapsiblePanel.tsx b/web/src/components/shared/CollapsiblePanel.tsx
new file mode 100644
index 0000000..b650e29
--- /dev/null
+++ b/web/src/components/shared/CollapsiblePanel.tsx
@@ -0,0 +1,58 @@
+import React, { useState, useId } from "react";
+import { ChevronDown } from "lucide-react";
+import { cn } from "@/lib/utils";
+
+interface CollapsiblePanelProps {
+  title: string;
+  summary: string;
+  children: React.ReactNode;
+  defaultOpen?: boolean;
+  className?: string;
+}
+
+export function CollapsiblePanel({
+  title,
+  summary,
+  children,
+  defaultOpen = false,
+  className
+}: CollapsiblePanelProps) {
+  const [isOpen, setIsOpen] = useState(defaultOpen);
+  const panelId = useId();
+
+  return (
+    <div className={cn("border border-border rounded-lg bg-card overflow-hidden transition-all duration-200 shadow-2xs", className)}>
+      <button
+        type="button"
+        aria-expanded={isOpen}
+        aria-controls={panelId}
+        onClick={() => setIsOpen(!isOpen)}
+        className="w-full flex items-center justify-between p-4 hover:bg-muted/30 text-left transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
+      >
+        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
+          <span className="font-semibold text-foreground">{title}</span>
+          <span className="text-sm text-secondary font-medium">{summary}</span>
+        </div>
+        <ChevronDown 
+          className={cn(
+            "w-5 h-5 text-muted-foreground transition-transform duration-300 ease-in-out flex-shrink-0",
+            isOpen && "rotate-180"
+          )}
+        />
+      </button>
+      <div 
+        id={panelId}
+        className={cn(
+          "grid transition-all duration-300 ease-in-out border-border bg-muted/5",
+          isOpen ? "grid-rows-[1fr] opacity-100 border-t" : "grid-rows-[0fr] opacity-0"
+        )}
+      >
+        <div className="overflow-hidden">
+          <div className="p-4 select-text">
+            {children}
+          </div>
+        </div>
+      </div>
+    </div>
+  );
+}
diff --git a/web/src/components/shared/DegradedBanner.tsx b/web/src/components/shared/DegradedBanner.tsx
new file mode 100644
index 0000000..f85e7d1
--- /dev/null
+++ b/web/src/components/shared/DegradedBanner.tsx
@@ -0,0 +1,29 @@
+import { AlertCircle, RefreshCw } from "lucide-react";
+
+interface DegradedBannerProps {
+  message: string;
+  onReconnect: () => void;
+}
+
+export function DegradedBanner({ message, onReconnect }: DegradedBannerProps) {
+  return (
+    <div
+      role="alert"
+      aria-live="assertive"
+      className="w-full bg-degraded-bg border-b border-degraded-border text-degraded-foreground py-3 px-4 flex flex-col sm:flex-row items-center justify-between gap-3 select-none"
+    >
+      <div className="flex items-center gap-2">
+        <AlertCircle className="w-5 h-5 flex-shrink-0 text-error animate-pulse" />
+        <span className="text-sm font-semibold tracking-tight leading-normal">{message}</span>
+      </div>
+
+      <button
+        onClick={onReconnect}
+        className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold border cursor-pointer select-none transition-all duration-300 bg-error text-white border-transparent hover:bg-red-700 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
+      >
+        <RefreshCw className="w-3.5 h-3.5" />
+        <span>Reconnect</span>
+      </button>
+    </div>
+  );
+}
diff --git a/web/src/components/shared/FilterIconRow.tsx b/web/src/components/shared/FilterIconRow.tsx
new file mode 100644
index 0000000..ad5d60a
--- /dev/null
+++ b/web/src/components/shared/FilterIconRow.tsx
@@ -0,0 +1,116 @@
+import { Clock, Shuffle, Image as ImageIcon, Key } from "lucide-react";
+import { cn } from "@/lib/utils";
+import type { FilterConfig } from "@/types/ui";
+import { Tooltip } from "./Tooltip";
+
+const getDaysText = (days: string[]) => {
+  const order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
+  const sorted = [...days].sort((a, b) => order.indexOf(a.toLowerCase()) - order.indexOf(b.toLowerCase()));
+  if (sorted.length === 5 && sorted[0].toLowerCase() === "mon" && sorted[4].toLowerCase() === "fri") {
+    return "MonΓÇôFri";
+  }
+  if (sorted.length === 7) {
+    return "Daily";
+  }
+  return sorted.map(d => d.charAt(0).toUpperCase() + d.slice(1).substring(0, 2)).join(", ");
+};
+
+const getOrdinal = (n: number) => {
+  const s = ["th", "st", "nd", "rd"];
+  const v = n % 100;
+  return n + (s[(v - 20) % 10] || s[v] || s[0]);
+};
+
+interface FilterIconRowProps {
+  config: FilterConfig;
+}
+
+export function FilterIconRow({ config }: FilterIconRowProps) {
+  // 1. Time Window
+  const hasTimeWindow = !!config.time_window;
+  const timeWindowTitle = hasTimeWindow
+    ? `${getDaysText(config.time_window!.days_of_week)} ${config.time_window!.start_time}ΓÇô${config.time_window!.end_time} ${config.time_window!.timezone}`
+    : "Time window: Inactive";
+
+  // 2. Sampling
+  const hasSampling = !!config.sampling && config.sampling.n > 0;
+  const samplingTitle = hasSampling
+    ? `Every ${getOrdinal(config.sampling!.n)} message`
+    : "Sampling: Inactive";
+
+  // 3. Media Type Filter
+  const hasMediaType = !!config.media_type_filter && config.media_type_filter.length > 0;
+  const mediaTypeTitle = hasMediaType
+    ? config.media_type_filter!.join(", ")
+    : "Media filter: Inactive";
+
+  // 4. Keywords
+  const blockCount = config.block_keywords?.length || 0;
+  const allowCount = config.allow_keywords?.length || 0;
+  const hasKeywords = blockCount > 0 || allowCount > 0;
+  const keywordsTitle = hasKeywords
+    ? `Keywords: ${blockCount} blocked, ${allowCount} allowed`
+    : "Keywords: Inactive";
+
+  const buttonClass = "w-6 h-6 flex items-center justify-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-all cursor-pointer";
+
+  return (
+    <div className="flex items-center gap-2 select-none">
+      {/* Time Window Icon */}
+      <Tooltip content={timeWindowTitle}>
+        <button
+          type="button"
+          aria-label={`Time window filter. Status: ${hasTimeWindow ? "Active" : "Inactive"}. Config: ${timeWindowTitle}`}
+          className={cn(
+            buttonClass,
+            hasTimeWindow ? "text-active opacity-100" : "text-secondary opacity-40"
+          )}
+        >
+          <Clock className="w-4 h-4" />
+        </button>
+      </Tooltip>
+
+      {/* Sampling Icon */}
+      <Tooltip content={samplingTitle}>
+        <button
+          type="button"
+          aria-label={`Sampling filter. Status: ${hasSampling ? "Active" : "Inactive"}. Config: ${samplingTitle}`}
+          className={cn(
+            buttonClass,
+            hasSampling ? "text-active opacity-100" : "text-secondary opacity-40"
+          )}
+        >
+          <Shuffle className="w-4 h-4" />
+        </button>
+      </Tooltip>
+
+      {/* Media Type Icon */}
+      <Tooltip content={mediaTypeTitle}>
+        <button
+          type="button"
+          aria-label={`Media type filter. Status: ${hasMediaType ? "Active" : "Inactive"}. Config: ${mediaTypeTitle}`}
+          className={cn(
+            buttonClass,
+            hasMediaType ? "text-active opacity-100" : "text-secondary opacity-40"
+          )}
+        >
+          <ImageIcon className="w-4 h-4" />
+        </button>
+      </Tooltip>
+
+      {/* Keywords Icon */}
+      <Tooltip content={keywordsTitle}>
+        <button
+          type="button"
+          aria-label={`Keyword filters. Status: ${hasKeywords ? "Active" : "Inactive"}. Config: ${keywordsTitle}`}
+          className={cn(
+            buttonClass,
+            hasKeywords ? "text-active opacity-100" : "text-secondary opacity-40"
+          )}
+        >
+          <Key className="w-4 h-4" />
+        </button>
+      </Tooltip>
+    </div>
+  );
+}
diff --git a/web/src/components/shared/LogRow.tsx b/web/src/components/shared/LogRow.tsx
new file mode 100644
index 0000000..58857d7
--- /dev/null
+++ b/web/src/components/shared/LogRow.tsx
@@ -0,0 +1,258 @@
+import React, { useState } from "react";
+import { 
+  ArrowUpRight, 
+  CircleSlash, 
+  AlertTriangle, 
+  Ban, 
+  Clock, 
+  Pencil, 
+  Trash2, 
+  CornerDownRight, 
+  Info,
+  Copy,
+  Check
+} from "lucide-react";
+import { Link } from "react-router-dom";
+import { toast } from "sonner";
+import { cn } from "@/lib/utils";
+import type { LogEntry } from "@/types/ui";
+import { Tooltip } from "./Tooltip";
+
+type LogRowVariant = 
+  | "forwarded"
+  | "filter_blocked"
+  | "telegram_rejected"
+  | "destination_unreachable"
+  | "flood_wait"
+  | "edit_propagated"
+  | "delete_propagated"
+  | "reply_orphaned"
+  | "default";
+
+const VARIANT_MAP: Record<string, LogRowVariant> = {
+  forward_succeeded: "forwarded",
+  edit_propagated: "edit_propagated",
+  delete_propagated: "delete_propagated",
+  
+  pipeline_blocked: "filter_blocked",
+  outside_time_window: "filter_blocked",
+  sampled_out: "filter_blocked",
+  media_type_filtered: "filter_blocked",
+  blocked_keyword: "filter_blocked",
+  no_allow_keyword_matched: "filter_blocked",
+  empty_after_processing: "filter_blocked",
+  unsupported_media_type: "filter_blocked",
+  
+  forward_failed: "telegram_rejected",
+  media_replacement_failed: "telegram_rejected",
+  telegram_session_invalidated: "telegram_rejected",
+  
+  flood_wait: "flood_wait",
+  reply_parent_not_found: "reply_orphaned",
+  reply_target_missing: "reply_orphaned",
+};
+
+const CONFIG_MAP: Record<LogRowVariant, {
+  stripeClass: string;
+  icon: React.ComponentType<any>;
+  iconClass: string;
+  labelClass?: string;
+}> = {
+  forwarded: {
+    stripeClass: "border-success",
+    icon: ArrowUpRight,
+    iconClass: "text-success",
+  },
+  filter_blocked: {
+    stripeClass: "border-muted",
+    icon: CircleSlash,
+    iconClass: "text-muted-foreground",
+  },
+  telegram_rejected: {
+    stripeClass: "border-error",
+    icon: AlertTriangle,
+    iconClass: "text-error",
+  },
+  destination_unreachable: {
+    stripeClass: "border-error",
+    icon: Ban,
+    iconClass: "text-error",
+  },
+  flood_wait: {
+    stripeClass: "border-warning-border",
+    icon: Clock,
+    iconClass: "text-warning-foreground",
+  },
+  edit_propagated: {
+    stripeClass: "border-success",
+    icon: Pencil,
+    iconClass: "text-success",
+  },
+  delete_propagated: {
+    stripeClass: "border-success",
+    icon: Trash2,
+    iconClass: "text-success",
+  },
+  reply_orphaned: {
+    stripeClass: "border-warning-border",
+    icon: CornerDownRight,
+    iconClass: "text-warning-foreground",
+    labelClass: "line-through opacity-70 text-warning-foreground/70",
+  },
+  default: {
+    stripeClass: "border-border",
+    icon: Info,
+    iconClass: "text-muted-foreground",
+  },
+};
+
+const formatEventLabel = (event: string) => {
+  return event
+    .split("_")
+    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
+    .join(" ");
+};
+
+const formatTimestamp = (ts: string) => {
+  try {
+    const date = new Date(ts);
+    return date.toLocaleTimeString(undefined, {
+      hour: "2-digit",
+      minute: "2-digit",
+      second: "2-digit",
+      hour12: false
+    });
+  } catch (e) {
+    return ts;
+  }
+};
+
+const getPayloadPreview = (entry: LogEntry) => {
+  if (entry.payload && typeof entry.payload === "object") {
+    return JSON.stringify(entry.payload);
+  }
+  const { event, level, timestamp, correlation_id, rule_id, ...rest } = entry;
+  if (Object.keys(rest).length === 0) return "";
+  return JSON.stringify(rest);
+};
+
+interface LogRowProps {
+  entry: LogEntry;
+}
+
+export function LogRow({ entry }: LogRowProps) {
+  const [isOpen, setIsOpen] = useState(false);
+  const [copied, setCopied] = useState(false);
+
+  const variant = VARIANT_MAP[entry.event] || "default";
+  const config = CONFIG_MAP[variant];
+  const Icon = config.icon;
+
+  const handleRowClick = (e: React.MouseEvent) => {
+    const target = e.target as HTMLElement;
+    if (target.closest("button") || target.closest("a")) {
+      return;
+    }
+    setIsOpen(!isOpen);
+  };
+
+  const handleCopyCorrelation = (e: React.MouseEvent) => {
+    e.stopPropagation();
+    if (entry.correlation_id) {
+      navigator.clipboard.writeText(entry.correlation_id);
+      setCopied(true);
+      toast.success("Correlation ID copied to clipboard");
+      setTimeout(() => setCopied(false), 2000);
+    }
+  };
+
+  const payloadPreview = getPayloadPreview(entry);
+
+  return (
+    <div 
+      className={cn(
+        "border border-border border-l-4 rounded-md overflow-hidden bg-card hover:bg-muted/15 transition-all duration-200 shadow-2xs select-none",
+        config.stripeClass,
+        isOpen && "shadow-xs"
+      )}
+    >
+      <div 
+        onClick={handleRowClick}
+        className="flex items-center justify-between p-3.5 gap-4 cursor-pointer"
+      >
+        <div className="flex items-center gap-3 min-w-0 flex-1">
+          <Icon className={cn("w-5 h-5 flex-shrink-0", config.iconClass)} />
+          <span className={cn("text-sm font-bold text-foreground truncate max-w-[180px] sm:max-w-[240px]", config.labelClass)}>
+            {formatEventLabel(entry.event)}
+          </span>
+          {payloadPreview && (
+            <span className="text-xs font-mono text-muted-foreground truncate max-w-sm sm:max-w-md md:max-w-lg hidden sm:inline select-text">
+              {payloadPreview}
+            </span>
+          )}
+        </div>
+
+        <div className="flex-shrink-0 flex items-center">
+          <Tooltip content={new Date(entry.timestamp).toLocaleString()}>
+            <span className="text-xs text-muted-foreground font-medium tabular-nums">
+              {formatTimestamp(entry.timestamp)}
+            </span>
+          </Tooltip>
+        </div>
+      </div>
+
+      <div 
+        className={cn(
+          "grid transition-all duration-300 ease-in-out border-border bg-muted/10",
+          isOpen ? "grid-rows-[1fr] border-t" : "grid-rows-[0fr]"
+        )}
+      >
+        <div className="overflow-hidden">
+          <div className="p-4 flex flex-col gap-3.5 select-text">
+            <div className="flex items-center justify-between gap-4 flex-wrap">
+              <div className="flex items-center gap-2">
+                <span className="text-xs text-muted-foreground">Level:</span>
+                <span className={cn(
+                  "text-xs px-2 py-0.5 rounded-full font-semibold border capitalize",
+                  entry.level === "debug" && "bg-muted-bg border-border text-muted-foreground",
+                  entry.level === "info" && "bg-success-bg border-success-border text-success-foreground",
+                  (entry.level === "warning" || entry.level === "error" || entry.level === "critical") && "bg-error-bg border-error-border text-error"
+                )}>
+                  {entry.level}
+                </span>
+              </div>
+              
+              <div className="flex items-center gap-3">
+                {entry.correlation_id && (
+                  <button
+                    onClick={handleCopyCorrelation}
+                    className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-card hover:bg-muted border border-border rounded-md text-muted-foreground hover:text-foreground transition-all cursor-pointer shadow-3xs"
+                  >
+                    {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
+                    <span>{copied ? "Copied" : "Copy Correlation ID"}</span>
+                  </button>
+                )}
+                {entry.rule_id && (
+                  <Link
+                    to={`/forwards?id=${entry.rule_id}`}
+                    onClick={(e) => e.stopPropagation()}
+                    className="text-xs text-primary hover:underline flex items-center gap-1 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
+                  >
+                    <span>Jump to rule ΓåÆ</span>
+                  </Link>
+                )}
+              </div>
+            </div>
+
+            <div className="flex flex-col gap-1.5">
+              <span className="text-xs font-semibold text-muted-foreground">Payload Details:</span>
+              <pre className="font-mono text-xs text-foreground p-3 bg-card border border-border rounded-md overflow-x-auto max-w-full shadow-3xs font-mono">
+                {JSON.stringify(entry, null, 2)}
+              </pre>
+            </div>
+          </div>
+        </div>
+      </div>
+    </div>
+  );
+}
diff --git a/web/src/components/shared/StatusPill.tsx b/web/src/components/shared/StatusPill.tsx
new file mode 100644
index 0000000..cd6b5d4
--- /dev/null
+++ b/web/src/components/shared/StatusPill.tsx
@@ -0,0 +1,49 @@
+import { CheckCircle2, Circle, AlertCircle, Clock } from "lucide-react";
+import { cn } from "@/lib/utils";
+import type { StatusPillStatus } from "@/types/ui";
+
+interface StatusPillProps {
+  status: StatusPillStatus;
+  className?: string;
+}
+
+const CONFIG = {
+  active: {
+    classes: "bg-success-bg border-success-border text-success-foreground",
+    icon: CheckCircle2,
+    label: "Active"
+  },
+  inactive: {
+    classes: "bg-muted-bg border-border text-muted-foreground",
+    icon: Circle,
+    label: "Inactive"
+  },
+  error: {
+    classes: "bg-error-bg border-error-border text-error",
+    icon: AlertCircle,
+    label: "Error"
+  },
+  stale: {
+    classes: "bg-warning-bg border-warning-border text-warning-foreground",
+    icon: Clock,
+    label: "Stale"
+  }
+};
+
+export function StatusPill({ status, className }: StatusPillProps) {
+  const config = CONFIG[status];
+  const Icon = config.icon;
+
+  return (
+    <span
+      className={cn(
+        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold select-none border",
+        config.classes,
+        className
+      )}
+    >
+      <Icon className="w-3.5 h-3.5 flex-shrink-0" />
+      <span>{config.label}</span>
+    </span>
+  );
+}
diff --git a/web/src/components/shared/Tooltip.tsx b/web/src/components/shared/Tooltip.tsx
new file mode 100644
index 0000000..5918f71
--- /dev/null
+++ b/web/src/components/shared/Tooltip.tsx
@@ -0,0 +1,56 @@
+import React, { useState, useId } from "react";
+import { cn } from "@/lib/utils";
+
+interface TooltipProps {
+  content: React.ReactNode;
+  children: React.ReactElement<any>;
+  className?: string;
+}
+
+export function Tooltip({ content, children, className }: TooltipProps) {
+  const [visible, setVisible] = useState(false);
+  const id = useId();
+
+  const handleFocus = () => setVisible(true);
+  const handleBlur = () => setVisible(false);
+
+  // Clone children to ensure they have the proper focus handlers if they need them
+  // and aria-describedby for accessibility.
+  const trigger = React.cloneElement(children, {
+    "aria-describedby": visible ? id : undefined,
+    onFocus: (e: React.FocusEvent<any>) => {
+      handleFocus();
+      if (children.props && typeof children.props.onFocus === "function") {
+        children.props.onFocus(e);
+      }
+    },
+    onBlur: (e: React.FocusEvent<any>) => {
+      handleBlur();
+      if (children.props && typeof children.props.onBlur === "function") {
+        children.props.onBlur(e);
+      }
+    }
+  });
+
+  return (
+    <div 
+      className="relative inline-block"
+      onMouseEnter={() => setVisible(true)}
+      onMouseLeave={() => setVisible(false)}
+    >
+      {trigger}
+      {visible && (
+        <div 
+          id={id}
+          className={cn(
+            "absolute bottom-full left-1/2 z-50 mb-2 w-max max-w-xs -translate-x-1/2 rounded bg-black/90 px-2.5 py-1.5 text-xs text-white shadow-md animate-in fade-in duration-100",
+            className
+          )}
+          role="tooltip"
+        >
+          {content}
+        </div>
+      )}
+    </div>
+  );
+}
diff --git a/web/src/components/shared/index.ts b/web/src/components/shared/index.ts
new file mode 100644
index 0000000..aad7db0
--- /dev/null
+++ b/web/src/components/shared/index.ts
@@ -0,0 +1,9 @@
+export { DegradedBanner } from "./DegradedBanner";
+export { LogRow } from "./LogRow";
+export { FilterIconRow } from "./FilterIconRow";
+export { StatusPill } from "./StatusPill";
+export { CollapsiblePanel } from "./CollapsiblePanel";
+export { ActivationBanner } from "./ActivationBanner";
+export { Tooltip } from "./Tooltip";
+export { Button } from "./Button";
+export { Sheet } from "./Sheet";
diff --git a/web/src/types/ui.ts b/web/src/types/ui.ts
new file mode 100644
index 0000000..0713f6c
--- /dev/null
+++ b/web/src/types/ui.ts
@@ -0,0 +1,25 @@
+export interface LogEntry {
+  event: string;
+  level: "debug" | "info" | "warning" | "error" | "critical";
+  timestamp: string;
+  correlation_id?: string;
+  rule_id?: string;
+  [key: string]: unknown;
+}
+
+export interface FilterConfig {
+  time_window?: {
+    timezone: string;
+    days_of_week: string[];
+    start_time: string;
+    end_time: string;
+  };
+  sampling?: {
+    n: number;
+  };
+  media_type_filter?: string[];
+  block_keywords?: string[];
+  allow_keywords?: string[];
+}
+
+export type StatusPillStatus = "active" | "inactive" | "error" | "stale";

</diff>
