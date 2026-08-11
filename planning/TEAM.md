# FinAlly Agent Team

Six specialist agents build the rest of the platform. Definitions live in
`.claude/agents/`. This document is the shared operating agreement: who owns
what, what order things happen in, and how agents hand off.

Every agent reads `PLAN.md` (the spec) and `API_CONTRACT.md` (the frozen
interface). `MARKET_DATA_SUMMARY.md` describes the one component that is
already finished.

## Members

| Agent | Owns | Depends on |
|---|---|---|
| `db-engineer` | `backend/app/db/` — schema, lazy init, seed, repositories | nothing |
| `backend-api-engineer` | `backend/app/main.py`, `backend/app/api/`, `backend/app/portfolio/` | db-engineer |
| `llm-engineer` | `backend/app/llm/`, `backend/app/api/chat.py` | db-engineer, backend-api-engineer |
| `frontend-engineer` | `frontend/` | API_CONTRACT.md only |
| `devops-engineer` | `Dockerfile`, `docker-compose.yml`, `scripts/`, `.env.example`, `.dockerignore` | frontend + backend build commands |
| `integration-tester` | `test/` | a running container |

## File ownership is exclusive

An agent edits only the paths it owns. Needing a change outside your paths is
not a reason to reach in — it is a reason to message the owner. Two agents
editing one file in a shared working directory produces silent, confusing
breakage.

Two shared-but-restricted exceptions:

- `backend/pyproject.toml` — anyone may `uv add` a dependency they need. Add
  only; never remove or re-pin another agent's dependency.
- `planning/API_CONTRACT.md` — owned by `backend-api-engineer`. Others propose
  changes by message; the owner edits.

## Off limits to everyone

`backend/app/market/` and `backend/tests/market/` are **complete and reviewed**
(101 tests, 99% coverage). Do not modify, refactor, or "improve" them. The one
piece of new code that touches this package is the FastAPI `lifespan` wiring in
`backend/app/main.py`, written by `backend-api-engineer` following the recipe in
`MARKET_DATA_SUMMARY.md` § "Usage in Downstream Code".

`planning/archive*/` are superseded drafts. Do not use them as reference.

## Build order

Work in waves. Within a wave, agents run in parallel.

**Wave 1 — foundation (parallel)**
- `db-engineer`: schema, lazy init, seed, repositories, unit tests.
- `frontend-engineer`: Next.js scaffold, static export config, dark theme,
  layout, all components driven by fixtures matching `API_CONTRACT.md`.
- `devops-engineer`: `.env.example` and the start/stop scripts.

**Wave 2 — backend (starts when db-engineer reports repositories ready)**
- `backend-api-engineer`: app factory, lifespan (market feed + cache),
  portfolio/watchlist/health routes, trade execution, snapshot background task.
- `llm-engineer`: LiteLLM client, structured output schema, system prompt,
  mock mode. Waits for the trade-execution service before wiring auto-execution.

**Wave 3 — integration**
- `frontend-engineer`: swap fixtures for real `fetch` + `EventSource`.
- `devops-engineer`: multi-stage Dockerfile, verify the container serves the
  built frontend and the API on port 8000.
- `integration-tester`: write Playwright specs and `docker-compose.test.yml`
  against `PLAN.md` §12.

**Wave 4 — verify and fix**
- `integration-tester` runs the suite against the container, files findings,
  and re-runs after each fix until green.

## Handoff protocol

When you finish a wave deliverable, message the agents listed as depending on
you. State what exists now, the import path or URL to use it, and anything you
deliberately left out. Do not announce completion of work you have not run.

When you are blocked, message the owner of the thing blocking you and keep
working on anything that doesn't depend on the answer. Do not idle, and do not
implement a stub in someone else's territory to unblock yourself.

## Bug reports from the Integration Tester

The Integration Tester does not fix code outside `test/`. It reports to the
owning agent with:

1. The failing spec name and the assertion that failed.
2. Observed vs. expected, quoted from the actual output.
3. The narrowest reproduction it found — a `curl` against the API, or a
   specific UI step.

The owning agent identifies the root cause before changing anything, fixes it,
and messages the tester to re-run. A test edited to make a real failure pass is
a defect, not a fix — if the tester believes the spec itself is wrong, it says
so and asks the owner to confirm before changing the spec.

## Definition of done, for every agent

- The code runs, and you have run it.
- Unit tests for your own area pass. Backend: `cd backend && uv run pytest`.
  Frontend: the project's test command.
- Backend lint is clean: `uv run ruff check app/ tests/` and
  `uv run ruff format --check app/ tests/`.
- No emoji anywhere in code, comments, log lines, or printed output.
- You reported honestly: what works, what you skipped, what you are unsure of.

## Conventions

- Python: `uv` only — `uv run pytest`, `uv add <pkg>`. Never `python3` or
  `pip install`. Python 3.12, line length 100, ruff `E,F,I,N,W`.
- Short modules, short functions, clear names. Docstrings over inline comments.
- Do not program defensively and do not over-engineer. No speculative
  abstraction layers, no config for things that have one value.
- Find the root cause before fixing a bug. Prove it, then fix it. No
  workarounds.
- Work incrementally: small steps, each one validated before the next.
