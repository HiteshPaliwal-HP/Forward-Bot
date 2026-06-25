---
baseline_commit: 424cecd133253d696b37bb010508975705c2250f
---
# Story 6.1: React SPA Foundation — Brand Tokens, App Layout & Authentication

Status: done

## Story

As a **Channel Operator**,
I want a polished, consistently branded single-page application that authenticates me with a session cookie and provides a persistent sidebar navigation,
so that I can operate the bot confidently from a professional interface without re-entering credentials on every page refresh.

## Acceptance Criteria

1. **Vite Build & Static Serving:**
   - **Given** the frontend scaffold exists inside `web/`.
   - **When** `npm run build` is executed inside `web/`.
   - **Then** compiled output lands in `web/dist/` and FastAPI's existing `StaticFiles` mount + SPA catch-all in `app.py` serves it correctly at `/`.
   - **And** the FastAPI catch-all `GET /{catchall:path}` remains the LAST route registered in `app.py` (already implemented — do NOT re-register it).

2. **Brand Token CSS System:**
   - **Given** the DESIGN.md brand token system (UX-DR1).
   - **When** `web/src/styles/tokens.css` is created and imported in `web/src/index.css`.
   - **Then** it declares all CSS custom properties for `[data-theme="light"]` and `[data-theme="dark"]` selectors matching DESIGN.md:
     - Warm-stone palette: `--color-bg` (`#FAFAF9` light / `#14130F` dark), `--color-bg-muted` (`#F4F4F2` light / `#1C1B16` dark), `--color-surface` (`#FFFFFF` light / `#1C1B16` dark), `--color-border` (`#E7E5E0` light / `#2A2823` dark), `--color-text-primary` (`#1C1917` light / `#E7E5E0` dark), `--color-text-secondary` (`#78716C` light / `#A8A29E` dark)
     - Forwarding Green accent: `--color-active` (`#16A34A` light / `#22C55E` dark), `--color-active-hover` (`#15803D` light / `#16A34A` dark)
     - State Success: `--color-success` (`#16A34A` light / `#22C55E` dark), `--color-success-bg` (`#F0FDF4` light / `rgba(34,197,94,0.12)` dark), `--color-success-border` (`#BBF7D0` light / `rgba(34,197,94,0.35)` dark), `--color-success-foreground` (`#15803D` light / `#4ADE80` dark)
     - State Warning: `--color-warning` (`#D97706` light / `#F59E0B` dark), `--color-warning-bg` (`#FEF3C7` light / `rgba(245,158,11,0.14)` dark), `--color-warning-border` (`#FDE68A` light / `rgba(245,158,11,0.45)` dark), `--color-warning-foreground` (`#92400E` light / `#FCD34D` dark)
     - State Error: `--color-error` (`#DC2626` light / `#EF4444` dark), `--color-error-bg` (`#FEF2F2` light / `rgba(239,68,68,0.12)` dark), `--color-error-border` (`#FECACA` light / `rgba(239,68,68,0.35)` dark)
     - State Degraded: `--color-degraded-bg` (`#FEF2F2` light / `rgba(239,68,68,0.14)` dark), `--color-degraded-border` (`#FCA5A5` light / `rgba(239,68,68,0.45)` dark), `--color-degraded-foreground` (`#991B1B` light / `#FCA5A5` dark)
     - State Muted: `--color-muted` (`#A8A29E` light / `#78716C` dark), `--color-muted-bg` (`#F4F4F2` light / `#1C1B16` dark)
     - Monospace font stack: `--font-mono` (`ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace` at 12px, 1.5 line-height)
     - Shadcn tokens wired to match variables (e.g. `--background`, `--foreground`, `--primary`, `--border`, `--card`, `--card-foreground`).

3. **React Router v7 Declarative Mode (MIGRATION REQUIRED):**
   - **Given** the current `web/src/router.tsx` uses `createBrowserRouter` (non-compliant with architecture F2).
   - **When** the story is implemented.
   - **Then** `web/src/main.tsx` is updated to use `BrowserRouter` + `Routes` (declarative mode).
   - **And** `web/src/router.tsx` is replaced by route definitions directly in `web/src/App.tsx` (or a `web/src/routes/index.tsx` file).
   - **And** all existing stub pages continue to resolve at their current paths.

