# Phase 5: One-Command Launch - Research

**Researched:** 2026-08-18
**Domain:** Docker multi-stage packaging (Node 20/22 + Python/uv), docker-compose, idempotent shell scripting, Playwright E2E in Docker, FastAPI static-file serving
**Confidence:** MEDIUM — core patterns are well-documented and cross-checked against this repo's actual code, but two areas (Windows PowerShell scripts, exact Playwright-in-compose wiring) have no first-party reference example and are synthesized from community patterns.

## Summary

Phase 5 wraps the already-complete application (Phases 1-4) in a single multi-stage Docker image, a docker-compose convenience file, idempotent start/stop scripts, and a separate Playwright E2E harness. Nothing here touches application logic — `backend/app/main.py` already does lazy DB init, already serves static files conditionally from `FINALLY_STATIC_DIR` (default `backend/static`), and `backend/app/db/database.py`'s `db_path()` already reads `FINALLY_DB_PATH` (default `db/finally.db` at repo root). Both of these env-var seams exist specifically so the container/bind-mount layer can override them explicitly instead of relying on `Path(__file__).resolve().parents[N]` math holding true inside a different directory layout — **this is the single most important integration detail for the Dockerfile.**

The standard `uv` Docker pattern is a two-stage build: a builder stage using the official `ghcr.io/astral-sh/uv` image to run `uv sync --locked` against a bind-mounted lockfile (for layer caching), then a slim `python:3.12-slim` runtime stage that copies only the resulting `/app` (virtualenv + code) — no `uv` binary ships in the final image. Pair this with a Node build stage that runs `npm ci && npm run build` against `frontend/`, producing `frontend/out/` (static export — **not** `.next/standalone`, which is a different, non-export Next.js output mode), and copy `out/` into wherever the backend stage's `FINALLY_STATIC_DIR` points.

**One finding overrides the phase description's literal wording:** Node.js 20 reached end-of-life on 2026-04-30 — it is no longer receiving security patches as of this research date (2026-08-18). `node:22-slim` (Maintenance LTS until 2027-04-30) is the correct current choice for the build stage; CONTEXT.md lists the exact base image as "Claude's Discretion," so this is a discretionary substitution, not a violation of a locked decision, but the planner should record it explicitly.

