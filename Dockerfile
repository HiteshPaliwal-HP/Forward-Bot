# Stage 1: Build the React Frontend SPA
FROM node:22-slim AS frontend-builder
WORKDIR /web
# Copy package files and install dependencies
COPY web/package*.json ./
RUN npm ci
# Copy source files and build
COPY web/ ./
RUN npm run build

# Stage 2: Create Python runtime and install backend dependencies
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip for simplicity and speed
RUN pip install --no-cache-dir uv

# Copy backend dependency declarations
COPY forward-bot/pyproject.toml forward-bot/uv.lock ./

# Synchronize python dependencies (frozen and no-dev as per AC 5)
RUN uv sync --frozen --no-dev

# Copy compiled frontend assets from Stage 1 to /app/static
COPY --from=frontend-builder /web/dist /app/static

# Copy backend source code to /app/src (which is packages root in pyproject.toml)
COPY forward-bot/src /app/src

# Expose server port
EXPOSE 8000

# Start server via Uvicorn (serving frontend assets from /static when UI_ENABLED=true)
CMD ["sh", "-c", "uv run uvicorn forward_bot.main:app --host ${BIND_HOST:-0.0.0.0} --port ${PORT:-8000}"]
