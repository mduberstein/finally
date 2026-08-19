---
phase: 05-one-command-launch
verified: 2026-08-19T14:30:00Z
status: passed
score: 25/25 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: One-Command Launch Verification Report

**Phase Goal:** Anyone can run the whole workstation with one command and keep their data across restarts
**Verified:** 2026-08-19T14:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

All claims below were re-proven independently against the current codebase (post CR-01 fix, commit `f3c7dd5`) — not taken from SUMMARY.md. Docker builds, container runs, script executions, persistence cycles, and the full Playwright E2E suite were all executed live in this session, not inferred from prior reports.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docker build -t finally .` from the current source produces one image serving the whole terminal on port 8000 (INFRA-02) | VERIFIED | Independent fresh `docker build` succeeded end-to-end (frontend export + backend sync + runtime stage); confirmed no cache reuse of any stale image |
| 2 | `curl -sf http://localhost:8000/api/health` returns HTTP 200 JSON (INFRA-02) | VERIFIED | `{"status":"ok"}` returned from a freshly built/run container |
| 3 | `curl -s http://localhost:8000/` returns the built Next.js export containing "FinAlly" — frontend actually mounted (INFRA-02) | VERIFIED | `grep -o FinAlly` matched on the served root page |
| 4 | Container writes SQLite to host's `db/finally.db` via `./db:/app/db` bind mount, same file dev `uv run uvicorn` uses (INFRA-04, D-01) | VERIFIED | Host-side file appeared and grew at the bind-mounted path immediately after container start; `FINALLY_DB_PATH=/app/db/finally.db` env var confirmed in Dockerfile |
| 5 | Cash, positions, trade history, watchlist, chat history survive `docker stop` + `docker start` (INFRA-04) | VERIFIED | Bought 1 AAPL (cash 10000.0 -> 9810.03), `docker stop`/`docker start`, re-GET `/api/portfolio` returned identical cash and position row |
| 6 | Image contains no `.env`/credential; secrets only via `--env-file` at run time (T-05-01) | VERIFIED | `docker run --entrypoint sh ... test ! -e /app/.env` succeeded; `.dockerignore` excludes `.env`/`.env.*` |
| 7 | Container process runs as non-root and can still write the bind-mounted `db/` (T-05-02) | VERIFIED | `docker exec ... id` -> `uid=999(finally) gid=999(finally)`; db file was written successfully as that user |
| 8 | Startup output names the resolved absolute SQLite path and whether it pre-existed, so a broken/absent mount is visible in logs | VERIFIED | `docker logs` showed `Created and seeded a new database at /app/db/finally.db` on first start and `Opened existing database at /app/db/finally.db` on restart |
| 9 | `.env.example` documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` exactly per PLAN.md section 5 | VERIFIED | Read `.env.example` directly (sandbox override required) — matches PLAN.md section 5 verbatim |
| 10 | Restart after an unclean stop (`docker kill`/SIGKILL) does not corrupt the DB; journal recovery leaves it consistent, pre-kill state intact (backstop truth) | VERIFIED | `docker kill` mid-session then `docker start`: `PRAGMA integrity_check` -> `ok`; portfolio state (cash 9810.03, 1 AAPL) intact after the unclean restart |
| 11 | `scripts/start_mac.sh` from a clean checkout builds if missing, starts one container, waits for `/api/health`, opens the browser (INFRA-03, D-05) | VERIFIED | Executed the real script (not just underlying docker commands) against a simulated clean checkout (moved aside `db/` and `.env`): built the image, created `.env` from the template, started the container, health-polled, printed ready message and invoked `open` |
| 12 | Running `scripts/start_mac.sh` a second time while running reports running and exits 0, no second container (INFRA-03) | VERIFIED | Second run printed "finally is already running..." exit 0; `docker ps -a` showed exactly one container named `finally` |
| 13 | Running `scripts/stop_mac.sh` stops the container; running it again reports nothing running and exits 0 (INFRA-03) | VERIFIED | First stop: "Stopped finally...", exit 0. Second stop: "finally is not running.", exit 0. Container still present (not removed), status Exited |
| 14 | After stop then start via the scripts, portfolio data is still there; stop path never removes the container or touches the host DB (INFRA-04, D-02) | VERIFIED | Container preserved across stop/start cycle (status Exited -> re-started, not re-created); `stop_mac.sh` never calls `docker rm` (confirmed by reading the script) |
| 15 | `docker compose up` brings up the same app with the same host bind mount `./db:/app/db`, not a named volume (INFRA-03, D-01) | VERIFIED | `docker-compose.yml` volumes: `./db:/app/db`, matching the scripts exactly |
| 16 | `docker compose up` succeeds on a clean checkout with no `.env` (env-file declared non-required) | VERIFIED | `docker-compose.yml` uses long-form `env_file: [{path: .env, required: false}]` |
| 17 | `scripts/start_mac.sh` on a checkout with no `.env` seeds one from `.env.example`, tells the user the OpenRouter key must be filled in, continues (INFRA-03) | VERIFIED | Directly observed: "Created .env from .env.example. Add your OpenRouter API key before AI chat will work." and the run continued to a healthy container |
| 18 | `start_windows.ps1`/`stop_windows.ps1` mirror the mac scripts' Docker CLI logic and carry a header stating they were never verified on Windows (D-04) | VERIFIED | Read both files: same `docker image inspect`/`build`/`inspect -f`/`start`/`run` (start) and `inspect -f`/`stop` (stop) subcommand sequence as the bash scripts; both carry the exact disclosure header |
| 19 | The published port is loopback-only on every launch path (T-05-04) | VERIFIED | `grep -c "127.0.0.1:8000:8000"` returns exactly 1 in each of `scripts/start_mac.sh`, `scripts/start_windows.ps1`, `docker-compose.yml`; no `0.0.0.0:8000` publish found anywhere |
| 20 | README documents the one-command launch, the bind mount, and manual reset; no longer instructs the named volume from PLAN.md section 11 (D-01, D-02) | VERIFIED | Read README.md Quick Start — mac/Linux/Windows/compose paths, bind-mount persistence note, documentation-only reset (`rm db/finally.db`), no mention of a named volume |
| 21 | No script offers a reset/wipe flag; reset is documentation only (D-02) | VERIFIED | No `--reset`/`--wipe`/`--clean` flag in any script; README's reset procedure is manual (`rm db/finally.db`) |
| 22 | `docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright` builds, runs the app, runs Playwright against it, exits with the suite's code (TEST-04) | VERIFIED | Ran this exact command live: build succeeded, all 5 specs ran, `playwright-1 exited with code 0`, compose reported exit 0 |
| 23 | Playwright container reaches the app via compose service DNS (`http://app:8000`), not localhost (TEST-04) | VERIFIED | `test/docker-compose.test.yml` sets `BASE_URL=http://app:8000`; `playwright.config.ts` resolves it via `getent` for Chromium's HTTPS-Upgrades throttle |
| 24 | Test app container runs with `LLM_MOCK=true`, deterministic/offline AI-chat scenarios (TEST-04, D-03) | VERIFIED | `docker compose -f test/docker-compose.test.yml config` shows `LLM_MOCK: "true"`; the AI-chat spec passed deterministically against the mock |
| 25 | Test app container never receives the OpenRouter credential and never reads the repo-root env file; SQLite is entirely its own, never touches host `db/` (T-05-13, D-03) | VERIFIED | `docker compose config \| grep -c OPENROUTER_API_KEY` = 0; no `env_file` directive in `test/docker-compose.test.yml`; no `volumes:` on the app service — ephemeral writable-layer DB |

