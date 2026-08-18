# Phase 5: One-Command Launch - Context

**Gathered:** 2026-08-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Anyone can run the whole FinAlly workstation with one command — `scripts/start_mac.sh` (or the Windows equivalent, or `docker compose up`) — which builds and starts a single container serving the complete working terminal at `localhost:8000`. Stopping and restarting preserves cash, positions, trade history, watchlist, and chat history. A Playwright E2E suite runs against the container with `LLM_MOCK=true` and covers: fresh start, add/remove ticker, buy and sell, AI-executed trade, and SSE reconnection. Start/stop scripts are safe to run repeatedly — no duplicate containers, no lost volume.

</domain>

<decisions>
## Implementation Decisions

### Data Persistence
- **D-01:** The Docker container bind-mounts the host's `db/` directory (`-v $(pwd)/db:/app/db`), not an opaque named Docker volume. This is the same `db/finally.db` file already used by local `uv run uvicorn` development — visible in the checkout, trivial to inspect or delete for a fresh demo. Deviates from PLAN.md §11's literal `finally-data:/app/db` named-volume example; docker-compose.yml must use the same bind-mount, not a named volume, for consistency. — **Reversibility:** reversible — a volume-mount argument, not a schema or app-code change; switching to a named volume later is a one-line edit to the run command / compose file.

### Fresh-Start / Reset Story
- **D-02:** No `--reset` flag on the start/stop scripts. Resetting to a clean $10k start is a documented manual step (delete `db/finally.db`, then start again — the app's existing lazy-init reseeds automatically). Keeps the scripts simple and matches ROADMAP's "safe to run repeatedly" requirement without adding a destructive code path. — **Reversibility:** reversible — a flag can be added later without changing the reset mechanism itself (delete-and-reseed already works via existing lazy-init).
- **D-03:** The Playwright E2E suite's database isolation (its own scratch DB via `docker-compose.test.yml`, per PLAN.md §12) is unaffected by D-01/D-02 — it already runs against a separate container/volume by design, never touching the bind-mounted `db/finally.db` a developer or demo user is using locally.

### Windows Scripts
- **D-04:** `scripts/start_windows.ps1` / `scripts/stop_windows.ps1` are a best-effort PowerShell mirror of the mac scripts' logic (build-if-needed, run with the same volume/port/env-file args, idempotent stop). They cannot be executed or verified on this machine (macOS) — document this limitation directly in the scripts' header comments and in the phase's verification notes. — **Reversibility:** reversible — scripts, no architectural dependency on them being correct on the first attempt.

### Launch UX
- **D-05:** `scripts/start_mac.sh` automatically opens the default browser to `http://localhost:8000` after the container is confirmed up (e.g. `open http://localhost:8000` on mac). The Windows equivalent uses `start http://localhost:8000`. — **Reversibility:** reversible — a single command in the script, easy to remove or gate behind a flag later.

### Claude's Discretion
- Exact Dockerfile base images (e.g. `node:20-slim` for the build stage, `python:3.12-slim` for the runtime stage) and multi-stage layer ordering/caching strategy.
- Exact Playwright test file organization within `test/` (one file per scenario vs. grouped) and `docker-compose.test.yml` service naming.
- Whether `--build` is the only way to force a rebuild, or the script also detects source changes — PLAN.md already specifies "builds if not already built, or if `--build` passed," so this is largely fixed; minor implementation detail only.
- `.env.example` exact contents/comments — PLAN.md §5 already specifies the required variables; formatting/comment style is open.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Plan
- `planning/PLAN.md` §11 (Docker & Deployment — multi-stage Dockerfile shape, volume mount, start/stop script responsibilities) — authoritative for the Dockerfile and script contracts, EXCEPT the named-volume example is overridden by D-01 above (bind-mount, not `finally-data`)
- `planning/PLAN.md` §12 (Testing Strategy — E2E: separate `docker-compose.test.yml` with a Playwright container, `LLM_MOCK=true` default, key scenarios list) — authoritative for the E2E suite shape
- `planning/PLAN.md` §4 (Directory Structure — `db/` volume mount target, `test/` directory, `scripts/` directory, `Dockerfile`, `docker-compose.yml`, `.env`/`.env.example`)
- `planning/PLAN.md` §5 (Environment Variables — `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`, `.env` read from project root)
- `.planning/REQUIREMENTS.md` (INFRA-02, INFRA-03, INFRA-04, TEST-04) — full requirement text for this phase
- `.planning/ROADMAP.md` §Phase 5 — goal and success criteria (authoritative for verification)

### Prior Phase Artifacts
- `backend/app/main.py` — `load_dotenv(Path(__file__).resolve().parents[2] / ".env")` resolves relative to the app's own file location (parents[2] from `backend/app/main.py` = project root when run from a normal checkout, but resolves to whatever root the container places `app/` under — verify this resolves correctly inside the Docker image's directory layout)
- `backend/app/db/database.py` — `db_path()` reads `FINALLY_DB_PATH` env var override, defaulting to `db/finally.db` relative to project root; this is the mechanism the bind-mount (D-01) and any E2E scratch-DB isolation (D-03) both rely on
- `.planning/phases/04-ai-copilot/04-SECURITY.md` — Phase 4's threat register and accepted-risk pattern; Phase 5's own threat model (Docker image contents, `.env` handling in the container, E2E test credentials if any) should follow the same STRIDE-register format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/db/database.py` `db_path()` / `FINALLY_DB_PATH` — the exact seam the bind-mount and any E2E isolation should use; no new env-var plumbing needed
- `frontend/next.config.ts` (`output: 'export'`) — already produces `frontend/out`, verified working in this session's manual checkpoints (Phase 4); the Dockerfile's build stage just needs to run `npm run build` and copy `out/` into the runtime stage's static directory
- `backend/pyproject.toml` `[project.optional-dependencies] dev` — pytest/ruff live here, not a dependency group; any Docker build step or CI step that needs them must use `uv sync --extra dev` / `uv run --extra dev`, matching this session's established pattern (plain `uv run` silently falls through to a system Python)

### Established Patterns
- Backend: FastAPI app in `backend/app/main.py`, lazy DB init on startup (no separate migration step) — the Docker image needs no init step beyond starting uvicorn
- No CI/CD wiring exists for this project's own test suites yet (the `.github/workflows/*.yml` files present are unrelated Claude Code review workflows, not this project's CI) — out of scope for this phase per REQUIREMENTS.md, not raised in discussion

### Integration Points
- `Dockerfile` (new) — multi-stage: Node 20 stage builds `frontend/out`, Python 3.12 stage runs `uv sync` and copies `frontend/out` into a static directory FastAPI serves, per PLAN.md §11
- `scripts/start_mac.sh` / `stop_mac.sh` (new) and `scripts/start_windows.ps1` / `stop_windows.ps1` (new) — wrap `docker build`/`docker run` with the bind-mount (D-01), `--env-file .env`, port mapping, and auto-open browser (D-05)
- `docker-compose.yml` (new, convenience wrapper) — same bind-mount as the scripts, not a named volume (D-01)
- `test/docker-compose.test.yml` (new) — app container + Playwright container, isolated from the bind-mounted dev DB (D-03)

</code_context>

<specifics>
## Specific Ideas

No specific Dockerfile mockups or exact script output copy given — base image choices, layer ordering, and exact console output formatting are open to the planner/executor within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. A `--reset` flag was considered and explicitly declined in favor of documentation-only (D-02); this is a decision, not a deferred idea.

</deferred>

---

*Phase: 5-One-Command Launch*
*Context gathered: 2026-08-18*
