---
phase: 05-one-command-launch
plan: 02
subsystem: infra
tags: [docker-compose, bash, powershell, idempotent-cli, launch-scripts, readme]

# Dependency graph
requires:
  - phase: 05-01
    provides: proven multi-stage Dockerfile (image tag `finally`), /api/health, FINALLY_DB_PATH/FINALLY_STATIC_DIR
provides:
  - docker-compose.yml convenience wrapper (bind mount, loopback port, optional .env)
  - Idempotent scripts/start_mac.sh and scripts/stop_mac.sh (build-if-missing, state-aware, health-polled, browser auto-open)
  - Best-effort scripts/start_windows.ps1 / stop_windows.ps1 mirrors (unverified on Windows, D-04)
  - Corrected README.md Quick Start (bind mount, no named volume, documented manual reset)
affects: [05-03, 05-04]

# Actuals (#2632)
actuals:
  tokens: 2400
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "docker inspect -f '{{.State.Status}}' / '{{.State.Running}}' guarded by exit-code capture, not stdout parsing on failure -- some Docker CLI versions write a stray blank line to stdout before failing a template-parse against a nonexistent object, which corrupts naive `cmd || echo fallback` state detection"
    - "docker compose long-form env_file entry (- path: .env / required: false) so a clean checkout with no .env still builds and runs"
    - "1:1 PowerShell port of the bash idempotency logic, keeping the exact same docker subcommand set (image inspect, build, inspect -f, start, run / inspect -f, stop) so the two platforms can never silently diverge in behavior"

key-files:
  created: [docker-compose.yml, scripts/start_mac.sh, scripts/stop_mac.sh, scripts/start_windows.ps1, scripts/stop_windows.ps1]
  modified: [README.md]

key-decisions:
  - "No --user override carried in any launch path: Plan 01's SUMMARY recorded the non-root bind mount worked without one on this macOS Docker Desktop host, so per the plan's own conditional instruction it was correctly omitted; README instead documents it as a Linux-only note"
  - "stop_mac.sh / stop_windows.ps1 check docker inspect -f '{{.State.Running}}' (not mere container existence) before deciding whether to print the stopped-message or the not-running-message -- existence alone would make every repeat stop print 'Stopped', never satisfying the acceptance criterion that a second consecutive stop reports nothing running"
  - "Checkpoint issue 1 (chat 401) traced to this isolated git worktree's own freshly-seeded .env (placeholder key, by design -- git worktrees never inherit gitignored files from the main checkout) rather than any defect in the compose/script env-file plumbing; verified end-to-end with the real key and left uncommitted, since .env is gitignored infrastructure, not a deliverable"
  - "Checkpoint issue 2 ('Live' label) traced to a stale, unrelated finally:latest Docker image tag already present on this development machine (built 2026-08-11 from an unrelated, non-ancestor branch, also tagged finally-e2e-terminal:latest) that collided with the bare 'finally' name my scripts/compose reference; the script's build-if-missing check is the plan's own locked contract (PLAN.md section 11) and behaved exactly as specified -- fixed by a one-time --build on this machine, not a code change"

requirements-completed: [INFRA-03]