4. **Authentication — Backend Auth Router (NEW FILE):**
   - **Given** `GET /api/v1/auth/me`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout` do not currently exist.
   - **When** `api/routers/auth.py` is created and registered in `app.py` before the SPA catch-all.
   - **Then**:
     - `GET /api/v1/auth/me` requires `Depends(get_current_operator)`, returns `{"ok": true}` (used by `RequireAuth` wrapper on frontend to check session).
     - `POST /api/v1/auth/login` accepts `{"api_key": "..."}`, validates via `secrets.compare_digest`, on match sets HttpOnly SameSite=Strict session cookie (24h TTL) using `itsdangerous.TimestampSigner`, returns `{"ok": true}`; on mismatch returns HTTP 401 with `{"error": {"code": "invalid_credentials", "message": "Invalid API key."}}`.
     - `POST /api/v1/auth/logout` clears the session cookie (sets max_age=0), returns `{"ok": true}` (no auth required to log out).
     - The cookie name is `session`; `Secure` flag set when `settings.bind_host != "127.0.0.1"`; `SameSite="strict"`.

5. **Authentication — Frontend Login Page:**
   - **Given** a user visits any protected page with no session cookie.
   - **When** the `RequireAuth` component in `web/src/components/auth/RequireAuth.tsx` evaluates auth state via `GET /api/v1/auth/me`.
   - **Then** the user is redirected to `/login?return=<current-path>`.
   - **And** `web/src/pages/Login.tsx` renders: a centered card with the Forward Bot wordmark, an "API Key" password input, a Submit button.
   - **And** on success `POST /api/v1/auth/login` responds HTTP 200 and the user is redirected to the saved `return` path (or `/` if absent).
   - **And** on HTTP 401 an inline error message "Invalid API key" appears below the input.
   - **And** any subsequent API call returning 401 mid-session redirects to `/login?return=<current-path>` with a toast "Session expired — sign in to continue."
   - **And** on mount, if the URL contains a `return` query parameter, the Login page renders the "Session expired — sign in to continue." toast to handle full-page reloads from the Axios interceptor.

6. **Persistent Sidebar Layout (UX-DR2 & UX-DR22):**
   - **Given** the user is authenticated and visits any route.
   - **When** the `AppLayout` component renders.
   - **Then** a persistent left sidebar contains: Forward Bot logo/wordmark at top, nav items for Dashboard (`/`), Forwards (`/forwards`), Sources (`/sources`), Logs (`/logs`), Settings (`/settings`); the active route item is highlighted using the `--color-active` accent.
   - **And** a top bar renders with: breadcrumb navigation on the left, Telegram status dot on the right (green = connected, yellow = reconnecting with pulse animation, red = disconnected/degraded) fetched from root `GET /health/telegram`, and a Rules cache stale warning pill (warning-tinted, text "Rules cache stale (last refresh <time> ago)") if the background cache refresh fails.
   - **And** a global `DegradedBanner` renders immediately below the top bar when Telegram status is disconnected/reconnecting or MongoDB is down (announcing to screen readers with `role="alert"` and `aria-live="assertive"`), showing status info and a `[Reconnect]` action button (with loading spinner during reconnection and green checkmark on success).
   - **And** the main content pane has a `max-w-6xl` centered layout.
   - **And** on screens < 768px (`md` breakpoint) the sidebar collapses and is accessible via a hamburger menu (shadcn Sheet component).

7. **Vim-Style Keyboard Shortcuts (UX-DR9):**
   - **Given** the user is on any authenticated screen.
   - **When** they press `g` then `d` within 1000 ms.
   - **Then** they navigate to Dashboard (`/`).
   - **And** `g→f` → `/forwards`; `g→s` → `/sources`; `g→l` → `/logs`; `g→,` → `/settings`.
   - **And** the chord resets after 1000 ms with no second key (useEffect cleanup).
   - **And** all shortcut triggers are ignored if the active document focus is inside an input, textarea, select, or contenteditable element to prevent typing interference.

8. **Theme Toggle (UX-DR22):**
   - **Given** a theme toggle exists in the sidebar (icon button cycling System → Light → Dark).
   - **When** the user clicks it.
   - **Then** `ThemeContext` (the only global context for theme per architecture F3) toggles `data-theme` on `<html>` between `light` and `dark`, persisted in `localStorage` under `fb-theme`, and applied before first render (no flash).

9. **Axios Client & TanStack Query Setup:**
   - **Given** `web/src/api/client.ts` exports an Axios instance.
   - **When** any API call is made.
   - **Then** the Axios instance has `baseURL: '/api/v1'`, `withCredentials: true`; a 401 response interceptor redirects to `/login?return=<current-path>`.

## Tasks / Subtasks

- [x] **1. Backend: Auth, Media & Health Routers** (AC: 4, NFR-RuleChange)
  - [x] Create `forward-bot/src/forward_bot/api/routers/auth.py` with `GET /api/v1/auth/me`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`
  - [x] Create `forward-bot/src/forward_bot/api/routers/media.py` with `GET /api/v1/media/replacement-images` listing files in `MEDIA_REPLACEMENT_BASE_DIR`
  - [x] Update `forward-bot/src/forward_bot/api/routers/health.py` or `stats.py` to expose cache health details (`refreshed_at`, `version`)
  - [x] Register routers in `app.py` before the SPA catch-all route
  - [x] Write unit tests in `forward-bot/tests/api/test_auth.py` and `test_media.py`
 
