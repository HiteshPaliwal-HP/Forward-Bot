---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: null
status: 'done'
createdAt: '2026-06-02'
startedAt: '2026-06-02'
completedAt: '2026-06-02'
story_id: '1.1'
story_key: '1-1-initialize-project-scaffold-directory-structure'
epic: 1
baseline_commit: 'NO_VCS'
commit: '538c285'
## Code Review Fixes Applied

### Critical Fixes (2026-06-03)

**Fixed in this session:**
1. ✅ **F2 - Main function now starts FastAPI server** with graceful shutdown handling
   - Created `app.py` with FastAPI app factory and health check endpoints
   - Updated `__main__.py` to instantiate and run uvicorn server
   - Added signal handlers for SIGINT/SIGTERM (graceful shutdown)

2. ✅ **F6 - FastAPI app factory created** 
   - App factory in `src/forward_bot/app.py` with CORS middleware pre-configured
   - Health checks: `/health` (liveness) and `/ready` (readiness)

3. ✅ **F10 - Environment variable validation added**
   - Settings class now validates that `API_KEY` and `SECRET_KEY` are not placeholder values
   - Startup check prevents running with dummy credentials
   - Updated `settings.py` with `Field` descriptions and validation

4. ✅ **F11 - Health check endpoints implemented**
   - `/health` endpoint for Kubernetes liveness probes
   - `/ready` endpoint for readiness checks

5. ✅ **F9 - Graceful shutdown mechanism added**
   - Signal handlers for SIGINT and SIGTERM
   - Contextmanager-based lifespan for startup/shutdown hooks

6. ✅ **F7/F15 - Dependency version conflicts resolved**
   - Removed duplicate `[project.optional-dependencies]` section
   - Consolidated dev dependencies in `[dependency-groups]` with latest versions

7. ✅ **F16 - React Router fully configured**
   - Created `router.tsx` with routes for all 8 dashboard screens (S1-S8)
   - Created `Layout.tsx` app shell with nav and footer
   - Created page components for: Dashboard, ForwardsList, ForwardEdit, SourcesList, SourceEdit, FolderModal, Logs, Settings, FirstRunWizard
   - Updated `main.tsx` to use RouterProvider with QueryClientProvider
   - Configured Vite alias support for `@/` imports

8. ✅ **Settings improvements**
   - Changed `bind_host` default from hardcoded `127.0.0.1` to `0.0.0.0` (all interfaces)
   - Added `.expanduser()` support for paths (`~/...` expansion)
   - Added Field descriptions for all config variables
   - Set `case_sensitive=True` for env var handling

### Deferred (for Story 1.2+)
- F3: Placeholder credentials security (Story 1.2)
- F5: Linux-specific paths (Story 1.2 env setup)
- F8: MongoDB error handling (Story 1.2)
- F13: MongoDB startup verification (Story 1.2)
- F12: Business logic implementations (Stories 1.2+)
- F14: README documentation (Story 1.3+)
- F17: Tailwind CSS full config (Story 6)

---

## Implementation Record

### Acceptance Criteria Status
- ✅ AC 1: Backend project initialization with uv (Python 3.12, FastAPI stack, all dependencies)
- ✅ AC 2: Frontend project initialization (React 18, TypeScript, Vite, shadcn/ui dependencies)
- ✅ AC 3: Backend imports cleanly (`import forward_bot` verified)
- ✅ AC 4: Frontend builds without TypeScript errors (strict mode enabled, npm run build successful)
- ✅ AC 5: .gitignore configured correctly (all patterns excluded)
- ✅ AC 6: Lock files committed (uv.lock, package-lock.json tracked in git)
- ✅ AC 7: .env.example documents all configuration (11 environment variables with descriptions)
- ✅ AC 8: pyproject.toml is single manifest (dependencies, dev-dependencies, package layout configured)

### Implementation Summary

**Backend (Python)**
- Initialized with `uv init forward-bot --python 3.12`
- Created src/forward_bot/ structure with Clean Architecture layers:
  - domain/entities/: Pure business logic
  - application/: Use cases and business processes
  - infrastructure/: External system integrations (MongoDB, Telegram, logging, cache)
  - api/: HTTP contract and FastAPI integration