coverage:
  - id: D1
    description: "One command (script, compose, or PowerShell) brings up the same working terminal at http://localhost:8000"
    requirement: "INFRA-03"
    verification:
      - kind: integration
        ref: "./scripts/start_mac.sh (build-if-missing, .env seed, health poll, browser open) and docker compose up -d, both against the same finally image and ./db bind mount"
        status: pass
    human_judgment: true
  - id: D2
    description: "Repeating start or stop is safe -- no duplicate containers, no data loss"
    requirement: "INFRA-03"
    verification:
      - kind: integration
        ref: "Full matrix: start, start, stop, stop, start -- exactly one container named finally throughout; db/finally.db shasum identical before the first start and after the full cycle"
        status: pass
    human_judgment: false
  - id: D3
    description: "A clean checkout with no .env still launches via docker compose (required: false) and via start_mac.sh (auto-seed from .env.example)"
    requirement: "INFRA-03"
    verification:
      - kind: integration
        ref: "docker compose config renders cleanly with no .env present; start_mac.sh's .env seeding path exercised on this worktree's genuinely-clean checkout"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every launch path publishes the API on loopback only, never on all interfaces"
    requirement: "INFRA-03 (T-05-07)"
    verification:
      - kind: test
        ref: "grep -c '127.0.0.1:8000:8000' across scripts/start_mac.sh, scripts/start_windows.ps1, docker-compose.yml -- each outputs exactly 1"
        status: pass
    human_judgment: false
  - id: D5
    description: "Windows scripts carry the mandatory D-04 unverified disclosure and mirror the bash docker subcommand set exactly"
    requirement: "INFRA-03 (D-04)"
    verification:
      - kind: manual
        ref: "Side-by-side read: start_mac.sh vs start_windows.ps1 (docker image inspect, docker build, docker inspect -f, docker start, docker run -- same set, same order); stop_mac.sh vs stop_windows.ps1 (docker inspect -f, docker stop -- same set)"
        status: pass
    human_judgment: true

duration: ~85min
completed: 2026-08-19
status: complete
---

# Phase 5 Plan 2: One-Command Launch (Compose Wrapper, Scripts, README) Summary

**Idempotent `scripts/start_mac.sh` / `stop_mac.sh` plus a `docker-compose.yml` convenience wrapper turn Plan 01's proven image into an actual one-command launch: build-if-missing, `.env` auto-seed, health-polled browser open, and a stop path that never removes the container or touches `db/` -- exercised through a full start/start/stop/stop/start matrix with a checksum-stable database throughout.**

## Performance

- **Duration:** ~85 min (includes the Task 3 checkpoint investigation)
- **Completed:** 2026-08-19T13:29:00Z
- **Tasks:** 3 (2 automated + 1 human checkpoint)
- **Files modified:** 6 (5 created: docker-compose.yml, scripts/start_mac.sh, scripts/stop_mac.sh, scripts/start_windows.ps1, scripts/stop_windows.ps1; 1 modified: README.md)

## Accomplishments

