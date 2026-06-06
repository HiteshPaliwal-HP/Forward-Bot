# Acceptance Auditor - Code Review Prompt

You are the **Acceptance Auditor**. Your goal is to review the code changes below against the official Acceptance Criteria (ACs) defined in the User Story.

## User Story & Acceptance Criteria

### User Story
As a **Channel Operator**,
I want the project initialized with its **complete directory structure and dependency manifests**,
So that the **development team has a working starting point with clean import boundaries and reproducible builds**.

### Acceptance Criteria

- **AC 1: Backend Project Initialization with `uv`**
  - Requires backend structure at `src/forward_bot/` with required subdirectories: `domain/entities/` (containing entities listed in AC), `application/` (containing folders listed), `infrastructure/` (containing mongo/repositories/, telegram/, logging/, cache/), `api/` (containing routers/, dependencies/, schemas/, middleware/), `__main__.py`, and `settings.py`.
- **AC 2: Frontend Project Initialization with React + shadcn/ui**
  - Requires frontend at `web/src/` with subdirectories: `components/ui/`, `components/shared/`, `components/layout/`, `pages/`, `hooks/`, `api/`, `contexts/`, `lib/`, `types/`, and `App.tsx`.
- **AC 3: Project Imports Cleanly (No Path Errors)**
  - Backend must import cleanly with no `ModuleNotFoundError` or path errors.
  - Package root configured to `src/` inside `pyproject.toml`.
- **AC 4: Frontend Builds Without TypeScript Errors**
  - Vite compiles TypeScript with no errors. Strict mode is enabled in `tsconfig.json`.
- **AC 5: `.gitignore` Configured Correctly**
  - Excludes `__pycache__/`, `.venv/`, `.env`, `*.session`, `web/node_modules/`, and `web/dist/`.
- **AC 6: Lock Files Committed for Reproducibility**
  - `uv.lock` and `package-lock.json` must be committed and tracked by git.
- **AC 7: `.env.example` Documents All Configuration**
  - Documents all variables: `MONGO_URI`, `API_KEY`, `SECRET_KEY`, `TELEGRAM_SESSION_PATH`, `MEDIA_REPLACEMENT_BASE_DIR`, `TIMEZONE_DEFAULT`, `SAMPLING_PERSIST`, `UI_ENABLED`, `LOG_RING_BUFFER_HOURS`, `HOT_RELOAD_INTERVAL`, `BIND_HOST`.
  - No secret values in the template.
- **AC 8: `pyproject.toml` is the Single Project Manifest**
  - Defines all backend dependencies under `[project] dependencies` and optional/dev dependencies under dev dependency groups.
  - Specifies package discovery from `src`.

---

## Codebase State to Audit

### 1. `forward-bot/pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "forward-bot"
version = "0.1.0"
description = "Self-hosted Telegram forwarding worker with React operator dashboard"
readme = "README.md"
requires-python = ">=3.12"
authors = [
    {name = "Hitesh Paliwal", email = "hpaliwal@sgintl.com"},
]
license = {text = "MIT"}

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "telethon>=1.29.0",
    "motor>=3.3.0",
    "pydantic-settings>=2.1.0",
    "structlog>=23.2.0",
    "itsdangerous>=2.1.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/forward_bot"]

