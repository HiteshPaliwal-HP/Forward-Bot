---
baseline_commit: NO_VCS
---

# Story 7.3: Web Admin Settings Page UI for Cache Refresh & Telegram Session Control

Status: done

## Story

As a Channel Operator,
I want UI controls on the Settings page (S8) and top header bar to trigger cache refreshes and manage the Telegram session,
so that I can control caching and session authentication directly from my browser.

## Acceptance Criteria

1. **Given** the operator is on Settings (S8) or the header action bar, **when** the operator clicks the **"Refresh Cache"** button, **then** `POST /api/v1/admin/cache/refresh` is called; on HTTP 200 a success toast notification appears surfacing the refreshed cache metadata (`version`, `rule_count`, `source_count`, `refreshed_at` timestamp), and `queryKeys.health.cache()` is invalidated (FR-12b). On HTTP 500 or network failure, a destructive toast surfaces the error to the operator.
2. **Given** the operator navigates to `/settings` (S8), **when** the Telegram Session Card renders, **then** it fetches status from `GET /api/v1/telegram/auth/status`. If connected, it displays a green "CONNECTED" badge with pulse indicator and "Terminate Session" button; if disconnected, it displays a red "DISCONNECTED" badge and the Telegram OTP connect form (FR-46).
3. **Given** the Telegram Session Card is DISCONNECTED, **when** `phone_required: true` (or `TELEGRAM_PHONE` is absent from `.env`), **then** an E.164 phone input field (`+<country><number>`) is displayed; clicking "Send OTP" triggers a 60s client-side throttle timer on the button and calls `POST /api/v1/telegram/auth/start`. On success, it reveals a 6-digit numeric OTP input field (FR-47).
4. **Given** the operator enters the 6-digit OTP code and clicks "Connect", **when** `POST /api/v1/telegram/auth/verify` is called with `{ "otp": "...", "phone": "..." }` (including the phone if entered previously), **then** on HTTP 200 the session connects, toast notification confirms connection, query cache invalidates, and UI transitions to CONNECTED state. If HTTP 202 `{ "requires_2fa": true }` is returned, a masked password input field is revealed for submitting 2FA credentials (FR-48).
5. **Given** auth edge cases during OTP/2FA submission (wrong OTP 400 `invalid_otp`, expired OTP 400 `otp_expired`, concurrent auth 409 `auth_in_progress`, already connected 409 `already_connected`), **when** an API error occurs, **then** clear inline error messages and toast notifications surface the error without crashing or losing form state (FR-50).
6. **Given** an active Telegram session exists and the operator clicks "Terminate Session", **when** the confirmation modal opens, **then** the operator must type `terminate` (case-insensitive) into a text field to enable the "Confirm Terminate" button. Clicking "Confirm Terminate" calls `POST /api/v1/telegram/auth/terminate`, closes the modal, surfaces a success toast, and transitions the UI to DISCONNECTED state (FR-49, UX-DR28).

## Tasks / Subtasks

