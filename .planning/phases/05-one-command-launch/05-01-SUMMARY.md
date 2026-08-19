---
phase: 05-one-command-launch
plan: 01
subsystem: infra
tags: [docker, dockerfile, uv, next-export, sqlite, bind-mount, uvicorn]

# Dependency graph
requires:
  - phase: 01-04
    provides: FastAPI app entrypoint, lazy SQLite init/seed, /api/health route
  - phase: 03-05
    provides: full frontend terminal (static-export-ready Next.js app)
  - phase: 04-04
    provides: completed AI chat integration (last app feature before packaging)
provides:
  - Multi-stage Dockerfile (node:22-slim -> uv builder -> python:3.12-slim runtime) serving the whole app on port 8000
  - .dockerignore keeping secrets, VCS metadata, and stale build artifacts out of the image
  - Startup log line naming the resolved SQLite path and existing-vs-new status
  - .env.example documenting the three PLAN.md environment variables
affects: [05-02, 05-03, 05-04]

# Actuals (#2632)
actuals:
  tokens: 8400
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "uv two-phase Docker sync (--no-install-project against bind-mounted lockfile, then full uv sync --locked after COPY) for dependency-layer caching"
    - "Explicit ENV FINALLY_DB_PATH / FINALLY_STATIC_DIR overrides instead of relying on Path(__file__).resolve().parents[N] matching the image's directory layout"
    - "logging.getLogger(\"uvicorn.error\") for any startup-visibility log that must reach docker logs, since uvicorn's default dictConfig leaves the root logger bare"

key-files:
  created: [Dockerfile, .dockerignore, .env.example]
  modified: [backend/app/db/database.py, frontend/package-lock.json]

key-decisions:
  - "node:22-slim substituted for the PLAN.md-literal node:20-slim: Node 20 reached EOL 2026-04-30, per CONTEXT.md base-image choice is Claude's discretion"
  - "Regenerated frontend/package-lock.json from scratch: the committed lockfile had a corrupted node_modules/@img/sharp-wasm32/node_modules/@emnapi/runtime entry (missing version field) that made npm ci fail deterministically under npm 10.9.8 (bundled in node:22-slim) with 'Invalid Version:'. Root-caused via verbose npm logs pointing at the exact broken entry; fix was a clean npm install --package-lock-only against the unchanged package.json, so no dependency version ranges changed (only lucide-react's resolved patch moved 1.31.0 -> 1.32.0, within its existing ^1.31.0 range)"
  - "Startup visibility log routed through logging.getLogger(\"uvicorn.error\") rather than a plain module logger, because uvicorn's dictConfig only attaches handlers to uvicorn.* loggers -- a bare module logger's .info() call falls through to logging.lastResort and is silently dropped below WARNING"
  - "Non-root finally user (uid 999) writes the bind-mounted db/ directory successfully on this macOS Docker Desktop host with no --user override needed -- the Plan's flagged Linux-host risk did not need to be exercised this session"

requirements-completed: [INFRA-02, INFRA-04]

coverage:
  - id: D1
    description: "docker build produces one image serving the complete FinAlly terminal (frontend + API) on port 8000"
    requirement: "INFRA-02"
    verification:
      - kind: integration
        ref: "docker build -t finally:dev . && curl -sf http://localhost:PORT/api/health && curl -s http://localhost:PORT/ | grep FinAlly"
        status: pass
    human_judgment: false
  - id: D2
    description: "Image contains no .env / credentials and runs as a non-root user"
    requirement: "INFRA-02"
    verification:
      - kind: integration
        ref: "docker run --rm --entrypoint sh finally:dev -c 'test ! -e /app/.env'; docker image inspect finally:dev --format '{{.Config.User}}'; docker run --rm --entrypoint sh finally:dev -c 'id -u'"
        status: pass
    human_judgment: false
  - id: D3
    description: "SQLite database persists across a clean docker stop / docker start cycle (cash, position, watchlist unchanged)"
    requirement: "INFRA-04"
    verification:
      - kind: integration
        ref: "manual persistence cycle recorded below: POST /api/portfolio/trade, POST /api/watchlist, docker stop, docker start, re-GET both endpoints"
        status: pass
    human_judgment: false
  - id: D4
    description: "SQLite database survives an unclean docker kill (SIGKILL) followed by docker start, with PRAGMA integrity_check reporting ok"
    requirement: "INFRA-04"
    verification:
      - kind: integration
        ref: "manual kill/start cycle recorded below: fresh trade, docker kill, docker start, GET /api/portfolio, sqlite3 <host db> PRAGMA integrity_check"
        status: pass
    human_judgment: false
  - id: D5
    description: "Startup log names the resolved absolute SQLite path and distinguishes new-vs-existing database on each start"
    requirement: "INFRA-04"
    verification:
      - kind: integration
        ref: "docker logs finally-persist (first start: 'Created and seeded a new database at /app/db/finally.db'; second start: 'Opened existing database at /app/db/finally.db')"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-18
