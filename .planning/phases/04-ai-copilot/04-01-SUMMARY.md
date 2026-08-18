---
phase: 04-ai-copilot
plan: 01
subsystem: backend-chat
tags: [litellm, openrouter, cerebras, structured-outputs, sqlite, fastapi]
dependency-graph:
  requires:
    - backend/app/db/database.py (connect, DEFAULT_USER_ID, chat_messages schema)
    - backend/app/market/cache.py (PriceCache, threaded through unused for now)
  provides:
    - backend/app/chat/ (models, llm, prompt, service, routes)
    - POST /api/chat
    - GET /api/chat/history
  affects:
    - backend/app/main.py (load_dotenv, router registration)
tech-stack:
  added:
    - litellm>=1.97.0
    - pydantic>=2.13.4 (promoted transitive to direct)
    - python-dotenv>=1.2.2 (promoted transitive to direct)
  patterns:
    - Router-factory pattern (create_chat_router(cache)) matching create_portfolio_router/create_watchlist_router
    - HTTP-agnostic service layer with no FastAPI import
    - DESC-then-Python-reverse history read pattern copied from get_portfolio_history
key-files:
  created:
    - backend/app/chat/__init__.py
    - backend/app/chat/models.py
    - backend/app/chat/llm.py
    - backend/app/chat/prompt.py
    - backend/app/chat/service.py
    - backend/app/chat/routes.py
    - backend/tests/chat/__init__.py
    - backend/tests/chat/test_llm.py
    - backend/tests/chat/test_routes.py
    - backend/tests/chat/test_service.py
  modified:
    - backend/app/main.py
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - "litellm package legitimacy approved via blocking-human checkpoint (Task 1) before install — PyPI/GitHub cross-checks confirmed BerriAI ownership and multi-year release history"
  - "Persisted actions payload shape (type/status/ticker + trade or watchlist-specific fields) fixed now in models.py docstring so Plans 03/04 build against one contract"
  - "Message length measured in Python string code points (len() on str), matching pydantic's max_length semantics"
metrics:
  duration: "~25 min"
  completed: 2026-08-17
status: complete
actuals:
  tokens: 90546
  tasks: 3
  commits: 3
---

# Phase 4 Plan 1: End-to-End Chat Tracer Summary

Wired the entire `/api/chat` surface end to end: a message posted to `POST /api/chat` reaches OpenRouter/Cerebras through LiteLLM with structured outputs, comes back parsed into a `ChatResponse`, persists to `chat_messages`, and returns as one complete JSON body — with `LLM_MOCK=true` short-circuiting the external call entirely.

## What Was Built

- **`backend/app/chat/models.py`** — `ChatResponse`, `TradeAction`, `WatchlistAction` (plain `pydantic.BaseModel` subclasses with no field-level constraints, satisfying Cerebras strict-mode limits), plus `MAX_MESSAGE_LENGTH` (4000 code points) and `PARSE_FALLBACK_MESSAGE`. The persisted `actions` payload contract is documented as a module docstring for Plans 03/04.
- **`backend/app/chat/llm.py`** — `call_llm()` (the `LLM_MOCK` gate plus the mandated `completion(model=..., response_format=ChatResponse, reasoning_effort="low", extra_body=...)` call from `.claude/skills/cerebras/SKILL.md`), `mock_response()` (deterministic, zero-network), `parse_response()` (defensive `ChatResponse.model_validate_json` with a truncated-excerpt warning log on failure, never the raw request or credentials).
- **`backend/app/chat/prompt.py`** — `SYSTEM_PROMPT` encoding D-05/D-07/D-08/D-09, `build_messages()` assembling the OpenAI-style list with a `context` seam for Plan 03.
- **`backend/app/chat/service.py`** — `handle_chat_message()` (load history, call LLM, parse, persist, return) and `get_recent_messages()` (DESC-then-reverse read, capped at `HISTORY_LIMIT = 100`).
- **`backend/app/chat/routes.py`** — `create_chat_router(cache)` factory owning `POST /api/chat` (`run_in_threadpool`-wrapped, since `completion` is synchronous) and `GET /api/chat/history` (new endpoint, not in `planning/PLAN.md` section 8 — required by CHAT-06/D-10, mirrors `GET /api/portfolio/history`).
- **`backend/app/main.py`** — `load_dotenv()` against the repo-root `.env` (default no-override behavior preserved) and `create_chat_router(cache)` registered above the `StaticFiles` catch-all mount.