**Score:** 25/25 truths verified (0 present-but-behavior-unverified)

*(Additional must-haves from the four plans — fresh-start scenario details, all five specs passing in filename order under one worker, no data-testid/waitForTimeout usage, exact-cash-assertion prohibition, gitignored test artifacts — were also checked directly; see Behavioral Spot-Checks / Probe Execution / Anti-Patterns sections below.)*

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Dockerfile` | 3-stage build serving both frontend+backend on 8000, non-root | VERIFIED | Read in full; `node:22-slim` -> `uv:python3.12-trixie-slim` -> `python:3.12-slim`, `USER finally`, `EXPOSE 8000` |
| `.dockerignore` | Excludes secrets, VCS, host artifacts | VERIFIED | Excludes `.env*` (negates `.env.example`), `.git`, `.venv`, `node_modules`, `db/finally.db`, planning dirs |
| `.env.example` | Documents 3 env vars per PLAN.md §5 | VERIFIED | Matches PLAN.md section 5 verbatim |
| `backend/app/db/database.py` | Lazy init + startup visibility log | VERIFIED | `initialize()` logs resolved path + existed/new via `logging.getLogger("uvicorn.error")` |
| `docker-compose.yml` | Convenience wrapper, bind mount, loopback port, optional `.env` | VERIFIED | One `app` service, all three properties present |
| `scripts/start_mac.sh` | Idempotent launcher | VERIFIED | Executed live; build-if-missing, `.env` seed, state-aware start, health poll, browser open, includes CR-01's `xdg-open` fallback |
| `scripts/stop_mac.sh` | Idempotent stopper, preserves container/db | VERIFIED | Executed live; checks `State.Running`, never calls `docker rm` |
| `scripts/start_windows.ps1` / `stop_windows.ps1` | PowerShell mirrors, D-04 disclosure | VERIFIED | Read in full; 1:1 docker-subcommand parity with bash scripts, disclosure header present |
| `README.md` | Corrected Quick Start | VERIFIED | Bind-mount Quick Start, no named-volume instruction |
| `test/docker-compose.test.yml` | Isolated 2-service E2E harness | VERIFIED | No volumes, no ports, no env_file on `app`; `LLM_MOCK: "true"`; DNS-based `BASE_URL` |
| `test/playwright.config.ts` | E2E config | VERIFIED | Single worker, `baseURL` from `BASE_URL` env |
| `test/package.json` / `package-lock.json` / `.gitignore` | Playwright deps + gitignore | VERIFIED | Present; `git status --porcelain test/` clean (no untracked build noise) |
| `test/e2e/01-fresh-start.spec.ts` through `05-sse-reconnect.spec.ts` | 5 scenario files | VERIFIED | All 5 present and pass in one live run |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Dockerfile runtime | `database.py db_path()` | `ENV FINALLY_DB_PATH=/app/db/finally.db` | WIRED | Confirmed in Dockerfile and `db_path()` reads `os.getenv("FINALLY_DB_PATH")` |
| Dockerfile runtime | `main.py` static mount | `ENV FINALLY_STATIC_DIR=/app/static` | WIRED | Confirmed `main.py` reads `os.getenv("FINALLY_STATIC_DIR", ...)`; served root page contains "FinAlly" |
| Dockerfile frontend stage | Dockerfile runtime stage | `COPY --from=frontend-builder /app/frontend/out /app/static` | WIRED | Confirmed in Dockerfile line 44 |
| host `./db` | container `/app/db` | bind mount, never a named volume | WIRED | Confirmed in Dockerfile-adjacent scripts and compose; verified live persistence |
| `scripts/start_mac.sh` | `finally` image | `docker build` when tag absent or `--build` passed | WIRED | Exercised live (build-if-missing behavior observed) |
| `scripts/start_mac.sh` | `GET /api/health` | bounded readiness poll (30x1s), never a fixed sleep | WIRED | Confirmed in script source and behavior |
| `test/docker-compose.test.yml` playwright | app | `BASE_URL=http://app:8000` | WIRED | Confirmed and exercised live |
| `test/e2e/04-ai-chat.spec.ts` | `frontend/components/ChatActionCard.tsx` via `lib/chat.ts actionCardText()` | `Bought`/`Sold` text pattern | WIRED | Traced: `actionCardText()` produces `"Bought 2 AAPL"`, spec asserts `/Bought 2 AAPL/`; spec passed live |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Fresh image builds from current source | `docker build -t finally-verify .` | Build succeeded, image produced | PASS |
| Container serves API + frontend on 8000 | `curl /api/health`, `curl / \| grep FinAlly` | `{"status":"ok"}`, "FinAlly" found | PASS |
| Non-root user | `docker exec ... id` | `uid=999(finally)` | PASS |
| No `.env` in image | `docker run --entrypoint sh ... test ! -e /app/.env` | no `.env` present | PASS |
| Clean stop/start preserves state | buy trade -> stop -> start -> re-GET portfolio | cash and position identical before/after | PASS |
| Unclean SIGKILL recovery | `docker kill` -> `docker start` -> `PRAGMA integrity_check` | `ok`, state intact | PASS |
| `start_mac.sh` idempotency | run twice | 2nd run: "already running", exit 0, 1 container | PASS |
| `stop_mac.sh` idempotency | run twice | 2nd run: "not running", exit 0, container not removed | PASS |
| No data-testid in specs/components | `grep -rn data-testid test/e2e frontend/components frontend/app` | no matches | PASS |
| No `waitForTimeout` in specs | `grep -rn waitForTimeout test/e2e` | no matches | PASS |
| Cash assertions after trade are directional | inspect `03-trade.spec.ts` | `toBeLessThan`/`toBeGreaterThan`, no exact-value assertion | PASS |
| No emoji in script/README output | `grep -P "[emoji ranges]"` | none found | PASS |
| No TODO/FIXME/XXX/TBD/HACK/PLACEHOLDER markers | grep across all phase artifacts | none found | PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| Playwright E2E suite (TEST-04) | `docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright` (run live, from repo root) | 5 specs passed in numeric order (01 fresh-start, 02 watchlist, 03 trade, 04 ai-chat, 05 sse-reconnect), `5 passed (8.5s)`, exit code 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INFRA-02 | 05-01 | Single multi-stage Dockerfile builds Next.js export + FastAPI into one image on port 8000 | SATISFIED | Independent fresh build + serve confirmed |
| INFRA-03 | 05-02 | `docker-compose.yml` and `scripts/start_mac.sh`/`stop_mac.sh` (+ Windows) launch/stop with one command | SATISFIED | Scripts executed live, idempotency proven both directions |
| INFRA-04 | 05-01, 05-02 | SQLite persists across container restarts via bind mount at `db/finally.db` | SATISFIED | Clean and unclean (SIGKILL) restart persistence proven live |
| TEST-04 | 05-03, 05-04 | Playwright E2E suite covers fresh start, add/remove ticker, buy/sell, AI chat trade, SSE reconnection | SATISFIED | All 5 specs run and passed live in one compose invocation |

