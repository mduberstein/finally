---
phase: 1
slug: live-streaming-terminal
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-20
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> Reconstructed retroactively on 2026-08-20 (State B — no VALIDATION.md existed at plan time; this phase predates the Nyquist validation gate). Built from `01-01-PLAN.md`..`01-04-PLAN.md`, `01-VERIFICATION.md`, and `01-UAT.md`, then cross-checked live against the actual test suite.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio (backend); Vitest 4.1.10 + jsdom (frontend). No `@testing-library/react` — established convention is testing pure `lib/*.ts` functions only, not rendered components. |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]`; `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/ -k <marker> -x` (must use `--extra dev` — plain `uv run pytest` silently falls through to a system pytest lacking `pytest-asyncio`) / `cd frontend && npx vitest run <file>` |
| **Full suite command** | `cd backend && uv run --extra dev pytest` / `cd frontend && npm test` |
| **Estimated runtime** | ~3s (backend, 228 tests), ~3s (frontend, 130 tests) |

---

## Sampling Rate

- **After every task commit:** targeted `pytest tests/<path> -x` / `vitest run <file>` for the module just touched
- **After every plan wave:** full backend + frontend suites
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01 | 01-01 | 1 | MARKET-01 | Watchlist prices update live via SSE from `PriceCache`/`MarketFeed` | integration | `uv run --extra dev pytest tests/test_app.py -k Stream -x` | ✅ | ✅ green |
| 01-01 | 01-01 | 1 | MARKET-04 | `MarketFeed` starts on lifespan startup with simulator fallback, stops cleanly | unit | `uv run --extra dev pytest tests/test_app.py::TestLifespan -x` | ✅ | ✅ green |
| 01-01 | 01-01 | 1 | WATCH-01 | Fresh DB seeds exactly the 10 default tickers | unit | `uv run --extra dev pytest tests/test_db.py::TestInitialize -x` | ✅ | ✅ green |
| 01-01 | 01-01 | 1 | INFRA-01 | SQLite lazily initializes schema and seeds default data on first run; reuses existing data on restart | unit | `uv run --extra dev pytest tests/test_db.py -x` | ✅ | ✅ green |
| 01-02 | 01-02 | 2 | UI-01 | Dark trading-terminal theme applied consistently | — | none — CSS/visual property, no automated test exists (established convention: no component-rendering or CSS-snapshot tests in this repo) | ❌ (by convention) | manual-only |
| 01-03 | 01-03 | 3 | MARKET-02 | Flash state machine: correct direction/fade-window logic, time-injected (no fake timers) | unit | `cd frontend && npx vitest run lib/flash.test.ts` | ✅ | ✅ green (logic); rendered tint/fade is manual-only |
| 01-04 | 01-04 | 3 | MARKET-03 | 3-state connection reducer: transitions + staleness downgrade, time-injected | unit | `cd frontend && npx vitest run lib/connection.test.ts` | ✅ | ✅ green (logic); live recovery cycle is manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files or framework installs were needed — `backend/tests/test_app.py`, `backend/tests/test_db.py`, `frontend/lib/flash.test.ts`, and `frontend/lib/connection.test.ts` were all written as part of the original plan execution and remain green.

---

## Manual-Only Verifications

All five items below are signed off `pass` in `01-UAT.md` (5/5).

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dark theme applied consistently (backgrounds, borders, no pure black) | UI-01 | CSS/visual property; project convention has no component-rendering or CSS-snapshot tests | Open the app, confirm `#0d1117`/`#161b22`/`#30363d` palette and no pure-black panels |
| Price flash tint and fade timing | MARKET-02 (visual component) | `flash.ts`'s state machine is fully unit-tested (13/13), but the rendered tint-and-fade in a browser is not exercised by any automated test | Watch the live watchlist grid for ~30s, confirm green/red tint fades within ~500ms |
| Reduced-motion suppression | MARKET-02 (visual component) | Requires an OS-level accessibility setting and visual confirmation | Set the OS to reduce motion, reload, confirm tint animation stops while glyph/percent remain |
| Row hover/selection/focus affordances | UI-01 (visual component) | Requires live mouse/keyboard interaction in a browser | Hover, click, and tab to a watchlist row; confirm border stripe and focus ring appear |
| Connection indicator live resilience cycle | MARKET-03 (visual component) | `reduceConnection` is fully unit-tested (11/11), but live EventSource retry/recovery against a killed-and-restarted backend requires a live browser session and process control | Stop and restart uvicorn without touching the browser; confirm the dot cycles Connected → Reconnecting → Disconnected → Connected automatically |

---

## Validation Sign-Off

- [x] All tasks have automated verify or are correctly routed to Manual-Only
- [x] Sampling continuity: no gaps in automated coverage for testable requirements
- [x] Wave 0 covers all MISSING references (none found — existing infra sufficient)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-20 (retroactive reconciliation; underlying requirements already independently confirmed in `01-VERIFICATION.md` and `01-UAT.md`)

## Validation Audit 2026-08-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 (all functionally-testable requirements already had passing automated coverage; UI-01 and the 4 live/rendering behaviors were already correctly routed to human verification, signed off in `01-UAT.md`) |
| Resolved | 0 |
| Escalated | 0 |