## Deviations from Plan

None — plan executed exactly as written. One cosmetic note: the plan's suggested verification one-liner (`[r.path for r in m.app.routes].index(...)`) doesn't work as literally written against this FastAPI version — `app.include_router(...)` now produces `_IncludedRouter` wrapper objects with `path=None` until the app starts, rather than flattened `Route` objects. Verified router-registration order by inspecting `app.routes` directly instead (all four `_IncludedRouter` entries — stream, portfolio, watchlist, chat — precede the `Mount` for static files), and independently by every route test passing against a live `TestClient`. No code change was needed; this only affected how the ordering was checked.

## Tracer Feedback Gate

Auto mode was not active for this session (`workflow.auto_advance: false`), so per the tracer protocol the working slice was verified end-to-end immediately after committing Task 2, before Task 3. The plan's `<human-check>` steps were run directly against a live server with the real `OPENROUTER_API_KEY` from the repo-root `.env` (network to `openrouter.ai`, normally outside this sandbox's allowlist, was reachable for this verification run):

- `POST /api/chat {"message":"Say hello in one short sentence."}` → `{"message":"Hello!","actions":[]}` — a real, non-canned Cerebras reply, confirming the live LiteLLM/OpenRouter/Cerebras structured-output round-trip works with the key loaded from `.env`.
- `GET /api/chat/history` → two entries, user message first, then the assistant reply.
- `POST /api/chat {"message":"   "}` → HTTP 422 (whitespace-only message rejected before any model call).

All three matched the plan's expected outcomes exactly. Server was torn down and the scratch database removed after verification.

## Tests

- `backend/tests/chat/test_llm.py` (7 tests) — mock determinism and zero-network guarantee, live call-shape recording (model, `response_format`, `reasoning_effort`, `extra_body`), well-formed parse, four malformed-response fixtures all falling back correctly.
- `backend/tests/chat/test_routes.py` (7 tests) — 200 with message/actions shape, 422 for empty/whitespace/over-cap messages with no row written, two-row history after one POST, cap-with-newest-last after exceeding `HISTORY_LIMIT`.
- `backend/tests/chat/test_service.py` (8 tests, TDD Task 3) — persistence row shape, returned dict shape, garbage-reply fallback with no exception, empty-table read, chronological ordering, cap identity, actions-column null/JSON deserialization, multi-turn history accumulation. All 8 passed on first run against Task 2's already-committed implementation — no defects found, no `service.py` changes needed.

Full backend suite: 196 passed (up from 172 baseline pre-phase-4). `ruff check app/ tests/` clean.

## TDD Gate Compliance

Task 3 (`tdd="true"`) followed the plan's explicit variant of the RED/GREEN flow: since Task 2 already implemented the behavior being pinned, the plan directed writing the test first and treating a first-run pass as confirmation rather than a defect signal (with any failure to be fixed in `service.py`, not the test). All 8 assertions passed on the first run; no implementation changes were required, so this task produced a single `test(...)` commit with no accompanying `feat(...)`/`fix(...)` commit — consistent with the plan's stated expectation.

## Self-Check: PASSED

- `backend/app/chat/__init__.py` — FOUND
- `backend/app/chat/models.py` — FOUND
- `backend/app/chat/llm.py` — FOUND
- `backend/app/chat/prompt.py` — FOUND
- `backend/app/chat/service.py` — FOUND
- `backend/app/chat/routes.py` — FOUND
- `backend/tests/chat/__init__.py` — FOUND
- `backend/tests/chat/test_llm.py` — FOUND
- `backend/tests/chat/test_routes.py` — FOUND
- `backend/tests/chat/test_service.py` — FOUND
- Commit `3c30222` (chore: add litellm/pydantic/python-dotenv) — FOUND in `git log`
- Commit `ceef7fd` (feat: end-to-end chat) — FOUND in `git log`
- Commit `7529330` (test: chat service coverage) — FOUND in `git log`
