# Phase 2: Trading & Portfolio - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

A user can buy and sell shares of a watchlisted ticker at the live market price via a trade bar, with instant fill, no fees, and no confirmation dialog. Cash and positions update immediately; invalid trades (insufficient cash, overselling) are rejected with a clear error. A positions table shows ticker, quantity, avg cost, current price, unrealized P&L, and % change. Total portfolio value (cash + positions) updates live in the header. Trade history is recorded append-only. Portfolio heatmap and P&L-over-time chart are explicitly **out of scope** — those are PORT-08/PORT-09, Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Trade Execution
- **D-01:** Trades fill at a server-authoritative price — the backend reads `PriceCache.get(ticker)` at the moment the trade is processed, never a client-supplied/displayed price. — **Reversibility:** costly — changing this later means renegotiating the trade API contract's trust boundary (client currently can't influence fill price at all; adding client-price trust would be a security-relevant change).
- **D-02:** Only tickers currently on the watchlist are tradable. The trade bar (or backend validation) rejects tickers with no live price in `PriceCache`, since watchlist add/remove doesn't ship until Phase 3. — **Reversibility:** reversible — Phase 3 can lift this restriction once arbitrary-ticker price lookup exists.
- **D-03:** Trade quantities are whole shares only in the trade bar's input validation. The `positions`/`trades` schema already stores quantity as `REAL` (unchanged) to support fractional LLM-initiated trades in Phase 4 without a migration. — **Reversibility:** reversible — purely a frontend/API input-validation choice; the schema doesn't need to change to lift this later.

### Error Handling
- **D-04:** Rejected trades (insufficient cash, overselling) show an inline error near the trade bar (not a toast or banner), clearing on the next valid input. — **Reversibility:** reversible.

### Claude's Discretion
- Exact positions-table row behavior when a sell reduces a position to zero (remove row immediately vs. brief "closed" transition) — no strong preference expressed; use judgment, default to removing the row since PORT-03 says "reduces or removes the position."
- Portfolio total value's exact update cadence in the header (every SSE tick vs. debounced) — follow the existing price-flash/SSE cadence pattern from Phase 1 unless a reason emerges to diverge.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Plan
- `planning/PLAN.md` §7 (Database schema: `positions`, `trades`, `portfolio_snapshots` — already created by Phase 1's lazy-init) — trade/position persistence contract
- `planning/PLAN.md` §8 (API Endpoints: `POST /api/portfolio/trade`, `GET /api/portfolio`, `GET /api/portfolio/history`) — endpoint shapes to implement
- `.planning/REQUIREMENTS.md` (PORT-01..07, PORT-10, UI-03, TEST-01) — full requirement text for this phase
- `.planning/ROADMAP.md` §Phase 2 — goal and success criteria (authoritative for verification)

### Prior Phase Artifacts
- `.planning/phases/01-live-streaming-terminal/01-SECURITY.md` — Phase 1's SQL-injection mitigation pattern (`?` placeholders, `INSERT OR IGNORE`, no destructive SQL) — Phase 2's trade/position writes must follow the same pattern
- `backend/app/db/database.py` — existing lazy-init/seed pattern and connection handling (`contextlib.closing`) to extend for positions/trades reads+writes
- `backend/app/main.py` — existing route registration and static-mount ordering (`/api/*` before the catch-all static mount) to extend with new portfolio routes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/market/cache.py` `PriceCache.get(ticker)` — the only sanctioned way to read a current price for trade fill; do not call a market source's `fetch()` directly (documented anti-pattern in `.planning/codebase/ARCHITECTURE.md`)
- `backend/app/db/database.py` — connection/init pattern (`contextlib.closing`, `?` placeholders) to follow for new portfolio queries
- `backend/app/db/schema.sql` — `positions`, `trades`, `users_profile.cash_balance`, `portfolio_snapshots` tables already exist and are seeded (`cash_balance=10000.0`), created lazily in Phase 1 — no schema migration needed for Phase 2

### Established Patterns
- Backend: async FastAPI routes, `?`-placeholder SQL, frozen dataclasses for domain models (`Quote`, `PriceUpdate` in `app/market/models.py`) — new portfolio models should follow the same frozen-dataclass style
- Frontend: dark-terminal Tailwind components (`WatchlistRow.tsx`, `PriceCell.tsx`, `ConnectionIndicator.tsx`) use `<div role="button">`/ARIA patterns rather than always reaching for semantic HTML elements, ~rem-based grid layout, `frontend/lib/*.ts` pure state-machine modules paired with component files

### Integration Points
- `backend/app/main.py` — new `/api/portfolio*` routes register here, before the catch-all static mount (same ordering constraint as the existing `/api/watchlist` and SSE routes)
- Frontend header (already renders cash/connection status per Phase 1) — total portfolio value display extends this existing header component
- `PriceCache` — trade execution and portfolio valuation both read from here, same single-source-of-truth constraint Phase 1 established for the watchlist

</code_context>

<specifics>
## Specific Ideas

No specific UI mockups or exact copy given — trade bar layout and positions-table styling are open to the planner/UI-phase to design within the dark-terminal theme (colors per PLAN.md §2).

</specifics>

<deferred>
## Deferred Ideas

- Portfolio heatmap (treemap) — explicitly Phase 3 (PORT-08)
- P&L-over-time chart — explicitly Phase 3 (PORT-09)
- Any-ticker trading (beyond the watchlist) — deferred until Phase 3's watchlist management ships arbitrary-ticker price lookup

None — discussion stayed within phase scope beyond the above, which are already scoped to later phases by ROADMAP.md.

</deferred>

---

*Phase: 02-Trading & Portfolio*
*Context gathered: 2026-08-16*
