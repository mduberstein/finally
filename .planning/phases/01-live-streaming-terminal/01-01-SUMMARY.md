---
phase: 01-live-streaming-terminal
plan: 01
subsystem: infra
tags: [sqlite, fastapi, sse, nextjs, shadcn, tailwind, walking-skeleton]

requires: []
provides:
  - "backend/app/db/ — lazy SQLite init/seed additive to an existing database"
  - "backend/app/main.py — FastAPI app with lifespan-wired MarketFeed/PriceCache, /api/health, /api/watchlist, SSE router, conditional static mount"
  - "frontend/ — Next.js static-export project with shadcn (base color neutral) initialized"
  - "frontend/lib/types.ts, usePriceStream.ts — the PriceTick/ConnectionStatus/WatchlistEntry contract and SSE hook every later frontend plan builds on"
affects: [02-portfolio-and-trading, 03-watchlist-curation, 04-ai-copilot, 05-docker-deployment]

actuals:
  tokens: 32000
  tasks: 2
  commits: 2

tech-stack:
  added: [next@16.3.1, react@19.2.8, tailwindcss@4, shadcn@4.18.0, lucide-react, eslint-config-next]
  patterns:
    - "Additive-only SQLite init: every CREATE is IF NOT EXISTS, every seed INSERT is OR IGNORE"
    - "Module-level PriceCache singleton (stream router binds to it at import time; lifespan constructs the feed around it)"
    - "Static mount registered last and only when the directory exists, so /api/* always wins and the backend test suite runs without a frontend build"
    - "usePriceStream merges SSE ticks into state by ticker, never replaces the whole map"

key-files:
  created:
    - backend/app/db/schema.sql
    - backend/app/db/database.py
    - backend/app/db/__init__.py
    - backend/app/main.py
    - backend/tests/test_db.py
    - backend/tests/test_app.py
    - backend/.gitignore
    - db/.gitkeep
    - frontend/next.config.ts
    - frontend/lib/types.ts
    - frontend/lib/usePriceStream.ts
    - frontend/app/page.tsx
    - frontend/components.json
  modified:
    - .gitignore

key-decisions:
  - "Static directory resolved against the repo root (Path(__file__).resolve().parents[2]) rather than process cwd, so FINALLY_STATIC_DIR's default 'backend/static' means the same directory whether uvicorn starts from the repo root or from inside backend/"
  - "shadcn CLI v4.18 changed -b to mean component-library primitive (radix/base/aria), not base color; base color neutral is now the -d/--defaults preset default, confirmed in the generated components.json"
  - "FastAPI's include_router() now wraps routes in a lazy _IncludedRouter with no .path attribute; test_app.py's route-registration check walks original_router.routes to find the wrapped route"

requirements-completed: [MARKET-01, MARKET-04, WATCH-01, INFRA-01]

coverage:
  - id: D1
    description: "Package legitimacy checkpoint (Task 1) — human confirms next/react/typescript/tailwindcss/shadcn/lucide-react/eslint packages before first install"
    verification: []
    human_judgment: true
    rationale: "Already reviewed and approved by the human before this execution run began (see checkpoint_already_resolved context handed to this executor); gate="blocking-human" so it is never auto-approved, and it was not — a real human approval preceded this run."
  - id: D2
    description: "SQLite schema self-seeds additively; restart preserves mutated data; missing tables are recreated without discarding existing rows"
    requirement: "MARKET-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_db.py#TestInitialize"
        status: pass
      - kind: unit
        ref: "backend/tests/test_app.py#TestLifespan"
        status: pass
      - kind: other
        ref: "grep -c 'CREATE TABLE IF NOT EXISTS' backend/app/db/schema.sql == 6"
        status: pass
      - kind: other
        ref: "grep -Eic 'drop table|delete from|truncate' backend/app/db/database.py == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "FastAPI app wires MarketFeed+PriceCache via lifespan (fallback_factory=SimulatorSource, start-once) and serves /api/health, /api/watchlist, /api/stream/prices"
    requirement: "MARKET-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_app.py#TestHealth,TestWatchlist,TestStreamRoute,TestLifespan"
        status: pass
      - kind: other
        ref: "grep -c 'fallback_factory=SimulatorSource' backend/app/main.py == 1"
        status: pass
      - kind: integration
        ref: "curl smoke test: /api/health 200, /api/watchlist 10 entries, /api/stream/prices emits >=2 JSON data: frames, / returns HTML, two 4s-apart watchlist reads differ"
        status: pass
    human_judgment: false
  - id: D4
    description: "Browser at localhost:8000 shows the ten watchlist tickers with prices visibly changing without a page reload (Task 2's embedded <human-check>)"
    requirement: "WATCH-01"
    verification:
      - kind: integration
        ref: "automated curl smoke test proves the underlying data path (see D3); the pixel-level 'ticker rows visibly changing' judgment call is unautomated"
        status: pass
    human_judgment: true
    rationale: "workflow.human_verify_mode = end-of-phase (config.json) — Task 2's <verify><human-check> is deferred to the phase-level UAT batch rather than a mid-flight checkpoint, per the standard human-verify suppression policy. The automated <verify><automated> half of Task 2 (pytest, ruff, npm build) already ran and passed above."