- [x] Task 1: Create Frontend API Clients & Query Keys (AC: #1, #2)
  - [x] Create `web/src/api/telegramAuth.ts` with API methods:
    - `getStatus()` -> `GET /api/v1/telegram/auth/status`
    - `startAuth(phone?: string)` -> `POST /api/v1/telegram/auth/start`
    - `verifyAuth(payload: { otp: string; password?: string; phone?: string })` -> `POST /api/v1/telegram/auth/verify`
    - `terminateSession()` -> `POST /api/v1/telegram/auth/terminate`
  - [x] Create `web/src/api/admin.ts` with method `refreshCache()` -> `POST /api/v1/admin/cache/refresh`.
  - [x] Update `web/src/lib/queryKeys.ts` with `telegramAuth` query key factory (`status`, `all`).
- [x] Task 2: Implement "Refresh Cache" Button in TopBar & Settings (AC: #1)
  - [x] Add "Refresh Cache" button affordance in `web/src/components/layout/TopBar.tsx`.
  - [x] Connect button to `adminApi.refreshCache()` mutation using `@tanstack/react-query`.
  - [x] Show loading state spinner while mutation is pending (`isPending`).
  - [x] On HTTP 200 (`onSuccess`): display `sonner` success toast with formatted metadata: `Cache rebuilt (v{version}) — {rule_count} rules, {source_count} sources` and invalidate `queryKeys.health.cache()`.
  - [x] On failure (`onError`): display `sonner` destructive toast with the error message.
- [x] Task 3: Implement Telegram Session Management Card in `web/src/pages/Settings.tsx` (AC: #2, #3, #4, #5)
  - [x] Query `telegramAuthApi.getStatus` using TanStack Query (`staleTime: 10_000`, `refetchInterval: 10_000`).
  - [x] Implement CONNECTED state UI:
    - Status badge: Green tinted pill with animated green pulse dot (using Tailwind `animate-pulse rounded-full`) & text "CONNECTED".
    - Details: Show masked phone number (e.g., `+123 •••• 7890`) and session storage path.
    - Action: "Terminate Session" button (red outline/subtle style).
  - [x] Implement DISCONNECTED state UI:
    - Status badge: Red tinted pill with red dot & text "DISCONNECTED".
    - Phone input field (E.164 format regex `^\+[1-9]\d{6,14}$`) when `phone_required: true`.
    - "Send OTP" button with 60s countdown timer (isolate timer logic into a custom hook or separate component to prevent full page re-renders).
    - OTP Step: Render 6-digit OTP code input + "Connect Telegram" button upon `/start` success.
    - 2FA Step: Render masked password input + "Submit 2FA Password" button upon HTTP 202 `requires_2fa: true`.
    - Error handling: Handle 400 (`invalid_otp`, `otp_expired`), 409 (`auth_in_progress`, `already_connected`), and 422 with inline alerts and toast messages. Ensure to pass the `phone` state into the `verifyAuth` mutation if provided.
- [x] Task 4: Implement Terminate Session Confirmation Modal (AC: #6)
  - [x] Import existing confirmation dialog components from `web/src/components/ui/dialog` or `alert-dialog` (do not run shadcn add if they already exist).
  - [x] Create confirmation dialog in `Settings.tsx`.
  - [x] Display warning text: "Terminating the Telegram session will disconnect the forwarding worker. Incoming messages will be dropped."
  - [x] Add text input requiring user to type `terminate` to unlock the action.
  - [x] Connect "Confirm Terminate" button to `telegramAuthApi.terminateSession()` mutation.
  - [x] On success (`onSuccess`): Show toast "Telegram session terminated", close modal, invalidate `queryKeys.telegramAuth.status()` and `queryKeys.health.telegram()`.
- [x] Task 5: Component Testing (AC: #1, #2, #3, #4, #6)
  - [x] Add tests in `web/src/pages/Settings.test.tsx` for Telegram Session Card rendering, Refresh Cache trigger, OTP flow steps, and Terminate Modal validation.

### Review Findings
- [x] [Review][Patch] Missing `refreshed_at` in the cache refresh success toast in `TopBar.tsx`. [web/src/components/layout/TopBar.tsx:28]
- [x] [Review][Patch] `otpCountdown` in `Settings.tsx` `useEffect` is in the dependency array, causing the interval to repeatedly tear down and recreate every second. [web/src/pages/Settings.tsx:75]
- [x] [Review][Defer] "Active Session Duration" `sessionUptime` starts ticking from 0 on client load, doesn't reflect actual backend session age. [web/src/pages/Settings.tsx:62] — deferred, pre-existing

## Dev Notes & Technical Requirements

### Architecture Compliance
- **S8 Settings Page (UX-DR26, UX-DR27, UX-DR28)**: Place the Telegram Session Card prominently in `Settings.tsx` above or beside appearance settings.
- **REST Endpoints & TypeScript Interfaces**:
  ```typescript
  // telegramAuth.ts
  export interface AuthStatus { connected: boolean; phone: string | null; phone_required: boolean; session_path: string; }
  export interface StartAuthPayload { phone?: string; }
  export interface VerifyAuthPayload { otp: string; password?: string; phone?: string; }
  
  // admin.ts
  export interface CacheRefreshResponse { status: string; cache: { version: number; rule_count: number; source_count: number; refreshed_at: string; } }
  ```
- **Error Envelope Handling**: 
  - Backend returns standard errors in envelope format: `{"error": {"code": "invalid_otp", "message": "..."}}`. 
  - FastAPI Pydantic validation errors (422) return `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.
  - Create a utility function (e.g., `parseApiError(err: unknown): string`) to safely extract the message from both Axios error formats to keep components clean.
- **Query Key Hygiene**: Use `queryKeys.telegramAuth.status()` for session status query. Invalidate `queryKeys.health.all` and `queryKeys.telegramAuth.all` on auth status changes.
- **Shadcn/UI Components**: Always check `web/src/components/ui/` for existing components (like Dialog, AlertDialog, Button, Input) before attempting to add them via CLI. Reuse existing components.

### Design System & Component Guidelines
- **Colors & Tokens**: Use `--color-success` / `bg-emerald-500` for connected status, `--color-error` / `bg-red-500` for disconnected status, and `--color-warning` / `bg-amber-500` for intermediate states.
- **Pulse Animation**: Use Tailwind classes `w-2 h-2 rounded-full bg-emerald-500 animate-pulse` for the CONNECTED badge indicator.
- **Buttons & Accessibility**:
  - "Send OTP" countdown: Disabled with copy `"Resend in 45s"` while countdown active.
  - "Terminate Session" button: Modal requires exact string `"terminate"` (case-insensitive `val.trim().toLowerCase() === "terminate"`).
  - ARIA attributes: Modals must have `role="dialog"`, inputs must have explicit labels or `aria-label`.

### File Structure Requirements
- `web/src/api/telegramAuth.ts`: API client module for Telegram Auth endpoints.
- `web/src/api/admin.ts`: API client module for Admin cache refresh endpoint.
- `web/src/lib/queryKeys.ts`: Update query keys factory object.
- `web/src/components/layout/TopBar.tsx`: Add Refresh Cache button to top header bar.
- `web/src/pages/Settings.tsx`: Update with Telegram Session Card, Refresh Cache button, and Terminate Modal.
- `web/src/pages/Settings.test.tsx`: Component tests.

### References
- [Epics Document: Story 7.3](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L1329)
- [Story 7.2 Specification & Dev Notes](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/implementation-artifacts/7-2-telegram-session-management-backend-api-lifecycle-methods.md)
- [Story 7.1 Multi-Tier Rule Cache](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/implementation-artifacts/7-1-multi-tier-rule-cache-rebuild-admin-refresh-api.md)
- [Backend Telegram Auth Router](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/telegram_auth.py)
- [Backend Admin Router](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/api/routers/admin.py)

## Dev Agent Record

### Agent Model Used
Gemini 3.6 Flash (High)

### Debug Log References

### Completion Notes List
- Implemented `web/src/api/telegramAuth.ts` and `web/src/api/admin.ts` API clients wrapping `/api/v1/telegram/auth` and `/api/v1/admin/cache/refresh` endpoints.
- Added `parseApiError` utility function in `web/src/lib/utils.ts` to parse standard error envelopes (`{ error: { message } }`) and Pydantic 422 detail arrays.
- Updated `web/src/lib/queryKeys.ts` with `telegramAuth` query key factory.
- Implemented "Refresh Cache" button affordance in `web/src/components/layout/TopBar.tsx` with loading spinner, success metadata toast, error handling, and query invalidation.
- Implemented Telegram Session Control Card in `web/src/pages/Settings.tsx` handling CONNECTED (green badge + pulse indicator, masked phone, session path, terminate trigger) and DISCONNECTED (red badge, E.164 phone input, 60s Send OTP countdown timer, 6-digit OTP code entry, and 2FA password step upon HTTP 202).
- Implemented Terminate Session confirmation modal in `Settings.tsx` enforcing user entry of `terminate` to unlock confirmation and trigger `telegramAuthApi.terminateSession()`.
- Created comprehensive component unit & integration tests in `web/src/pages/Settings.test.tsx` verifying all ACs (1-6).

### File List
- `web/src/lib/utils.ts` (Modified)
- `web/src/api/telegramAuth.ts` (New)
- `web/src/api/admin.ts` (New)
- `web/src/lib/queryKeys.ts` (Modified)
- `web/src/components/layout/TopBar.tsx` (Modified)
- `web/src/pages/Settings.tsx` (Modified)
- `web/src/pages/Settings.test.tsx` (New)

### Change Log
- 2026-09-07: Completed implementation of Web Admin Settings Page UI for Cache Refresh & Telegram Session Control (Story 7-3).
