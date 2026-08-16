---
phase: 2
slug: trading-portfolio
status: draft
nyquist_compliant: false
wave_0_complete: false
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

*Populated with per-requirement targets from 02-RESEARCH.md's Validation Architecture — the planner assigns exact task IDs when it creates PLAN.md files; each row below is filled in as the corresponding task is planned.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | PORT-01 | — | Fresh user has $10,000 cash | integration | `uv run --extra dev pytest tests/test_app.py -k cash -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-02 | T-02-* (SQLi/price-trust) | Buy fills at cache price, cash decreases, position created | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k buy -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-03 | T-02-* | Sell fills at cache price, cash increases, position reduced/removed | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k sell -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-04 | — | Insufficient cash rejected, state unchanged | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k insufficient_cash -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-05 | — | Overselling rejected, state unchanged | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k oversell -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-06 | — | `GET /api/portfolio` shape: ticker/qty/avg_cost/price/pnl/% change | integration | `uv run --extra dev pytest tests/portfolio/test_routes.py -k shape -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-07 | — | Total value = cash + Σ(qty × current price) | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k total_value -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PORT-10 | — | Every trade appends a `trades` row, never updates/deletes | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k trade_history -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-03 | — | Trade bar submits buy/sell with one click | manual/UAT | — (component unit coverage is TEST-03, Phase 3 — not added early) | n/a | ⬜ pending |
| TBD | TBD | TBD | TEST-01 | — | Umbrella: trade execution, P&L math, edge cases | suite | `uv run --extra dev pytest tests/portfolio/ -v` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | (concurrency) | T-02-* (lost-update race) | Concurrent trade requests do not corrupt cash/position state (`BEGIN IMMEDIATE`) | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k concurrent -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/portfolio/__init__.py` — new test package, mirrors `tests/market/`
- [ ] `backend/tests/portfolio/test_service.py` — covers PORT-02, PORT-03, PORT-04, PORT-05, PORT-07, PORT-10, and the concurrent-trade race case
- [ ] `backend/tests/portfolio/test_routes.py` — covers PORT-01, PORT-06 (`GET /api/portfolio` shape and status codes), plus `POST /api/portfolio/trade`'s HTTP-layer error mapping
- [ ] No new fixtures needed beyond the existing `_use_tmp_db(tmp_path, monkeypatch)` helper already in `tests/test_app.py` — reuse it

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trade bar one-click buy/sell submission and inline error rendering | UI-03 | Frontend component unit-test coverage for this element is TEST-03, scoped to Phase 3 per REQUIREMENTS.md traceability — not added early; this phase verifies the interaction live | Enter a ticker + quantity, click Buy/Sell, confirm cash/position update and inline error text on rejection |
| Header total portfolio value updates live with every price tick | PORT-07 (visual component) | Requires watching the running SSE stream in a browser; the value-computation math itself is unit-tested | Open the app, watch the header total value change as watchlist prices tick |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