duration: 20min
completed: 2026-08-14
status: complete
---

# Phase 1 Plan 1: Live Streaming Terminal — Walking Skeleton Summary

**Lazily-seeding SQLite schema + FastAPI lifespan wiring of the existing MarketFeed/PriceCache into a running app, plus a Next.js static-export frontend (shadcn/Tailwind) that streams the ten default tickers live via SSE.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 (Task 1 checkpoint pre-approved by the human before this run; Task 2 executed in full)
- **Files modified:** 26 (9 backend, 1 root .gitignore, ~24 frontend scaffold files including generated shadcn/Next.js boilerplate)

## Accomplishments

- Six-table SQLite schema (`users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`), every statement `CREATE TABLE IF NOT EXISTS`, with additive-only seeding (`INSERT OR IGNORE`) verified to survive a mutated `cash_balance` across a second `initialize()` call and to recreate a dropped table without discarding rows in surviving tables
- FastAPI app (`backend/app/main.py`) wires the already-built `MarketFeed`/`PriceCache`/`create_source()` into a real lifespan, passing `fallback_factory=SimulatorSource` so the documented 401/403 fallback is live; serves `/api/health`, `/api/watchlist` (nullable price fields for not-yet-ticked tickers), the existing `/api/stream/prices` SSE router, and a static mount registered last (only when the directory exists)
- Next.js 16 static-export frontend scaffolded via `create-next-app` + `npx shadcn@latest init` (base color neutral, confirmed in `components.json`), with `frontend/lib/types.ts` (the `PriceTick`/`ConnectionStatus`/`WatchlistEntry` contract) and `frontend/lib/usePriceStream.ts` (an `EventSource` hook merging ticks by ticker, never replacing the whole map)
- `frontend/app/page.tsx` renders one row per watchlist ticker, live SSE price taking precedence over the initial `/api/watchlist` fetch, em dash for not-yet-ticked cells, dark background, and an explicit "prices shown are generated by a market simulator" disclosure line (project-wide prohibition, not decoration)
- Full-stack smoke test passed: `/api/health` returns `ok`, `/api/watchlist` returns exactly 10 tickers, `/api/stream/prices` emits parseable JSON `price` frames, `/` serves the built HTML, and two `/api/watchlist` reads four seconds apart differ — proving the feed is actually writing into the cache

## Task Commits

1. **Task 1: Package legitimacy verification before first npm install** — pre-approved by the human before this execution run (see checkpoint_already_resolved context); no code changes, no commit for this task itself
2. **Task 2: End-to-end live price — seeded SQLite through FastAPI to a streaming browser page** — `052715d` (feat: db + app layer) and `042c0b8` (feat: frontend scaffold)

_No plan-metadata commit in this worktree — the orchestrator commits STATE.md/ROADMAP.md centrally after merging all wave worktrees._

## Files Created/Modified