status: complete
---

# Phase 5 Plan 1: One-Command Launch (Docker Packaging Tracer) Summary

**Multi-stage Dockerfile (node:22-slim frontend export -> uv-built backend -> python:3.12-slim runtime) that serves the complete FinAlly terminal on port 8000 as a non-root user, with SQLite persisting through both clean and unclean container restarts via a host bind mount.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-18T22:09:41-04:00
- **Tasks:** 2
- **Files modified:** 5 (3 created: Dockerfile, .dockerignore, .env.example; 2 modified: backend/app/db/database.py, frontend/package-lock.json)

## Accomplishments

- Three-stage Dockerfile builds the Next.js static export and the FastAPI backend into a single ~343 MiB image (`finally:dev`, size 360137005 bytes) that serves both on port 8000
- `.dockerignore` keeps `.env`, `.git`, `node_modules`, `.venv`, and every build artifact out of every layer; verified with `docker run ... test ! -e /app/.env`
- Container runs as a non-root `finally` user (uid 999); the bind-mounted `db/` directory was writable without any `--user` override on this macOS Docker Desktop host
- `database.py`'s `initialize()` now logs the resolved absolute SQLite path and whether it opened an existing database or created a new one, routed through `logging.getLogger("uvicorn.error")` so it actually reaches `docker logs`
- Full persistence proof against a scratch bind mount: a buy, a watchlist add, `docker stop` + `docker start` (state unchanged), then a fresh trade, `docker kill` (SIGKILL) + `docker start` (state unchanged, `PRAGMA integrity_check` reports `ok`)
- Root-caused and fixed a corrupted `frontend/package-lock.json` entry that made `npm ci` fail deterministically inside the `node:22-slim` build stage

## Task Commits

Each task was committed atomically:

1. **Task 1: One image, one port — build the container and serve the whole terminal end to end** - `a7226ed` (feat)
2. **Task 2: Persistence proof and startup visibility — data survives restart, and a broken mount is loud** - `585c5ee` (feat)

_No plan-metadata commit in worktree mode — the orchestrator commits STATE.md/ROADMAP.md centrally after merge; SUMMARY.md and this plan's own artifacts are committed as part of Task 2's commit above and this file's own commit (see below)._

## Files Created/Modified

- `Dockerfile` - Three-stage multi-stage build: `node:22-slim` frontend export, `ghcr.io/astral-sh/uv:python3.12-trixie-slim` backend dependency sync, `python:3.12-slim` runtime serving both on port 8000 as non-root user `finally`
- `.dockerignore` - Build-context exclusion list: `.env`/`.env.*` (with `!.env.example` negated back in), `.git`, `.venv`, `node_modules`, `frontend/out`, `backend/static`, `backend/tests`, `db/finally.db`, and project tooling directories
- `.env.example` - Committed template documenting `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` per `planning/PLAN.md` section 5, verbatim
- `backend/app/db/database.py` - Added `logging.getLogger("uvicorn.error")` and one `initialize()` log record naming the resolved absolute DB path and new-vs-existing status; docstring Contract paragraph updated to mention it
- `frontend/package-lock.json` - Regenerated from scratch (see Deviations) to fix a corrupted `@emnapi/runtime` sub-entry; no dependency version ranges in `package.json` changed

## Decisions Made

