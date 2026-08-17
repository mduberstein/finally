# Phase 3: Visual Terminal & Watchlist Control - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

A user can see the whole portfolio at a glance (heatmap sized by position weight, colored by P&L; a P&L-over-time chart) and curate which tickers the terminal tracks (add/remove watchlist tickers, each row growing a progressive sparkline, clicking a row loads that ticker into the main chart). The complete terminal layout — watchlist, main chart, heatmap, P&L chart, positions table, trade bar, an AI chat panel *slot*, and header — fits a wide desktop screen without excess scrolling and stays usable (not broken) at tablet width. The AI chat panel's actual functionality is out of scope — Phase 4 fills its content.

</domain>

<decisions>
## Implementation Decisions

### Charting
- **D-01:** Recharts is the charting library for the main price chart and the P&L-over-time chart. — **Reversibility:** costly — swapping charting libraries later touches every chart component and their data-shaping code.
- **D-02:** The portfolio heatmap (treemap) is a hand-built CSS grid/flexbox layout, not a dedicated treemap library — consistent with Phase 1-2's precedent of hand-rolling dark-terminal components (`WatchlistRow`, `PriceCell`, `PositionRow`) rather than reaching for a component library first. — **Reversibility:** reversible — an isolated component; can be swapped for a library later without touching other charts.

### Layout
- **D-03:** The AI chat panel gets a reserved, empty placeholder panel in Phase 3's grid layout (not omitted) — so Phase 4 only fills content into an already-correctly-sized slot instead of triggering a layout reflow. — **Reversibility:** reversible — the placeholder is styling/structure only, no chat logic.
- **D-04:** At tablet width, all panels (watchlist, main chart, heatmap, P&L chart, positions table, trade bar, chat placeholder, header) stack vertically in a single scrollable column. Nothing is hidden or collapsed. — **Reversibility:** reversible.

### Watchlist
- **D-05:** Adding a ticker uses an inline text input + Add button in the watchlist panel (type ticker, press Add or Enter). Removing a ticker uses a small remove (×) control per row. No modal/dialog. — **Reversibility:** reversible.

### Claude's Discretion
- Sparkline data-source/reset behavior on ticker removal-then-re-add — no strong preference expressed; default to resetting the sparkline history (starts empty again) since there's no persisted price history to restore from.
- Main chart data granularity — follows the same "accumulated client-side from the SSE stream since page load" pattern as sparklines (no historical-data backend endpoint exists); use judgment on exact windowing/resolution.
- Watchlist ticker validation and any practical maximum count — no strong preference expressed; use judgment (e.g. reject unknown/invalid symbols client-side, no hard cap unless layout genuinely breaks).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Plan
- `planning/PLAN.md` §10 (Frontend Design — layout elements, charting library guidance, sparkline/heatmap/P&L-chart descriptions)
- `planning/PLAN.md` §2 (Visual Design — color scheme, dark theme values) — Phase 3 introduces the heatmap's green/red P&L coloring, must match Phase 1-2's established `--up`/`--down` semantic tokens
- `.planning/REQUIREMENTS.md` (PORT-08, PORT-09, WATCH-02, WATCH-03, WATCH-04, WATCH-05, UI-02, UI-04, TEST-03) — full requirement text for this phase
- `.planning/ROADMAP.md` §Phase 3 — goal and success criteria (authoritative for verification)

### Prior Phase Artifacts
- `.planning/phases/02-trading-portfolio/02-SECURITY.md` — Phase 2's SQL/rendering-safety patterns (grep-gated `dangerouslySetInnerHTML` absence, `?`-placeholder SQL) to continue for any new backend routes (e.g. `GET /api/portfolio/history`, watchlist write endpoints)
- `.planning/phases/01-live-streaming-terminal/01-UI-SPEC.md` and `.planning/phases/02-trading-portfolio/02-UI-SPEC.md` — established Design System, spacing scale, typography, and color reservations (Phase 3 introduces the Purple/Yellow-adjacent heatmap coloring on top of these, must reconcile)
- `backend/app/db/schema.sql` — `portfolio_snapshots` table already exists (created lazily in Phase 1, unused until now); Phase 3's `GET /api/portfolio/history` reads from it and a background task must start writing to it every 30s + after each trade (PORT-09)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/lib/usePriceStream.ts` — the single open `EventSource`; sparklines and the main chart must accumulate from this same stream, never open a second connection
- `frontend/components/WatchlistRow.tsx`, `PriceCell.tsx` — grid-row and price-cell patterns to extend for sparkline rendering inline in each watchlist row
- `frontend/lib/portfolio.ts` — pure derivation functions (`derivePortfolioValue`, `derivePositionRows`) established in Phase 2; the heatmap's per-position weight/P&L and the P&L-chart's total-value-over-time should follow the same "pure function over snapshot + live prices" pattern
- `backend/app/main.py` — existing route registration order (`/api/*` before the static catch-all mount); new watchlist-write and portfolio-history routes extend this
- `backend/app/db/database.py` — lazy-init/seed pattern, `contextlib.closing()` connections, `?`-placeholder SQL, `INSERT OR IGNORE` — the pattern for any new `portfolio_snapshots` writer and watchlist add/remove queries

### Established Patterns
- Backend: async FastAPI routes, frozen dataclasses for domain models, router-factory pattern (`create_stream_router`, `create_portfolio_router`) — a `create_watchlist_router`/history endpoint should follow the same shape
- Frontend: hand-built `<div>`-based components over pulling in UI-library primitives for anything beyond shadcn `button`/`skeleton`/`input`; `frontend/lib/*.ts` pure state/derivation modules paired 1:1 with the component that renders them

### Integration Points
- `frontend/app/page.tsx` — the page-level layout composing all panels; Phase 3 adds the heatmap, P&L chart, chat placeholder, and reflows the grid to accommodate them at both desktop and tablet widths
- `PriceCache` — sparklines and the main chart both read live prices from here via the existing SSE stream; no new price-fetching path
- Watchlist selection state (which ticker is "selected" for the main chart) is new client-side state this phase introduces — `page.tsx` is the natural owner, matching where `derivePortfolioValue`/`derivePositionRows` are currently invoked

</code_context>

<specifics>
## Specific Ideas

No specific UI mockups or exact copy given — heatmap cell layout, sparkline dimensions, and the chat placeholder's exact appearance are open to the planner/UI-phase to design within the dark-terminal theme and the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- AI chat panel functionality (message input, LLM responses, trade execution via chat) — explicitly Phase 4, only the empty placeholder slot ships this phase (D-03)
- A dedicated treemap library for the heatmap — considered and explicitly declined in favor of a hand-built CSS grid (D-02); revisit only if the hand-built approach proves genuinely insufficient

None — discussion stayed within phase scope beyond the above.

</deferred>

---

*Phase: 03-Visual Terminal & Watchlist Control*
*Context gathered: 2026-08-17*
