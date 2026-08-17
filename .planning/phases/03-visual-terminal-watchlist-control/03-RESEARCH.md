# Phase 3: Visual Terminal & Watchlist Control - Research

**Researched:** 2026-08-17
**Domain:** React/Recharts charting on Next.js static export, hand-built CSS treemap layout, FastAPI background snapshot task, SSE-accumulated client-side time series
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Recharts is the charting library for the main price chart and the P&L-over-time chart. — **Reversibility:** costly — swapping charting libraries later touches every chart component and their data-shaping code.
- **D-02:** The portfolio heatmap (treemap) is a hand-built CSS grid/flexbox layout, not a dedicated treemap library — consistent with Phase 1-2's precedent of hand-rolling dark-terminal components (`WatchlistRow`, `PriceCell`, `PositionRow`) rather than reaching for a component library first. — **Reversibility:** reversible — an isolated component; can be swapped for a library later without touching other charts.
- **D-03:** The AI chat panel gets a reserved, empty placeholder panel in Phase 3's grid layout (not omitted) — so Phase 4 only fills content into an already-correctly-sized slot instead of triggering a layout reflow. — **Reversibility:** reversible — the placeholder is styling/structure only, no chat logic.
- **D-04:** At tablet width, all panels (watchlist, main chart, heatmap, P&L chart, positions table, trade bar, chat placeholder, header) stack vertically in a single scrollable column. Nothing is hidden or collapsed. — **Reversibility:** reversible.
- **D-05:** Adding a ticker uses an inline text input + Add button in the watchlist panel (type ticker, press Add or Enter). Removing a ticker uses a small remove (×) control per row. No modal/dialog. — **Reversibility:** reversible.

### Claude's Discretion

- Sparkline data-source/reset behavior on ticker removal-then-re-add — no strong preference expressed; default to resetting the sparkline history (starts empty again) since there's no persisted price history to restore from.
- Main chart data granularity — follows the same "accumulated client-side from the SSE stream since page load" pattern as sparklines (no historical-data backend endpoint exists); use judgment on exact windowing/resolution.
- Watchlist ticker validation and any practical maximum count — no strong preference expressed; use judgment (e.g. reject unknown/invalid symbols client-side, no hard cap unless layout genuinely breaks).

### Deferred Ideas (OUT OF SCOPE)

- AI chat panel functionality (message input, LLM responses, trade execution via chat) — explicitly Phase 4, only the empty placeholder slot ships this phase (D-03)
- A dedicated treemap library for the heatmap — considered and explicitly declined in favor of a hand-built CSS grid (D-02); revisit only if the hand-built approach proves genuinely insufficient

