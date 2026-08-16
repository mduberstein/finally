# Phase 2: Trading & Portfolio - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16
**Phase:** 02-trading-portfolio
**Areas discussed:** Trade fill price semantics, Rejected trade error presentation, Tradable ticker scope, Fractional shares in the trade bar

---

## Trade fill price semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Server-authoritative fresh read | Server reads `PriceCache.get(ticker)` at trade-processing time, not whatever the client had displayed. Matches PLAN.md's "instant fill at current market price" and avoids client/server price mismatch. | ✓ |
| Client-displayed price | Trade fills at the price shown on screen when clicked, passed from client to server. Simpler mental model but risks staleness if there's any lag between render and click. | |

**User's choice:** Server-authoritative fresh read
**Notes:** None

---

## Rejected trade error presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Inline near the trade bar | Error text appears right where the action was taken, clears on next valid input. | ✓ |
| Toast/banner notification | Error appears as a floating toast or top-of-page banner, separate from the trade bar. | |

**User's choice:** Inline near the trade bar
**Notes:** None

---

## Tradable ticker scope

| Option | Description | Selected |
|--------|-------------|----------|
| Watchlist-only | Trade bar only accepts tickers with a live price in PriceCache (i.e. on the watchlist). Matches what's actually tradable today — watchlist add/remove UI ships in Phase 3. | ✓ |
| Any ticker | User can type any symbol. Requires a price lookup path for tickers not currently in PriceCache, which doesn't exist until Phase 3's watchlist management. | |

**User's choice:** Watchlist-only
**Notes:** None

---

## Fractional shares in the trade bar

| Option | Description | Selected |
|--------|-------------|----------|
| Whole shares only | Simpler input validation (integer quantity), matches typical retail-trading mental model. Schema still stores quantity as REAL for future LLM-initiated fractional trades in Phase 4. | ✓ |
| Fractional allowed | Matches the schema's REAL quantity type directly; more flexible but adds decimal input validation now. | |

**User's choice:** Whole shares only
**Notes:** None

---

## Claude's Discretion

- Positions-table row behavior when a sell reduces a position to zero — default to removing the row.
- Portfolio total value's exact header update cadence — follow the existing Phase 1 SSE/price-flash cadence pattern unless a reason emerges to diverge.

## Deferred Ideas

- Portfolio heatmap (treemap) — explicitly Phase 3 (PORT-08)
- P&L-over-time chart — explicitly Phase 3 (PORT-09)
- Any-ticker trading (beyond the watchlist) — deferred until Phase 3's watchlist management ships arbitrary-ticker price lookup
