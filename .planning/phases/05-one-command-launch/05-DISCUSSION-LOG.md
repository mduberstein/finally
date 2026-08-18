# Phase 5: One-Command Launch - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-18
**Phase:** 5-One-Command Launch
**Areas discussed:** Data volume strategy, Fresh-start / demo reset, Windows script rigor, Auto-open browser on start

---

## Data volume strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Bind-mount ./db | Same db/finally.db file used by local `uv run uvicorn` dev today. Visible in checkout, trivial to inspect/back up/delete for a fresh demo. | ✓ |
| Named volume finally-data | Matches PLAN.md's literal example. Data lives inside Docker's own storage, not visible in checkout; more typical for production. | |
| You decide | Let the planner/executor pick based on what's simplest to implement correctly. | |

**User's choice:** Bind-mount ./db (Recommended)
**Notes:** No follow-up questions — user moved directly to next area.

---

## Fresh-start / demo reset

| Option | Description | Selected |
|--------|-------------|----------|
| Document a reset command | README/start script mentions manual `rm db/finally.db` before a real demo/grading run; lazy-init reseeds automatically. | ✓ |
| Separate scratch DB for E2E only | E2E suite already needs its own isolated DB per docker-compose.test.yml — leave local dev db/finally.db alone entirely. | |
| Both | E2E gets its own isolated DB (needed regardless) AND a documented manual reset step. | |

**User's choice:** Document a reset command (Recommended)

Follow-up question — should the reset be documentation-only or a script flag:

| Option | Description | Selected |
|--------|-------------|----------|
| Documentation only | Keeps scripts simple/idempotent per ROADMAP requirement. README/start output mentions the manual delete-and-restart step. | ✓ |
| Add a --reset flag | scripts/start_mac.sh --reset deletes db/finally.db before starting — more convenient but adds a destructive-action code path. | |

**User's choice:** Documentation only (Recommended)
**Notes:** E2E test isolation (docker-compose.test.yml's own scratch DB) is unaffected by this choice — it's already guaranteed by PLAN.md's existing E2E architecture, independent of the dev-DB reset story.

---

## Windows script rigor

| Option | Description | Selected |
|--------|-------------|----------|
| Best-effort mirror | Written to mirror the mac script's logic using standard PowerShell/Docker Desktop commands, unverified by actual execution, documented as such. | ✓ |
| You'll test them yourself | Written best-effort, then the user runs them on a real Windows machine and reports back issues. | |
| Skip Windows for now | Ship mac/Linux scripts only this phase; defer Windows equivalents to a follow-up (would leave INFRA-03 partially unmet). | |

**User's choice:** Best-effort mirror (Recommended)
**Notes:** No follow-up questions — user moved directly to next area.

---

## Auto-open browser on start

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-open | `open http://localhost:8000` on mac after start; nicer one-command demo experience. Windows equivalent uses `start`. | ✓ |
| Print URL only | Script prints the URL and exits; user opens it themselves. Simpler, no OS-specific browser-launch code path. | |

**User's choice:** Auto-open (Recommended)
**Notes:** This was the last selected area.

---

## Claude's Discretion

- Exact Dockerfile base images and multi-stage layer ordering/caching strategy
- Exact Playwright test file organization within `test/` and `docker-compose.test.yml` service naming
- `.env.example` exact contents/comment formatting (required variables already fixed by PLAN.md §5)

## Deferred Ideas

None — discussion stayed within phase scope. A `--reset` script flag was considered and explicitly declined (documentation-only chosen instead); this is a locked decision (D-02 in CONTEXT.md), not a deferred idea.
