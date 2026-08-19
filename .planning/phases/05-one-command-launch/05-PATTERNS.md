# Phase 5: One-Command Launch - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 12
**Analogs found:** 0 exact / 12 (no Docker/scripts/E2E infra exists yet in this repo — this phase introduces all of it fresh)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `Dockerfile` | config | batch (build) | none in-repo | no-analog (use RESEARCH.md Pattern 1/2) |
| `.dockerignore` | config | — | `.gitignore` (root) | role-match (same exclusion-list mechanics) |
| `docker-compose.yml` | config | — | none in-repo | no-analog (use RESEARCH.md Pattern 4) |
| `.env.example` | config | — | `.env` (undocumented, gitignored) + PLAN.md §5 | role-match |
| `scripts/start_mac.sh` | utility | event-driven (CLI orchestration) | none in-repo | no-analog (use RESEARCH.md Pattern 3 + health-check loop) |
| `scripts/stop_mac.sh` | utility | event-driven | none in-repo | no-analog (use RESEARCH.md idempotent-stop example) |
| `scripts/start_windows.ps1` | utility | event-driven | `scripts/start_mac.sh` (same-phase sibling, ported) | role-match (1:1 logic port, unverified per D-04) |
| `scripts/stop_windows.ps1` | utility | event-driven | `scripts/stop_mac.sh` (same-phase sibling, ported) | role-match |
| `test/docker-compose.test.yml` | config | — | `docker-compose.yml` (same-phase sibling) | role-match (adds scratch bind mount + playwright service) |
| `test/playwright.config.ts` | config | — | `frontend/vitest.config.ts` (only existing test-framework config in repo) | partial-match (different framework, same "test config" role) |
| `test/e2e/*.spec.ts` (fresh-start, watchlist, trade, ai-chat, sse-reconnect) | test | request-response / event-driven (browser E2E) | `frontend/**/*.test.tsx` (vitest component tests, if present) — otherwise none | partial-match |
| `test/package.json` | config | — | `frontend/package.json` | role-match (same package.json shape, npm scripts pattern) |

## Pattern Assignments

### `Dockerfile`

**Analog:** None in-repo. Use RESEARCH.md's verified official `uv`-Docker pattern and this repo's own env-var seams.

**Critical integration values (from in-repo verified source, not to be re-derived):**
```python
# backend/app/db/database.py:45-49 — db_path() override seam
override = os.getenv("FINALLY_DB_PATH")
if override:
    return Path(override)
repo_root = Path(__file__).resolve().parents[3]
return repo_root / "db" / "finally.db"
```
```python
# backend/app/main.py:67-70 — static dir override seam
_repo_root = Path(__file__).resolve().parents[2]
_static_dir = Path(os.getenv("FINALLY_STATIC_DIR", str(_repo_root / "backend" / "static")))
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
```
```python
# backend/app/main.py:53-56 — health endpoint, poll target for start script
@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Required runtime ENV in the Dockerfile's final stage** (do not rely on parents[N] math — see RESEARCH.md Pitfall 2):
```dockerfile
ENV FINALLY_DB_PATH=/app/db/finally.db
ENV FINALLY_STATIC_DIR=/app/static
```

**uv two-phase sync pattern** (RESEARCH.md Pattern 1, cited from astral-sh/uv-docker-example):
```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY backend/ /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
```

**Frontend build stage** — must produce `frontend/out/` (this repo uses `output: 'export'`, verified in `frontend/next.config.ts`), never `.next/standalone`:
```dockerfile
FROM node:22-slim AS frontend-builder
WORKDIR /app
COPY frontend/ .
RUN npm ci && npm run build
```

**pyproject.toml dependency source** (confirms base image / Python version to match):
```toml
# backend/pyproject.toml:1-16
[project]
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0", "uvicorn[standard]>=0.32.0", "httpx>=0.27.0",
    "sse-starlette>=2.1.0", "litellm>=1.97.0", "pydantic>=2.13.4",
    "python-dotenv>=1.2.2",
]
```
No new dependencies for this phase — the Dockerfile installs exactly what's already pinned in `backend/uv.lock`.

Include a non-root `USER` directive in the final stage (Security Domain, Elevation of Privilege mitigation) — no in-repo precedent, follow the official uv-docker-example convention.

---

### `.dockerignore`

**Analog:** `.gitignore` (root) — same exclusion-list mechanics, largely overlapping entries.

**Pattern to copy (exclusion categories already established in `.gitignore`):**
```
# From .gitignore — reuse these categories directly
__pycache__/
.pytest_cache/
.ruff_cache/
.env
.venv
db/finally.db
```
**Additions specific to Docker build context** (not in `.gitignore` because they're not git-ignored, just build-context-excluded per RESEARCH.md Pitfall 4 and Open Question 1):
```
.git
node_modules
frontend/out
backend/static
backend/tests
frontend/**/*.test.ts
test/
```

---

### `docker-compose.yml`

**Analog:** None in-repo. RESEARCH.md Pattern 4 (cited: docker/docs compose-file reference).

**Bind-mount pattern (D-01 — bind mount, NOT named volume):**
```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./db:/app/db
```

---

### `.env.example`

**Analog:** PLAN.md §5 (the canonical variable list) — no existing `.env.example` file, `.env` itself is gitignored and not readable as a template source.

**Variables to document (from PLAN.md §5, verbatim contract):**
```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

