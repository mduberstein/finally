---
phase: 2
slug: trading-portfolio
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`backend/pyproject.toml` pins `pytest>=8.3.0`) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --extra dev pytest tests/portfolio/ -v` |
| **Full suite command** | `uv run --extra dev pytest -v` |
| **Estimated runtime** | ~10 seconds (quick), ~30 seconds (full, includes `tests/market/`) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --extra dev pytest tests/portfolio/ -v`
- **After every plan wave:** Run `uv run --extra dev pytest -v` (full backend suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Reconciled 2026-08-20 against the actual executed plans and live-run test suite (State A audit — this table was seeded pre-execution with `TBD` task IDs; all commands below were re-run and confirmed green).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01 | 02-01 | 1 | PORT-01 | — | Fresh user has $10,000 cash | integration | `uv run --extra dev pytest tests/ -k cash -x` | ✅ | ✅ green |
| 02-01 | 02-01 | 1 | PORT-02 | T-02-* (SQLi/price-trust) | Buy fills at cache price, cash decreases, position created | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k buy -x` | ✅ | ✅ green |
| 02-02 | 02-02 | 2 | PORT-03 | T-02-* | Sell fills at cache price, cash increases, position reduced/removed | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k sell -x` | ✅ | ✅ green |
| 02-01/02-02 | 02-01, 02-02 | 1, 2 | PORT-04 | — | Insufficient cash rejected, state unchanged | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k insufficient_cash -x` | ✅ | ✅ green |
| 02-02 | 02-02 | 2 | PORT-05 | — | Overselling rejected, state unchanged | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k oversell -x` | ✅ | ✅ green |
| 02-03 | 02-03 | 2 | PORT-06 | — | `GET /api/portfolio` shape: ticker/qty/avg_cost/price/pnl/% change | integration | `uv run --extra dev pytest tests/portfolio/test_routes.py -k shape -x` | ✅ | ✅ green |
| 02-01/02-03 | 02-01, 02-03 | 1, 2 | PORT-07 | — | Total value = cash + Σ(qty × current price) | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k total_value -x` | ✅ | ✅ green |
| 02-01 | 02-01 | 1 | PORT-10 | — | Every trade appends a `trades` row, never updates/deletes | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k trade_history -x` | ✅ | ✅ green |
| 02-01/02-02 | 02-01, 02-02 | 1, 2 | UI-03 | — | Trade bar submits buy/sell with one click | manual/UAT | — (component unit coverage is TEST-03, Phase 3 scope by convention) | n/a | manual-only, `02-UAT.md` pass |
| 02-02 | 02-02 | 2 | TEST-01 | — | Umbrella: trade execution, P&L math, edge cases | suite | `uv run --extra dev pytest tests/portfolio/ -v` | ✅ | ✅ green (26 tests) |
| 02-02 | 02-02 | 2 | (concurrency) | T-02-* (lost-update race) | Concurrent trade requests do not corrupt cash/position state (`BEGIN IMMEDIATE`) | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k concurrent -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 files were created during execution and are confirmed present and green:

- [x] `backend/tests/portfolio/__init__.py` — test package, mirrors `tests/market/`
- [x] `backend/tests/portfolio/test_service.py` — covers PORT-02, PORT-03, PORT-04, PORT-05, PORT-07, PORT-10, and the concurrent-trade race case
- [x] `backend/tests/portfolio/test_routes.py` — covers PORT-01, PORT-06 (`GET /api/portfolio` shape and status codes), plus `POST /api/portfolio/trade`'s HTTP-layer error mapping
- [x] No new fixtures needed beyond the existing `_use_tmp_db(tmp_path, monkeypatch)` helper already in `tests/test_app.py` — reused as planned

---

## Manual-Only Verifications

Both items below are signed off `pass` in `02-UAT.md` (4/4, including the 5 judgment-tier prohibitions).

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trade bar one-click buy/sell submission and inline error rendering | UI-03 | Frontend component unit-test coverage for this element is TEST-03, scoped to Phase 3 per REQUIREMENTS.md traceability — not added early; this phase verifies the interaction live | Enter a ticker + quantity, click Buy/Sell, confirm cash/position update and inline error text on rejection |
| Header total portfolio value updates live with every price tick | PORT-07 (visual component) | Requires watching the running SSE stream in a browser; the value-computation math itself is unit-tested | Open the app, watch the header total value change as watchlist prices tick |

---

## Validation Sign-Off

- [x] All tasks have automated verify or are correctly routed to Manual-Only
- [x] Sampling continuity: no gaps in automated coverage for testable requirements
- [x] Wave 0 covers all MISSING references (all Wave 0 files present and green)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-20 (retroactive reconciliation; underlying requirements already independently confirmed in `02-VERIFICATION.md` and `02-UAT.md`)

## Validation Audit 2026-08-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 functional gaps. 11 rows had `TBD` task IDs and unfilled `File Exists`/`Status` columns from the pre-execution draft — reconciled against actual Plan IDs and a live re-run of every listed command (all green; full project backend suite is 228/228 as of this audit). |
| Resolved | 11 (Task ID / Plan / Wave columns filled; Status flipped to green after re-running every listed command) |
| Escalated | 0 |