- [x] **2. Frontend: CSS Brand Token System** (AC: 2)
  - [x] Create `web/src/styles/tokens.css` with warm-stone palette, Forwarding Green, state success/warning/error/degraded/muted variables, and shadcn token wiring for both `[data-theme="light"]` and `[data-theme="dark"]`
  - [x] Update `web/src/index.css` to import tokens and reset the default vite/shadcn CSS to project conventions
 
- [x] **3. Frontend: Router Migration** (AC: 3)
  - [x] Replace `createBrowserRouter` + `RouterProvider` in `main.tsx` with `BrowserRouter` + `Routes` (declarative mode per architecture F2)
  - [x] Create `web/src/routes/index.tsx` with all existing routes preserved; do NOT run `npx shadcn init` again to avoid overwriting stub pages
  - [x] Remove or repurpose `web/src/router.tsx`
 
- [x] **4. Frontend: Axios Client, QueryClient & QueryKeys** (AC: 9)
  - [x] Create `web/src/api/client.ts` (Axios instance, baseURL, withCredentials, 401 interceptor)
  - [x] Create `web/src/lib/queryClient.ts` (QueryClient instance, move from `main.tsx` inline)
  - [x] Create `web/src/lib/queryKeys.ts` (centralized key factory)
  - [x] Create `web/src/api/auth.ts` with `login()`, `logout()`, `me()` calls
  - [x] Create `web/src/api/media.ts` with `fetchReplacementImages()` call
 
- [x] **5. Frontend: ThemeContext** (AC: 8)
  - [x] Create `web/src/contexts/ThemeContext.tsx` with System/Light/Dark state, `localStorage` persistence under `fb-theme`, `data-theme` attribute applied to `<html>`, and active preference listener for system theme changes
  - [x] Apply theme before first render to prevent flash (inline `<script>` in `index.html` or `useLayoutEffect` on mount)
 
- [x] **6. Frontend: Auth Flow** (AC: 5)
  - [x] Create `web/src/hooks/useAuth.ts` (TanStack Query backed by `GET /api/v1/auth/me`)
  - [x] Create `web/src/components/auth/RequireAuth.tsx` (redirects to `/login?return=...` if not authenticated)
  - [x] Create `web/src/pages/Login.tsx` (centered card UI, API key input, submit, inline error, session expired toast from URL return check)
 
- [x] **7. Frontend: AppLayout & Sidebar** (AC: 6)
  - [x] Create `web/src/components/layout/Sidebar.tsx` (logo, 5 nav items, active highlight, theme toggle, mobile Sheet collapse)
  - [x] Create `web/src/components/layout/TopBar.tsx` (breadcrumbs, Telegram status dot with pulse, rules cache stale pill)
  - [x] Create `web/src/components/layout/DegradedBanner.tsx` (announce-only global alert banner, Reconnect button with loading/success states)
  - [x] Update `web/src/components/layout/Layout.tsx` to become the full `AppLayout` wrapping Sidebar + TopBar + DegradedBanner + main content
  - [x] Create `web/src/api/health.ts` with `fetchHealth()`, `fetchTelegramStatus()`, and `fetchCacheStatus()` functions
 
