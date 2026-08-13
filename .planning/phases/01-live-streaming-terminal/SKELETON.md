# Walking Skeleton — FinAlly

**Phase:** 1
**Generated:** 2026-08-13

## Capability Proven End-to-End

A visitor opening `http://localhost:8000` sees the ten seeded watchlist tickers, read from a self-initializing SQLite database, streaming live prices that change on screen without a page reload.

This exercises every layer the rest of the project builds on: SQLite lazy init and seed, a FastAPI lifespan owning a background task, the existing `MarketFeed`/`PriceCache` pair, the SSE endpoint, the Next.js static export, and same-origin serving of that export by FastAPI.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI on Python 3.12, managed by `uv` | Fixed by `planning/PLAN.md`; already the shape of the existing `backend/` project and its 101-test market suite |
| Frontend framework | Next.js App Router, TypeScript, static export (`output: 'export'`) | Fixed by `planning/PLAN.md`. Static export is what allows one origin and one port, which is why no CORS configuration exists anywhere in this codebase |
| Serving model | FastAPI mounts the built export at `/` via `StaticFiles(html=True)`, registered after all `/api/*` routes | One container, one port, no reverse proxy. Route order is load-bearing: the mount is last so API paths are matched first |
| Data layer | SQLite at `db/finally.db`, raw `sqlite3`, no ORM | Fixed by `planning/PLAN.md`. Single-user, zero-config, volume-mountable. Schema lives in `backend/app/db/schema.sql` |
| Schema initialization | Lazy, additive, on lifespan startup — `CREATE TABLE IF NOT EXISTS` plus `INSERT OR IGNORE` seeds | No migration step and no manual setup. Additive-only is what makes restarting against an existing database non-destructive |
| Connection strategy | A new short-lived `sqlite3` connection per call | Simplest correct thing for a single-user local app; avoids cross-task connection state. Local reads are microseconds, so the feed's 2 Hz watchlist poll is not a load concern |
| Real-time transport | Server-Sent Events at `GET /api/stream/prices`, native `EventSource` on the client | Fixed by `planning/PLAN.md`. One-way push is all this app needs; the browser supplies reconnection for free |
| Market data | Existing `backend/app/market/` package, unchanged — `create_source()` → `MarketFeed` → `PriceCache` | Already built and tested. Phase 1 wires it in; it does not rebuild it |
| Feed lifecycle | One `MarketFeed`, started exactly once in the FastAPI lifespan with `fallback_factory=SimulatorSource`, stopped on shutdown | `MarketFeed.start()` raises on a second call. The explicit fallback factory is what makes the documented 401/403 auto-fallback live rather than inert |
| Price reads | Everything downstream reads `PriceCache.get()` / `.snapshot()`, never a source's `fetch()` | Documented anti-pattern in `.planning/codebase/ARCHITECTURE.md`; calling `fetch()` directly causes duplicate polling and lets components disagree about direction |
| Design system | shadcn CLI, base color `neutral`, with the dark terminal palette layered on the generated CSS variables | Fixed by `01-UI-SPEC.md`. Layering avoids a second, competing theme system |
| Auth | None — single hardcoded `user_id="default"` on every table | Fixed by `planning/PLAN.md`. The column exists so multi-user is a later feature, not a migration |
| Test runners | pytest (`uv run --extra dev pytest`) for the backend, vitest for the frontend | pytest is already established. `--extra dev` is required — a bare `uv run pytest` resolves a different pytest without `pytest-asyncio` |
| Deployment target | Documented local full-stack run in Phase 1; Docker packaging is Phase 5 | Keeps the skeleton thin. `INFRA-02`/`INFRA-03`/`INFRA-04` are explicitly Phase 5 requirements |
| Directory layout | `backend/app/{market,db}/` by concern, `frontend/{app,components,lib}/` per Next.js convention | Matches the existing backend structure; `lib/` holds pure, unit-tested logic separate from React components |

## Stack Touched in Phase 1

- [x] Project scaffold — Next.js + TypeScript + Tailwind + ESLint scaffold, shadcn init, vitest; backend project already exists
- [x] Routing — `GET /api/health`, `GET /api/watchlist`, `GET /api/stream/prices`, and `/` serving the static export
- [x] Database — real write (schema creation plus seeding ten watchlist rows and the $10,000 profile) and real read (`watchlist_tickers()` feeding both the API and the market feed)
- [x] UI — the watchlist grid consuming `/api/watchlist` and a live `EventSource`, with row selection, price flash, and the connection indicator
- [x] Deployment — documented local full-stack run: build the export, copy `frontend/out` to `backend/static`, run uvicorn on port 8000

## Full-Stack Run Command

Documented in `backend/README.md` by Plan 01:

1. `cd frontend && npm run build`, then copy `frontend/out` to `backend/static`
2. `cd backend && uv run --extra dev uvicorn app.main:app --port 8000`
3. Open `http://localhost:8000`

## Out of Scope (Deferred to Later Slices)

Explicitly not in the skeleton. This list exists so later phases do not re-litigate Phase 1's minimalism.

- Trading, cash, positions, P&L math, and the trade bar — Phase 2. The `positions` and `trades` tables are created but never written this phase.
- Portfolio heatmap, P&L chart, sparklines, and the main chart area — Phase 3. The `portfolio_snapshots` table is created but never written.
- Watchlist add/remove and click-to-load-chart — Phase 3 (`WATCH-02`, `WATCH-03`, `WATCH-05`). Row selection state exists in Phase 1 because the UI-SPEC reserves the accent stripe for it, but the selected ticker has no destination yet.
- The AI chat panel and all LLM integration — Phase 4. The `chat_messages` table is created but never written.
- Tablet-width responsive behavior (`UI-04`) and the full multi-panel desktop layout (`UI-02`) — Phase 3. Phase 1 targets desktop at 1280px and wider.
- Dockerfile, compose file, start/stop scripts, and volume persistence testing — Phase 5.
- The Playwright E2E suite — Phase 5. Frontend unit coverage beyond the pure helpers is `TEST-03` in Phase 3.
- Real Massive market data — permanently out of scope for this build; `MassiveSource` remains in the tree as the alternate implementation but is never exercised.

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering the architectural decisions above:

- **Phase 2** — buy and sell at live cache prices; cash, positions, and total value respond
- **Phase 3** — heatmap, P&L chart, sparklines, main chart, and watchlist curation in the full terminal layout
- **Phase 4** — the AI copilot that analyzes the portfolio and executes trades and watchlist changes through natural language
- **Phase 5** — one Docker image, start/stop scripts, persistent volume, and a passing Playwright E2E suite
