# syntax=docker/dockerfile:1

# --- Stage 1: frontend static export ---------------------------------------
# node:22-slim, not node:20-slim: Node 20 reached EOL 2026-04-30, node:22 is
# the current Maintenance LTS. This is a build-only stage, discarded after
# `npm run build`, so it never ships in the runtime image.
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# --webpack, not the Next 16 default (Turbopack): every prior production
# build in this project has been verified on webpack; Turbopack has failed
# under this environment (see 01-03-SUMMARY.md, 01-04-SUMMARY.md).
RUN npx next build --webpack

# --- Stage 2: backend dependency + project sync -----------------------------
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS backend-builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependency layer first, keyed only on the lockfile, so it stays cached
# across source-only changes. --no-install-project defers installing the
# project itself (backend/app) to the second sync below.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY backend/ /app/
# No --extra dev / --extra demo: pytest, ruff, and rich have no place in a
# runtime image. hatchling reads backend/README.md during this sync, so it
# must stay in the build context (not excluded by .dockerignore).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# --- Stage 3: runtime ---------------------------------------------------
# Same image family and tag as backend-builder (not python:3.12-slim, which
# floats independently) so the venv copied in below is guaranteed to match
# the Debian release it was built against -- avoids a glibc mismatch if the
# two tags' underlying releases ever diverge.
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS runtime

RUN groupadd --system finally && useradd --system --gid finally finally

WORKDIR /app
COPY --from=backend-builder --chown=finally:finally /app /app
COPY --from=frontend-builder --chown=finally:finally /app/frontend/out /app/static
RUN mkdir -p /app/db && chown finally:finally /app/db

ENV PATH="/app/.venv/bin:$PATH" \
    FINALLY_DB_PATH=/app/db/finally.db \
    FINALLY_STATIC_DIR=/app/static \
    PYTHONUNBUFFERED=1

EXPOSE 8000
USER finally
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