- [x] **8. Frontend: Keyboard Shortcuts Hook** (AC: 7)
  - [x] Create `web/src/hooks/useKeyboardShortcuts.ts` with 2-key chord detection (1000ms window), ignoring input fields, and wire navigation to `useNavigate()`
  - [x] Register hook in `AppLayout`
 
- [x] **9. Verify Build** (AC: 1)
  - [x] Run `npm run build` in `web/` — must complete with zero TypeScript errors
  - [x] Verify all existing routes still resolve after router migration

### Review Findings

- [x] [Review][Patch] Tailwind v4 Color Utility Bug [web/src/components/*] — Tailwind v4 strips the `color-` prefix from custom CSS variables when generating utility classes. UI files use `text-color-error`, `bg-color-error-bg`, etc., which do not exist. Update them to `text-error`, `bg-error-bg`, etc.
- [x] [Review][Patch] Weak route matching for redirect interceptor [web/src/api/client.ts:13] — uses `startsWith("/login")` which could falsely match `/login-history`. Use strict equality `=== "/login"`.
- [x] [Review][Patch] Uncleaned setInterval memory leak [web/src/components/layout/DegradedBanner.tsx:44] — polling interval does not clean itself up if component unmounts prematurely, causing state updates on an unmounted component.
- [x] [Review][Defer] TopBar Cache Status Edge Case [web/src/components/layout/TopBar.tsx] — deferred, pre-existing; UI silently fails to warn if cacheRefreshedAt is missing (e.g. fresh startup).

## Dev Notes

### Critical: Router Migration (Architecture F2)

The current `web/src/router.tsx` uses `createBrowserRouter` which is the **Data Router** API — this does NOT comply with the architecture decision F2 which explicitly requires `BrowserRouter + Routes` (Declarative mode). The dev agent MUST migrate this.

### Backend Auth Router (NEW FILE REQUIRED)

Register auth router in `app.py` with prefix `/api/v1/auth` BEFORE the SPA catch-all:
```python
from forward_bot.api.routers.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1/auth")
```

### Brand Token CSS (UX-DR1)

The existing `web/src/index.css` is the default shadcn/Vite starter CSS — it needs to be replaced/augmented with the project's brand system. Create `web/src/styles/tokens.css` with the exact DESIGN.md palette mapping:

```css
/* Light theme */
[data-theme="light"] {
  --color-bg: #FAFAF9;
  --color-bg-muted: #F4F4F2;
  --color-surface: #FFFFFF;
  --color-border: #E7E5E0;
  --color-text-primary: #1C1917;
  --color-text-secondary: #78716C;
  --color-active: #16A34A;         /* Forwarding Green */
  --color-active-hover: #15803D;
  --color-success: #16A34A;
  --color-success-bg: #F0FDF4;
  --color-success-border: #BBF7D0;
  --color-success-foreground: #15803D;
  --color-warning: #D97706;
  --color-warning-bg: #FEF3C7;
  --color-warning-border: #FDE68A;
  --color-warning-foreground: #92400E;
  --color-error: #DC2626;
  --color-error-bg: #FEF2F2;
  --color-error-border: #FECACA;
  --color-degraded-bg: #FEF2F2;
  --color-degraded-border: #FCA5A5;
  --color-degraded-foreground: #991B1B;
  --color-muted: #A8A29E;
  --color-muted-bg: #F4F4F2;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;

  /* Wire shadcn tokens */
  --background: var(--color-bg);
  --foreground: var(--color-text-primary);
  --muted: var(--color-bg-muted);
  --muted-foreground: var(--color-text-secondary);
  --border: var(--color-border);
  --primary: var(--color-active);
  --primary-foreground: #FFFFFF;
  --card: var(--color-surface);
  --card-foreground: var(--color-text-primary);
}

/* Dark theme */
[data-theme="dark"] {
  --color-bg: #14130F;
  --color-bg-muted: #1C1B16;
  --color-surface: #1C1B16;
  --color-border: #2A2823;
  --color-text-primary: #E7E5E0;
  --color-text-secondary: #A8A29E;
  --color-active: #22C55E;         /* Forwarding Green dark */
  --color-active-hover: #16A34A;
  --color-success: #22C55E;
  --color-success-bg: rgba(34,197,94,0.12);
  --color-success-border: rgba(34,197,94,0.35);
  --color-success-foreground: #4ADE80;
  --color-warning: #F59E0B;
  --color-warning-bg: rgba(245,158,11,0.14);
  --color-warning-border: rgba(245,158,11,0.45);
  --color-warning-foreground: #FCD34D;
  --color-error: #EF4444;
  --color-error-bg: rgba(239,68,68,0.12);
  --color-error-border: rgba(239,68,68,0.35);
  --color-degraded-bg: rgba(239,68,68,0.14);
  --color-degraded-border: rgba(239,68,68,0.45);
  --color-degraded-foreground: #FCA5A5;
  --color-muted: #78716C;
  --color-muted-bg: #1C1B16;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;

  /* Wire shadcn tokens */
  --background: var(--color-bg);
  --foreground: var(--color-text-primary);
  --muted: var(--color-bg-muted);
  --muted-foreground: var(--color-text-secondary);
  --border: var(--color-border);
  --primary: var(--color-active);
  --primary-foreground: #14130F;
  --card: var(--color-surface);
  --card-foreground: var(--color-text-primary);
}
```

### Telegram Status Dot & Health Paths

In `TopBar`, fetch root `GET /health/telegram` using:
```ts
// web/src/api/health.ts
import axios from 'axios';
export const fetchTelegramStatus = () => axios.get('/health/telegram');
export const fetchCacheStatus = () => axios.get('/health/ready');
```

### Directory Structure to Create

**Backend (NEW files/modified files only):**
```
forward-bot/src/forward_bot/api/routers/
├── auth.py                              ← NEW
├── media.py                             ← NEW
└── health.py                            ← MODIFY
```

**Frontend (NEW directories and files):**
```
web/src/
├── api/
│   ├── client.ts                        ← NEW (Axios instance)
│   ├── auth.ts                          ← NEW
│   ├── health.ts                        ← NEW
│   └── media.ts                         ← NEW
├── contexts/
│   └── ThemeContext.tsx                 ← NEW
├── hooks/
│   ├── useAuth.ts                       ← NEW
│   └── useKeyboardShortcuts.ts          ← NEW
├── components/
│   ├── auth/
│   │   └── RequireAuth.tsx              ← NEW
│   └── layout/
│       ├── Layout.tsx                   ← MODIFY (replace stub with AppLayout)
│       ├── Sidebar.tsx                  ← NEW
│       ├── TopBar.tsx                   ← NEW
│       └── DegradedBanner.tsx           ← NEW
├── lib/
│   ├── queryClient.ts                   ← NEW
│   └── queryKeys.ts                     ← NEW
├── routes/
│   └── index.tsx                        ← NEW
├── styles/
│   └── tokens.css                       ← NEW
├── pages/
│   └── Login.tsx                        ← NEW
- Health / Telegram status: `staleTime: 0`, `refetchInterval: 10_000`
- Rules list: `staleTime: 30_000`
- Sources + Folders: `staleTime: 60_000`
- Stats summary: `staleTime: 0`, `refetchInterval: 30_000`
- Logs recent: `staleTime: 0`, `refetchInterval: 5_000`
- Auth me: `staleTime: 5 * 60 * 1000` (5 min — session doesn't expire that quickly)

### Installed Packages (already in package.json)

```json
"@tanstack/react-query": "^5.100.14",
"class-variance-authority": "^0.7.1",
"clsx": "^2.1.1",
"lucide-react": "^1.17.0",
"react": "^19.2.6",
"react-dom": "^19.2.6",
"react-router-dom": "^7.16.0",
"tailwind-merge": "^3.6.0",
"tailwindcss": "^4.3.0"
```

Axios is NOT installed yet — **install it**: `npm install axios` inside `web/`.

shadcn/ui components (Button, Sheet, Toast) need to be added via `npx shadcn@latest add button sheet sonner` (or the project's preferred shadcn CLI approach). Check if there's a `components.json` in `web/` first.

### Previous Story Intelligence (from Epic 5 completion)

From story 5-3 (the last completed story):
- Backend auth pattern: `get_current_operator` dependency in `api/dependencies/auth.py` handles both X-API-Key and session cookie — use it as-is for `GET /api/v1/auth/me`
- All API routers are registered in `app.py`'s `create_app()` function before the SPA routes
- The `itsdangerous.TimestampSigner` is already used in auth.py for cookie verification — import and reuse the same pattern for the auth router

### Git Intelligence (Recent Commits)

```
424cecd  epic 5 completed
abe83bc  story 5-3 done
b534983  story 5-2 completed
cdb0812  story 5-1 completed
```

All Epic 5 observability work is complete. The SSE broadcaster, ring buffer, and all log/stats/admin endpoints are fully wired. The web scaffold is a fresh shadcn Vite template with stub pages — this story builds the real foundation.

## Project Structure Notes

- Backend project root: `forward-bot/` (contains `pyproject.toml`, `src/`)
- Frontend project root: `web/` (contains `package.json`, `src/`)
- Implementations: `forward-bot/src/forward_bot/`
- Tests: `forward-bot/tests/`
- Planning artifacts: `_bmad-output/planning-artifacts/`
- Story files: `_bmad-output/implementation-artifacts/`

### References

- [Epic 6 Acceptance Criteria in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L1014-L1048)
- [Architecture Decision F2 (React Router), F1 (stale times), F3 (global state)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L161-L165)
- [UX Design Requirements UX-DR1, UX-DR2, UX-DR9, UX-DR19, UX-DR22](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L187-L229)
- [Authentication (FR-43, Architecture S1, S2)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L103-L147)
- [Existing auth dependency](file:///c:/Users/hitesh.paliwal/Documents/GitHub\Forward-Bot/forward-bot/src/forward_bot/api/dependencies/auth.py)
- [Current app.py (StaticFiles + SPA catch-all)](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/src/forward_bot/app.py#L357-L391)

## Dev Agent Record

### Agent Model Used

Antigravity (Claude Sonnet 4.6 Thinking)

### Debug Log References

- None

### Completion Notes List

- Story created with comprehensive context for Story 6.1
- Key deviation identified: existing `router.tsx` uses `createBrowserRouter` (Data Router API) — must be migrated to `BrowserRouter + Routes` (Declarative mode) per architecture F2
- Auth router (`/api/v1/auth/*`) does not exist in the backend — must be created as a new file
- Web scaffold is a fresh Vite/shadcn template with stub pages — brand token CSS system must be implemented from scratch
- Axios not installed in `web/package.json` — must be installed as part of this story
- StaticFiles + SPA catch-all already working in `app.py` — do not re-register
- Successfully created new backend auth routes (`/me`, `/login`, `/logout`) and media route (`/replacement-images`), and registered them in `app.py`.
- Updated backend `/health/ready` check to expose cache version and last refresh time, and updated health tests to verify the new payload shape.
- Added comprehensive unit tests for auth and media routers, all passing successfully.
- Upgraded the frontend `package.json` with `axios` and `sonner`.
- Configured Vite with `@tailwindcss/vite` plugin and index.css with tokens.css to load the design system warm-stone color variables.
- Migrated legacy react-router from `createBrowserRouter` to declarative `BrowserRouter + Routes` and defined them in `routes/index.tsx`, deleting `router.tsx`.
- Designed global Axios client with 401 response interceptors to catch expired sessions.
- Created `ThemeContext` providing Light/Dark/System theme options, persisting selection inside `localStorage` under `fb-theme`, and avoiding unstyled flashing using inline head script logic.
- Built a persistent layout `Layout.tsx` containing the Sidebar navigation drawer (active item high-contrast highlights, mobile drawers, theme selectors), a TopBar (breadcrumb routes, status state dots, stale cache warnings), and a `DegradedBanner` alert (ARIA alert, reconnect API dispatch).
- Implemented vim keyboard shortcuts (`g+d`, `g+f`, `g+s`, `g+l`, `g+,`) chord inputs.
- Created `Login.tsx` rendering credentials inputs and catching expired redirect toasts.
- Verified compilation build processes completed with zero TypeScript errors.