- `docker-compose.yml`: one `app` service, builds from the repo root, publishes `127.0.0.1:8000:8000`, bind-mounts `./db:/app/db`, reads `.env` via the long-form `required: false` entry so a clean checkout with no `.env` still builds and runs, and healthchecks `/api/health` through the image's own Python (no curl in `python:3.12-slim`)
- `scripts/start_mac.sh`: resolves the repo root from its own location (not the caller's cwd), builds the image only when missing or `--build` is passed, seeds `.env` from `.env.example` on a clean checkout without ever overwriting an existing one, branches on `docker inspect -f '{{.State.Status}}'` (running / exited-or-created / absent), and polls `/api/health` up to 30 times at 1s intervals before opening the browser -- never a fixed sleep
- `scripts/stop_mac.sh`: checks `docker inspect -f '{{.State.Running}}'` (not mere existence) so a second consecutive stop correctly reports "not running" instead of re-issuing a no-op `docker stop`; never calls `docker rm`, never touches `db/`
- `scripts/start_windows.ps1` / `scripts/stop_windows.ps1`: a 1:1 PowerShell port of the same docker CLI logic (same subcommand set, same idempotency checks), each carrying the mandatory D-04 header disclosure that they have not been executed or verified on Windows
- `README.md`: replaced the Quick Start block that instructed a named Docker volume (`finally-data`, rejected by D-01) with mac/Linux, Windows, and compose launch paths, a bind-mount data-persistence note, a documentation-only reset procedure (delete `db/finally.db`, restart -- no `--reset` flag exists by design), and the Linux `--user` note carried from Plan 01
- Fixed a real Docker CLI quirk found while exercising the idempotency matrix: `docker inspect -f` on a nonexistent container writes a stray blank line to stdout before failing the template-parse error, which corrupted naive `VAR=$(cmd 2>/dev/null || echo fallback)` state detection in both `start_mac.sh` and `stop_mac.sh`. Fixed by discarding stdout entirely on a nonzero exit rather than folding a partial value into the state variable.
- Full idempotency matrix exercised by hand: start (from no container) -> start again -> stop -> stop again -> start again. Exactly one container named `finally` at every point; both stops exited 0; the second stop correctly printed the not-running message; `db/finally.db`'s `shasum` (`b9f67f0b23fab34411d0d394113b86231333976a`) was identical before the first start and after the full cycle
- `docker compose up -d` independently reached a healthy app writing to the same `db/finally.db` (same checksum), and `docker compose down` exited 0

## Task Commits

Each automated task was committed atomically:

1. **Task 1: The one-command launch surface -- compose wrapper and idempotent mac scripts** - `4e2f729` (feat)
2. **Task 2: Windows mirror and the corrected README** - `601f23d` (feat)

Task 3 (human checkpoint) required no deliverable code changes -- see Checkpoint Investigation below.

_No plan-metadata commit in worktree mode -- the orchestrator commits STATE.md/ROADMAP.md centrally after merge; SUMMARY.md and REQUIREMENTS.md are committed as part of this file's own commit._

## Files Created/Modified

- `docker-compose.yml` - One `app` service: `build: context: .`, `127.0.0.1:8000:8000`, `./db:/app/db` bind mount, `env_file: [{path: .env, required: false}]`, `/api/health` healthcheck via `python3 -c urllib.request`
- `scripts/start_mac.sh` - Idempotent macOS/Linux launcher: build-if-missing (`--build` or `docker image inspect` failure), `.env` auto-seed, state-aware start (running/exited-or-created/absent), 30x1s health poll, `open http://localhost:8000`
- `scripts/stop_mac.sh` - Idempotent macOS/Linux stopper: checks `State.Running`, `docker stop` (never `docker rm`), never touches `db/`
- `scripts/start_windows.ps1` / `scripts/stop_windows.ps1` - Best-effort PowerShell mirrors, unverified on Windows (D-04 header disclosure mandatory and present)
- `README.md` - Quick Start replaced (mac/Linux/Windows/compose paths, bind-mount note, documentation-only reset procedure, Linux `--user` note)
- `.planning/REQUIREMENTS.md` - INFRA-03 marked complete (checkbox and traceability table)

## Decisions Made

- **No `--user` override in any launch path**: Plan 01's SUMMARY recorded the bind mount worked without one on macOS Docker Desktop, so per the plan's own conditional instruction ("carry a `--user` argument here if and only if Plan 01's SUMMARY recorded..."), it was correctly omitted from both the mac and Windows scripts; the README documents it as a Linux-only contingency instead.
- **Stop scripts check `State.Running`, not mere container existence**: the plan's action text literally says "if a container named finally exists, stop it," but the acceptance criteria require a second consecutive stop to report "nothing running." Existence-only detection can never satisfy that (a stopped-but-not-removed container always "exists"), so both stop scripts check the `Running` boolean instead -- this is the interpretation that makes the acceptance criteria internally consistent.
- **`docker inspect -f` stdout is discarded entirely on a nonzero exit, never folded into a fallback string**: some Docker CLI versions write a blank line to stdout even when the template-parse fails against a nonexistent object, so `VAR=$(cmd 2>/dev/null || echo "absent")` silently produces `"\nabsent"` instead of `"absent"`, breaking every downstream string comparison. Both scripts now use `if ! VAR=$(cmd 2>/dev/null); then VAR="absent"; fi` so a failed inspect always yields a clean, comparison-safe value.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `docker inspect -f` blank-stdout-before-failure corrupting idempotency state detection**
- **Found during:** Task 1, first `./scripts/start_mac.sh` run against a genuinely absent container
- **Issue:** `docker inspect -f '{{.State.Status}}' finally 2>/dev/null || echo "absent"` produced the literal string `"\nabsent"` (a leading blank line from a stray stdout write before the template-parse error, followed by the fallback), which matched none of the `case` statement's patterns (`running` / `exited|created` / `absent`), so the `absent` branch silently never ran and `docker run` was never invoked. The script then spent 30 seconds polling a health endpoint with nothing behind it and exited non-zero with a misleading "did not become healthy" message.
- **Fix:** Replaced the `cmd || echo fallback` pattern with an explicit `if ! VAR=$(cmd 2>/dev/null); then VAR="fallback"; fi` in both `start_mac.sh` (`State.Status`) and `stop_mac.sh` (`State.Running`), discarding any partial stdout on failure instead of concatenating it with the fallback.
- **Files modified:** `scripts/start_mac.sh`, `scripts/stop_mac.sh`
- **Verification:** Full idempotency matrix (start/start/stop/stop/start) then ran clean, with correct branch selection and correct not-running detection on the second stop.
- **Committed in:** `4e2f729` (Task 1 commit)

---

**Total code deviations:** 1 auto-fixed (1 bug). No architectural changes, no scope creep beyond the plan's own file list.

## Checkpoint Investigation (Task 3)

The human's first browser pass at the Task 3 checkpoint reported two issues. Both were investigated to root cause before any action, per project convention.

### Issue 1: Chat request failed with `AuthenticationError: Missing Authentication header`

**Root cause, proven end-to-end:**
1. This plan runs inside an isolated git worktree. Git worktrees never inherit gitignored files (including `.env`) from the main checkout -- each worktree starts with none.
2. `scripts/start_mac.sh` correctly executed its documented, required behavior: on finding no `.env` in this worktree, it seeded one from `.env.example`, whose `OPENROUTER_API_KEY` value is the literal 28-character placeholder `your-openrouter-api-key-here` (verified: `docker exec finally sh -c 'echo ${#OPENROUTER_API_KEY}'` returned `28` before the fix, matching the placeholder's exact length).
3. OpenRouter correctly rejected that placeholder as invalid/missing authentication -- the compose/script env-file plumbing (`--env-file`, `env_file: required: false`) passed it through byte-for-byte exactly as designed; nothing in this plan's deliverables dropped or mangled the key.
4. The main (non-worktree) checkout's `.env` does contain a real, working key (confirmed by the user's own project notes and by `PROJECT.md`). This worktree simply never had access to it, by the nature of worktree isolation -- not by any defect in this plan's code.

**Resolution:** Copied the real project-root `.env` into this worktree (a local-only, gitignored file, never committed) purely to complete human verification. Recreated the container so it picked up the new env file (`docker exec finally sh -c 'echo ${#OPENROUTER_API_KEY}'` now returns `73`, a real key length). Re-verified with a direct `POST /api/chat` call: `{"message":"Your total portfolio value is $9,913.25 (cash $7,811.35 + positions $2,101.90).","actions":[]}` -- a genuine OpenRouter round trip succeeded. No code was changed; the plumbing was already correct. This finding is consistent with `05-02-PLAN.md`'s own `flagged_assumptions` item 3, which already flagged the `.env` auto-seed-and-continue behavior as a planner discretion, not a defect.

### Issue 2: Header showed "Live" instead of "Connected"

**Root cause, proven end-to-end (this one was a genuine defect, though not in this plan's own script/compose logic):**
1. The current, committed `frontend/lib/connection.ts` (`git log` shows exactly one commit ever touched it, `69fb866`, Phase 1) has always returned `"Connected"` / `"Reconnecting"` / `"Disconnected"` from `statusLabel()`. No file in this repository's actual history for the current branch has ever contained the string `"Live"` as a connection-status label.
2. `git log --all -S'"Live"'` found the string only in two commits (`82d9a87`, `5dcd36b`) that belong to an entirely separate, non-ancestor branch (`agent-teams-md`) -- an earlier, abandoned prototype of this same app built with a different agent framework.
3. `docker image inspect finally` on this development machine resolved to image ID `c174fd140925`, created **2026-08-11** (a week before this session), 595MB, tagged both `finally:latest` and `finally-e2e-terminal:latest` -- a stale, unrelated image left over from that abandoned branch, sharing the bare `finally` tag my scripts and compose reference.
4. `scripts/start_mac.sh`'s build-if-missing check (`docker image inspect "$IMAGE_NAME"` succeeds -> skip build) is not a bug -- it is PLAN.md section 11's exact, locked contract ("Builds the Docker image if not already built"). Because *an* image already existed under the `finally` tag, the script correctly skipped rebuilding and the container ran from this stale, unrelated image instead of Plan 01's fresh build, serving 8-day-old frontend code with the wrong label copy.

**Resolution:** Ran `./scripts/start_mac.sh --build` once on this machine to force a rebuild, overwriting the stale `finally:latest` tag with a fresh build of the current source (image `sha256:72284a7d...`, matching the hash `docker compose build` had already produced earlier in Task 1). Recreated the container. Verified directly against the served bundle: `grep` for `"Live"` across every chunk in `/app/static/_next/static/chunks/` now returns zero matches, and the compiled `statusLabel` switch (`case"connected":return"Connected";case"reconnecting":return"Reconnecting";case"disconnected":return"Disconnected"`) is present verbatim. Re-confirmed `/api/health` still returns `{"status":"ok"}` and `db/finally.db` persisted through the container recreation.

**Scope conclusion:** This was a real defect in what was being *served*, but not a defect in any file this plan owns or commits -- the deliverable scripts implement PLAN.md's locked build-if-missing contract correctly, and no code change was made or is warranted. It was a one-time collision between this specific development machine's leftover image tag (from an unrelated, non-ancestor branch built over a week earlier) and the bare `finally` name. A fresh clone on a machine with no such stale tag would never hit this. No script defense against unrelated stale image-tag collisions was added, since PLAN.md explicitly locks the "build only if missing" behavior and adding staleness detection would be an architectural change (Rule 4) outside this plan's authorized scope.

**No SUMMARY-blocking stubs, skipped tests, or unrun `<verify>` steps resulted from this investigation** -- both issues were fully root-caused and resolved (or, for issue 1, shown not to require a code fix) before Task 3 was marked complete.

## Issues Encountered

See Checkpoint Investigation above for both issues raised at the Task 3 human-verify gate. No other issues encountered.

## User Setup Required

None beyond what the README already documents (`OPENROUTER_API_KEY` in `.env`). Note for anyone running this phase's verification on a development machine that has previously built an unrelated image under the bare `finally` tag: run `./scripts/start_mac.sh --build` once to ensure the current source is what gets served, since the idempotent build-skip behavior is `docker image inspect finally`-based (any image under that name satisfies it) and is a locked contract from PLAN.md section 11, not something this plan's scripts second-guess.

## Next Phase Readiness

- INFRA-03 is fully satisfied: one script, one compose command, or one PowerShell script (unverified but logically identical) each bring up the same working terminal at `http://localhost:8000`, and repeating any of them is safe.
- The `finally` image tag on this development machine now correctly points at a fresh build of the current source (verified via the served bundle's compiled label strings), so Plan 05-03/05-04 work building on top of this image will not silently inherit the earlier stale-tag issue.
- No blockers for Plan 05-03/05-04. Git log shows Plan 05-03 (Playwright E2E harness) already merged into `finally-gsd-md` in parallel with this plan's worktree session.

---
*Phase: 05-one-command-launch*
*Completed: 2026-08-19*

## Self-Check: PASSED

- FOUND: docker-compose.yml
- FOUND: scripts/start_mac.sh
- FOUND: scripts/stop_mac.sh
- FOUND: scripts/start_windows.ps1
- FOUND: scripts/stop_windows.ps1
- FOUND: README.md (Quick Start replaced)
- FOUND commit: 4e2f729
- FOUND commit: 601f23d