[tool.mypy]
python_version = "3.12"
check_untyped_defs = true
disallow_incomplete_defs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "ASYNC", "BLE", "C4", "ISC", "RUF"]
ignore = ["E501"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.4.0",
    "mypy>=2.1.0",
    "ruff>=0.15.15",
]
```

### 2. `forward-bot/src/forward_bot/settings.py`
```python
"""Configuration settings for Forward Bot using Pydantic Settings."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    # Core settings with validation
    api_key: str = Field(
        default="your-api-key-here",
        description="API key for authentication (required for production)",
    )
    secret_key: str = Field(
        default="your-secret-key-here",
        description="Secret key for signing (required for production)",
    )

    # Database
    mongo_uri: str = Field(
        default="mongodb://localhost:27017/forward_bot",
        description="MongoDB connection URI",
    )

    # Telegram
    telegram_session_path: str = Field(
        default="/app/data/telegram.session",
        description="Path to store Telegram session data",
    )

    # Media handling
    media_replacement_base_dir: str = Field(
        default="/app/data/replacement-images",
        description="Base directory for replacement media files",
    )

    # Timezone and sampling
    timezone_default: str = Field(
        default="UTC",
        description="Default timezone for timestamp operations",
    )
    sampling_persist: bool = Field(
        default=False,
        description="Whether to persist sampling counters across restarts",
    )

    # UI and server
    ui_enabled: bool = Field(
        default=True,
        description="Whether to serve the React dashboard UI",
    )
    bind_host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)",
    )

    # Logging and caching
    log_ring_buffer_hours: int = Field(
        default=1,
        description="Ring buffer size in hours for structured logging",
    )
    hot_reload_interval: int = Field(
        default=30,
        description="Cache refresh interval in seconds",
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_telegram_session_path(self) -> Path:
        """Get the telegram session path as a Path object."""
        return Path(self.telegram_session_path).expanduser()

    def get_media_replacement_dir(self) -> Path:
        """Get the media replacement directory as a Path object."""
        return Path(self.media_replacement_base_dir).expanduser()
```

### 3. `forward-bot/src/forward_bot/__main__.py`
```python
"""Entry point for the Forward Bot application."""
import asyncio
import signal
from contextlib import asynccontextmanager

import uvicorn

from forward_bot.app import create_app
from forward_bot.settings import Settings


@asynccontextmanager
async def lifespan(app):
    """Handle application startup and shutdown."""
    # Startup
    print("Forward Bot starting up...")
    yield
    # Shutdown
    print("Forward Bot shutting down gracefully...")


async def main() -> None:
    """Main entry point for the application."""
    settings = Settings()

    # Validate settings on startup
    try:
        _validate_settings(settings)
    except ValueError as e:
        print(f"Configuration error: {e}")
        return

    # Create FastAPI app
    app = create_app(settings)
    app.router.lifespan_context = lifespan

    # Print startup info
    print(f"Forward Bot starting on {settings.bind_host}:8000")
    print(f"MongoDB: {settings.mongo_uri}")
    print(f"UI Enabled: {settings.ui_enabled}")
    print(f"Telegram Session: {settings.telegram_session_path}")

    # Configure graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start uvicorn server
    config = uvicorn.Config(
        app,
        host=settings.bind_host,
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        print("Server stopped")


def _validate_settings(settings: Settings) -> None:
    """Validate critical settings on startup."""
    if settings.api_key == "your-api-key-here":
        raise ValueError("API_KEY must be set to a real value (not placeholder)")

    if settings.secret_key == "your-secret-key-here":
        raise ValueError("SECRET_KEY must be set to a real value (not placeholder)")

    if not settings.mongo_uri or settings.mongo_uri == "mongodb://localhost:27017/forward_bot":
        print("⚠️  Using default MongoDB URI — ensure MongoDB is running on localhost:27017")

    if not settings.api_key:
        raise ValueError("API_KEY environment variable is required")

    if not settings.secret_key:
        raise ValueError("SECRET_KEY environment variable is required")


if __name__ == "__main__":
    asyncio.run(main())
```

### 4. `forward-bot/src/forward_bot/app.py`
```python
"""FastAPI application factory and configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forward_bot.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Forward Bot API",
        version="0.1.0",
        description="Self-hosted Telegram forwarding worker with operator dashboard",
    )

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Liveness probe for Kubernetes/Docker health checks."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def readiness_check() -> dict[str, str]:
        """Readiness probe — checks if app is ready to serve requests."""
        return {"status": "ready"}

    return app
```

### 5. `forward-bot/.env.example`
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
LOG_RING_BUFFER_HOUES=1

# Cache refresh interval in seconds (Story 3.3)
HOT_RELOAD_INTERVAL=30

# Server binding (Story 1.3)
BIND_HOST=127.0.0.1
```

### 6. `web/package.json`
```json
{
  "name": "web",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.100.14",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^1.17.0",
    "react": "^19.2.6",
    "react-dom": "^19.2.6",
    "react-router-dom": "^7.16.0",
    "tailwind-merge": "^3.6.0"
  },
  "devDependencies": {
    "@eslint/js": "^10.0.1",
    "@types/node": "^24.12.3",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.1",
    "autoprefixer": "^10.5.0",
    "eslint": "^10.3.0",
    "eslint-plugin-react-hooks": "^7.1.1",
    "eslint-plugin-react-refresh": "^0.5.2",
    "globals": "^17.6.0",
    "postcss": "^8.5.15",
    "tailwindcss": "^4.3.0",
    "typescript": "~6.0.2",
    "typescript-eslint": "^8.59.2",
    "vite": "^8.0.12"
  }
}
```

### 7. `web/tsconfig.app.json`
```json
{
  "compilerOptions": {
    "ignoreDeprecations": "6.0",
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "es2023",
    "lib": ["ES2023", "DOM"],
    "module": "esnext",
    "types": ["vite/client"],
    "skipLibCheck": true,

    /* Strict Type Checking */
    "strict": true,
    "noImplicitAny": true,
    "noImplicitThis": true,
    "strictNullChecks": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Path mapping */
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    },

    /* Linting */
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

### 8. `web/src/router.tsx`
```typescript
import { createBrowserRouter } from "react-router-dom";

import Layout from "@/components/layout/Layout";
import Dashboard from "@/pages/Dashboard";
import ForwardsList from "@/pages/ForwardsList";
import ForwardEdit from "@/pages/ForwardEdit";
import SourcesList from "@/pages/SourcesList";
import SourceEdit from "@/pages/SourceEdit";
import FolderModal from "@/pages/FolderModal";
import Logs from "@/pages/Logs";
import Settings from "@/pages/Settings";
import FirstRunWizard from "@/pages/FirstRunWizard";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: "forwards",
        element: <ForwardsList />,
      },
      {
        path: "forwards/:id",
        element: <ForwardEdit />,
      },
      {
        path: "sources",
        element: <SourcesList />,
      },
      {
        path: "sources/:id",
        element: <SourceEdit />,
      },
      {
        path: "folders/:id",
        element: <FolderModal />,
      },
      {
        path: "logs",
        element: <Logs />,
      },
      {
        path: "settings",
        element: <Settings />,
      },
      {
        path: "wizard",
        element: <FirstRunWizard />,
      },
    ],
  },
]);
```

## Audit Output Format

Please audit the above files and verify if they fully satisfy the acceptance criteria. Output findings as a list. For each finding, list:
- Which AC or constraint it relates to
- Analysis / Evidence from the code
- Pass/Fail/Warning status