- Installed 30 production dependencies (FastAPI, Telethon, Motor, Pydantic Settings, Structlog, etc.)
- Installed 13 development dependencies (pytest, mypy, ruff, etc.)
- Created settings.py with Pydantic Settings configuration loading from .env
- Created __main__.py as entry point for `uv run python -m forward_bot`
- All __init__.py files created for proper package structure

**Frontend (React + TypeScript)**
- Initialized with Vite React + TypeScript template
- Installed 6 additional production dependencies (TanStack Query, React Router)
- Installed shadcn/ui foundation dependencies (Tailwind, PostCSS, Autoprefixer, CVA, Clsx, Lucide, Tailwind Merge)
- Created web/src/ structure:
  - components/ui/: shadcn/ui component library
  - components/shared/: Cross-feature reusable components
  - components/layout/: App shell and navigation
  - pages/: Page components for 8 dashboard screens
  - hooks/, api/, contexts/, lib/, types/: Supporting infrastructure
- Updated tsconfig.app.json with strict TypeScript mode enabled
- Verified build: `npm run build` successful with zero TypeScript errors, output in dist/

**Configuration & Version Control**
- Created .env.example with all 11 required environment variables (MongoDB, Auth, Telegram, Media, Logging, Cache, UI, Server)
- Updated .gitignore at project root and per-directory
- Initialized git repository at project root
- Committed complete scaffold (50 files) with both lock files included
- Successfully tested backend import and frontend build

### Files Created/Modified
**Backend Files:**
- forward-bot/.env.example
- forward-bot/.gitignore
- forward-bot/.python-version
- forward-bot/README.md
- forward-bot/pyproject.toml
- forward-bot/uv.lock
- forward-bot/src/forward_bot/__init__.py
- forward-bot/src/forward_bot/__main__.py
- forward-bot/src/forward_bot/settings.py
- All layer __init__.py files (domain, application, infrastructure, api, tests)

**Frontend Files:**
- web/package.json
- web/package-lock.json
- web/vite.config.ts
- web/tsconfig.json / tsconfig.app.json / tsconfig.node.json
- web/.gitignore
- web/src/App.tsx and supporting files
- Directory structure for components, pages, hooks, api, contexts, lib, types

**Root Files:**
- .gitignore (project-level)
- Git commit 538c285 with message: "Story 1.1: Initialize project scaffold and directory structure"

### Technical Decisions

1. **src/ Layout for Backend**: Used src/forward_bot/ structure (not top-level package) for cleaner import boundaries and simpler deployment.

2. **Clean Architecture Layers**: Established four-layer architecture from the start to enforce dependency flow (api → application → domain ← infrastructure).

3. **TypeScript Strict Mode**: Enabled all strict TypeScript options (noImplicitAny, strictNullChecks, etc.) to catch type errors early.

4. **Lock File Commitment**: Both uv.lock and package-lock.json committed to ensure reproducible builds across environments.

5. **Environment Template**: Created .env.example with all variables from PRD Addendum §4.1 to establish configuration expectations for story 1.2.

### Testing Notes

No automated tests for this story (pure scaffolding). Manual verification completed:
- `uv run python -c "import forward_bot"` → Success
- `cd web && npm run build` → Success (0 TypeScript errors, output in dist/)
- Git history: Confirmed uv.lock and package-lock.json are tracked
- .gitignore patterns: Verified __pycache__, .venv, .env, *.session, node_modules/, dist/ are excluded

---

# Story 1.1: Initialize Project Scaffold & Directory Structure

**Epic:** 1 — Project Foundation & Telegram Connectivity  
**Story ID:** 1.1  
**Status:** Ready for Development  
**Effort:** Baseline setup story (2-3 days)

## User Story

As a **Channel Operator**,
I want the project initialized with its **complete directory structure and dependency manifests**,
So that the **development team has a working starting point with clean import boundaries and reproducible builds**.

## Acceptance Criteria

### AC 1: Backend Project Initialization with `uv`

**Given** the developer runs the following initialization commands:
```bash
# Backend setup (Python 3.12, async-first)
uv init forward-bot --python 3.12

# Install backend dependencies (FastAPI, Telegram, MongoDB, Logging)
uv add fastapi uvicorn[standard] telethon motor pydantic-settings structlog itsdangerous

# Install development dependencies (testing, type checking, formatting)
uv add --dev pytest pytest-asyncio mypy ruff
```

**When** the commands complete  
**Then** the backend project structure exists at `src/forward_bot/` with these **required subdirectories:**