No orphaned requirements: REQUIREMENTS.md traceability maps only INFRA-02, INFRA-03, INFRA-04, TEST-04 to Phase 5, and all four are claimed and satisfied across the four plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `Dockerfile` | 18, 38 | Builder stage pinned to Debian trixie (`uv:python3.12-trixie-slim`), runtime stage on floating `python:3.12-slim` tag — potential glibc mismatch on a future base-image rebuild | Warning (carried from 05-REVIEW.md WR-01, unfixed) | Does not block current one-command launch goal; is a future-rebuild risk, not an immediate defect. Not a blocker for this phase's stated goal. |
| `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` | header | Never executed on Windows (self-disclosed, D-04) | Warning (documented limitation, carried from 05-REVIEW.md WR-02) | Explicitly out of scope per D-04 — a known, accepted limitation, not a silent gap |

The one prior CRITICAL finding (CR-01: `scripts/start_mac.sh` crashing on Linux due to macOS-only `open` with no fallback) was independently re-verified as fixed: the current script includes the `command -v open ... elif command -v xdg-open ...` fallback chain (commit `f3c7dd5`), read directly from the file in this session.

### Human Verification Required

None. All must-haves were independently verified through direct code execution (fresh Docker builds, live script runs, live E2E suite run) rather than SUMMARY.md claims alone.

