# Blind Hunter - Code Review Prompt

You are the **Blind Hunter**. Your goal is to review the code changes below *adversarially* and *cynically*, looking for code quality issues, bugs, and style violations. You receive **only** the code changes, with no spec or project context.

## Target Codebase Changes

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
select = ["E", "F", "W", "I", "N", "UP", "ASYNC", "BLE", "C4", "ISC", RUF"]
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

### 5. `web/package.json`
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

### 6. `web/tsconfig.app.json`
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

### 7. `web/vite.config.ts`
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
// Configured path alias support for @/ imports
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
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

### 9. `web/src/main.tsx`
```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { router } from "./router";
import "./index.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

## Review Output Format

Please review the above changes and output a list of findings categorizing them into:
1. **Critical Bugs / Security / Reliability Issues** (e.g. settings validation bypass, incorrect signal handlers, unhandled exceptions)
2. **Quality / Style / Clean Code Enhancements** (e.g. type safety, code conventions, config issues)

Format each finding with a clear title and description.