- `backend/app/db/schema.sql` — six-table schema, all `CREATE TABLE IF NOT EXISTS`
- `backend/app/db/database.py` — `db_path()`, `connect()`, `initialize()`, `watchlist_tickers()`, additive seeding only
- `backend/app/db/__init__.py` — re-exports matching `app/market/__init__.py` style
- `backend/app/main.py` — lifespan, `cache` singleton, `/api/health`, `/api/watchlist`, SSE router inclusion, conditional static mount
- `backend/tests/test_db.py` — fresh-init, restart-preserves-mutation, missing-table-recreated coverage
- `backend/tests/test_app.py` — health/watchlist/route-registration/lifespan coverage (with a route-walking helper for FastAPI's newer lazy `_IncludedRouter`)
- `backend/.gitignore` — ignores `static/` (build output, not source)
- `db/.gitkeep` — volume-mount target tracked in the repo
- `frontend/next.config.ts` — `output: 'export'`, `images.unoptimized`, `trailingSlash`
- `frontend/lib/types.ts` — `PriceTick`, `ConnectionStatus`, `WatchlistEntry`
- `frontend/lib/usePriceStream.ts` — `usePriceStream()` SSE hook
- `frontend/app/page.tsx` — watchlist grid consuming both `/api/watchlist` and the live stream
- `frontend/components.json`, `frontend/app/globals.css`, `frontend/components/ui/button.tsx` — shadcn init output
- `.gitignore` (root) — added `db/finally.db`; added `!frontend/lib/` to unshadow the pre-existing Python-packaging `lib/` ignore rule from the new Next.js `frontend/lib/` convention directory

## Decisions Made

- Resolved `FINALLY_STATIC_DIR`'s default against the repo root rather than the process working directory, so the mount behaves identically regardless of whether uvicorn is started from the repo root or from `backend/`
- Adapted to the shadcn CLI's v4.18 flag change (`-b` now selects a component-library primitive, not a base color); confirmed base color neutral is already the `-d`/`--defaults` preset default by inspecting the generated `components.json`
- Adapted the route-registration test to FastAPI's newer lazy `_IncludedRouter` wrapper (`app.include_router()` no longer flattens routes directly into `app.routes` in this version)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reworded prose comments that were false-triggering the plan's own acceptance-criteria greps**
- **Found during:** Task 2 acceptance-criteria verification loop
- **Issue:** `schema.sql`'s header comment literally contained the phrase "CREATE TABLE IF NOT EXISTS" (making the table-count grep return 7, not 6), and `database.py`'s module docstring used the word "truncates" (a substring match for the destructive-SQL grep's `truncate` pattern, making it return 1, not 0)
- **Fix:** Reworded both comments to describe the same behavior without using the literal grepped phrases
- **Files modified:** `backend/app/db/schema.sql`, `backend/app/db/database.py`
- **Verification:** Both greps re-run and now return the values the plan's acceptance criteria specify (6 and 0)
- **Committed in:** `052715d`

**2. [Rule 3 - Blocking] Fixed `next.config.ts` quote style to satisfy the plan's literal grep**
- **Found during:** Task 2 acceptance-criteria verification loop
- **Issue:** Wrote `output: "export"` (double quotes); the acceptance criterion greps for the single-quoted literal `output: 'export'`
- **Fix:** Changed to single quotes
- **Files modified:** `frontend/next.config.ts`
- **Verification:** `grep -c "output: 'export'" frontend/next.config.ts` returns 1; `npm run build` still succeeds
- **Committed in:** `042c0b8`

**3. [Rule 3 - Blocking] Un-shadowed `frontend/lib/` from a pre-existing root `.gitignore` rule**
- **Found during:** Staging the frontend commit
- **Issue:** The repo's root `.gitignore` (inherited from a standard Python template) contains a bare `lib/` pattern intended for Python packaging build output, which also matched `frontend/lib/` — silently excluding `types.ts` and `usePriceStream.ts` from staging
- **Fix:** Added `!frontend/lib/` after the existing rule to restore tracking for the Next.js convention directory
- **Files modified:** `.gitignore`
- **Verification:** `git check-ignore -v frontend/lib/*.ts` now reports no match; `git status` shows the files staged
- **Committed in:** `042c0b8`

**4. [Rule 1 - Bug] Fixed the route-registration test for FastAPI's lazy `_IncludedRouter`**
- **Found during:** Task 2, first `pytest` run
- **Issue:** `app.include_router(create_stream_router(cache))` in this FastAPI version wraps the sub-router in a lazy `_IncludedRouter` object with no `.path` attribute, so `{route.path for route in app.routes}` raised `AttributeError`
- **Fix:** Added a small recursive `_registered_paths()` helper in the test that descends into `original_router.routes` when present
- **Files modified:** `backend/tests/test_app.py`
- **Verification:** `test_stream_prices_route_registered` passes
- **Committed in:** `052715d`

---

**Total deviations:** 4 auto-fixed (3 blocking, 1 bug)
**Impact on plan:** All four were required to make the plan's own stated acceptance criteria pass, or to avoid silently losing source files to an unrelated pre-existing ignore rule. No scope creep — no functionality was added beyond what the plan specified.

## Issues Encountered

- `uv sync` initially failed with `Failed to initialize cache at /Users/mdub/.cache/uv: Operation not permitted` — a sandbox filesystem restriction unrelated to the code; resolved by running the command with the sandbox override, per the standard sandbox-failure protocol (not a deviation from the plan's code).

## User Setup Required

None — no external service configuration required. `MASSIVE_API_KEY` and `OPENROUTER_API_KEY` remain unused by this phase's code paths.

## Next Phase Readiness

- The database schema is complete for the whole project (all six tables), so Phase 2 (portfolio/trading) only needs to add routes and business logic against `positions` and `trades` — no migration needed
- `frontend/lib/types.ts` establishes the `PriceTick`/`ConnectionStatus`/`WatchlistEntry` contract that Plans 02-04 build against without renaming
- Full dark-terminal theming (beyond the plain dark background added this plan) is explicitly Plan 02's job, per the UI-SPEC
- The Task 2 `<human-check>` (visual confirmation that ticker rows update live in a browser) is deferred to end-of-phase UAT per `workflow.human_verify_mode = end-of-phase`; the automated smoke test already proves the underlying data path works end-to-end

## Self-Check: PASSED

- `backend/app/db/schema.sql`, `database.py`, `__init__.py` — FOUND
- `backend/app/main.py` — FOUND
- `backend/tests/test_db.py`, `test_app.py` — FOUND
- `frontend/next.config.ts`, `lib/types.ts`, `lib/usePriceStream.ts`, `app/page.tsx`, `components.json` — FOUND
- `db/.gitkeep` — FOUND
- Commit `052715d` — FOUND in `git log`
- Commit `042c0b8` — FOUND in `git log`
- `cd backend && uv run --extra dev pytest -q` — 111 passed
- `cd backend && uv run ruff check app/ tests/` — all checks passed
- `cd frontend && npm run build` — succeeded, `frontend/out/index.html` exists
- Full-stack curl smoke test (health/watchlist/stream/root/two-reads-differ) — all passed

---
*Phase: 01-live-streaming-terminal*
*Completed: 2026-08-14*