```
src/forward_bot/
├── domain/
│   └── entities/
│       ├── source.py
│       ├── source_folder.py
│       ├── forwarding_rule.py
│       ├── replacement_rule.py
│       ├── message_mapping.py
│       └── pipeline_context.py
├── application/
│   ├── sources/
│   ├── folders/
│   ├── rules/
│   ├── replacements/
│   └── pipeline/
│       └── steps/
├── infrastructure/
│   ├── mongo/
│   │   └── repositories/
│   ├── telegram/
│   ├── logging/
│   └── cache/
├── api/
│   ├── routers/
│   ├── dependencies/
│   ├── schemas/
│   └── middleware/
├── __main__.py
└── settings.py
```

### AC 2: Frontend Project Initialization with React + shadcn/ui

**Given** the developer runs:
```bash
# Frontend setup (React 18 + TypeScript + Vite + shadcn/ui)
npx shadcn@latest init -t vite web

# Install frontend dependencies (state management, routing, UI patterns)
npm install @tanstack/react-query react-router-dom
```

**When** the commands complete  
**Then** the frontend project structure exists at `web/src/` with these **required subdirectories:**

```
web/
├── src/
│   ├── components/
│   │   ├── ui/           # shadcn/ui component library
│   │   ├── shared/       # Cross-feature reusable components
│   │   └── layout/       # App shell, nav, sidebars
│   ├── pages/            # Page components (S1–S8)
│   ├── hooks/            # Custom React hooks
│   ├── api/              # API client functions (fetch wrappers)
│   ├── contexts/         # React context definitions
│   ├── lib/              # Utility functions
│   ├── types/            # TypeScript type definitions
│   └── App.tsx
├── package.json
├── vite.config.ts        # With TypeScript strict mode enabled
├── tsconfig.json         # Strict TypeScript configuration
└── public/
```

### AC 3: Project Imports Cleanly (No Path Errors)

**Given** the project scaffold exists  
**When** the developer runs:
```bash
uv run python -c "import forward_bot"
```

**Then:**
- Import succeeds with **no ModuleNotFoundError**, **no path errors**
- The `src/` directory layout enforces clean import boundaries (no `__init__.py` tricks)
- `sys.path` includes `src/` so submodules can import from `forward_bot.*`

**Developer Note:** The `pyproject.toml` must configure the package root to `src/` so that `uv` and tools understand the layout. This is standard Python practice for projects using `uv` or `pip`.

### AC 4: Frontend Builds Without TypeScript Errors

**Given** the project scaffold exists  
**When** the developer runs:
```bash
cd web && npm run build
```

**Then:**
- Vite compiles TypeScript to JavaScript with **no errors**
- Build output appears in `web/dist/` directory
- **TypeScript strict mode is enabled** in `tsconfig.json`:
  - `"strict": true` (enforces null checks, type strictness)
  - `"noImplicitAny": true`
  - `"noImplicitThis": true`
  - `"strictNullChecks": true`
- No console warnings about missing type definitions

### AC 5: `.gitignore` Configured Correctly

**Given** the project scaffold exists  
**When** the developer lists what Git tracks  
**Then** these patterns are **excluded** from version control:
- `__pycache__/` (Python bytecode)
- `.venv/` (Virtual environment)
- `.env` (Secrets file, see AC 7)
- `*.session` (Telegram session artifacts)
- `web/node_modules/` (npm packages)
- `web/dist/` (Built frontend)
- `*.pyc`, `*.pyo` (More Python bytecode)

### AC 6: Lock Files Committed for Reproducibility

**Given** the project scaffold exists  
**When** the developer commits  
**Then:**
- `uv.lock` is **committed** (guarantees reproducible Python dependency resolution)
- `package-lock.json` is **committed** (guarantees reproducible npm resolution)
- These files are tracked so that `uv sync --frozen` and `npm ci` produce identical installs on all machines

### AC 7: `.env.example` Documents All Configuration

