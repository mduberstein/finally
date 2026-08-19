---
phase: 5
slug: one-command-launch
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-18
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Docker Compose + Playwright 1.62.1 (E2E); pytest 9.1.1 (backend unit, pre-existing) |
| **Config file** | `test/docker-compose.test.yml`, `test/playwright.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run --extra dev pytest && uv run --extra dev ruff check app/` |
| **Full suite command** | `docker compose -f test/docker-compose.test.yml down -v --remove-orphans; docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright; RC=$?; docker compose -f test/docker-compose.test.yml down -v --remove-orphans; exit $RC` |
| **Estimated runtime** | ~3-4s for the Playwright run itself (`5 passed (3.2s)` observed); several minutes including Docker image build |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run --extra dev pytest` (backend tasks) or the task's own `<automated>` Docker/compose chain
- **After every plan wave:** Run the full E2E suite (`docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~60s (dominated by Docker build, not test execution)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | INFRA-02 | T-05-01 / T-05-02 | Non-root user, no `.env` baked into image | integration | `docker build -t finally:dev . && ... curl -sf http://localhost:8000/api/health && curl -s http://localhost:8000/ | grep -q FinAlly && test -s /tmp/finally-tracer-db/finally.db` | ✅ | ✅ green |
| 05-01-02 | 01 | 1 | INFRA-04 | T-05-03 | Startup log names path only, never a credential | unit + manual | `cd backend && uv run --extra dev pytest && uv run --extra dev ruff check app/` (+ manual stop/start/kill persistence cycles) | ✅ | ✅ green |
| 05-02-01 | 02 | 2 | INFRA-03 | T-05-07 / T-05-04 | Loopback-only port publish on every launch path | integration | `bash -n scripts/start_mac.sh && ... ./scripts/start_mac.sh && ./scripts/start_mac.sh && test "$(docker ps -a --filter name=^finally$ ...)" = "1" && ./scripts/stop_mac.sh && ./scripts/stop_mac.sh` | ✅ | ✅ green |
| 05-02-02 | 02 | 2 | INFRA-03 | T-05-11 / T-05-12 | Windows scripts disclose unverified status; no `.env` value echoed | integration + manual | `grep -q 'NOT been executed or verified' scripts/start_windows.ps1 && grep -q 'NOT been executed or verified' scripts/stop_windows.ps1 && ...` (+ manual line-by-line PowerShell/bash comparison, D-04) | ✅ | ✅ green |
| 05-02-03 | 02 | 2 | INFRA-03 | — | N/A (UX confirmation, not a security control) | human-verify (blocking gate) | N/A — live browser UAT by design | N/A | ✅ approved |
| 05-03-01 | 03 | 2 | TEST-04 | T-05-13 / T-05-14 | No real credential reaches test container; `LLM_MOCK=true` forces deterministic path | e2e | `docker compose -f test/docker-compose.test.yml down -v --remove-orphans; docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright; ...` | ✅ | ✅ green |
| 05-03-02 | 03 | 2 | TEST-04 | T-05-15 | No mount reaching outside the test directory; host database untouched | integration | `BEFORE=$(shasum db/finally.db ...); ... two full runs ...; AFTER=$(shasum db/finally.db ...); test "$BEFORE" = "$AFTER"` | ✅ | ✅ green |
| 05-04-01 | 04 | 3 | TEST-04 | T-05-18 / T-05-19 | Chat scenario mock-only; specs use production selectors | e2e | `docker compose -f test/docker-compose.test.yml down -v --remove-orphans; docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright; ...` | ✅ | ✅ green |
| 05-04-02 | 04 | 3 | TEST-04 | T-05-20 | Zero retries; three consecutive green runs required | e2e | `... up --build --exit-code-from playwright; RC=$?; ...; test "$(ls test/e2e/*.spec.ts | wc -l | tr -d ' ')" = "5" && exit $RC` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — every task's own `<automated>` verify block ran and passed per SUMMARY evidence (pytest/ruff clean on Plan 01; Docker tracer chains green on Plans 01-04; E2E suite `5 passed` across three consecutive runs on Plan 04). No stub tests or new framework installs were needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end launch UX (browser opens, terminal renders live, a real buy and chat message work) | INFRA-03 | `checkpoint:human-verify` blocking gate (05-02 Task 3) — requires visual confirmation of a live browser session, price animation, and panel rendering that no headless assertion captures as a UX judgment call | Run `./scripts/stop_mac.sh` then `./scripts/start_mac.sh`; confirm the browser opens to a fully live terminal, buy NVDA x3, send a chat message, restart and confirm state persisted. Full steps in `05-02-PLAN.md` Task 3 |
| Windows PowerShell script correctness | INFRA-03 | D-04: no Windows machine available in this environment to execute `start_windows.ps1` / `stop_windows.ps1`; risk transferred to the Windows operator via disclosed unverified-status headers (T-05-11, accepted in `05-SECURITY.md`) | Line-by-line comparison against the verified bash equivalents, performed and recorded in `05-02-SUMMARY.md` |
| SQLite integrity after unclean shutdown (`docker kill` + restart) | INFRA-04 | Backstop check on real Docker Desktop file-sharing/lock behavior — not a property that can be asserted in a headless unit test without also standing up a real container with a bind mount | Kill a running container mid-session, restart it, confirm `GET /api/portfolio` matches pre-kill state and `PRAGMA integrity_check` reports `ok`. Steps in `05-01-PLAN.md` Task 2 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none were MISSING)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-19