### Gaps Summary

No gaps. All 25 must-haves across the phase's four plans were independently re-proven in this verification session:

- A fresh `docker build` (not reusing any prior image) produces a working, non-root, secret-free image serving both the API and the frontend on port 8000.
- SQLite persistence was proven through both a clean `docker stop`/`docker start` cycle and an unclean `docker kill` (SIGKILL) cycle, with `PRAGMA integrity_check` reporting `ok` and portfolio state intact in both cases.
- `scripts/start_mac.sh` and `scripts/stop_mac.sh` were executed directly (not just their underlying docker primitives) against a simulated clean checkout, proving build-if-missing, `.env` auto-seeding, health-gated readiness, and full start/start/stop/stop idempotency.
- The previously-flagged CR-01 critical (macOS-only `open` crashing on Linux) is confirmed fixed in the current source.
- The full 5-scenario Playwright E2E suite was run live via the documented one-command compose invocation and passed with exit code 0, with credential and database isolation independently confirmed via `docker compose config` and `docker inspect`.

Two warnings remain from the prior code review (Dockerfile base-image pinning risk, unverified Windows scripts) — both are non-blocking: the base-image warning is a future-rebuild risk rather than a present defect, and the Windows-script limitation is an explicit, documented, accepted scope boundary (D-04), not a silent gap.

---

_Verified: 2026-08-19T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