**Primary recommendation:** Two-stage Dockerfile (`node:22-slim` build stage → `python:3.12-slim` runtime stage using the official `uv` builder pattern), explicit `ENV FINALLY_DB_PATH=/app/db/finally.db` and `ENV FINALLY_STATIC_DIR=/app/static` in the runtime stage (don't rely on directory-nesting math), a `.dockerignore` that excludes `.env`/`node_modules`/`.venv`/test artifacts, idempotent `docker ps --filter name=` checks in the start/stop scripts, and a `test/docker-compose.test.yml` running `mcr.microsoft.com/playwright:v1.62.1-noble` as a sibling service pointed at the app container via its compose DNS name.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Static frontend asset serving | API/Backend (FastAPI `StaticFiles`) | CDN/Static (not used — single container) | PLAN.md §11 mandates single-origin, single-port serving; no separate static host |
| Container build/packaging | Build/Ops (Dockerfile) | — | Multi-stage build is purely a packaging concern, no runtime code changes |
| Data persistence across restarts | Database/Storage (bind-mounted SQLite file) | Build/Ops (compose volume declaration) | `db_path()` already isolates this to one function; Docker only needs to point the bind mount at the same path |
| Launch orchestration | Build/Ops (start/stop scripts, docker-compose) | Browser/Client (auto-open browser, D-05) | Scripts are pure orchestration; the one client-facing side effect is opening a tab |
| E2E test execution | Build/Ops (`docker-compose.test.yml`) | Browser/Client (Playwright drives a real browser) | Isolated from the dev bind-mount per D-03; own throwaway container/network |

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The Docker container bind-mounts the host's `db/` directory (`-v $(pwd)/db:/app/db`), not an opaque named Docker volume. This is the same `db/finally.db` file already used by local `uv run uvicorn` development — visible in the checkout, trivial to inspect or delete for a fresh demo. Deviates from PLAN.md §11's literal `finally-data:/app/db` named-volume example; docker-compose.yml must use the same bind-mount, not a named volume, for consistency. — **Reversibility:** reversible.
- **D-02:** No `--reset` flag on the start/stop scripts. Resetting to a clean $10k start is a documented manual step (delete `db/finally.db`, then start again — the app's existing lazy-init reseeds automatically). — **Reversibility:** reversible.
- **D-03:** The Playwright E2E suite's database isolation (its own scratch DB via `docker-compose.test.yml`, per PLAN.md §12) is unaffected by D-01/D-02 — it already runs against a separate container/volume by design, never touching the bind-mounted `db/finally.db` a developer or demo user is using locally.
- **D-04:** `scripts/start_windows.ps1` / `scripts/stop_windows.ps1` are a best-effort PowerShell mirror of the mac scripts' logic (build-if-needed, run with the same volume/port/env-file args, idempotent stop). They cannot be executed or verified on this machine (macOS) — document this limitation directly in the scripts' header comments and in the phase's verification notes. — **Reversibility:** reversible.
- **D-05:** `scripts/start_mac.sh` automatically opens the default browser to `http://localhost:8000` after the container is confirmed up (e.g. `open http://localhost:8000` on mac). The Windows equivalent uses `start http://localhost:8000`. — **Reversibility:** reversible.

### Claude's Discretion

- Exact Dockerfile base images (e.g. `node:20-slim` for the build stage, `python:3.12-slim` for the runtime stage) and multi-stage layer ordering/caching strategy. **Research finding: substitute `node:22-slim` — Node 20 is EOL as of 2026-04-30 (see Common Pitfalls).**
- Exact Playwright test file organization within `test/` (one file per scenario vs. grouped) and `docker-compose.test.yml` service naming.
- Whether `--build` is the only way to force a rebuild, or the script also detects source changes — PLAN.md already specifies "builds if not already built, or if `--build` passed," so this is largely fixed; minor implementation detail only.
- `.env.example` exact contents/comments — PLAN.md §5 already specifies the required variables; formatting/comment style is open.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. A `--reset` flag was considered and explicitly declined in favor of documentation-only (D-02); this is a decision, not a deferred idea.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-02 | Single multi-stage Dockerfile builds the Next.js static export and the FastAPI backend into one image serving port 8000 | Standard Stack (uv + Node multi-stage pattern), Code Examples, Common Pitfalls (static-dir path resolution) |
| INFRA-03 | `docker-compose.yml` and `scripts/start_mac.sh`/`stop_mac.sh` (and Windows equivalents) let the user launch/stop the app with one command | Architecture Patterns (idempotent script pattern), Code Examples |
| INFRA-04 | SQLite file persists across container restarts via a volume mount at `db/finally.db` | Runtime State Inventory, Code Examples (bind mount + `FINALLY_DB_PATH`) |
| TEST-04 | Playwright E2E suite (`test/`, `LLM_MOCK=true`) covers: fresh start, add/remove ticker, buy/sell trade flow, AI chat trade execution, SSE reconnection | Standard Stack (Playwright), Validation Architecture, Common Pitfalls (compose networking) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work incrementally, small validated steps; do not overengineer or program defensively.
- Identify root cause before fixing; prove with evidence.
- Use `uv` as Python package manager: `uv run`, `uv add`/`uv sync` — never bare `python3`/`pip install`. Docker build stage must use `uv sync`, not `pip install -r requirements.txt`.
- Use latest library/API versions as of now (2026-08-18) — informed the Node 20→22 substitution below.
- No emojis in code, scripts, or log output (applies to `start_mac.sh`/`stop_mac.sh` echo/print statements).
- Ruff-enforced style (`E, F, I, N, W`, line length 100, ignore E501) applies to any new Python — not expected in this phase (no new backend modules), but any conftest/fixture additions for Playwright-adjacent Python code (there should be none — Playwright test stack is JS/TS per existing repo conventions) must comply.
- Backend tests require `uv sync --extra dev` / `uv run --extra dev pytest` — plain `uv run pytest` silently falls through to a system Python missing `pytest-asyncio` (established project gotcha, also recorded in user MEMORY.md). This matters if the Dockerfile or a CI-style script ever runs backend tests inside the image.

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python:3.12-slim` | 3.12 (Debian trixie) | Backend runtime base image | Matches `backend/pyproject.toml`'s `requires-python = ">=3.12"` [VERIFIED: backend/pyproject.toml:8] |
| `ghcr.io/astral-sh/uv` | `python3.12-trixie-slim` tag | Build-stage base providing the `uv` binary pre-installed | Official Astral-published image, avoids a separate `curl \| sh` install step in the Dockerfile [CITED: github.com/astral-sh/uv-docker-example] |
| `node:22-slim` | 22.x (Maintenance LTS) | Frontend build stage | Node 20 is EOL as of 2026-04-30; Node 22 is the current Maintenance LTS (EOL 2027-04-30) [CITED: nodejs.org/en/about/eol] — see Common Pitfalls |
| `@playwright/test` | 1.62.1 | E2E test runner | Official Microsoft package; matches this repo's existing TypeScript-first test conventions (`vitest` in `frontend/`) rather than introducing a Python test runner for E2E [VERIFIED: npm registry — see Package Legitimacy Audit] |
| `mcr.microsoft.com/playwright` | `v1.62.1-noble` | Playwright's own Docker image, pinned to the exact `@playwright/test` version | Official image; browsers pre-installed matching the package version, avoids `npx playwright install` inside CI/compose [CITED: playwright.dev/docs/docker] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Docker Compose v2 (`docker compose`, not `docker-compose`) | bundled with current Docker Desktop/Engine | `docker-compose.yml` convenience wrapper, `test/docker-compose.test.yml` | Compose v2 is the current CLI plugin form; the standalone Python `docker-compose` binary is legacy |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `node:22-slim` build stage | `node:22-alpine` | Alpine is smaller but uses musl libc, which occasionally breaks native Next.js/npm postinstall binaries; `-slim` (Debian) is the safer default for a build-only stage that's discarded after `npm run build` |
| Playwright `@playwright/test` (JS) | `pytest-playwright` (Python) | Python option exists, but this repo's frontend is TypeScript-first (`vitest` already in use) and PLAN.md's E2E section describes a "Playwright container," implying the standard JS/TS Playwright toolchain — no reason to introduce a second test language |
| `ghcr.io/astral-sh/uv` builder image | `pip install uv` inside `python:3.12-slim` | The official uv image is a single `FROM`, no extra install layer, and is what uv's own Docker documentation recommends |

**Installation:**
```bash
# Backend (already exists — no new deps for this phase)
cd backend && uv sync --extra dev

# Playwright E2E harness (new — a package.json under test/)
cd test && npm init -y && npm install -D @playwright/test
```

**Version verification:** Verified 2026-08-18 via `npm view <pkg> version` (npm registry is on the network allowlist):
- `@playwright/test` → `1.62.1` (created 2020-09-24, ~37.5M weekly downloads, `github.com/microsoft/playwright` repo) [VERIFIED: npm registry]
- `fastapi` (already installed) → latest registry version `0.141.1`, matches `backend/uv.lock`'s pinned `0.141.1` exactly [VERIFIED: backend/uv.lock — `name = "fastapi"` / `version = "0.141.1"`]
- Node 20 EOL / Node 22 Maintenance-LTS status confirmed via WebSearch cross-referencing nodejs.org's official EOL page [CITED: nodejs.org/en/about/eol]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `@playwright/test` | npm | 5.9 yrs (created 2020-09-24) | ~37.5M/week | `github.com/microsoft/playwright` | OK (manually verified — see note) | Approved |

**Note on verdict:** the automated `package-legitimacy check` seam returned `SUS` for `@playwright/test` with `unknown-age`/`unknown-downloads`/`no-repository` reasons — its live-signal fetch returned `null` for all three fields in this session (a tool-side data-fetch gap, not a finding about the package). I independently queried the npm registry directly (`npm view @playwright/test`, `api.npmjs.org/downloads`) and confirmed: created 2020-09-24, ~37.5M weekly downloads, official `microsoft/playwright` GitHub repo, no `postinstall` script. This is Microsoft's own first-party test package for their own Playwright project — overriding the automated `SUS` to `OK` based on directly-verified registry data. The planner does **not** need to add a `checkpoint:human-verify` task for this package, but should note this override in the plan if audited later.

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none (see override note above).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── docker build ───────────────────────────┐
│                                                                     │
│  Stage 1: node:22-slim          Stage 2: ghcr.io/astral-sh/uv      │
│  ┌──────────────────────┐       ┌──────────────────────────────┐  │
│  │ COPY frontend/        │      │ COPY backend/pyproject.toml   │  │
│  │ npm ci                │      │ COPY backend/uv.lock          │  │
│  │ npm run build          │      │ uv sync --locked              │  │
│  │  → frontend/out/       │      │  --no-install-project (cache) │  │
│  └──────────┬─────────────┘      │ COPY backend/                 │  │
│             │                     │ uv sync --locked (full)       │  │
│             │                     └──────────────┬─────────────────┘  │
│             │                                    │                  │
│             └──────────────┬─────────────────────┘                  │
│                             ▼                                       │
│              Stage 3: python:3.12-slim (final runtime image)        │
│              COPY --from=stage2 /app/.venv  → PATH                  │
│              COPY --from=stage2 backend/app → /app/backend/app      │
│              COPY --from=stage1 frontend/out → /app/static          │
│              ENV FINALLY_STATIC_DIR=/app/static                     │
│              ENV FINALLY_DB_PATH=/app/db/finally.db                 │
│              CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", ...│
└──────────────────────────────────────────────────────────────────────┘
                             │
                             ▼  docker run / docker compose up
┌─────────────────────────── runtime container ───────────────────────┐
│  uvicorn serves FastAPI app on :8000                                 │
│   ├─ /api/*           → REST routes (portfolio, watchlist, chat)    │
│   ├─ /api/stream/*    → SSE price stream                            │
│   └─ /*               → StaticFiles(directory=FINALLY_STATIC_DIR)   │
│                                                                       │
│  lifespan startup: db.initialize() → lazy schema+seed against        │
│    FINALLY_DB_PATH (bind-mounted to host ./db/finally.db)            │
└────────────────────────────────────────────────────────────────────┘
                             │
                    host bind mount: ./db:/app/db
                             ▼
                  db/finally.db (persists across
                  container stop/start/recreate)
```

### Recommended Project Structure

```
finally/
├── Dockerfile                    # multi-stage: node:22-slim → uv builder → python:3.12-slim runtime
├── .dockerignore                 # excludes .env, node_modules, .venv, __pycache__, db/finally.db, test artifacts
├── docker-compose.yml            # convenience wrapper: same bind-mount/env-file/port as scripts
├── .env.example                  # documents OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK
├── scripts/
│   ├── start_mac.sh              # idempotent: build-if-needed, run, wait for /api/health, open browser
│   ├── stop_mac.sh               # idempotent: docker stop (not rm), preserves bind-mounted db/
│   ├── start_windows.ps1         # best-effort mirror, unverified on this machine (D-04)
│   └── stop_windows.ps1          # best-effort mirror, unverified on this machine (D-04)
└── test/
    ├── docker-compose.test.yml   # app service (scratch env/db) + playwright service
    ├── package.json              # @playwright/test devDependency
    ├── playwright.config.ts      # baseURL points at the compose app service DNS name
    └── e2e/
        ├── fresh-start.spec.ts
        ├── watchlist.spec.ts
        ├── trade.spec.ts
        ├── ai-chat.spec.ts
        └── sse-reconnect.spec.ts
```

### Pattern 1: uv two-phase sync for Docker layer caching

**What:** Sync dependencies from `pyproject.toml`/`uv.lock` alone first (`--no-install-project`), so the dependency layer is cached and only invalidated when the lockfile changes; then `COPY` the actual source and run `uv sync --locked` again to install the project itself.

**When to use:** Any multi-stage Python Dockerfile using `uv` — this is uv's own documented pattern, not project-specific.

**Example:**
```dockerfile
# Source: github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile [CITED]
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

### Pattern 2: Explicit env-var overrides instead of relying on directory-nesting math

**What:** `db_path()` and the static-dir resolution in `main.py` both fall back to `Path(__file__).resolve().parents[N]`-based defaults that assume a specific repo layout (`backend/app/db/database.py` → 3 parents up = repo root; `backend/app/main.py` → 2 parents up = repo root, then `/backend/static`). Inside a Docker image, the directory layout is whatever the Dockerfile's `COPY` commands produce — it does not have to (and likely won't, once source files are split across build stages) match the checkout layout exactly.

**When to use:** Always, for this phase's Dockerfile — set both env vars explicitly rather than trying to reproduce the exact `repo_root/backend/...` nesting inside the image.

**Example:**
```dockerfile
ENV FINALLY_DB_PATH=/app/db/finally.db
ENV FINALLY_STATIC_DIR=/app/static
```
```python
# Source: backend/app/db/database.py:45-49 [VERIFIED: backend/app/db/database.py:45-49]
#     override = os.getenv("FINALLY_DB_PATH")
#     if override:
#         return Path(override)
#     repo_root = Path(__file__).resolve().parents[3]
#     return repo_root / "db" / "finally.db"
# Source: backend/app/main.py:67-70 [VERIFIED: backend/app/main.py:67-70]
#     _repo_root = Path(__file__).resolve().parents[2]
#     _static_dir = Path(os.getenv("FINALLY_STATIC_DIR", str(_repo_root / "backend" / "static")))
#     if _static_dir.is_dir():
#         app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
```

### Pattern 3: Idempotent container lifecycle in bash

**What:** Before `docker run`, check whether a container with the target name already exists and in what state; only create a new one if absent.

**When to use:** `scripts/start_mac.sh` / `scripts/stop_mac.sh`, per D-04/D-05 and the "safe to run repeatedly" success criterion.

**Example:**
```bash
# Source: synthesized from community patterns (docker inspect / docker ps filtering) [ASSUMED — see Assumptions Log]
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

### Pattern 4: docker-compose bind mount + env_file + ports

**Example:**
```yaml
# Source: docker/docs compose-file reference [CITED: github.com/docker/docs — content/reference/compose-file/services.md]
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./db:/app/db
```
`env_file` values are overridden by an explicit `environment:` block if both are present; relative `volumes` short-syntax paths (`./db:/app/db`) auto-create the host directory if missing, and are resolved relative to the compose file's own directory [CITED: github.com/docker/docs].

### Pattern 5: Playwright as a sibling docker-compose service

**What:** A dedicated `docker-compose.test.yml` with an `app` service (built from the same Dockerfile, `LLM_MOCK=true`, its own scratch bind mount or tmpfs so it never touches the dev `db/finally.db` per D-03) and a `playwright` service using the official image, pointed at `app` via compose's internal DNS.

**Example:**
```yaml
# Source: synthesized — no first-party Playwright docs example for this topology [ASSUMED — see Assumptions Log]
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

### Anti-Patterns to Avoid

- **`COPY . .` at the repo root into either build stage:** pulls in `.env`, `node_modules`, `.venv`, `db/finally.db`, and `.git` unless a `.dockerignore` explicitly excludes them — leaks secrets into image layers even if a later `RUN rm` deletes the file, because Docker layers are immutable and the deleted file is still present in an earlier layer.
- **Copying `.next/standalone` when `next.config.ts` has `output: 'export'`:** these are two different Next.js output modes; `output: 'export'` produces `out/`, not `.next/standalone`. Copying the wrong directory silently produces an empty or broken static bundle. [VERIFIED: frontend/next.config.ts — `output: 'export'`]
- **`docker rm` in the stop script:** removing the container (rather than just stopping it) is not itself destructive to the bind-mounted `db/`, but it does discard the container's own state/logs and defeats the "safe to run repeatedly, no duplicate containers" success criterion's intent of reusing the same container across stop/start cycles — `docker stop` + `docker start` is the idempotent pair.
- **Relying on the app's `parents[N]` path defaults inside the container:** see Pattern 2 — use explicit env vars instead of trying to reproduce the source tree's exact nesting in the image.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container-exists detection | Custom `ps aux \| grep docker` parsing | `docker inspect -f '{{.State.Status}}' <name>` or `docker ps -a --filter name=<name> --format '{{.Names}}'` | Docker's own CLI already exposes structured state; string-grepping process lists is fragile and racy |
| Waiting for the app to be ready before opening a browser | Fixed `sleep N` | Poll `curl -sf http://localhost:8000/api/health` in a loop with a timeout | `/api/health` already exists [VERIFIED: backend/app/main.py:54-56 — `@app.get("/api/health")` / `return {"status": "ok"}`] — a fixed sleep is either too short (flaky) or too long (slow demo) |
| SPA fallback routing | Custom catch-all FastAPI route serving `index.html` | Existing `StaticFiles(directory=..., html=True)` mount (already implemented) — or FastAPI's newer `app.frontend(path, directory=..., fallback="auto")` if multi-route client-side navigation is ever added | This app has exactly one client route (`/`) [VERIFIED: frontend/app — only `page.tsx`, `layout.tsx`, no nested route directories found]; the existing mount already handles it. No change needed for this phase. |
| Playwright browser install management | Manual `npx playwright install` scripting in CI | Official `mcr.microsoft.com/playwright:v<version>-<distro>` image (browsers pre-installed, version-matched) | Avoids install flakiness and version drift between the npm package and installed browser binaries |

**Key insight:** Every piece of "one-command launch" plumbing in this phase already has an existing, tested seam to hook into (`/api/health`, `FINALLY_DB_PATH`, `FINALLY_STATIC_DIR`, lazy `db.initialize()`) — the phase's job is wiring, not building new mechanisms.

## Runtime State Inventory

> Included because this phase changes how the app's persistent state is addressed (bind mount vs. the PLAN.md's original named-volume example) and packages it for the first time.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `db/finally.db` — SQLite file, currently created by local `uv run uvicorn` runs at `db_path()`'s default (repo-root `db/finally.db`) [VERIFIED: backend/app/db/database.py:45-49] | None beyond the bind mount + explicit `FINALLY_DB_PATH` env var (Pattern 2) — same file, same schema, no migration. If a `db/finally.db` already exists in this checkout from prior manual runs, it will be picked up as-is (lazy init is additive, never destructive [VERIFIED: backend/app/db/database.py:1-8 docstring — "Contract: initialize() is purely additive"]) |
| Live service config | None — no external services (n8n, Datadog, etc.) in this project | None |
| OS-registered state | None — no launchd/systemd/Task Scheduler registrations planned or found | None |
| Secrets/env vars | `.env` at repo root (gitignored, contains `OPENROUTER_API_KEY`) [VERIFIED: .gitignore — `.env` entry present]; no `.env.example` exists yet | Code edit: create `.env.example` documenting `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` per PLAN.md §5 — no key renames, only a new template file |
| Build artifacts | `backend/static/` already contains a manually-built frontend export from a prior session (index.html, `_next/`, etc.) [VERIFIED: directory listing — `ls backend/static` shows `index.html`, `_next`, `404.html`] | This is a stale manual artifact, not a Docker build output — the Dockerfile's own build stage should regenerate this from `frontend/out/` at image-build time, not rely on the checked-in copy. Confirm `backend/static/` is gitignored or explicitly excluded from the image via `.dockerignore` (verify — not confirmed in this session) |

**Nothing found in category:** Live service config and OS-registered state — verified by reviewing the full project structure (`ls -la` at repo root) and confirming no `n8n`, `launchd`, or `systemd` references anywhere in the codebase or planning docs.

## Common Pitfalls

### Pitfall 1: Node 20 is EOL — do not use it for a new build in August 2026

**What goes wrong:** The phase description and CONTEXT.md's discretion-area example both say "Node 20," matching PLAN.md's original spec. But Node.js 20 reached end-of-life on 2026-04-30 — it no longer receives security patches.
**Why it happens:** PLAN.md was written before Node 20's EOL date; the spec text is now stale relative to the current date.
**How to avoid:** Use `node:22-slim` (current Maintenance LTS, EOL 2027-04-30) for the build stage. This is a build-stage-only image (discarded after `npm run build`), so the security exposure is minimal either way, but using an EOL base image is still bad practice and trivially avoidable.
**Warning signs:** `docker build` logs showing `node:20-slim` pulling successfully (it still exists on Docker Hub — EOL doesn't mean the image is removed) masks the fact that it's unpatched.

### Pitfall 2: Static/DB path resolution silently breaks if the container layout doesn't mirror the checkout

**What goes wrong:** `db_path()` and the static-dir default both use `Path(__file__).resolve().parents[N]` — if the Dockerfile's `COPY` commands don't reproduce the exact `repo_root/backend/app/...` nesting, these defaults resolve to the wrong (likely non-existent) path. For the static dir specifically, `main.py`'s `if _static_dir.is_dir():` guard means a wrong path doesn't error — it just silently skips mounting the frontend entirely, and the app serves only `/api/*` with a 404 on `/`.
**Why it happens:** These path-resolution defaults were designed for "run from a normal checkout," not "run from an arbitrary container filesystem layout."
**How to avoid:** Set `FINALLY_DB_PATH` and `FINALLY_STATIC_DIR` explicitly as `ENV` in the Dockerfile's runtime stage (Pattern 2) rather than trying to preserve exact directory nesting.
**Warning signs:** Container starts successfully, `/api/health` returns 200, but `http://localhost:8000/` returns 404 or an empty response — check `_static_dir.is_dir()` by shelling into the container (`docker exec ... ls /app/static`).

### Pitfall 3: `output: 'export'` vs `.next/standalone` confusion in Dockerfile guides

**What goes wrong:** Most public Next.js Docker tutorials found in this research target `output: 'standalone'` (a Node.js server bundle), copying `.next/standalone`. This project uses `output: 'export'` [VERIFIED: frontend/next.config.ts], which produces a plain static `out/` directory instead — no Node.js server runs at all in the final image.
**Why it happens:** `standalone` is the more commonly documented mode because most Next.js Docker deployments run their own Node server; this project deliberately avoids that (PLAN.md §11: FastAPI serves everything, single port).
**How to avoid:** Copy `frontend/out/` (built via `npm run build` with `output: 'export'` already configured), not `.next/standalone`.
**Warning signs:** A build stage referencing `.next/standalone` in this project would fail or produce nothing, since that directory won't exist under an `export`-mode build.

### Pitfall 4: `.env` leaking into image layers

**What goes wrong:** A `COPY . .` (or any recursive copy of the repo root) without a `.dockerignore` bakes `.env` — including `OPENROUTER_API_KEY` — directly into an image layer. Even removing it in a later `RUN rm .env` step doesn't help; the secret remains recoverable from the earlier layer.
**Why it happens:** `.dockerignore` doesn't exist yet in this repo (not found in this session's directory listing).
**How to avoid:** Create a `.dockerignore` excluding at minimum: `.env`, `.git`, `node_modules`, `.venv`, `__pycache__`, `*.egg-info`, `.pytest_cache`, `.ruff_cache`, `db/finally.db`, `frontend/out` (rebuilt fresh in-image, no need to copy the host's stale copy), `backend/static` (same reason), `backend/tests`, `frontend/**/*.test.ts`. Secrets are supplied at `docker run`/`docker compose up` time via `--env-file`/`env_file:`, never baked in.
**Warning signs:** `docker history --no-trunc <image>` shows a layer with `.env`'s contents, or `docker run --rm <image> cat /app/.env` succeeds.

### Pitfall 5: Playwright container can't reach `localhost:8000`

**What goes wrong:** Inside `docker-compose.test.yml`, `http://localhost:8000` from the Playwright container refers to the Playwright container itself, not the app container — Docker Compose's default bridge network requires using the app service's *service name* as the hostname.
**Why it happens:** Compose gives each service its own network namespace; only explicit service-name DNS (or `network_mode: service:app`) crosses that boundary.
**How to avoid:** Set the Playwright `baseURL`/`BASE_URL` to `http://<app-service-name>:8000` (Pattern 5), and add `depends_on: [app]` so compose starts the app first (note: `depends_on` alone doesn't wait for readiness — pair with a healthcheck or a startup retry/poll inside the test setup).
**Warning signs:** `net::ERR_CONNECTION_REFUSED` in Playwright test output when run inside compose, despite the same tests passing when run against a locally-started app.

## Code Examples

### Idempotent stop script

```bash
#!/usr/bin/env bash
# Source: synthesized from Docker CLI idempotency patterns [ASSUMED — see Assumptions Log]
set -euo pipefail
CONTAINER_NAME="finally"
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  docker stop "$CONTAINER_NAME"
  echo "Stopped $CONTAINER_NAME. Data in db/ is preserved."
else
  echo "$CONTAINER_NAME is not running."
fi
```

### FastAPI health-check wait loop (for start_mac.sh, before opening the browser)

```bash
# Source: /api/health endpoint verified in backend/app/main.py:54-56 [VERIFIED]
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

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `node:20-slim`/`node:20-alpine` for new Docker builds | `node:22-slim`/`node:22-alpine` | Node 20 EOL 2026-04-30 | Build-stage-only risk is low, but using an unsupported base image is avoidable with a one-line change |
| Standalone `docker-compose` (Python binary) | `docker compose` (Docker CLI plugin, v2) | Compose v2 has been the default for several years now | Syntax is compose-file-spec compatible either way; invoke via `docker compose`, not the legacy hyphenated binary |
| Manual `uv pip install` inside Docker | `uv sync --locked` against a bind-mounted `uv.lock` | Standard since uv's Docker guide was published | Reproducible installs matching the committed lockfile exactly, no separate `requirements.txt` export step needed |

**Deprecated/outdated:**
- Node 20 for any new build as of this research date — superseded by Node 22 (Maintenance LTS) or Node 24 (Active LTS).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact idempotent-script shape (`docker inspect -f '{{.State.Status}}'` + case statement) | Architecture Patterns (Pattern 3), Code Examples | Low — this is a well-established, easily-testable shell pattern; if the exact command differs slightly, the planner/executor can adjust without architectural impact. No official Docker doc prescribes one canonical idempotent-start-script shape. |
| A2 | Playwright-in-docker-compose sibling-service topology (service DNS name as `BASE_URL`, `depends_on`) | Architecture Patterns (Pattern 5), Common Pitfalls (Pitfall 5) | Medium — no first-party Playwright documentation example was found for this exact topology (confirmed via both Context7 and WebFetch of playwright.dev/docs/docker, which explicitly states it doesn't cover multi-service compose setups). The general Docker Compose networking behavior (service-name DNS) is well-established and cross-checked, but the specific compose file shape is synthesized, not sourced from an authoritative Playwright example. |
| A3 | `docker:22-slim` and `node:22-alpine` exist as valid Docker Hub tags | Standard Stack | Low — Node's own release/EOL page confirms Node 22 is a released, current LTS line; Docker Hub tag availability for LTS lines has never lagged an npm release in this project's experience, but Docker Hub itself is not on the network allowlist for direct verification in this session. |

**If this table is empty:** N/A — see entries above; all three are LOW-MEDIUM risk and easily verified by the planner/executor at build time (a failed `docker pull` or `docker build` immediately surfaces any wrong tag).

## Open Questions

1. **Should `backend/static/` (the stale manually-built frontend copy already in the repo) be added to `.gitignore`/`.dockerignore` now, or left as a working fallback for local `uv run uvicorn` development?**
   - What we know: It currently lets local (non-Docker) development serve the frontend without a Docker build.
   - What's unclear: Whether Phase 5's Dockerfile should assume a fresh `npm run build` always happens at image-build time (safe either way) and whether keeping the checked-in copy around causes confusion about which copy is "live" during local dev.
   - Recommendation: Leave `backend/static/` un-gitignored (it's evidently already a working dev convenience) but ensure `.dockerignore` excludes it from the Docker build context so the image always gets a byte-for-byte fresh export — never a stale one.

2. **Exact PowerShell idempotency pattern for `start_windows.ps1`/`stop_windows.ps1` — cannot be verified on this (macOS) machine per D-04.**
   - What we know: The bash pattern (`docker inspect`/`docker ps --filter`) has direct PowerShell equivalents (`docker inspect` works identically cross-platform since it's the Docker CLI, not a shell built-in).
   - What's unclear: PowerShell-specific syntax for conditionals/error handling around the same `docker` CLI calls — not verified in this session.
   - Recommendation: Mirror the bash script's `docker inspect`/`docker start`/`docker run` logic 1:1 (the underlying `docker` commands are identical across platforms), wrapped in PowerShell `if`/`try`/`catch` — document explicitly in the script header that it is unverified, per D-04.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Engine / Docker Desktop | Entire phase (INFRA-02/03/04) | Not verified in this sandboxed research session (`docker info` requires host access beyond the research sandbox) | — | None — Docker is a hard requirement per PLAN.md §11; the planner should have the executor verify `docker info` succeeds before starting implementation |
| Docker Compose v2 (`docker compose` plugin) | `docker-compose.yml`, `test/docker-compose.test.yml` | Not verified (same reason) | — | None — bundled with current Docker Desktop; if using Docker Engine directly on Linux, the compose plugin may need separate install |
| Node.js / npm | Frontend build (already used in Phases 1-4) | Not re-verified this session (already confirmed working in Phase 3/4 close-out notes) | — | — |
| `uv` | Backend build/test | Not re-verified this session (already confirmed working throughout Phases 1-4) | — | — |

**Missing dependencies with no fallback:**
- Docker Engine/Desktop and Docker Compose v2 availability on the execution machine — must be confirmed by the executor at the start of Phase 5 work; this research session's sandbox does not have Docker CLI access to verify directly.

**Missing dependencies with fallback:**
- None identified.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.3+ / pytest-asyncio, config in `backend/pyproject.toml` [VERIFIED: backend/pyproject.toml — `[tool.pytest.ini_options]` block, `testpaths = ["tests"]`] |
| Frontend framework | vitest 4.x, config in `frontend/vitest.config.ts` [VERIFIED: frontend/package.json — `"test": "vitest run"`] |
| E2E framework (new this phase) | `@playwright/test` 1.62.1, config to be created at `test/playwright.config.ts` |
| Quick run command (backend) | `cd backend && uv run --extra dev pytest` |
| Quick run command (frontend) | `cd frontend && npm test` |
| Quick run command (E2E) | `cd test && docker compose -f docker-compose.test.yml up --build --abort-on-container-exit` |
| Full suite command | Same as quick run — this phase adds no new backend/frontend logic, only packaging; the "full suite" for this phase *is* the E2E suite plus a `docker build` sanity check |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-02 | `docker build` produces a working single image | smoke | `docker build -t finally . && docker run --rm -d -p 8000:8000 --env-file .env finally && curl -sf localhost:8000/api/health` | ❌ Wave 0 — no Dockerfile yet |
| INFRA-03 | `scripts/start_mac.sh` / `docker compose up` brings up the app at `localhost:8000` idempotently | smoke + manual | `scripts/start_mac.sh` run twice in a row, second run is a no-op/reuse | ❌ Wave 0 — scripts don't exist yet |
| INFRA-04 | Data (cash/positions/trades/watchlist/chat) survives a stop/start cycle | e2e | Playwright test: seed state via UI, `docker compose restart`, reload page, assert state unchanged | ❌ Wave 0 — needs a dedicated E2E spec |
| TEST-04 | Playwright suite covers fresh start, add/remove ticker, buy/sell, AI chat trade, SSE reconnection | e2e | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit` | ❌ Wave 0 — entire `test/` directory doesn't exist yet |

### Sampling Rate

- **Per task commit:** N/A for Dockerfile/script tasks (no unit test framework applies to shell scripts or Dockerfiles themselves) — use `docker build` / `shellcheck` (if available) as the fast local check.
- **Per wave merge:** Full `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit` run.
- **Phase gate:** All 5 E2E scenarios (fresh start, watchlist add/remove, buy/sell, AI chat trade, SSE reconnection) green, plus a clean `docker build` and a manual stop/start persistence check, before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `Dockerfile` — does not exist yet
- [ ] `.dockerignore` — does not exist yet
- [ ] `docker-compose.yml` — does not exist yet
- [ ] `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` — none exist yet
- [ ] `test/` directory, `test/docker-compose.test.yml`, `test/package.json`, `test/playwright.config.ts` — none exist yet
- [ ] `.env.example` — does not exist yet
- [ ] Framework install: `cd test && npm install -D @playwright/test`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | PLAN.md explicitly specifies zero-auth, single hardcoded `user_id="default"` — out of scope for all phases, not just this one [VERIFIED: PLAN.md §7 — `id` TEXT PRIMARY KEY (default: `"default"`)] |
| V3 Session Management | No | Same as above — no sessions exist |
| V4 Access Control | No | Same as above |
| V5 Input Validation | No (unchanged this phase) | Existing Pydantic validation on API routes (Phases 1-4), untouched by Docker packaging |
| V6 Cryptography | No | No new secrets/crypto introduced; `OPENROUTER_API_KEY` handling is unchanged (env-var passthrough, never logged or persisted) |
| V14 Configuration (not in the default V1-V6 table above but relevant here) | Yes | Docker/`.dockerignore`/`.env` handling — see Known Threat Patterns below |

### Known Threat Patterns for Docker packaging

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret (`OPENROUTER_API_KEY`) baked into an image layer via unfiltered `COPY` | Information Disclosure | `.dockerignore` excluding `.env`; secrets injected only at `docker run --env-file` / compose `env_file:` time, never at build time (Pitfall 4) |
| Container running as root by default | Elevation of Privilege | Follow the uv-docker-example pattern's `--chown=nonroot:nonroot` / add a non-root `USER` directive in the final stage — the official uv example does this; recommend the planner include it |
| Supply-chain risk from a new npm dependency (`@playwright/test`) | Tampering | Package Legitimacy Audit above; `uv.lock`/`package-lock.json` pin exact versions, `npm ci` (not `npm install`) in any reproducible build/test step |
| Accepted-but-unaddressed risks carried forward from Phases 1-3 (no SSE auth, no rate limiting, error responses carry user's own data) explicitly flagged "revisit at Phase 5 container publish" in `STATE.md` | Multiple (Spoofing/DoS via exposed SSE, Information Disclosure via error detail) | This phase does not add authentication or rate limiting (out of scope per PLAN.md's zero-auth design and REQUIREMENTS.md's Out of Scope table). The "container publish" trigger in the accepted-risk notes refers to genuine internet-facing deployment; `docker run -p 8000:8000` on a local machine for a course demo is not equivalent to public internet exposure. Recommend the plan explicitly re-confirm these risks remain accepted (not silently dropped) rather than attempt new mitigations out of scope for this phase. |

## Sources

### Primary (MEDIUM confidence — Context7-sourced, tagged [CITED])
- `/astral-sh/uv-docker-example` (Context7) — multi-stage Dockerfile pattern, `uv sync --locked --no-install-project` caching pattern
- `/docker/docs` (Context7) — compose-file bind-mount short syntax, `env_file`, `ports`, `docker compose up --build` recreate behavior
- `/microsoft/playwright` (Context7) — official Docker image tag pattern, `playwright.dev/docs/docker` (via WebFetch) confirming no first-party compose+sibling-service example exists
- `/websites/fastapi_tiangolo` (Context7) — `StaticFiles` API reference, newer `app.frontend()` SPA-fallback helper

### Secondary (LOW confidence — WebSearch, tagged [ASSUMED] where used)
- WebSearch: Next.js multi-stage Docker patterns (mostly targeting `output: 'standalone'`, cross-checked against this repo's actual `output: 'export'` config to avoid the mismatch — see Pitfall 3)
- WebSearch: idempotent Docker start/stop bash patterns (`docker inspect`/`docker ps --filter` — general community consensus, no single canonical source)
- WebSearch + nodejs.org: Node.js 20 EOL date (2026-04-30) cross-referenced across multiple results (HeroDevs, TuxCare, nodejs.org's own `/en/about/eol` page)

### Verified in-repo (HIGH confidence, tagged [VERIFIED: path:lines])
- `backend/app/main.py` (full file read) — lifespan wiring, `/api/health`, `StaticFiles` mount, `FINALLY_STATIC_DIR` resolution
- `backend/app/db/database.py` (lines 1-49 read) — `db_path()`, `FINALLY_DB_PATH`, lazy-init contract docstring
- `frontend/next.config.ts` — confirmed `output: 'export'`
- `backend/pyproject.toml` — confirmed `requires-python = ">=3.12"`, `dev` optional-dependencies group, pytest/ruff config
- `backend/uv.lock` — confirmed `fastapi` pinned at `0.141.1`
- `.gitignore` — confirmed `.env` and `db/finally.db` are gitignored, no `.dockerignore` exists
- npm registry (`npm view`, `api.npmjs.org`) — `@playwright/test` version, age, downloads, repo URL

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH for versions directly verified against npm/uv.lock; MEDIUM for the uv/Docker/Playwright/Compose patterns (Context7-sourced official docs, not independently executed in this session)
- Architecture: MEDIUM — the Dockerfile/compose patterns are standard and cross-checked against this repo's actual code seams (`FINALLY_DB_PATH`, `FINALLY_STATIC_DIR`, `/api/health`); the Playwright-in-compose topology (A2) is synthesized, not sourced from an authoritative example
- Pitfalls: HIGH for the two in-repo-verified pitfalls (static/DB path resolution, `export` vs `standalone`); MEDIUM for Node 20 EOL (cross-referenced across multiple independent sources)

**Research date:** 2026-08-18
**Valid until:** ~2026-09-17 (30 days — Docker/Node/uv patterns are stable, but Node LTS status and Playwright's pinned version will drift; re-verify version numbers if planning is delayed)
