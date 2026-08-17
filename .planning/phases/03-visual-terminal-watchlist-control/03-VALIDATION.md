---
phase: 3
slug: visual-terminal-watchlist-control
status: draft
nyquist_compliant: false
wave_0_complete: false
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

*Populated with per-requirement targets from 03-RESEARCH.md's Validation Architecture — the planner assigns exact task IDs when it creates PLAN.md files.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | PORT-08 | — | Heatmap weight/P&L derivation correct for a given snapshot | unit | `npx vitest run frontend/lib/heatmap.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-08 | — | Squarified layout partitions items into rows with correct total weight per row | unit | `npx vitest run frontend/lib/heatmap.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-09 | — | `GET /api/portfolio/history` returns snapshots in chronological order | integration | `uv run pytest tests/portfolio/test_routes.py -k history -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-09 | — | Post-trade snapshot written atomically with the trade (same transaction) | integration | `uv run pytest tests/portfolio/test_service.py -k snapshot -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-09 | — | 30s background snapshot writer starts/stops cleanly | unit | `uv run pytest tests/market/test_snapshot_feed.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WATCH-02 | T-03-* (SQLi on new INSERT) | `POST /api/watchlist` adds a ticker; duplicate add rejected/idempotent | integration | `uv run pytest tests/watchlist/test_routes.py -k add -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WATCH-03 | T-03-* (SQLi on new DELETE) | `DELETE /api/watchlist/{ticker}` removes a ticker | integration | `uv run pytest tests/watchlist/test_routes.py -k remove -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WATCH-04 | — | `appendTick`/`pruneToWatchlist` accumulate and reset history correctly | unit | `npx vitest run frontend/lib/priceHistory.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WATCH-05 | — | Selecting a watchlist row updates the main-chart-selected ticker | unit | Covered by existing pattern; no new backend test | ✅ | ⬜ pending |
| TBD | TBD | TBD | TEST-03 | — | Umbrella: watchlist CRUD + portfolio display calcs | suite | `cd frontend && npm test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/lib/heatmap.test.ts` — covers PORT-08 (weight/P&L derivation, squarified row partitioning)
- [ ] `frontend/lib/priceHistory.test.ts` — covers WATCH-04 (`appendTick`, `pruneToWatchlist`)
- [ ] `frontend/lib/watchlistForm.test.ts` — covers WATCH-02 client-side validation
- [ ] `backend/tests/portfolio/test_routes.py` extension — covers PORT-09 `GET /api/portfolio/history`
- [ ] `backend/tests/portfolio/test_service.py` extension — covers PORT-09 post-trade snapshot write
- [ ] `backend/tests/market/test_snapshot_feed.py` — covers PORT-09's 30s background task (mirrors `test_feed.py`)
- [ ] `backend/tests/watchlist/` — new test package for the new `watchlist/` module (mirrors `tests/portfolio/`)
- Framework install: none — Vitest and pytest already fully configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Heatmap visual layout (rectangle sizing, green/red coloring) | PORT-08 (visual component) | Requires watching the rendered treemap in a browser; the weight/layout math itself is unit-tested | Open the app with 2+ positions, confirm rectangle area proportional to position weight and color matches P&L sign |
| P&L chart live growth | PORT-09 (visual component) | Requires waiting 30s+ in a browser to see a new point appear | Watch the P&L chart for 30+ seconds and after a trade, confirm new points appear |
| Sparkline progressive fill | WATCH-04 (visual component) | Requires watching the sparkline fill in over time in a browser | Load the page, watch a watchlist row's sparkline fill in as ticks arrive |
| Tablet-width layout | UI-04 | Requires resizing/viewing at tablet width in a browser | Resize to tablet width, confirm all panels stack vertically and remain usable |
| Chat panel placeholder appearance | UI-02 (D-03) | Visual confirmation of reserved slot | Confirm an empty placeholder panel is visible in the layout, sized reasonably |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
