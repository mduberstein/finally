# FinAlly — Project Status vs. PLAN.md

_Assessment date: 2026-07-23_

## Summary

The project is at an **early stage**. Exactly one of the platform's major
components — the **market data subsystem** — is complete, tested, and reviewed.
Everything else described in `PLAN.md` (database, portfolio/watchlist/chat APIs,
LLM integration, frontend, Docker, scripts, E2E tests) is **not yet built**.

Rough completion estimate against the full spec: **~15%**.

## What Exists

### Market data subsystem — COMPLETE
Location: `backend/app/market/` (8 modules).

- `MarketDataSource` ABC with two implementations: `SimulatorDataSource`
  (GBM, correlated moves, shock events, default) and `MassiveDataSource`
  (Polygon.io REST poller, used when `MASSIVE_API_KEY` is set).
- `PriceCache` — thread-safe in-memory store with a version counter for SSE
  change detection.
- `create_market_data_source()` factory selecting source by env var.
- `create_stream_router()` — FastAPI SSE router for `GET /api/stream/prices`.
- **73 unit tests pass** (verified via `uv run pytest`); ~84% coverage.
- Rich terminal demo at `backend/market_data_demo.py`.

This fully satisfies PLAN.md sections 6 (Market Data) and the
`/api/stream/prices` endpoint from section 8.

### Backend project scaffolding — PARTIAL
- `backend/pyproject.toml` configured as a `uv` project (fastapi, uvicorn,
  numpy, massive, rich; dev: pytest, ruff). Lockfile present.

## What Is Missing

### Backend (section 3, 7, 8, 9)
- **No FastAPI application entrypoint.** There is no `main.py`/`app.py` that
  instantiates `FastAPI()`, wires the market data background task, mounts the
  stream router, or serves static frontend files. The SSE router exists but is
  never mounted into a running app.
- **No database layer.** No SQLite code, no `backend/db/` schema/seed logic,
  no lazy initialization. None of the tables (`users_profile`, `watchlist`,
  `positions`, `trades`, `portfolio_snapshots`, `chat_messages`) exist.
- **No REST endpoints** beyond the SSE stream. Missing:
  - `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`
  - `GET/POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`
  - `POST /api/chat`
  - `GET /api/health`
- **No portfolio/trade logic** — trade execution, P&L calculation, validation
  (insufficient cash/shares), portfolio snapshots.
- **No LLM integration.** No LiteLLM/OpenRouter code, no structured-output
  schema, no auto-execution of trades/watchlist changes, no `LLM_MOCK` mode.
  (The `cerebras` skill is available for this work.)

### Frontend (section 10) — NOT STARTED
- No `frontend/` directory at all. No Next.js project, no watchlist panel,
  charts, heatmap, positions table, trade bar, AI chat panel, or header.

### Infrastructure (sections 4, 11) — NOT STARTED
- No `Dockerfile`, no `docker-compose.yml`.
- No `scripts/` (`start_mac.sh`, `stop_mac.sh`, `start_windows.ps1`,
  `stop_windows.ps1`).
- No top-level `db/` volume-mount directory or `.gitkeep`.
- No `.env.example` committed (PLAN.md section 5 references it).

### Testing (section 12) — PARTIAL
- Backend market-data unit tests: present and passing.
- No backend tests for portfolio, LLM, or API routes (those features don't
  exist yet).
- No frontend unit tests.
- No `test/` directory, no Playwright E2E tests, no `docker-compose.test.yml`.

## Directory Structure vs. PLAN.md (section 4)

| Expected | Present |
|---|---|
| `frontend/` | Missing |
| `backend/` | Yes (market module only) |
| `backend/db/` | Missing |
| `planning/` | Yes |
| `scripts/` | Missing |
| `test/` | Missing |
| `db/` (volume target) | Missing |
| `Dockerfile` | Missing |
| `docker-compose.yml` | Missing |
| `.env.example` | Missing |

## Recommended Next Steps (incremental)

1. **Create the FastAPI app entrypoint** — instantiate `FastAPI()`, start the
   market data source + `PriceCache` on startup (lifespan), mount the existing
   stream router, add `GET /api/health`. This makes the completed market data
   work actually runnable end-to-end.
2. **Add the database layer** — SQLite schema, lazy init, and seed data for the
   six tables. Keep it a thin module.
3. **Build portfolio + watchlist REST endpoints** with trade execution and P&L
   logic; add unit tests.
4. **Add the LLM chat endpoint** using the `cerebras` skill, structured outputs,
   and `LLM_MOCK` mode for tests.
5. **Scaffold the Next.js frontend** (static export) and build UI incrementally,
   starting with the watchlist + live SSE prices.
6. **Add Dockerfile, scripts, and E2E tests** once the app runs end-to-end.

_Note: `backend/planning/` and `planning/REVIEW_BY_HOOK_COMMAND.md` are
untracked review artifacts produced by the Stop hook / review agents, not
product code._