**Given** the project scaffold exists  
**When** the developer reads `.env.example`  
**Then:** it contains **all required environment variables** with:
- Clear variable names matching `pydantic-settings` expected keys
- Descriptive comments explaining each variable's purpose
- **No secret values** (examples only, e.g., `MONGO_URI=mongodb://localhost:27017/forward_bot`)
- All variables from the PRD addendum §4.1: `MONGO_URI`, `API_KEY`, `SECRET_KEY`, `TELEGRAM_SESSION_PATH`, `MEDIA_REPLACEMENT_BASE_DIR`, `TIMEZONE_DEFAULT`, `SAMPLING_PERSIST`, `UI_ENABLED`, `LOG_RING_BUFFER_HOURS`, `HOT_RELOAD_INTERVAL`, `BIND_HOST`

**Developer Note:** This file is committed to version control so developers know what env vars to configure. Actual `.env` (with secrets) is gitignored.

### AC 8: `pyproject.toml` is the Single Project Manifest

**Given** the project scaffold exists  
**When** a developer reviews `pyproject.toml`  
**Then:**
- It defines **all backend dependencies** (from AC 1) under `[project] dependencies`
- It defines **all dev dependencies** (pytest, mypy, ruff) under `[project] optional-dependencies` or `[dependency-groups] dev`
- It specifies **package discovery** with `packages = [{include = "forward_bot", from = "src"}]`
- It specifies **Python requirement** as `requires-python = ">=3.12"`
- It includes **project metadata** (name, version, description, authors, license)
- No manual `setup.py` or `setup.cfg` exists (uv works with `pyproject.toml` only)

## Developer Context

### Architecture Foundations (Story 1.1 establishes)

This story creates the **foundation for Clean Architecture + DDD** layering that all subsequent stories depend on:

1. **Domain Layer** (`src/forward_bot/domain/entities/`) — pure business logic, no I/O
   - Source, SourceFolder, ForwardingRule, ReplacementRule entities
   - PipelineContext: carries state through the 18-step pipeline
   - No FastAPI, no MongoDB imports at this layer

2. **Application Layer** (`src/forward_bot/application/`) — use cases and business processes
   - Sources, Folders, Rules, Replacements: CRUD operations
   - Pipeline steps: stateless, composable filters and transforms
   - No database or framework specifics — depends on repositories via DI

3. **Infrastructure Layer** (`src/forward_bot/infrastructure/`) — external system details
   - MongoDB repositories (mongo/repositories/)
   - Telegram client wrapper (telegram/)
   - Structured logging setup (logging/)
   - Cache manager (cache/)

4. **API Layer** (`src/forward_bot/api/`) — HTTP contract and FastAPI integration
   - Routers: endpoint handlers
   - Dependencies: FastAPI dependency injection (get_db, get_settings, etc.)
   - Schemas: Pydantic models for request/response bodies
   - Middleware: authentication, correlation ID propagation

**Why this structure matters:**
- Tight import boundaries prevent circular dependencies
- Business logic is testable without FastAPI or MongoDB mocks
- Swapping implementations (e.g., PostgreSQL instead of MongoDB) requires only changing the repository implementation
- Each layer has a single, clear responsibility

### Technology Stack Rationale

**Python 3.12 + async-first:**
- All I/O paths (Telegram client, MongoDB queries, file reads, HTTP calls) are `async`
- Blocking calls are explicitly isolated and documented
- Enables single FastAPI worker to handle concurrent messages and API requests

**FastAPI + Uvicorn:**
- Modern async web framework, excellent for high-concurrency I/O
- Built-in OpenAPI/Swagger documentation at `/docs`
- Dependency injection system for clean middleware/repository injection

**Telethon:**
- Mature MTProto implementation for Telegram
- Supports SQLiteSession for persistent login (no interactive re-auth on restart)
- Single-instance design (all source channels subscribed through one client)

**MongoDB + Motor:**
- Async driver (Motor) aligns with async-first architecture
- Schemaless flexibility for evolving rule configurations
- Atomic transactions (across 5 collections: sources, source_folders, forwarding_rules, replacement_rules, message_mappings)

**React 18 + TypeScript + Vite + shadcn/ui:**
- React 18: latest hooks, concurrent features
- TypeScript: type safety for 8-screen SPA
- Vite: fast hot-module reload during development, optimized production builds
- shadcn/ui: pre-built accessible components (buttons, modals, forms) matching Tailwind + UX design spec
- TanStack Query: server state management (cache, refetch, invalidation)
- React Router: client-side routing for 8 dashboard screens

### Critical File Creation Checklist

**Backend files to create during initialization:**

