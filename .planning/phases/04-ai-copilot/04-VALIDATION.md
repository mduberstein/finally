---
phase: 4
slug: ai-copilot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-17
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8.3.0 (9.1.1 installed) + pytest-asyncio (`asyncio_mode = "auto"`), backend; Vitest ^4.1.10, frontend |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]`; `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/chat -x` — **must use `--extra dev`**; plain `uv run pytest` silently falls through to a system pytest lacking `pytest-asyncio` (known project gotcha) / `cd frontend && npm test -- lib/chat` |
| **Full suite command** | `cd backend && uv run --extra dev pytest` / `cd frontend && npm test` |
| **Estimated runtime** | ~2s (backend), ~1s (frontend) |

---

## Sampling Rate

- **After every task commit:** targeted `tests/chat/` file or `lib/chat` file for the module just touched
- **After every plan wave:** `cd backend && uv run --extra dev pytest` and `cd frontend && npm test` (full suites)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

*Populated with per-requirement targets from 04-RESEARCH.md's Validation Architecture — the planner assigns exact task IDs when it creates PLAN.md files.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | CHAT-01 | — | `POST /api/chat` returns `{message, actions}` shaped JSON | integration | `uv run --extra dev pytest tests/chat/test_routes.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-02 | — | Portfolio context (positions, cash, concentration, P&L) reaches the LLM prompt | unit | `uv run --extra dev pytest tests/chat/test_service.py::test_build_portfolio_context -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-03 | V5 Input Validation | A trade proposed + agreed executes via `execute_trade()`, no confirmation; LLM output revalidated before write | unit (mocked `call_llm`) | `uv run --extra dev pytest tests/chat/test_service.py -k trade -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-04 | V5 Input Validation | Watchlist add/remove executes via `add_ticker`/`remove_ticker`; LLM ticker revalidated before write | unit (mocked `call_llm`) | `uv run --extra dev pytest tests/chat/test_service.py -k watchlist -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-05 | — | Insufficient-cash/oversell trade surfaces as plain-language explanation, portfolio unchanged | unit | `uv run --extra dev pytest tests/chat/test_service.py -k rejected -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-06 | — | History persists and is readable after reload (fresh `GET /api/chat/history`) | integration | `uv run --extra dev pytest tests/chat/test_routes.py -k history -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-07 | — | Loading indicator shown while assistant thinks | unit (frontend) | `cd frontend && npm test -- ChatPanel` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-08 | — | LLM call shape matches `.claude/skills/cerebras/SKILL.md` exactly (model, `extra_body`, `response_format`) | unit (assert call args on monkeypatched `litellm.completion`) | `uv run --extra dev pytest tests/chat/test_llm.py -k call_shape -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-09 | V6 Cryptography (secret handling) | `LLM_MOCK=true` → deterministic response, zero network calls, no key echoed | unit | `uv run --extra dev pytest tests/chat/test_llm.py -k mock -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TEST-02 | — | `parse_response()` handles valid and malformed JSON without crashing | unit | `uv run --extra dev pytest tests/chat/test_llm.py -k parse -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/chat/__init__.py`, `test_llm.py`, `test_service.py`, `test_routes.py` — new test package, no existing coverage
- [ ] `frontend/lib/chat.test.ts`, `frontend/components/*.test.tsx` for the new chat components — mirrors existing `lib/trade.test.ts`/`lib/watchlistForm.test.ts` shape
- Framework install: none — pytest-asyncio and Vitest already fully configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Typing-dots loading animation | CHAT-07 (D-03) | Requires watching the animation render in a browser | Send a chat message, confirm animated dots appear in place of the assistant's next bubble while waiting |
| Action-card visual rendering | D-04 | Visual confirmation of bordered action card styling | Trigger a trade or watchlist change via chat, confirm a distinct bordered card renders beneath the assistant's message |
| Chat bubble left/right alignment | D-01 | Visual layout confirmation | Send messages, confirm user bubbles align right and assistant bubbles align left |
| Auto-scroll on load and on new message | D-11 | Requires observing scroll position in a browser | Reload with existing history, confirm transcript is scrolled to newest message; send a new message, confirm it scrolls again |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
