# Stage 1: build the Next.js static export.
# Manifests are copied before the source so npm ci is reused when only source changes.
FROM node:24-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Python runtime. Serves the API and the built frontend on 8000.
FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Dependencies resolve from the lockfile alone, so this layer survives a source
# change. README.md is required: pyproject declares readme = "README.md".
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --locked --no-install-project

# The application itself, then the frontend build output into the directory
# app/main.py serves from (STATIC_DIR = app/../static).
COPY backend/ ./
RUN uv sync --locked
COPY --from=frontend /frontend/out ./static

# WORKDIR is load-bearing: DB_PATH defaults to the relative path db/finally.db,
# which must resolve to /app/db, the finally-data volume mount point.
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
