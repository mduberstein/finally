---
phase: 3
slug: visual-terminal-watchlist-control
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-17
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.10 + jsdom (frontend); pytest 9.1.1 + pytest-asyncio (backend). No `@testing-library/react` — established convention is testing pure `lib/*.ts` functions only. |
| **Config file** | `frontend/vitest.config.ts`; `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd frontend && npx vitest run <file>` / `cd backend && uv run pytest tests/<path> -x` (must run from `backend/`) |
| **Full suite command** | `cd frontend && npm test` / `cd backend && uv run pytest` |
| **Estimated runtime** | ~1s (frontend), ~2s (backend) |

---

## Sampling Rate

- **After every task commit:** targeted `vitest run <file>` / `pytest <path> -x` for the file(s) touched
- **After every plan wave:** `cd frontend && npm test` and `cd backend && uv run pytest` (full suites)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

*Reconciled 2026-08-20 against the actual executed plans and live-run test suite (State A audit — this table was seeded pre-execution with `TBD` task IDs and, in two rows, a since-corrected file path/filter; all commands below were re-run and confirmed green).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-04 | 03-04 | 4 | PORT-08 | — | Heatmap weight/P&L derivation correct for a given snapshot | unit | `cd frontend && npx vitest run lib/heatmap.test.ts` | ✅ | ✅ green |
| 03-04 | 03-04 | 4 | PORT-08 | — | Squarified layout partitions items into rows with correct total weight per row | unit | `cd frontend && npx vitest run lib/heatmap.test.ts` | ✅ | ✅ green |
| 03-03 | 03-03 | 3 | PORT-09 | — | `GET /api/portfolio/history` returns snapshots in chronological order | integration | `uv run --extra dev pytest tests/portfolio/test_routes.py -k history -x` | ✅ | ✅ green |
| 03-03 | 03-03 | 3 | PORT-09 | — | Post-trade snapshot written atomically with the trade (same transaction) | integration | `uv run --extra dev pytest tests/portfolio/test_service.py -k snapshot -x` | ✅ | ✅ green |
| 03-03 | 03-03 | 3 | PORT-09 | — | 30s background snapshot writer starts/stops cleanly | unit | `uv run --extra dev pytest tests/portfolio/test_snapshot_feed.py -x` (corrected path — draft said `tests/market/test_snapshot_feed.py`, which does not exist; the actual file lives under `tests/portfolio/`) | ✅ | ✅ green |
| 03-01/03-02 | 03-01, 03-02 | 1, 2 | WATCH-02 | T-03-* (SQLi on new INSERT) | `POST /api/watchlist` adds a ticker; duplicate add rejected/idempotent | integration | `uv run --extra dev pytest tests/watchlist/test_routes.py -k add -x` | ✅ | ✅ green |
| 03-01/03-02 | 03-01, 03-02 | 1, 2 | WATCH-03 | T-03-* (SQLi on new DELETE) | `DELETE /api/watchlist/{ticker}` removes a ticker | integration | `uv run --extra dev pytest tests/watchlist/test_routes.py -k remove -x` | ✅ | ✅ green |
| 03-02 | 03-02 | 2 | WATCH-04 | — | `appendTick`/`pruneToWatchlist` accumulate and reset history correctly | unit | `cd frontend && npx vitest run lib/priceHistory.test.ts` | ✅ | ✅ green |
| 03-04 | 03-04 | 4 | WATCH-05 | — | Selecting a watchlist row updates the main-chart-selected ticker | manual/UAT | — (`page.tsx` click-selection wiring is not unit-tested, consistent with the project's pure-function-only convention; verified live) | n/a | manual-only, `03-UAT.md` pass |
| 03-02/03-04 | 03-02, 03-04 | 2, 4 | TEST-03 | — | Umbrella: watchlist CRUD + portfolio display calcs | suite | `cd frontend && npm test` | ✅ | ✅ green (130 tests) — partial-by-convention: no test exercises the live `fetch`-based add/remove network call itself, only the pure derivation/validation functions (accepted tech debt, see milestone audit) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 files were created during execution and are confirmed present and green (one location differs from the original plan — noted below):

- [x] `frontend/lib/heatmap.test.ts` — covers PORT-08 (weight/P&L derivation, squarified row partitioning)
- [x] `frontend/lib/priceHistory.test.ts` — covers WATCH-04 (`appendTick`, `pruneToWatchlist`)
- [x] `frontend/lib/watchlistForm.test.ts` — covers WATCH-02 client-side validation
- [x] `backend/tests/portfolio/test_routes.py` extension — covers PORT-09 `GET /api/portfolio/history`
- [x] `backend/tests/portfolio/test_service.py` extension — covers PORT-09 post-trade snapshot write
- [x] `backend/tests/portfolio/test_snapshot_feed.py` — covers PORT-09's 30s background task (planned location was `tests/market/`; executor placed it under `tests/portfolio/` instead, alongside the rest of the snapshot-related tests — a reasonable deviation, now reflected above)
- [x] `backend/tests/watchlist/` — new test package for the new `watchlist/` module (mirrors `tests/portfolio/`)
- Framework install: none — Vitest and pytest already fully configured

---

## Manual-Only Verifications

All items below are signed off `pass` in `03-UAT.md` (10/10).

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Heatmap visual layout (rectangle sizing, green/red coloring) | PORT-08 (visual component) | Requires watching the rendered treemap in a browser; the weight/layout math itself is unit-tested | Open the app with 2+ positions, confirm rectangle area proportional to position weight and color matches P&L sign |
| P&L chart live growth | PORT-09 (visual component) | Requires waiting 30s+ in a browser to see a new point appear | Watch the P&L chart for 30+ seconds and after a trade, confirm new points appear |
| Sparkline progressive fill | WATCH-04 (visual component) | Requires watching the sparkline fill in over time in a browser | Load the page, watch a watchlist row's sparkline fill in as ticks arrive |
| Selecting a watchlist row updates the main chart, isolated from the remove control | WATCH-05 | `page.tsx` click-selection wiring is not unit-tested, consistent with the project's pure-function-only convention | Click a watchlist row, confirm the chart switches; click a different row's remove control, confirm the chart stays put |
| Tablet-width layout | UI-04 | Requires resizing/viewing at tablet width in a browser | Resize to tablet width, confirm all panels stack vertically and remain usable |
| Chat panel placeholder appearance | UI-02 (D-03) | Visual confirmation of reserved slot | Confirm an empty placeholder panel is visible in the layout, sized reasonably |

---

## Validation Sign-Off

- [x] All tasks have automated verify or are correctly routed to Manual-Only
- [x] Sampling continuity: no gaps in automated coverage for testable requirements
- [x] Wave 0 covers all MISSING references (all Wave 0 files present and green)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-20 (retroactive reconciliation; underlying requirements already independently confirmed in `03-VERIFICATION.md` and `03-UAT.md`)

## Validation Audit 2026-08-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 functional gaps. 10 rows had `TBD` task IDs; 1 row (`PORT-09` background writer) named a test file path (`tests/market/test_snapshot_feed.py`) that does not exist — the executor correctly placed the file at `tests/portfolio/test_snapshot_feed.py` instead, but the draft was never updated to match; `WATCH-05` had no real automated command behind its claimed coverage. |
| Resolved | 11 (Task ID / Plan / Wave columns filled for 10 rows; snapshot-feed path corrected; WATCH-05 reclassified from a fabricated "covered" claim to accurately-described manual-only, backed by its `03-UAT.md` pass) |
| Escalated | 0 |