---

### `scripts/start_mac.sh` (utility, event-driven CLI orchestration)

**Analog:** None in-repo (first shell script of its kind in this project). Use RESEARCH.md's Pattern 3 (idempotent lifecycle) + health-check-wait Code Example directly — both are cited as the recommended, tested shape.

**Idempotent container-state pattern:**
```bash
CONTAINER_NAME="finally"
STATE=$(docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "absent")

case "$STATE" in
  running)
    echo "finally is already running at http://localhost:8000"
    ;;
  exited|created)
    docker start "$CONTAINER_NAME"
    ;;
  absent)
    docker run -d --name "$CONTAINER_NAME" \
      -v "$(pwd)/db:/app/db" \
      -p 8000:8000 \
      --env-file .env \
      finally
    ;;
esac
```

**Health-check-wait-then-open-browser pattern (D-05):**
```bash
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    open http://localhost:8000
    exit 0
  fi
  sleep 1
done
echo "finally did not become healthy within 30s" >&2
exit 1
```

**Style constraint (CLAUDE.md, MANDATORY):** No emojis in echo/print statements; `set -euo pipefail` at top (per RESEARCH.md's idempotent-stop example).

---

### `scripts/stop_mac.sh` (utility, event-driven)

**Analog:** None in-repo. RESEARCH.md's idempotent stop-script Code Example (self-contained, directly usable):
```bash
#!/usr/bin/env bash
set -euo pipefail
CONTAINER_NAME="finally"
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  docker stop "$CONTAINER_NAME"
  echo "Stopped $CONTAINER_NAME. Data in db/ is preserved."
else
  echo "$CONTAINER_NAME is not running."
fi
```
**Anti-pattern to avoid (RESEARCH.md):** Do NOT `docker rm` — use `docker stop`/`docker start` as the idempotent pair so container identity is reused across cycles.

---

### `scripts/start_windows.ps1` / `scripts/stop_windows.ps1`

**Analog:** Sibling mac scripts in this same phase — port the same `docker inspect`/`docker start`/`docker run` logic 1:1 into PowerShell `if`/`try`/`catch`, per D-04 and RESEARCH.md Open Question 2. Use `start http://localhost:8000` (not `open`) per D-05.

**Required header comment (D-04, mandatory):**
```powershell
# NOTE: This script mirrors scripts/start_mac.sh's docker CLI logic 1:1.
# It has NOT been executed or verified on Windows in this development session
# (development machine is macOS). Verify docker inspect/start/run behavior
# before relying on it for a live demo.
```

---

### `test/docker-compose.test.yml`

**Analog:** `docker-compose.yml` (same-phase sibling) — same bind-mount/env-file/ports shape, plus a scratch DB path (D-03 isolation) and a `playwright` service.

**Pattern (RESEARCH.md Pattern 5, synthesized — no first-party Playwright+compose example exists per Assumption A2):**
```yaml
services:
  app:
    build:
      context: ..
    environment:
      - LLM_MOCK=true
    volumes:
      - ./scratch-db:/app/db
    ports:
      - "8000:8000"

  playwright:
    image: mcr.microsoft.com/playwright:v1.62.1-noble
    depends_on:
      - app
    working_dir: /work
    volumes:
      - .:/work
    environment:
      - BASE_URL=http://app:8000
    command: sh -c "npm ci && npx playwright test"
```
**Critical pitfall (RESEARCH.md Pitfall 5):** `baseURL`/`BASE_URL` must use the compose service name `app`, never `localhost` — the Playwright container is a separate network namespace.

---

### `test/package.json`

**Analog:** `frontend/package.json` — same shape (scripts block, devDependencies), different toolchain (Playwright instead of Vitest).

**Imports/scripts pattern to mirror** (from `frontend/package.json:5-11`):
```json
{
  "scripts": {
    "test": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.62.1"
  }
}
```

---

### `test/playwright.config.ts`

**Analog:** `frontend/vitest.config.ts` (only existing test-config file in repo) — partial match, different framework, but establishes this repo's convention of a root-level `defineConfig`-style TS config file colocated with its test suite.

**Key value to set:** `baseURL` must resolve to the compose service DNS name (`http://app:8000`) when run inside `docker-compose.test.yml`, or `http://localhost:8000` for local/manual runs — parameterize via `process.env.BASE_URL` per the compose service pattern above.

---

### `test/e2e/*.spec.ts` (fresh-start, watchlist, trade, ai-chat, sse-reconnect)

**Analog:** No existing Playwright/E2E spec in-repo. Frontend component tests (`frontend/**/*.test.tsx`, vitest) establish this project's TypeScript-first test-writing convention but are a different test tier (unit/component vs E2E browser).

**Scenario list is fixed by PLAN.md §12 and REQUIREMENTS.md TEST-04** (not discretionary):
- fresh start: default watchlist appears, $10k balance shown, prices streaming
- add/remove ticker from watchlist
- buy shares: cash decreases, position appears
- sell shares: cash increases, position updates/disappears
- AI chat (mocked, `LLM_MOCK=true`): send message, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

**Env precondition for deterministic AI chat test:** `LLM_MOCK=true` must be set on the `app` service in `test/docker-compose.test.yml` (see above) — this is what makes the `ai-chat.spec.ts` scenario deterministic without a real OpenRouter call.

---

## Shared Patterns

### Environment-variable-driven configuration, not directory-nesting assumptions
**Source:** `backend/app/db/database.py:45-49`, `backend/app/main.py:67-70`
**Apply to:** `Dockerfile`, `docker-compose.yml`, `test/docker-compose.test.yml`
Both `db_path()` and the static-dir resolution already have an explicit env-var override (`FINALLY_DB_PATH`, `FINALLY_STATIC_DIR`) specifically so container layouts don't need to mirror the source checkout's directory nesting. Every compose/Dockerfile file in this phase must set these explicitly rather than relying on the `Path(__file__).resolve().parents[N]` fallback math.

### Idempotent CLI orchestration (docker inspect + case statement)
**Source:** RESEARCH.md Pattern 3 / Code Examples (synthesized, not in-repo, but adopted as this phase's canonical shape)
**Apply to:** `scripts/start_mac.sh`, `scripts/stop_mac.sh`, and their Windows ports
Use `docker inspect -f '{{.State.Status}}'` to branch on running/exited/absent; never `docker rm` in the stop path.

### No-emoji, plain output style
**Source:** `.claude/CLAUDE.md` project conventions (MANDATORY)
**Apply to:** All shell/PowerShell script echo/print/Write-Host statements

### `uv sync --extra dev` for any test-execution step
**Source:** MEMORY.md gotcha + `.claude/CLAUDE.md` — "plain `uv run pytest` silently uses Anaconda's pytest"
**Apply to:** Any CI-style step in scripts or compose files that runs backend tests inside the image (none currently planned, but note if added)

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `Dockerfile` | config | batch | First Docker packaging in this repo; no prior multi-stage build exists — RESEARCH.md's cited official uv-docker-example pattern is the source of truth instead |
| `docker-compose.yml` / `test/docker-compose.test.yml` | config | — | No prior compose file in repo |
| `scripts/*.sh` / `scripts/*.ps1` | utility | event-driven | No prior orchestration scripts in `scripts/` (directory doesn't exist yet) |
| `test/e2e/*.spec.ts` | test | request-response/event-driven | No prior browser-level E2E suite; only unit/component tests (vitest, pytest) exist |

## Metadata

**Analog search scope:** repo root, `backend/app/`, `backend/pyproject.toml`, `frontend/` (package.json, next.config.ts, vitest.config.ts), `.gitignore`, `.planning/phases/04-ai-copilot/`
**Files scanned:** `backend/app/main.py`, `backend/app/db/database.py`, `backend/pyproject.toml`, `frontend/package.json`, `.gitignore`, plus directory listings of `frontend/`, `.planning/phases/04-ai-copilot/`
**Pattern extraction date:** 2026-08-18