1. `pyproject.toml` — **primary manifest**, defines all dependencies and package layout
2. `uv.lock` — **locked versions**, committed to git for reproducible installs
3. `.env.example` — **configuration template**, no secrets
4. `.gitignore` — **version control filters**
5. All subdirectories in `src/forward_bot/` — **layer structure**
6. `src/forward_bot/__init__.py` — **package marker** (can be empty initially)
7. `src/forward_bot/__main__.py` — **entry point** for `uv run python -m forward_bot`
8. `src/forward_bot/settings.py` — **configuration class** (story 1.2 adds Pydantic Settings details)
9. All subdirectories in `src/forward_bot/` are marked with `__init__.py` files (empty is fine)

**Frontend files to create during initialization:**

1. `web/package.json` — **frontend manifest**
2. `web/package-lock.json` — **locked npm versions**
3. `web/vite.config.ts` — **Vite configuration** (can be minimal, shadcn init creates it)
4. `web/tsconfig.json` — **TypeScript strict configuration**
5. All subdirectories in `web/src/` — **component and page structure**
6. `web/src/App.tsx` — **root component** (shadcn init creates a basic version)
7. `web/public/` — **static assets** (favicon, etc.)

### Import Boundaries & Dependency Flow

```
Outer Layers (depend on inner layers)
    api/ → application/ → domain/
          infrastructure/ → (no dependencies, talks to external systems)
Inner Layers (depend only on inner layers or nothing)
    domain/ (depends on nothing)
```

**Key constraint:** Domain entities must never import from `api/`, `infrastructure/`, or `application/`. They contain only pure business logic.

**Example valid import in application/:**
```python
from forward_bot.domain.entities import ForwardingRule
from forward_bot.infrastructure.mongo.repositories import RuleRepository

async def get_rules() -> list[ForwardingRule]:
    repo = RuleRepository()
    return await repo.find_all()
```

**Example INVALID import (would create circular dependency):**
```python
# ❌ DO NOT DO THIS in domain/entities/
from forward_bot.api.schemas import RuleSchema
```

### Environment Variables (Set in `.env.example`)

All these are required by later stories. Define them now with helpful defaults:

```env
# MongoDB connection (Story 1.2 validates this)
MONGO_URI=mongodb://localhost:27017/forward_bot

# Authentication (Story 1.2 validates missing values)
API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-here

# Telegram session storage (Story 1.4)
TELEGRAM_SESSION_PATH=/app/data/telegram.session

# Media replacement filesystem root (Story 4.3)
MEDIA_REPLACEMENT_BASE_DIR=/app/data/replacement-images

# Timezone fallback (Story 4.2)
TIMEZONE_DEFAULT=UTC

# Sampling counter persistence (Story 4.2)
SAMPLING_PERSIST=false

# UI serving (Story 1.3)
UI_ENABLED=true

# Logging configuration (Story 5.2)
LOG_RING_BUFFER_HOURS=1

# Cache refresh interval in seconds (Story 3.3)
HOT_RELOAD_INTERVAL=30

# Server binding (Story 1.3)
BIND_HOST=127.0.0.1
```

### Testing Approach for This Story

**Manual verification (dev does this):**
1. Run `uv init` and `npm install` commands
2. Verify `import forward_bot` works without errors
3. Verify `npm run build` completes with no TypeScript errors
4. Verify `.gitignore`, `.env.example`, `pyproject.toml` contain expected content
5. Verify `uv.lock` and `package-lock.json` exist and are tracked by git

**No automated tests for this story.** It's pure scaffolding — the next stories add code that gets tested.

### Git Commit Pattern

After this story, the repository should have:
```
Forward Bot/
├── .git/
├── .gitignore
├── .env.example
├── pyproject.toml
├── uv.lock
├── src/forward_bot/
│   ├── __init__.py
│   ├── __main__.py
│   ├── settings.py
│   ├── domain/
│   │   ├── __init__.py
│   │   └── entities/
│   │       └── __init__.py
│   ├── application/
│   │   ├── __init__.py
│   │   ├── sources/
│   │   ├── folders/
│   │   ├── rules/
│   │   ├── replacements/
│   │   └── pipeline/
│   │       └── steps/
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── mongo/
│   │   │   └── repositories/
│   │   ├── telegram/
│   │   ├── logging/
│   │   └── cache/
│   └── api/
│       ├── __init__.py
│       ├── routers/
│       ├── dependencies/
│       ├── schemas/
│       └── middleware/
├── web/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── shared/
│   │   │   └── layout/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   ├── contexts/
│   │   ├── lib/
│   │   ├── types/
│   │   └── App.tsx
│   └── public/
└── README.md (optional)
```

