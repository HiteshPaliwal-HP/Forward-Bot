# Story 1.3: FastAPI Application Shell, Health Endpoints & Docker Build

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Channel Operator**,
I want **the service to expose health endpoints and be deployable as a Docker container**,
so that **I can verify the service is running and deploy it to my VPS with `docker compose up`**.

## Acceptance Criteria

1. **Liveness Health Endpoint:**
   - **Given** the FastAPI application is running.
   - **When** a `GET /health` request is received.
   - **Then** HTTP 200 is returned with JSON body `{"status": "ok"}`.

2. **Readiness Health Endpoint:**
   - **Given** the MongoDB connection is active and reachable.
   - **When** a `GET /health/ready` request is received.
   - **Then** HTTP 200 is returned with JSON body `{"mongodb": "up"}`.
   - **Given** the MongoDB connection is down or unreachable.
   - **When** a `GET /health/ready` request is received.
   - **Then** HTTP 503 is returned with JSON body `{"mongodb": "down"}` (exceptions must be caught and logged).

3. **Telegram Health Endpoint (Stub):**
   - **Given** the application is started but Telegram connection is not yet implemented.
   - **When** a `GET /health/telegram` request is received.
   - **Then** HTTP 200 is returned with JSON body `{"telegram": "disconnected", "last_event": null}`.

4. **Lifespan Manager Integration:**
   - **Given** the FastAPI application starts up.
   - **When** the lifespan context is initialized.
   - **Then** it must connect to MongoDB using the `mongo_client` singleton: `await mongo_client.connect(settings)`.
   - **And** it must start three asyncio background task stubs (`cache_refresher`, `mapping_sweeper`, `telegram_worker`) that log their start/stop but immediately return/sleep in MVP Story 1.3.
   - **And** it must perform a startup health check verifying MongoDB reachability (e.g. by pinging the admin database). If MongoDB is unreachable within 30 seconds, it logs a CRITICAL event and exits the process with a non-zero code.
   - **Given** the FastAPI application shuts down.
   - **Then** the lifespan context manager must cancel the stub tasks and close the `mongo_client` connection cleanly.

5. **Docker Build Configuration (Multi-Stage):**
   - **Given** a Docker multi-stage build is run via `docker build -t forward-bot:latest .` in the project root.
   - **When** Stage 1 runs:
     - Uses `node:22-slim`.
     - Installs frontend dependencies inside `/web` with `npm ci`.
     - Compiles the React SPA static assets into `/web/dist` with `npm run build` (with strict TypeScript verification).
   - **When** Stage 2 runs:
     - Uses `python:3.12-slim`.
     - Installs `uv` and runs `uv sync --frozen --no-dev` to install Python dependencies.
     - Copies backend code (`src/`) and compiled frontend static assets from Stage 1 (`/web/dist`) to `/app/static`.
     - Configures `CMD` to start the FastAPI server via uvicorn (serving frontend assets from `/static` when `UI_ENABLED=true`).
   - **Then** the container builds successfully and runs with a healthy status.

6. **Docker Compose & Makefile:**
   - **Given** `docker-compose.yml` is defined in the project root.
   - **When** `docker compose up` is executed.
   - **Then** it starts the `app` container and a `mongodb` container.
   - **And** it configures volume mounts for:
     - `TELEGRAM_SESSION_PATH` (e.g., `./data/telegram.session`)
     - MongoDB data directory
     - `MEDIA_REPLACEMENT_BASE_DIR` (e.g., `./data/replacement-images`)
   - **And** a `Makefile` is created at the project root with the following targets:
     - `build` - builds the docker image.
     - `run` - starts the docker compose services.
     - `auth` - runs the auth CLI tool inside the app container.

7. **API Documentation:**
   - **Given** the application is running.
   - **When** the operator navigates to `/docs` or `/redoc`.
   - **Then** the Swagger UI/ReDoc pages are fully accessible (unprotected for this story).

## Dev Notes

- **Lifespan Task Stubs:** In `src/forward_bot/app.py` (or a dedicated tasks module), define stubs for:
  ```python
  async def run_cache_refresher():
      # Stub for Story 1.3
      logger.info("cache_refresher_started", status="stub")
      try:
          await asyncio.sleep(float('inf'))
      except asyncio.CancelledError:
          logger.info("cache_refresher_stopped")
  ```
- ** serving static files:** If `settings.ui_enabled` is True, mount the `/app/static` directory using FastAPI `StaticFiles` at `/`. A catch-all route must serve `index.html` for SPA client routing, registered *after* all API routers.
- **Port Binding:** Ensure the server binds to `settings.bind_host` and `settings.port`.
- **Database Connection Check:** Perform a simple command execution (e.g., `db.command("ping")`) to verify connection readiness.
- **Testing:** Add test cases in `tests/api/test_health.py` asserting liveness, readiness, and telegram endpoint statuses. Use an HTTPX async test client.

### Project Structure Notes

- **New Entry Point:** Create `src/forward_bot/main.py` which will instantiate the FastAPI app and expose `app` directly for Uvicorn imports:
  ```python
  from forward_bot.app import create_app
  from forward_bot.config import Settings
  
  settings = Settings()
  app = create_app(settings)
  ```
- **Update App:** Modify `src/forward_bot/app.py` to accept the lifespan context manager.
- **Tests Location:** Tests go into `tests/api/test_health.py` to mirror the API router directory.

### References

- [Epics and Stories](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/epics.md#Story-1.3)
- [Architecture Document](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/architecture.md)
- [DESIGN.md](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/_bmad-output/planning-artifacts/ux-designs/ux-Forward%20Bot-2026-05-31/DESIGN.md)

## Tasks / Subtasks

- [ ] Implement FastAPI Application Shell & Health Routers (AC: 1, 2, 3)
  - [ ] Add `/health` returning `{"status": "ok"}`
  - [ ] Add `/health/ready` verifying MongoDB connectivity
  - [ ] Add `/health/telegram` stub returning disconnected
- [ ] Implement Lifespan and Startup Database Verifier (AC: 4)
  - [ ] Initialize MongoDB client connection in lifespan
  - [ ] Setup background task stubs (`cache_refresher`, `mapping_sweeper`, `telegram_worker`)
  - [ ] Add 30-second timeout checks on MongoDB connectivity at startup
- [ ] Setup Web Static Files Serving (AC: 5)
  - [ ] Mount `StaticFiles` for `/static` when `ui_enabled=True`
  - [ ] Add catch-all SPA fallback route to serve `index.html`
- [ ] Configure Docker & Compose Deployment (AC: 5, 6)
  - [ ] Create multi-stage `Dockerfile` (Node compiler stage + Python runtime stage)
  - [ ] Create `docker-compose.yml` with MongoDB and persistent volume mounts
  - [ ] Create `Makefile` with `build`, `run`, and `auth` targets
- [ ] Add API Verification and Integration Tests (AC: 7)
  - [ ] Write tests under `tests/api/test_health.py` for health endpoints using `httpx.AsyncClient`

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Debug Log References

### Completion Notes List

### File List

- [NEW] [main.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/main.py)
- [MODIFY] [app.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/src/forward_bot/app.py)
- [NEW] [test_health.py](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/forward-bot/tests/api/test_health.py)
- [NEW] [Dockerfile](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/Dockerfile)
- [NEW] [docker-compose.yml](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/docker-compose.yml)
- [NEW] [Makefile](file:///c:/Users/Hitesh%20-%20HP/OneDrive/Documents/Github/Forward-Bot/Makefile)