- **`node:22-slim` over `node:20-slim`**: Node 20 is EOL as of 2026-04-30; CONTEXT.md marks the base image as Claude's discretion, and RESEARCH.md had already flagged this substitution. Recorded in the Dockerfile as the build-stage base.
- **Startup log routed through `logging.getLogger("uvicorn.error")`**: the module-level alternative (`logging.getLogger(__name__)` at `INFO`) would silently be dropped by `logging.lastResort` under uvicorn's default `dictConfig`, since only `uvicorn.*` loggers get handlers attached. Using the `uvicorn.error` logger name guarantees the record reaches `docker logs` without any additional logging configuration.
- **No `--user` override needed for the bind mount**: the Plan flagged this as a possible Linux-only risk (macOS Docker Desktop's file-sharing layer remaps ownership permissively); verified writable as-is on this host, so the risk did not need to be exercised or documented as a required run-time flag for this session.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Regenerated a corrupted `frontend/package-lock.json` entry that made `npm ci` fail deterministically**
- **Found during:** Task 1 (`docker build` — `RUN npm ci` step in the `frontend-builder` stage)
- **Issue:** `npm ci` failed with `npm error Invalid Version:` under Node 22 / npm 10.9.8 (the version bundled in `node:22-slim`). Verbose npm logging traced the failure to `Node.canDedupe` calling `semver.gte()` on `node_modules/@img/sharp-wasm32/node_modules/@emnapi/runtime`, whose lockfile entry was `{"optional": true}` — missing `version`, `resolved`, and `integrity` entirely, even though its parent `@img/sharp-wasm32` (an optional transitive dependency of `next`, unused at runtime since this project sets `images: { unoptimized: true }`) declares `"@emnapi/runtime": "^1.11.1"`. This is a pre-existing corruption in the committed lockfile, not something introduced by this plan's changes.
- **Fix:** Regenerated `frontend/package-lock.json` from scratch via `npm install --package-lock-only` (run inside a `node:22-slim` container to match the exact npm version the Dockerfile build stage uses) against the unmodified `frontend/package.json`. Confirmed every top-level dependency version in the new lockfile still satisfies its `package.json` semver range (one transitive patch bump: `lucide-react` 1.31.0 -> 1.32.0, within its existing `^1.31.0` range). The corrupted `@emnapi/runtime` sub-entry does not appear at all in the regenerated tree.
- **Files modified:** `frontend/package-lock.json`
- **Verification:** `npm ci` succeeds cleanly against the regenerated lockfile inside `node:22-slim`; full `docker build -t finally:dev .` then completes end-to-end; the built image serves the frontend correctly (`curl -s http://localhost:PORT/ | grep FinAlly` passes)
- **Committed in:** `a7226ed` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to get past `npm ci` in the Docker build at all — without it, Task 1's tracer slice (and the entire phase) is blocked. No scope creep: only the lockfile was regenerated, no `package.json` dependency declarations changed.

## Issues Encountered

- **Docker daemon not running at session start.** The precondition check (`docker info` with sandbox disabled) failed with "Cannot connect to the Docker daemon" — Docker Desktop itself was not launched on the host. Started it with `open -a Docker`, waited ~20s for the daemon socket to come up, then proceeded; this was an environment-startup gap, not a task-related blocker, so it did not warrant a checkpoint.
- **Host port 8000 already occupied.** A pre-existing local `python3.1` process (unrelated to this task, likely another dev server) was bound to `127.0.0.1:8000`, so the tracer/persistence verification containers were run against alternate host ports (`18000`, `18001`) instead of `8000` — the container's internal port and all Dockerfile/compose contracts remain `8000` unchanged; only the ad hoc verification `docker run -p` host-side mapping differed. Did not touch the unrelated host process.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `finally` Docker image (tagged `finally:dev` locally during this session) is proven correct end-to-end: builds cleanly, serves the whole terminal on port 8000, persists SQLite through clean and unclean restarts, runs non-root, and contains no secrets.
- Plan 02 (docker-compose.yml, start/stop scripts) can build directly on this Dockerfile with no further changes required to it.
- Plan 02's README/script documentation should still carry the Plan's flagged note that a Linux host might require `--user "$(id -u):$(id -g)"` for the bind mount, even though this session's macOS verification did not need it (the risk was never exercised, only carried forward as documented in `05-01-PLAN.md`'s `flagged_assumptions`).
- No blockers for Plan 02/03/04.

---
*Phase: 05-one-command-launch*
*Completed: 2026-08-18*

## Self-Check: PASSED

- FOUND: Dockerfile
- FOUND: .dockerignore
- FOUND: .env.example
- FOUND: .planning/phases/05-one-command-launch/05-01-SUMMARY.md
- FOUND commit: a7226ed
- FOUND commit: 585c5ee
- FOUND commit: ab9118d