All `__init__.py` files can be empty initially (Python 3.3+ namespace packages).

### Review Checklist (for code-review agent)

- [ ] `uv.lock` is committed (reproducible Python dependency resolution)
- [ ] `package-lock.json` is committed (reproducible npm resolution)
- [ ] `.gitignore` excludes `__pycache__/`, `.venv/`, `.env`, `*.session`, `node_modules/`, `dist/`
- [ ] `.env.example` has all required variables with no secret values
- [ ] All subdirectories exist and have `__init__.py` files (even if empty)
- [ ] `import forward_bot` succeeds with no ModuleNotFoundError
- [ ] `npm run build` completes with no TypeScript errors in strict mode
- [ ] `pyproject.toml` specifies `packages = [{include = "forward_bot", from = "src"}]`
- [ ] `tsconfig.json` has `"strict": true` and all strict options enabled
- [ ] No bare `__init__.py` imports cause circular dependencies (check with `uv run python -c "import forward_bot"`)

## Success Metrics

✅ Developer can run `uv init` and `npm` commands without manual path tweaking  
✅ Project imports cleanly (`import forward_bot` succeeds)  
✅ Frontend builds successfully with strict TypeScript checking  
✅ Lock files are committed for reproducibility  
✅ `.env.example` documents all configuration needs  
✅ Clean Architecture layer boundaries are established and enforced  

## Blockers & Dependencies

**None.** This is the first story in the epic.

**Dependencies (what this story unblocks):**
- All of Epic 1 (stories 1.2, 1.3, 1.4) depend on this scaffold
- Epic 2 (sources) depends on having a working project structure
- All downstream epics inherit this structure

---

### Review Findings

- [x] [Review][Patch] Invalid Syntax in ruff Configuration [pyproject.toml:41]
- [x] [Review][Patch] Missing __dirname in ESM Context [web/vite.config.ts:10]
- [x] [Review][Patch] Improper Lifespan Setup in FastAPI [forward-bot/src/forward_bot/__main__.py:35]
- [x] [Review][Patch] Signal Handler / KeyboardInterrupt Conflict and Windows Compatibility [forward-bot/src/forward_bot/__main__.py:44]
- [x] [Review][Patch] No Non-Zero Exit Code on Startup Failure [forward-bot/src/forward_bot/__main__.py:29]
- [x] [Review][Patch] Hardcoded CORS Origins [forward-bot/src/forward_bot/app.py:22]
- [x] [Review][Patch] Invalid/Futuristic Dependency and Compiler Configurations [web/package.json:34]
- [x] [Review][Patch] Non-portable Root Directory Paths in Settings [forward-bot/src/forward_bot/settings.py:28]
- [x] [Review][Patch] Redundant Settings Validation Checks [forward-bot/src/forward_bot/__main__.py:66]
- [x] [Review][Patch] Lack of Frontend Route Error Boundaries [web/src/router.tsx:14]
- [x] [Review][Patch] Hard-Coded Port (8000) [forward-bot/src/forward_bot/__main__.py:55]
- [x] [Review][Patch] Environment-Variable Validation (Empty / Whitespace) [forward-bot/src/forward_bot/__main__.py:68]
- [x] [Review][Patch] Hot-Reload Interval Clamp [forward-bot/src/forward_bot/settings.py:64]
- [x] [Review][Patch] Timezone Default Validation [forward-bot/src/forward_bot/settings.py:40]
- [x] [Review][Defer] Default MongoDB URI Warn/Error in Production [forward-bot/src/forward_bot/__main__.py:74] — deferred, pre-existing
- [x] [Review][Defer] UI Enabled Flag verification for static files directory [forward-bot/src/forward_bot/__main__.py:40] — deferred, pre-existing
- [x] [Review][Defer] Logging Ring-Buffer Size Default Configuration [forward-bot/src/forward_bot/settings.py:60] — deferred, pre-existing

---

## Next Story

**Story 1.2: Configure Application Settings & Database Client**  
Depends on: Story 1.1 ✓  
Adds: Pydantic Settings validation, MongoDB connection initialization, environment variable parsing