None — discussion stayed within phase scope beyond the above.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| PORT-08 | User can view a portfolio heatmap (treemap) sized by position weight, colored by P&L | Pattern 2 (squarified layout + flexbox rendering, hand-rolled per D-02); Architectural Responsibility Map |
| PORT-09 | User can view a P&L chart of total portfolio value over time, recorded every 30s and after each trade | Pattern 3 (30s background snapshot writer, mirrors `MarketFeed`) and Pattern 4 (post-trade snapshot inside `execute_trade`'s transaction); Pitfall 4 (total_value must re-price every position) |
| WATCH-02 | User can add a ticker to the watchlist | New `watchlist/` module (Recommended Project Structure); Pitfall 3 (new row briefly has no price); Security Domain (input validation, parameterized SQL) |
| WATCH-03 | User can remove a ticker from the watchlist | New `watchlist/` module; Pattern 1 / Pitfall 2 (removal is the only reliable prune signal for client-side history, since `PriceCache` never purges a ticker) |
| WATCH-04 | Each watchlist row shows a sparkline mini-chart accumulated from the SSE stream since page load | Pattern 1 (shared price-history accumulator); Code Examples (hand-rolled inline SVG sparkline); Alternatives Considered (why not a second Recharts instance per row) |
| WATCH-05 | Clicking a watchlist ticker selects it in the main chart area | Pattern 1 (shared accumulator feeds both sparklines and the selected ticker's main chart); existing `selectedTicker` state in `frontend/app/page.tsx` extends directly |
| UI-02 | Layout includes watchlist, main chart, heatmap, P&L chart, positions table, trade bar, AI chat panel, header — all visible without excess scrolling on wide desktop | System Architecture Diagram; Recommended Project Structure (`ChatPlaceholder.tsx`); D-03/D-04 from User Constraints |
| UI-04 | App is usable (not broken) on a tablet-width viewport | D-04 from User Constraints (vertical stack, no hide/collapse); Pitfall 1 (charts need explicit-height containers so they don't collapse to 0 on reflow) |
| TEST-03 | Frontend unit tests cover price flash animation, watchlist CRUD, and portfolio display calculations | Validation Architecture section — pure-function `lib/*.ts` testing convention (no RTL), Phase Requirements → Test Map, Wave 0 Gaps |
</phase_requirements>

## Summary

Phase 3 has two backend additions (a `portfolio_snapshots` writer for PORT-09 and watchlist add/remove routes for WATCH-02/03) and a larger frontend slice (heatmap, P&L chart, sparklines, main chart, layout reflow). Every backend pattern needed already exists in the codebase almost verbatim — `MarketFeed`'s background-task shape covers the 30s snapshot loop, and `execute_trade`'s existing open transaction is the natural place for the "immediately after each trade" snapshot write (not a second call site, because `execute_trade` is documented as the shared entry point Phase 4's chat flow will call directly, bypassing the HTTP route). Frontend charting is locked to Recharts (D-01) for the main chart and P&L chart; Recharts 3.10.1 (`npm view` confirmed, published 2026-07-25) is React 19-compatible and Client-Component-only usage is fully supported under `output: 'export'` per Next.js's own static-export docs, so no SSR/build-time constraint applies. The heatmap is hand-built per D-02; a well-known algorithm (Bruls/Huizing/van Wijk "squarified treemap") combined with CSS flexbox `flex-grow` (a native proportional-sizing primitive) avoids any pixel-math layer in the component.

The single most important architectural finding is about state ownership: `PriceCache` on the backend never deletes a ticker once seen (confirmed by reading `cache.py` and `stream.py`), so the SSE stream keeps a removed ticker's last price forever, and the frontend must not rely on ticker disappearance from the SSE `prices` map to reset sparkline history. Combined with CONTEXT.md's discretion default ("reset sparkline history on remove-then-re-add"), sparkline/main-chart price history must be pruned explicitly by the watchlist-owning component when a ticker leaves the watchlist entries list — not left to component unmount/remount alone and not left to the SSE stream to signal removal (it never will).

**Primary recommendation:** Add one shared `usePriceHistory` accumulator hook at the page level (fed by the existing `usePriceStream`, pruned against the current watchlist entries), feed both the sparklines and the main chart from it, use Recharts `LineChart`+`ResponsiveContainer` for the main/P&L charts only, hand-roll sparklines as lightweight inline SVG (not a second Recharts instance per row) for performance, and write the post-trade snapshot inside `execute_trade`'s existing transaction rather than as a second call site.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Heatmap weight/P&L computation | Browser/Client | — | Pure derivation from existing `/api/portfolio` snapshot + live SSE prices, same pattern as `derivePortfolioValue`; no new backend data needed |
| Heatmap rectangle layout (squarified algorithm) | Browser/Client | — | Pure layout math over already-derived weights; no backend involvement, must stay a pure function per project convention |
| P&L-over-time data | API/Backend | Database/Storage | New `portfolio_snapshots` rows require a durable, timestamped write outside the browser's lifetime — must survive page reloads/navigations, which the SSE-accumulated client pattern (used for sparklines/main chart) explicitly cannot do here |
| P&L-over-time snapshot writer (30s + post-trade) | API/Backend | Database/Storage | Must run continuously regardless of any open browser tab (background asyncio task in the FastAPI lifespan), matching `MarketFeed`'s existing shape |
| Sparkline / main chart price history | Browser/Client | — | CONTEXT.md explicitly rules out a new backend history endpoint for these ("no historical-data backend endpoint exists"); accumulated client-side from the already-open SSE connection |
| Watchlist add/remove | API/Backend | Database/Storage | Mutates the `watchlist` table (source of truth for `MarketFeed`'s ticker list); client input is a thin form over this endpoint |
| Watchlist ticker validation | Browser/Client | API/Backend | Client-side rejects obviously malformed input before a request; server is still the authority (unknown ticker just never gets a live price — same "untradable ticker" pattern PORT already established) |
| Layout responsiveness (desktop/tablet) | Browser/Client | — | Pure CSS (Tailwind breakpoints), no server involvement |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 3.10.1 (verified via `npm view recharts version`, published 2026-07-25) | Main price chart, P&L-over-time chart | Locked by CONTEXT.md D-01; industry-standard declarative React/SVG charting library, actively maintained, React 19 peer-dep support confirmed |

### Supporting

No new supporting libraries are required. `react-is` is a transitive peer dependency of `recharts` and will be pulled in automatically by npm/pnpm — it does not need to be added explicitly.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts (main/P&L charts) | Lightweight Charts (TradingView) | Better for candlestick/OHLC and huge tick counts, but heavier API surface for a simple line chart and PLAN.md only names it as one of two "preferred" options — CONTEXT.md D-01 already locked Recharts, so this is moot for this phase |
| Recharts (sparklines) | Recharts `LineChart` with hidden axes/grid, one instance per row | Simpler code (reuse one library everywhere), but 10-15 concurrent `ResponsiveContainer` instances each register their own `ResizeObserver` and re-render on every SSE tick (~500ms) — STATE.md already flags "per-tick position recompute cost, revisit at Phase 3 heatmap/sparklines" (T-02-13) as an accepted risk to address here. A hand-rolled inline `<svg><polyline>` sparkline (no chart library, no ResizeObserver, pure `<path>` string from an array of points) avoids this entirely and matches the existing hand-rolled-`<div>` component precedent (`WatchlistRow`, `PriceCell`) |
| Hand-built CSS treemap (D-02) | `recharts`' built-in `<Treemap>` component | Recharts ships a working squarified `<Treemap>` (confirmed via Context7: `ResponsiveContainer` officially supports `<Treemap/>` as a child) — genuinely simpler, but D-02 explicitly declined a treemap library/component in favor of hand-rolling, consistent with Phase 1-2 precedent; not re-litigated here |

**Installation:**
```bash
cd frontend && npm install recharts
```

**Version verification:** `npm view recharts version` → `3.10.1`, `npm view recharts time.modified` → `2026-07-25T15:23:05.815Z`, `npm view recharts peerDependencies` → `{ react: '^16.8.0 || ^17.0.0 || ^18.0.0 || ^19.0.0', 'react-dom': '^16.0.0 || ^17.0.0 || ^18.0.0 || ^19.0.0', 'react-is': '^16.8.0 || ^17.0.0 || ^18.0.0 || ^19.0.0' }` — compatible with the project's React 19.2.8. `[VERIFIED: npm registry]`

## Package Legitimacy Audit

The automated `package-legitimacy check` seam returned `SUS` for `recharts` with reasons `unknown-age`, `unknown-downloads`, `no-repository` — this reflects that seam's tool having no network reachability in this sandbox (all three signals came back `null`, not populated-and-suspicious), not an actual finding about the package. Independent verification below was run directly against the live npm registry (`registry.npmjs.org` is an allowed network host in this environment) and overrides the seam's inconclusive verdict.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| recharts | npm | Created 2015-08-07 (`npm view recharts time.created`), latest 3.10.1 published 2026-07-25 | Not checked (npm CLI has no download-count command; `recharts` is one of the most widely used React charting libraries by longstanding community consensus — used across shadcn/ui's own chart component, which is already in this project's ecosystem) | `git+https://github.com/recharts/recharts.git` (confirmed via `npm view recharts repository.url`) | OK (manually verified) | Approved |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `recharts` was flagged by the automated seam due to a network-access limitation in that tool, not a legitimacy concern — manually verified `OK` above via direct npm registry queries (10-year-old package, real GitHub repo, MIT license, no `postinstall` script per `npm view recharts scripts.postinstall` returning empty). No `checkpoint:human-verify` is required for this install.

No other new external packages are introduced by this phase — the treemap is hand-rolled per D-02 and no new backend dependencies are needed (background task and SQL patterns reuse `asyncio`/`sqlite3`, already in use).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Browser (Client Components) ───────────────────────────┐
│                                                                                     │
│  usePriceStream() ──(EventSource, single connection)──> /api/stream/prices (SSE)   │
│       │                                                                             │
│       ├─> prices: Record<ticker, PriceTick>  ──────────┐                           │
│       │                                                  │                          │
│       └─> usePriceHistory(prices, watchlistTickers)     │                          │
│              │  (NEW this phase — prunes on removal)     │                          │
│              ├─> history: Record<ticker, PricePoint[]>   │                          │
│              │        │                                  │                          │
│              │        ├──> Watchlist rows ──> hand-rolled SVG sparkline (per row)   │
│              │        └──> Main chart (selected ticker) ──> Recharts LineChart      │
│                                                                                      │
│  fetch /api/portfolio ──> derivePortfolioValue / derivePositionRows (existing)      │
│       └──> Heatmap: derive weight+P&L per position ──> squarified layout (pure fn)  │
│              ──> nested flexbox divs (flex-grow = weight)                           │
│                                                                                      │
│  fetch /api/portfolio/history (NEW) ──> Recharts LineChart (P&L-over-time)          │
│                                                                                      │
│  Watchlist add/remove: inline input+button (D-05) ──POST/DELETE──> /api/watchlist   │
│                                                                                      │
└──────────────────────────────────────┬──────────────────────────────────────────────┘
                                        │
┌───────────────────────────── FastAPI (Backend) ──────────────────────────────────┐
│                                                                                     │
│  lifespan: MarketFeed (existing) ── polls db.watchlist_tickers() every tick ──┐    │
│                                                                                │    │
│  lifespan: SnapshotWriter (NEW) ── asyncio task, sleep(30) loop ──┐           │    │
│       └─> reads PriceCache + positions ──> INSERT portfolio_snapshots        │    │
│                                                                    │           │    │
│  POST /api/portfolio/trade ─> execute_trade() ─┬─ existing trade write ───────┘    │
│                                                  └─ NEW: INSERT portfolio_snapshots │
│                                                     (same transaction, so ANY       │
│                                                     future caller incl. Phase 4     │
│                                                     chat gets a snapshot for free)  │
│                                                                                      │
│  GET  /api/portfolio/history (NEW) ─> SELECT portfolio_snapshots ORDER BY recorded_at│
│                                                                                      │
│  POST /api/watchlist (NEW)   ─> INSERT watchlist (id, user_id, ticker, added_at)   │
│  DELETE /api/watchlist/{t} (NEW) ─> DELETE FROM watchlist WHERE ticker = ?         │
│       (MarketFeed's next poll — ≤500ms — automatically picks up the new/removed    │
│        set; no feed restart needed, since it already re-reads tickers() every tick)│
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
backend/app/
├── portfolio/
│   ├── routes.py          # add GET /api/portfolio/history to create_portfolio_router
│   ├── service.py         # add snapshot INSERT inside execute_trade's transaction;
│   │                       #   add a small read-only history query function
│   └── models.py          # (unchanged — no new exception types needed for history)
├── watchlist/              # NEW module, mirrors portfolio/ shape
│   ├── __init__.py
│   ├── routes.py          # create_watchlist_router(): POST/DELETE /api/watchlist
│   └── service.py          # add_ticker / remove_ticker plain functions over db.py
└── market/
    └── snapshot_feed.py    # NEW — 30s background task, same shape as feed.py's MarketFeed

frontend/
├── lib/
│   ├── priceHistory.ts     # NEW — pure accumulator + prune logic (usePriceHistory hook)
│   ├── heatmap.ts           # NEW — pure squarified layout algorithm + weight/P&L derivation
│   └── watchlistForm.ts     # NEW — ticker input validation (pure function, testable)
├── components/
│   ├── Sparkline.tsx        # NEW — hand-rolled inline SVG polyline
│   ├── MainChart.tsx        # NEW — Recharts LineChart wrapper
│   ├── PnlChart.tsx          # NEW — Recharts LineChart wrapper over /api/portfolio/history
│   ├── Heatmap.tsx            # NEW — nested flexbox rows from heatmap.ts output
│   ├── HeatmapCell.tsx         # NEW
│   ├── WatchlistAddForm.tsx     # NEW — inline input + Add button (D-05)
│   └── ChatPlaceholder.tsx       # NEW — empty reserved panel (D-03)
└── app/page.tsx              # reflow grid: watchlist, main chart, heatmap, P&L chart,
                                # positions table, trade bar, chat placeholder, header
```

### Pattern 1: Shared client-side price-history accumulator, pruned on watchlist removal

**What:** A single hook (or plain accumulator function called from `page.tsx`) that appends every SSE tick to a `Record<ticker, {price:number, timestamp:string}[]>` map, and removes a ticker's array entirely when that ticker is no longer present in the `/api/watchlist` response.

**When to use:** Both the sparklines (WATCH-04) and the main chart (WATCH-05) need "progressive fill since page load" history for possibly-different tickers at the same time — the sparklines need it for every watchlist ticker simultaneously, the main chart only for the selected one. One shared accumulator avoids two separate, possibly-inconsistent implementations.

**Why not rely on component unmount/remount to reset history:** `PriceCache` on the backend (read directly, `backend/app/market/cache.py`) never deletes a ticker entry — `apply()` only ever inserts/updates, and `snapshot()`/`get()` have no purge path. The SSE stream (`backend/app/market/stream.py`) sends from `cache.snapshot()`, which still contains removed tickers at their last price forever. This means the frontend cannot infer "ticker was removed" from the `prices` map ever going empty for that ticker — it will not. The removal signal is exclusively the `/api/watchlist` response (or the DELETE call's own success), so pruning must be driven from there, explicitly, not from SSE state.

**Example (pure derivation to test without RTL, matching the existing `lib/*.ts` pattern):**
```typescript
// frontend/lib/priceHistory.ts — pattern to follow, not verbatim required code
export interface PricePoint {
  price: number;
  timestamp: string;
}

/** Appends a new tick for one ticker, keeping history bounded. */
export function appendTick(
  history: Record<string, PricePoint[]>,
  ticker: string,
  point: PricePoint,
  maxPoints: number,
): Record<string, PricePoint[]> {
  const existing = history[ticker] ?? [];
  const next = [...existing, point].slice(-maxPoints);
  return { ...history, [ticker]: next };
}

/** Drops history for any ticker no longer present in the current watchlist —
 * the only reliable "removed" signal, since PriceCache never purges a ticker
 * (verified: backend/app/market/cache.py has no delete path). */
export function pruneToWatchlist(
  history: Record<string, PricePoint[]>,
  currentTickers: readonly string[],
): Record<string, PricePoint[]> {
  const keep = new Set(currentTickers);
  const next: Record<string, PricePoint[]> = {};
  for (const ticker of Object.keys(history)) {
    if (keep.has(ticker)) next[ticker] = history[ticker];
  }
  return next;
}
```

### Pattern 2: Squarified treemap layout as a pure function + flexbox rendering

**What:** A recursive algorithm that groups weighted items into "rows" (alternating horizontal/vertical) to keep rectangle aspect ratios close to square, implemented as a pure function returning a tree of `{ weight, children }` groups — then rendered as nested flexbox `<div>`s where each sibling's `flex-grow` equals its weight. No pixel/percentage math is computed in the component; the browser's flexbox engine does the proportional sizing.

**When to use:** PORT-08's heatmap — the only treemap-shaped visualization in this phase, and explicitly not to use a treemap library (D-02).

**Source:** Algorithm attributed to Bruls, Huizing, van Wijk (squarified treemaps); cross-checked against multiple independent JS/TS implementations ([huy-nguyen/squarify](https://github.com/huy-nguyen/squarify) — TypeScript, MIT, no runtime deps) that agree on the same core recursion. `[CITED: web — cross-checked against squarify TS reference implementation]`

```typescript
// frontend/lib/heatmap.ts — algorithm sketch, not verbatim required code
interface WeightedItem {
  ticker: string;
  weight: number;      // position value / total portfolio value
  pnlPercent: number;  // drives cell color (up/down token)
}

interface TreemapRow {
  items: WeightedItem[];
  direction: "row" | "column"; // alternates by recursion depth
}

/**
 * Greedily builds rows: sort items descending by weight, add items to the
 * current row while doing so keeps improving the row's worst aspect ratio,
 * otherwise close the row and start a new one on the remaining space.
 * Returns a flat list of rows; each row (and the overall container) is
 * rendered as a flexbox container whose children's flex-grow = item weight.
 */
function squarify(items: WeightedItem[]): TreemapRow[] { /* ... */ }
```

```tsx
// Rendering: CSS flex-grow does the proportional sizing, no pixel math
<div className="flex flex-col h-full w-full">
  {rows.map((row, i) => (
    <div key={i} className="flex" style={{ flexGrow: rowTotalWeight(row) }}>
      {row.items.map((item) => (
        <HeatmapCell
          key={item.ticker}
          style={{ flexGrow: item.weight }}
          className={item.pnlPercent >= 0 ? "bg-up/70" : "bg-down/70"}
        />
      ))}
    </div>
  ))}
</div>
```
`[CITED: web — flexbox flex-grow proportional-sizing technique, cross-checked against MDN's flex-grow documentation]`

### Pattern 3: Background snapshot writer, mirroring `MarketFeed`'s lifecycle shape

**What:** A second asyncio background task started/stopped alongside `MarketFeed` in the FastAPI `lifespan` handler, looping every 30 seconds and writing one `portfolio_snapshots` row.

**Verified against existing code** `[VERIFIED: backend/app/market/feed.py:1-56]` — `MarketFeed.start()` guards against double-start (`if self._task is not None and not self._task.done(): raise RuntimeError`), uses `asyncio.create_task(self._run())`, and `stop()` cancels + awaits the task, catching `CancelledError`. The exact same shape (task handle, `start()`/`stop()`, `while True: await asyncio.sleep(interval)` loop) applies directly to a 30-second snapshot writer — no new pattern needs to be invented.

```python
# backend/app/main.py — lifespan wiring, extending the existing pattern verbatim
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    feed = MarketFeed(...)          # existing
    feed.start()
    snapshot_writer = SnapshotWriter(cache, interval=30.0)   # NEW, same shape as MarketFeed
    snapshot_writer.start()
    app.state.prices = cache
    app.state.feed = feed
    yield
    await feed.stop()
    await snapshot_writer.stop()
```

### Pattern 4: Post-trade snapshot write inside `execute_trade`'s existing transaction

**What:** Insert the `portfolio_snapshots` row for "immediately after each trade" (PORT-09) as one more statement inside the same `BEGIN IMMEDIATE ... COMMIT` block in `execute_trade`, not as a second call from the HTTP route layer.

**Why:** `[VERIFIED: backend/app/portfolio/service.py:1-6]` — the module docstring states verbatim: *"Both `execute_trade` and `get_portfolio` are plain functions with no FastAPI dependency, so Phase 4's chat flow can import and call them directly rather than re-implementing trade validation."* If the snapshot write instead lived in `backend/app/portfolio/routes.py`'s `trade()` handler (the natural-looking place at first glance), Phase 4's chat-initiated trades — which the docstring says will call `execute_trade` directly, bypassing the HTTP route — would silently skip snapshot recording, produce an inconsistent contract, and require someone to notice and duplicate the call site four phases from now. Writing it inside `execute_trade` itself makes the invariant "every trade produces a snapshot" hold for every current and future caller automatically, and it can share the already-open `conn`/transaction so the trade and its snapshot commit atomically together.

**Total value computation inside the transaction:** the existing `_read_cash_balance`/position-reading helpers already run inside this same transaction; computing `total_value` for the snapshot requires cash (`new_cash_balance`, already computed) plus the value of every position at current cache prices (not just the traded ticker) — the transaction already has `cache: PriceCache` available as a parameter, so this is a straightforward re-read of all positions (`SELECT * FROM positions WHERE user_id = ?`) valued via `cache.get(ticker).price`, mirroring `get_portfolio`'s existing valuation loop.

### Anti-Patterns to Avoid

- **A second Recharts `ResponsiveContainer` instance per watchlist row for sparklines:** 10+ concurrent `ResizeObserver`-backed chart instances re-rendering on every ~500ms SSE tick is the exact per-tick recompute cost STATE.md already flagged as an accepted risk to revisit at this phase (T-02-13). Hand-roll sparklines as a plain `<svg><polyline>` computed from the shared price-history array instead.
- **Reading ticker removal from the SSE `prices` map going stale/absent:** it never will — `PriceCache` has no delete path (verified by reading `cache.py`). Always prune price history from the `/api/watchlist` response (or the DELETE call's own success), never by inferring absence from the stream.
- **Restarting `MarketFeed` when the watchlist changes:** unnecessary — `MarketFeed._tick()` already calls `self._tickers()` (bound to `db.watchlist_tickers`) fresh on every poll (verified: `backend/app/market/feed.py`'s `_run`/`_tick`), so a plain `INSERT`/`DELETE` on the `watchlist` table takes effect within one poll interval automatically.
- **Computing the heatmap's pixel positions in JavaScript (`getBoundingClientRect`, manual `left`/`top`/`width`/`height` styles):** defeats the purpose of choosing a flexbox-based layout (D-02's intent) and reintroduces a resize-observer/pixel-math dependency the CSS approach avoids entirely.
- **A second, ungated `POST /api/portfolio/trade`-adjacent snapshot write in `routes.py`:** duplicates Pattern 4's logic and risks drift between the HTTP-triggered snapshot and whatever Phase 4 does — keep it a single call site inside `execute_trade`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line/area chart rendering, axis scaling, tooltips | A custom SVG/Canvas chart renderer | Recharts `LineChart` + `ResponsiveContainer` (locked, D-01) | Axis scale math, resize handling, and tooltip positioning are exactly the kind of deceptively fiddly problem a mature library has already solved; D-01 already made this call |
| Responsive container resize detection | Manual `window.resize` listeners + `getBoundingClientRect` | Recharts' built-in `ResponsiveContainer` (uses `ResizeObserver` internally, confirmed via Context7 docs) | Already handled; a hand-rolled resize listener would just reimplement what `ResponsiveContainer` does, badly |

**Key insight:** The two things this phase explicitly *should* hand-roll (the treemap layout and the sparklines) are both explicitly justified — the treemap by CONTEXT.md's D-02 (small, isolated, reversible), and the sparkline recommendation by a concrete perf issue (T-02-13) already flagged in this project's own state file. Everything else (the two Recharts-driven charts) should use the library, not be reimplemented.

## Common Pitfalls

### Pitfall 1: `ResponsiveContainer` renders 0x0 inside a flex/grid parent with no explicit height

**What goes wrong:** Recharts' own source (`ResponsiveContainer.tsx`, confirmed via Context7) emits a runtime warning and renders nothing when its calculated width/height is 0 — this is the single most common Recharts integration bug, and it happens specifically when the parent element's height comes from `flex-grow`/`grid` sizing rather than an explicit `height` or `aspect-ratio`.

**Why it happens:** `ResponsiveContainer` measures its parent via `ResizeObserver`; if the parent's own height is undefined until content (i.e. the chart) renders, there's a circular sizing dependency that resolves to 0.

**How to avoid:** Give every chart's direct parent container an explicit height (e.g. Tailwind `h-64`, or `aspect-[16/9]`) — never let a chart's wrapping `<div>` depend purely on `flex-grow` for its cross-axis size in a column flex container without a `min-height`.

**Warning signs:** Chart renders blank with a console warning about width/height being 0; works fine at first paint but breaks after a layout reflow (e.g. tablet-width stacking, D-04).

### Pitfall 2: Sparkline history keyed globally by ticker without pruning leaks removed tickers

**What goes wrong:** If price history is accumulated in a single `Record<ticker, PricePoint[]>` that's never pruned, removing then re-adding a ticker (WATCH-02/03) shows the *old* sparkline history instantly on re-add instead of starting empty, contradicting the CONTEXT.md discretion default.

**Why it happens:** The natural-looking implementation (a `useState` map at the page level, updated only by appending) has no removal path — nothing ever calls `delete`.

**How to avoid:** Explicitly prune the history map against the current `/api/watchlist` response every time it's fetched (see Pattern 1's `pruneToWatchlist`), not relying on component unmount to clear the data since it's stored above the row component in the tree.

### Pitfall 3: Watchlist add races the SSE stream — new row shows no price for one poll interval

**What goes wrong:** After `POST /api/watchlist` succeeds, the new ticker has no cached price yet (the simulator/`MarketFeed` hasn't polled it), so a freshly-added row would show a blank/null price for up to one poll interval.

**Why it happens:** `MarketFeed` re-reads `db.watchlist_tickers()` fresh each tick and the simulator ticks every 500ms — this is a very short window, but not zero, and the row must render *something* sane in that window.

**How to avoid:** Follow the existing `WatchlistEntry`/`PriceCell` null-handling convention already established in `PriceCell.tsx` and `main.py`'s `_watchlist_entry` (price/change/direction all nullable, rendered as an empty/dash state) — no special-casing needed, just make sure the new watchlist row is added to UI state optimistically after a successful POST and lets the existing null-price rendering path handle the brief gap.

### Pitfall 4: `portfolio_snapshots` total_value written without re-pricing every position

**What goes wrong:** If the post-trade snapshot only accounts for the just-traded ticker's new value (e.g. reusing `TradeResult.cash_balance` plus a naive delta), the recorded `total_value` will silently drift from the true portfolio value whenever other positions' prices have moved since the last snapshot.

**Why it happens:** `execute_trade`'s existing code path only touches the one traded ticker's `positions` row — it's tempting to compute the snapshot the same narrow way.

**How to avoid:** Snapshot `total_value` must be `cash_balance + sum(quantity * current_cache_price for every open position)`, mirroring `get_portfolio()`'s existing valuation loop exactly (same formula, same `cache.get(ticker).price` source) — not a shortcut based only on the trade just executed.

## Code Examples

### Recharts LineChart with theme colors via CSS variables (confirmed pattern)

```tsx
// Source: Context7 /recharts/recharts — "CSS variable on Bar fill" snippet,
// confirmed the same var() passthrough works for Line's `stroke` prop since
// Recharts passes string props straight to the underlying SVG element.
<ResponsiveContainer width="100%" height="100%">
  <LineChart data={history} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
    <XAxis dataKey="timestamp" stroke="var(--muted-foreground)" tick={{ fontSize: 12 }} />
    <YAxis stroke="var(--muted-foreground)" tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
    <Tooltip
      contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)" }}
      labelStyle={{ color: "var(--popover-foreground)" }}
    />
    <Line
      type="monotone"
      dataKey="price"
      stroke={changeIsPositive ? "var(--up)" : "var(--down)"}
      dot={false}
      isAnimationActive={false}
    />
  </LineChart>
</ResponsiveContainer>
```
`[CITED: Context7 /recharts/recharts]` — `isAnimationActive={false}` is a deliberate recommendation, not from the docs snippet: with ticks arriving every ~500ms, Recharts' default enter/update animation would constantly restart, producing visible jitter; existing project precedent (`PriceCell`'s CSS-only flash) already avoids animating on every tick for the same reason.

### Hand-rolled inline SVG sparkline (no chart library)

```tsx
// frontend/components/Sparkline.tsx — pattern, not verbatim required code
interface SparklineProps {
  points: { price: number }[];
  width?: number;
  height?: number;
  direction: "up" | "down" | "flat" | null;
}

export function Sparkline({ points, width = 96, height = 28, direction }: SparklineProps) {
  if (points.length < 2) return <svg width={width} height={height} aria-hidden="true" />;

  const prices = points.map((p) => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const coords = points.map((p, i) => {
    const x = (i / (points.length - 1)) * width;
    const y = height - ((p.price - min) / range) * height;
    return `${x},${y}`;
  });

  const stroke = direction === "down" ? "var(--down)" : "var(--up)";

  return (
    <svg width={width} height={height} aria-hidden="true">
      <polyline points={coords.join(" ")} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `accessibilityLayer` prop required explicitly on Recharts charts | `accessibilityLayer` defaults to `true` | Recharts 3.0 (confirmed via Context7 accessibility docs snippet) | No action needed — keyboard/screen-reader support is on by default in the installed 3.10.1, don't add the prop expecting it's opt-in |
| `next export` CLI command | `output: 'export'` in `next.config.ts` | Next.js 14.0.0 (per Next's own static-export doc version history) | Already correctly configured in this project's `frontend/next.config.ts` — no action needed, noted for completeness |

**Deprecated/outdated:** None relevant surfaced for this phase's scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Squarified treemap algorithm summary (row-building heuristic) is accurately described from training knowledge, cross-checked only against secondary web sources (GitHub repo descriptions), not the original Bruls/Huizing/van Wijk paper itself | Pattern 2 | If the described row-building heuristic has a subtle error, the resulting layout may look "off" (poor aspect ratios) but will still be a valid, weight-proportional treemap since the fallback (any correctly-weighted flex-grow partition) still satisfies PORT-08's literal requirement ("sized by position weight") — low risk, cosmetic only |
| A2 | Recharts default line-chart re-render behavior under rapid (~500ms) data updates causes visible animation jitter unless `isAnimationActive={false}` is set | Code Examples | If wrong, worst case is a cosmetic animation quirk on the main chart, not a functional bug — easy to spot and fix during implementation/UAT |
| A3 | `npm view recharts` weekly download count was not directly queried (no `npm view` field for it) — legitimacy is argued from the package's 10-year registry age, real GitHub repo, and known community prominence (e.g. shipped inside shadcn/ui's own chart component) rather than a download-count figure | Package Legitimacy Audit | Low risk — age, repo, and license signals are independently strong; if this reasoning is wrong the planner should re-run `npm view recharts` fresh before install |

## Open Questions

1. **Exact sparkline/main-chart history window (point count / time span)**
   - What we know: CONTEXT.md explicitly leaves "exact windowing/resolution" to implementer judgment, and confirms there is no backend history endpoint for this data (client-accumulates since page load only).
   - What's unclear: A hard cap on points (e.g. last 200 ticks vs. unbounded) isn't specified — unbounded accumulation over a long-running session could grow memory/render cost.
   - Recommendation: Cap each ticker's history array at a fixed length (e.g. 300 points ≈ 2.5 minutes of simulator ticks at 500ms) via `.slice(-maxPoints)` as shown in Pattern 1 — cheap, bounded, and 2.5 minutes of visible history is more than enough for a sparkline/main-chart at MVP scope.

2. **Whether the new watchlist module should be a new `backend/app/watchlist/` package or added to `backend/app/portfolio/`**
   - What we know: The existing project structure gives `market/` and `portfolio/` each their own package with a `routes.py`/`service.py`/`models.py` shape; watchlist logic (add/remove tickers) is conceptually closer to `market/` (it drives what `MarketFeed` polls) but the CRUD/db-write shape matches `portfolio/`'s pattern more closely.
   - What's unclear: No existing precedent settles this exactly — Phase 1/2 never needed a watchlist *write* path (only `db.watchlist_tickers()` read).
   - Recommendation: A new `backend/app/watchlist/` package (Recommended Project Structure above) — keeps `market/` focused purely on price-fetching/streaming and `portfolio/` focused on money/trades, with `watchlist/` as its own third domain, matching the existing one-package-per-concern convention rather than overloading either existing package.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | `recharts` install, `next build` | ✓ | npm CLI functional (registry reachable) | — |
| Recharts (npm registry) | D-01 charts | ✓ | 3.10.1 confirmed on registry | — |

No missing dependencies block this phase — no new backend runtime dependencies are introduced (background task and SQL patterns reuse the existing `asyncio`/`sqlite3` stack already present).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (frontend) | Vitest 4.1.10 + jsdom (`frontend/vitest.config.ts`), no `@testing-library/react` installed |
| Framework (backend) | pytest 9.1.1 + pytest-asyncio (`backend/pyproject.toml`, `testpaths = ["tests"]`) |
| Config file (frontend) | `frontend/vitest.config.ts` |
| Config file (backend) | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command (frontend) | `cd frontend && npx vitest run <file>` |
| Quick run command (backend) | `cd backend && uv run pytest tests/<path> -x` (must run from `backend/` — see STATE.md environment note) |
| Full suite command (frontend) | `cd frontend && npm test` |
| Full suite command (backend) | `cd backend && uv run pytest` |

**Important, project-established convention (verified by reading existing test files):** `[VERIFIED: frontend/lib/flash.test.ts:1-10, frontend/package.json:1-20]` Phase 1 and Phase 2's `TEST-03`-equivalent frontend coverage (price flash animation, portfolio display calculations) was satisfied entirely by testing pure functions in `lib/*.ts` (e.g. `nextFlashState`, `derivePortfolioValue`) with plain Vitest `describe`/`it`/`expect` — no `@testing-library/react` component-rendering tests exist anywhere in the repo, and the package is not installed. Phase 3's `TEST-03` ("watchlist CRUD ... portfolio display calculations") should follow the identical pattern: test the pure logic in `lib/priceHistory.ts`, `lib/heatmap.ts`, and `lib/watchlistForm.ts` directly, not introduce a new RTL dependency to render `<Watchlist>`/`<Heatmap>` components. This keeps the test suite's dependency footprint unchanged.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-08 | Heatmap weight/P&L derivation is correct for a given portfolio snapshot | unit | `npx vitest run frontend/lib/heatmap.test.ts` | ❌ Wave 0 |
| PORT-08 | Squarified layout partitions items into rows with correct total weight per row | unit | `npx vitest run frontend/lib/heatmap.test.ts` | ❌ Wave 0 |
| PORT-09 | `GET /api/portfolio/history` returns snapshots in chronological order | integration | `uv run pytest tests/portfolio/test_routes.py -k history -x` | ❌ Wave 0 |
| PORT-09 | Post-trade snapshot is written atomically with the trade (same transaction) | integration | `uv run pytest tests/portfolio/test_service.py -k snapshot -x` | ❌ Wave 0 |
| PORT-09 | 30s background snapshot writer starts/stops cleanly (mirrors `test_feed.py`) | unit | `uv run pytest tests/market/test_snapshot_feed.py -x` | ❌ Wave 0 |
| WATCH-02 | `POST /api/watchlist` adds a ticker; duplicate add is rejected or idempotent | integration | `uv run pytest tests/watchlist/test_routes.py -k add -x` | ❌ Wave 0 |
| WATCH-03 | `DELETE /api/watchlist/{ticker}` removes a ticker | integration | `uv run pytest tests/watchlist/test_routes.py -k remove -x` | ❌ Wave 0 |
| WATCH-04 | `appendTick`/`pruneToWatchlist` accumulate and reset history correctly | unit | `npx vitest run frontend/lib/priceHistory.test.ts` | ❌ Wave 0 |
| WATCH-05 | Selecting a watchlist row updates the main-chart-selected ticker (existing `selectedTicker` state pattern, already present in `page.tsx`) | unit | Covered by existing `frontend/lib/*.test.ts` conventions; no new backend test needed | ✅ (pattern exists) |
| TEST-03 | Watchlist CRUD + portfolio display calcs (heatmap/history) covered by frontend unit tests | unit | `cd frontend && npm test` | ❌ Wave 0 (new files above) |

### Sampling Rate

- **Per task commit:** targeted `vitest run <file>` / `pytest <path> -x` for the file(s) touched
- **Per wave merge:** `cd frontend && npm test` and `cd backend && uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `frontend/lib/heatmap.test.ts` — covers PORT-08 (weight/P&L derivation, squarified row partitioning)
- [ ] `frontend/lib/priceHistory.test.ts` — covers WATCH-04 (`appendTick`, `pruneToWatchlist`)
- [ ] `frontend/lib/watchlistForm.test.ts` — covers WATCH-02 client-side validation
- [ ] `backend/tests/portfolio/test_routes.py` extension — covers PORT-09 `GET /api/portfolio/history`
- [ ] `backend/tests/portfolio/test_service.py` extension — covers PORT-09 post-trade snapshot write
- [ ] `backend/tests/market/test_snapshot_feed.py` — covers PORT-09's 30s background task (new file, mirrors `test_feed.py`)
- [ ] `backend/tests/watchlist/` — new test package for the new `watchlist/` module (mirrors `tests/portfolio/`)
- Framework install: none — Vitest and pytest are already fully configured; no new test framework needed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | Zero-auth by design (PLAN.md, single hardcoded `user_id="default"`) — unchanged this phase |
| V3 Session Management | no | No sessions exist in this app |
| V4 Access Control | no | No multi-user boundary exists to enforce |
| V5 Input Validation | yes | Watchlist ticker input: server-side validation before any DB write (uppercase/trim, reject empty/overlength strings) — mirror `execute_trade`'s existing `ticker.strip().upper()` pattern (`[VERIFIED: backend/app/portfolio/service.py:39]`, `ticker = ticker.strip().upper()`) |
| V6 Cryptography | no | No new secrets or crypto surface introduced this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| SQL injection via ticker input on new `INSERT`/`DELETE` watchlist queries | Tampering | Parameterized `?`-placeholder SQL — the existing, established convention throughout `database.py` and `service.py` (e.g. `"INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)"` `[VERIFIED: backend/app/db/database.py:88-93]`) — the new watchlist routes must follow the identical pattern, never string-format a ticker into SQL |
| Unbounded watchlist growth (no ticker count cap) causing `MarketFeed` to poll an ever-growing ticker list | Denial of Service (self-inflicted, low severity) | CONTEXT.md leaves this to implementer judgment ("no hard cap unless layout genuinely breaks") — a soft cap (e.g. reject add past N tickers client-side) is reasonable but not a hard security requirement for this single-user, zero-auth MVP |
| XSS via ticker symbol rendered unescaped in the DOM | Tampering/Info disclosure | React's default JSX text-node escaping already covers this (same as every other ticker render in `WatchlistRow`/`PositionRow`) — no `dangerouslySetInnerHTML` should be introduced anywhere in this phase's new components, matching Phase 1-2's `02-SECURITY.md` grep-gated precedent |

## Sources

### Primary (HIGH confidence)
- `npm view recharts version` / `time.created` / `time.modified` / `peerDependencies` / `repository.url` / `license` / `scripts.postinstall` — direct npm registry queries, run this session
- `backend/app/market/cache.py`, `backend/app/market/feed.py`, `backend/app/market/stream.py`, `backend/app/portfolio/service.py`, `backend/app/portfolio/routes.py`, `backend/app/db/database.py`, `backend/app/db/schema.sql`, `frontend/lib/usePriceStream.ts`, `frontend/lib/portfolio.ts`, `frontend/components/Watchlist.tsx`, `frontend/components/WatchlistRow.tsx`, `frontend/components/PriceCell.tsx`, `frontend/app/page.tsx`, `frontend/app/globals.css` — read directly this session

### Secondary (MEDIUM confidence)
- Context7 `/recharts/recharts` — `ResponsiveContainer` sizing warning source, CSS `var()` passthrough on `fill`/`stroke`, `accessibilityLayer` default-true since v3.0, supported `ResponsiveContainer` children list (confirms `<Treemap/>` exists as a built-in alternative, correctly declined per D-02)
- `frontend/node_modules/next/dist/docs/01-app/02-guides/static-exports.md` — bundled Next.js 16.3.1 docs confirming Client Components (including third-party chart libraries using browser APIs) are fully supported under `output: 'export'`, with no server-only feature required by Recharts

### Tertiary (LOW confidence, cross-checked to MEDIUM)
- WebSearch: squarified treemap algorithm references ([huy-nguyen/squarify](https://github.com/huy-nguyen/squarify), multiple independent implementations agreeing on the same Bruls/Huizing/van Wijk recursion) — cross-checked against training knowledge of the same well-documented algorithm, raised to MEDIUM confidence
- WebSearch: CSS flexbox `flex-grow` proportional-sizing technique (MDN-sourced summaries) — well-established, standard CSS behavior, cross-checked to MEDIUM confidence

## Metadata

**Confidence breakdown:**
- Standard stack (Recharts version/compat): HIGH — directly verified via live npm registry query and Context7 official docs
- Architecture (background task, transaction-scoped snapshot, price-history pruning): HIGH — derived from reading the actual source files this session, not assumed
- Heatmap algorithm: MEDIUM — cross-checked web sources, not read from the original academic paper
- Pitfalls: HIGH — `ResponsiveContainer` sizing behavior from Recharts' own source via Context7; `PriceCache` no-purge behavior verified by reading `cache.py` directly

**Research date:** 2026-08-17
**Valid until:** 2026-09-16 (30 days — stable, well-established libraries/patterns; Recharts version pin should be re-verified if this research is reused past that window)
