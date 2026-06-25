# Review Findings: Shared UI Component Library

## Blind Hunter (Adversarial Review)
- **LogRow Accessibility Violation**: `LogRow` uses a `div` with `onClick` to toggle expansion, but it lacks `role="button"`, `tabIndex={0}`, and an `onKeyDown` handler. This makes the row expansion inaccessible to keyboard users.
- **Missing Loading States**: Both `DegradedBanner`'s `[Reconnect]` button and `ActivationBanner`'s `[Activate]` button accept `onClick` handlers but lack a `disabled` or `loading` state to prevent users from double-clicking or spamming the action during network requests.
- **LogRow Event Label Formatting**: `formatEventLabel` splits by `_` and capitalizes, but does not handle potential missing fields or non-string values gracefully. If `entry.event` is undefined, it crashes.
- **StatusPill Invalid Status**: `StatusPill` accesses `CONFIG[status]`. If `status` is somehow passed outside the strict types (e.g. from backend API changing), `config` is undefined and it crashes trying to read `config.icon`.
- **CollapsiblePanel Accessibility**: While `aria-expanded` is set, the content only uses `grid-rows-[0fr]` and `opacity-0` when closed. Depending on screen reader heuristics, focusable elements inside the collapsed panel might still be focusable unless `aria-hidden="true"` or `visibility: hidden` is applied.

## Edge Case Hunter
- **LogRow Date Parsing**: The `formatTimestamp` function uses `new Date(ts)`. If the timestamp is invalid, `new Date("invalid")` does not throw an error; it results in an Invalid Date object. `toLocaleTimeString` then returns "Invalid Date", bypassing the `try/catch` fallback to the original string.
- **FilterIconRow Day Formatting**: `getDaysText` has logic to format "Mon-Fri" or "Daily". If an unknown day is passed or capitalization is unexpected, `sort` relies on finding it in the `order` array. Unfound elements get `indexOf = -1` and might sort unexpectedly.
- **ActivationBanner Conflict**: If both `isFirstRun={true}` and `isActive={true}` are passed, `isFirstRun` takes precedence and renders the warning banner, which contradicts the concept of being "active".

## Acceptance Auditor
- **Violation of UX-DR21 (Accessibility Floor)**: "keyboard focus rings are visible... semantic HTML is used: `<button>` for all interactive triggers." `LogRow` expansion uses a `div` instead of a semantic `<button>` or at least `role="button"` with keyboard support, violating the spec.
- **Missing Tooltip Keyboard Focus**: The AC mandates "full screen-reader and keyboard focus accessibility" for `Tooltip` in AC:1. Since `Tooltip` relies on wrapping elements, it requires the child to be focusable (which `FilterIconRow` buttons are), but it's important to verify if hover-only logic is robust.
- **FilterIconRow Tooltip Format**: AC states `time_window` should show `"Mon–Fri 09:00–17:00 Europe/Warsaw"`. The implementation dynamically builds this string correctly, aligning perfectly with the AC.
- **CollapsiblePanel Spec Alignment**: Grid transitions and `rotate-180` are implemented exactly as specified.

