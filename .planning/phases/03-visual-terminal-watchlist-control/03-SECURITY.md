---
phase: 03
slug: visual-terminal-watchlist-control
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-17
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser → `POST /api/watchlist` | Untrusted ticker string crosses into a database write | User-typed ticker symbol |
| browser → `DELETE /api/watchlist/{ticker}` | Untrusted path segment reaches a delete statement | Ticker symbol path segment |
| `watchlist` table → `MarketFeed` | Table contents drive which tickers the background feed polls every tick | Ticker list |
| add-form input → `/api/watchlist` | User-typed text leaves the browser toward a database write | Ticker symbol |
| ticker string → DOM | User-supplied text rendered into watchlist rows, heatmap cells, chart headers, and accessible labels | Ticker symbol text |
| price stream → browser memory | Unbounded per-ticker history would grow for as long as the tab stays open | Accumulated price points |
| simulator price → user judgment | A price shown for an invented symbol can be misread as evidence the symbol is real | Simulated price data |
| trade transaction → `portfolio_snapshots` | New durable write joins the only financial write path in the system | Portfolio total value |
| background task → SQLite | A writer running outside any request touches the database on a timer | Portfolio snapshot rows |
| browser → `GET /api/portfolio/history` | Portfolio value history crosses out to the client | Historical snapshot series |
| npm registry → build | The phase's only new third-party dependency enters the frontend bundle | `recharts@3.10.1` |
| portfolio snapshot → heatmap geometry | Server-supplied numbers drive element sizing, not just text | Position weight values |
| layout → the simulated-data disclaimer | A reflow can change what a user sees before they scroll, including whether the simulation notice is visible | Disclaimer visibility |
| reserved chat slot → Phase 4 | A panel shipped now becomes the container a later phase's untrusted LLM output renders into | Static placeholder only (Phase 3) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | SQL in `backend/app/watchlist/service.py` | high | mitigate | Every INSERT/DELETE binds through `?` placeholders — confirmed via grep, no string interpolation in any SQL statement. | closed |
| T-03-02 | Tampering | `ticker` field of POST/DELETE `/api/watchlist` | high | mitigate | `normalize_ticker` enforces `^[A-Z]{1,10}$` server-side (`backend/app/watchlist/service.py:20,29`) before any DB access; non-matching input raises `InvalidTickerError` → 400. | closed |
| T-03-03 | Denial of service | Unbounded watchlist growth driving `MarketFeed`'s per-tick list | medium | mitigate | `MAX_WATCHLIST_TICKERS = 50` enforced inside the insert's own connection (`service.py:18,48-49`). | closed |
| T-03-05 | Repudiation | Watchlist writes leave no audit trail | low | accept | `added_at` timestamps adds; deletes are not journalled. Single-user, zero-auth, loopback app with no compliance surface. | closed (accepted) |
| T-03-18 | Elevation of privilege | Watchlist DELETE statement's table scope | high | mitigate | `DELETE FROM watchlist WHERE user_id = ? AND ticker = ?` (`service.py:75`) names exactly one table; test suite asserts `positions`/`trades` unchanged across a delete. | closed |
| T-03-SC | Tampering | Package-manager installs, Plan 01 | low | mitigate | No `uv add`/`npm install` run in this plan. | closed |
| T-03-04 | Tampering | User-supplied ticker text rendered into DOM (watchlist rows, aria-labels) | medium | mitigate | No `dangerouslySetInnerHTML` present in any Phase 3 component (grep-confirmed across all 9 new/modified components) — all text reaches the DOM as escaped JSX. | closed |
| T-03-19 | Denial of service | Per-ticker price history accumulating in browser memory | low | mitigate | `MAX_HISTORY_POINTS = 300` (`frontend/lib/priceHistory.ts:14`) trims every array on append; `pruneToWatchlist` drops arrays for removed tickers. Bound: 300 × 50-ticker cap. | closed |
| T-03-20 | Spoofing | Simulator-generated price for a user-invented symbol | medium | mitigate | Simulated-data disclaimer stays the first element inside `<main>` at both widths (`frontend/app/page.tsx:127-129`), never conditionally hidden. | closed |
| T-03-21 | Elevation of privilege | Removal flow's reach into portfolio state | medium | mitigate | `handleRemove` (`page.tsx:108-121`) issues exactly one DELETE against `/api/watchlist/{ticker}` and mutates only watchlist state — grep-confirmed no portfolio fetch/mutation on this path; UAT test 3 confirmed cash/positions unchanged after a live removal. | closed |
| T-03-SC (02) | Tampering | Package-manager installs, Plan 02 | low | mitigate | No `npm install` run in this plan; `lucide-react` already a direct dependency. | closed |
| T-03-06 | Tampering | Snapshot INSERT inside `execute_trade` | high | mitigate | Insert runs on the already-open `BEGIN IMMEDIATE` transaction (`backend/app/portfolio/service.py:54,76`), bound through `?` placeholders; any exception hits the existing rollback branch. | closed |
| T-03-07 | Tampering | `GET /api/portfolio/history` query | high | mitigate | Only caller-influenced value is a server-side default row limit with no request parameter; bound through `?` placeholder. | closed |
| T-03-08 | Denial of service | Unbounded `portfolio_snapshots` growth / response size | medium | mitigate | `SNAPSHOT_HISTORY_LIMIT = 1000` (`service.py:24,133`) bounds response size regardless of table size. | closed |
| T-03-09 | Denial of service | Background writer blocking the event loop | medium | mitigate | Synchronous SQLite write dispatched through `run_in_threadpool` (`backend/app/portfolio/snapshot_feed.py:13,82`); raising recorder is logged, loop continues. | closed |
| T-03-10 | Information disclosure | Portfolio value history served to client | low | accept | Response carries only the single local user's own simulated total value — data already visible in the header. Single-user loopback app; revisit at Phase 5 container publish. | closed (accepted) |
| T-03-SC-02 | Tampering | `npm install recharts@3.10.1` | high | mitigate | `03-RESEARCH.md` Package Legitimacy Audit: manual OK/Approved verdict (created 2015, real GitHub source, MIT licence, no postinstall script); version pinned exactly, lockfile committed. Confirmed the only new dependency across the whole phase (`git log -- frontend/package.json` shows one touching commit, `1866c40`). | closed |
| T-03-11 | Tampering | Ticker/numeric text in `HeatmapCell`, `MainChart` headers, tooltips | medium | mitigate | No `dangerouslySetInnerHTML` in any Phase 3 component (grep-confirmed). | closed |
| T-03-12 | Denial of service | Client-side price history feeding main chart on every SSE tick | medium | mitigate | Same `MAX_HISTORY_POINTS` accumulator bound as T-03-19; chart itself performs no accumulation. | closed |
| T-03-13 | Denial of service | Chart-library resize observers multiplying across panels | low | mitigate | Exactly two `recharts` imports exist in the whole app (`MainChart.tsx`, `PnlChart.tsx`, grep-confirmed); all other sparklines are hand-rolled SVG with no observer. | closed |
| T-03-14 | Tampering | Heatmap geometry derived from portfolio values | low | mitigate | `deriveHeatmapItems`/`squarify` (`frontend/lib/heatmap.ts:37,90`) are pure numeric functions (`Math.max`/`Math.min`/`Math.sqrt` only); a wrong number produces a wrong-sized rectangle, never a script or layout escape. | closed |
| T-03-SC (04) | Tampering | Package-manager installs, Plan 04 | low | mitigate | No `uv add`/`npm install` run in this plan. | closed |
| T-03-15 | Spoofing | Simulated figures shown without disclaimer after a layout reflow | medium | mitigate | Disclaimer is the first element inside `<main>` at both widths (`page.tsx:127-129`), no panel conditionally hidden. | closed |
| T-03-16 | Tampering | Reserved chat panel as future rendering surface for model output | low | mitigate | `ChatPlaceholder.tsx` ships with zero input, handler, or dynamic state — confirmed by direct file read; pure static JSX. Inert container for Phase 4, not pre-wired. | closed |
| T-03-17 | Denial of service | Chart panels re-measuring on every viewport change | low | accept | Two library chart instances register resize observers; cost is re-renders on a local single-user page only. | closed (accepted) |
| T-03-SC (05) | Tampering | Package-manager installs, Plan 05 | low | mitigate | No `uv add`/`npm install` run in this plan. | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-05 | Watchlist add/remove leaves no audit trail beyond `added_at`. Single-user, zero-auth, localhost-only app with no compliance surface. | Phase 3 execution | 2026-08-17 |
| AR-03-02 | T-03-10 | Portfolio history endpoint discloses only the single local user's own data, already visible elsewhere in the UI. Revisit at Phase 5 container publish. | Phase 3 execution | 2026-08-17 |
| AR-03-03 | T-03-17 | Resize-observer re-render cost on chart panels is bounded to a local single-user session. | Phase 3 execution | 2026-08-17 |

*Carried forward from prior phases, still open and correctly deferred (not re-litigated here): AR-01-01/T-01-06 (error response secrets, revisit Phase 5), AR-01-02/T-01-07 (SSE auth surface, revisit Phase 5), T-01-09 (frontend secret handling, revisit Phase 4 chat panel — Phase 3's `ChatPlaceholder` is inert, so this stays deferred), AR-02-01 (trade rejection detail, revisit Phase 5), AR-02-02 (trade rate limiting, revisit Phase 5).*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-17 | 27 | 27 | 0 | GSD orchestrator (grep-level ASVS L1 verification against implementation, register authored at plan time across all 5 plans) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-17
