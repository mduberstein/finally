---
phase: 05-one-command-launch
plan: 03
subsystem: testing
tags: [playwright, docker-compose, e2e, llm-mock, chromium]

# Dependency graph
requires:
  - phase: 05-01
    provides: Dockerfile serving the whole app on port 8000, FINALLY_DB_PATH/FINALLY_STATIC_DIR env seams, /api/health
provides:
  - Two-service Playwright E2E harness (test/docker-compose.test.yml) proven green against the real shipping image
  - Playwright config (test/playwright.config.ts) with a Chromium-navigation workaround required for any future spec
  - First E2E scenario (fresh-start) covering TEST-04's baseline assertions
affects: [05-04]

# Actuals (#2632)
actuals:
  tokens: 2700
  tasks: 2
  commits: 1

# Tech tracking
tech-stack:
  added: ["@playwright/test@1.62.1"]
  patterns:
    - "getent-based synchronous DNS resolution in a CommonJS playwright.config.ts to sidestep Chromium's non-disableable HTTPS-Upgrades navigation throttle when the browser navigates to a compose service DNS name"
    - "exact: true on getByRole name matching whenever a role=\"button\" wrapper div contains a nested element with its own aria-label — the wrapper's computed accessible name concatenates descendant content and produces false substring matches"
    - "No volumes + no ports on the compose app service as the isolation mechanism (ephemeral writable-layer SQLite, no host reachability) rather than an explicit scratch bind mount"

key-files:
  created: [test/docker-compose.test.yml, test/playwright.config.ts, test/package.json, test/package-lock.json, test/.gitignore, test/e2e/01-fresh-start.spec.ts]
  modified: []

key-decisions:
  - "Chromium's HTTPS-Upgrades navigation throttle cannot be disabled via --disable-features=HttpsUpgrades in the mcr.microsoft.com/playwright:v1.62.1-noble image (verified empirically: the flag is present in Playwright's own default launch args and the throttle still fires). Worked around by resolving the compose service DNS name to its container IP once at config load, since Chromium exempts IP-literal navigation targets from the throttle."
  - "DNS resolution in playwright.config.ts uses execFileSync + getent, not the async node:dns module, because Playwright loads this config as CommonJS (no top-level await) and test/package.json declares no \"type\": \"module\". A resolution failure (e.g. getent absent on a non-Linux host) falls back to the unresolved URL rather than crashing config load."
  - "The watchlist row's getByRole('button', { name }) locator requires exact: true — the row's own role=\"button\" wrapper has no aria-label, so its computed accessible name falls back to concatenated descendant content, which includes the nested remove button's aria-label text, causing a substring match to resolve to both elements."
  - "Cash assertion is scoped to the sibling <span> immediately following the Cash label via an xpath following-sibling locator, not a bare page.getByText match, because a fresh portfolio's cash and total value are both 10,000.00."

patterns-established:
  - "Any future E2E spec navigating to the compose app service by its DNS name inherits the getent-based IP resolution already applied in playwright.config.ts's baseURL — no per-spec workaround needed."

requirements-completed: [TEST-04]

coverage:
  - id: D1
    description: "docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright builds the shipping image, starts it isolated (LLM_MOCK=true, no volumes, no ports, no env-file), runs Playwright against it over the compose network, and exits 0 with the fresh-start spec passing"
    requirement: "TEST-04"
    verification:
      - kind: e2e
        ref: "test/e2e/01-fresh-start.spec.ts — fresh start: default watchlist, starting cash, live connection, streaming prices"
        status: pass
    human_judgment: false
  - id: D2
    description: "Harness leaks no credential to the test app container (rendered compose config and the live container's process environment both contain LLM_MOCK=true and no *_API_KEY variable), touches no host bind mount, and is repeatable across two full runs with teardown between them"
    requirement: "TEST-04"
    verification:
      - kind: integration
        ref: "docker compose config grep for OPENROUTER_API_KEY (0 matches) + docker compose exec app env (no *_API_KEY) + docker inspect .Mounts (empty array) + two full suite runs, each preceded by teardown, both exit 0 with 1 passed"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-19
status: complete
---

# Phase 5 Plan 3: Playwright E2E Harness (Tracer) Summary

**Two-service `docker-compose.test.yml` (shipping app image + official Playwright container) proven green end-to-end on the fresh-start scenario, with a getent-based DNS-resolution workaround for a non-disableable Chromium navigation throttle that would otherwise fail every E2E spec in this harness.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-19T12:30:00Z
- **Tasks:** 2
- **Files modified:** 6 (all created; no existing files touched)

## Accomplishments

- `test/docker-compose.test.yml`: `app` service builds from the repository root Dockerfile with `LLM_MOCK: "true"` (verified rendered as the lowercase string, not `True`), no volumes (ephemeral writable-layer SQLite), no ports, no environment-file reference, and a Python-based healthcheck (`urllib.request` against `/api/health` — the runtime image has no curl); `playwright` service uses `mcr.microsoft.com/playwright:v1.62.1-noble`, waits on `condition: service_healthy`, and points `BASE_URL` at `http://app:8000`
- `test/playwright.config.ts`: single-worker, non-parallel, filename-ordered spec execution; 60s test timeout / 15s expect timeout; trace-on-failure; `baseURL` reads `BASE_URL` with a `localhost:8000` fallback for manual host-side runs
- `test/e2e/01-fresh-start.spec.ts`: the ten default tickers (by exact remove-button accessible name), the `10,000.00` starting cash figure, the `Connected` status region, live price streaming (both a changing-text poll and a flash-animation-class assertion), and the empty positions state
- `test/package.json` + generated `test/package-lock.json` (`@playwright/test@^1.62.1`, matching the pinned image tag) and `test/.gitignore` (`node_modules/`, `playwright-report/`, `test-results/`, `.playwright/`)
- Root-caused and worked around a Chromium behavior that would have blocked every spec in this harness, not just this one (see Deviations)
- Task 2's three isolation/repeatability properties all passed on first verification, with no correction needed to `test/docker-compose.test.yml`:
  - Credential isolation: rendered `docker compose config` and the live `app` container's `docker compose exec app env` both show only `LLM_MOCK=true`, zero `*_API_KEY` variables
  - Host-database isolation: `docker inspect` on the running `app` container reports `"Mounts": []` (no mount at all, matching the "declare no volume" design); `db/finally.db` did not exist on the host before this plan's work and remained absent after every suite run (checksum-equivalent: absent → absent)
  - Repeatability: two full suite runs, each preceded by `docker compose ... down -v --remove-orphans`, both exited 0 with `1 passed`; a third pair run back-to-back **without** teardown between them also both passed — see Deviations/Issues for why that doesn't prove teardown is unnecessary going forward

## Task Commits

Each task was committed atomically:

1. **Task 1: The E2E harness end to end — compose, config, and one green scenario** - `1df3dbf` (feat)
2. **Task 2: Isolation and repeatability proof — no credential leak, no state leak, no host database touched** - no commit (pure verification; all three properties passed without any correction to `test/docker-compose.test.yml`, so there was nothing to stage)

_No plan-metadata commit in worktree mode — the orchestrator commits STATE.md/ROADMAP.md centrally after merge; this SUMMARY.md is committed separately per the worktree execution contract._

## Canonical E2E Run Command

Recorded verbatim for Plan 04's verify blocks and the README's testing section:

```bash
docker compose -f test/docker-compose.test.yml down -v --remove-orphans
docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright
docker compose -f test/docker-compose.test.yml down -v --remove-orphans
```

**Teardown-before-up is the canonical form**, matching the plan's own `<verify>` blocks. Observed behavior without teardown (see Issues Encountered) did not fail *this specific* read-only spec, but only because the fresh-start spec never mutates state — Plan 04's buy/sell and watchlist-mutation specs will depend on a pristine seeded database, so the teardown step stays in the canonical command rather than being dropped on the strength of this session's read-only observation.

## Files Created/Modified

- `test/docker-compose.test.yml` - Two-service E2E harness: app built from the repo Dockerfile with mock LLM and no persistent state, plus the official Playwright image pointed at it over compose DNS with a healthcheck-gated `depends_on`
- `test/playwright.config.ts` - Playwright configuration: `./e2e` test dir, single worker, `BASE_URL`-driven `baseURL` with a `getent`-based IP-resolution workaround for Chromium's HTTPS-Upgrades throttle
- `test/package.json` - `@playwright/test` devDependency, `npm test` script
- `test/package-lock.json` - Generated via `npm install` in `test/` on the host for a reproducible `npm ci` inside the Playwright container
- `test/.gitignore` - Excludes `node_modules/`, `playwright-report/`, `test-results/`, `.playwright/`
- `test/e2e/01-fresh-start.spec.ts` - The fresh-start scenario: default watchlist, starting cash, connection status, streaming prices, empty positions

## Rendered Environment / Checksum Evidence (for the record)

**`docker compose -f test/docker-compose.test.yml config` (app service, relevant excerpt):**
```yaml
environment:
  LLM_MOCK: "true"
```
`grep -c OPENROUTER_API_KEY` against this rendered output: 0.

**Live container process environment (`docker compose exec app env`):**
```
FINALLY_DB_PATH=/app/db/finally.db
FINALLY_STATIC_DIR=/app/static
LLM_MOCK=true
PATH=/app/.venv/bin:...
PYTHONUNBUFFERED=1
(+ standard Python/Debian base-image vars: GPG_KEY, HOME, HOSTNAME, LANG, PYTHON_SHA256, PYTHON_VERSION)
```
No variable name ends in `_API_KEY`.

**`docker inspect test-app-1 --format '{{json .Mounts}}'`:** `[]` — no bind mount of any kind.

**Host database checksum:** `db/finally.db` did not exist in this worktree checkout before this plan's work (`ls db/` showed only `.gitkeep`). It remained absent after every suite run performed in this session (Task 1's proof run, Task 2's two-run repeatability pair, and the additional no-teardown pair) — an absent-before/absent-after result is the isolation guarantee stated as a measurement, per the task's own framing.

## Decisions Made

- **`getent`-based synchronous IP resolution over an async `node:dns` top-level-await approach**: Playwright loads `.ts` configs as CommonJS by default (confirmed via a `SyntaxError: await is only valid in async functions` failure when a top-level-`await` version was tried first), and `test/package.json` has no `"type": "module"`. `execFileSync("getent", ["hosts", host])` is synchronous and the official Playwright image ships `getent`. Wrapped in try/catch so a resolution failure degrades to the unresolved URL instead of crashing config load.
- **Resolve-to-IP rather than fight the browser feature further**: `--disable-features=HttpsUpgrades` was tried first (matching the initial plan-time assumption) and empirically does *not* work in this Chromium build — the flag is present in Playwright's own default launch args and the throttle still fires. Chromium's browser-internal `Fetch`/`Network` CDP domains also don't expose the synthetic upgrade redirect for `page.route()` interception (tested and ruled out). IP-literal exemption is a real, verified Chromium behavior (confirmed via a standalone debug script) and requires no browser flags at all.
- **`exact: true` on the remove-button locator, not a `data-testid`**: the plan explicitly rules out adding `data-testid` attributes (flagged assumption #3). The strict-mode violation this fixes is a locator precision issue, not evidence that accessible-name locators are the wrong choice.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Chromium's HTTPS-Upgrades navigation throttle fails every navigation to the compose service DNS name**
- **Found during:** Task 1's "Prove it" step — first `docker compose up --build --exit-code-from playwright` run
- **Issue:** `page.goto("/")` (resolving against `baseURL: http://app:8000`) failed with `net::ERR_SSL_PROTOCOL_ERROR at http://app:8000/`. Diagnosis (via a standalone `playwright-core` debug script with request/response logging, run in an ephemeral container attached to the compose network): Chromium synthesizes an internal 307 redirect from `http://app:8000/` to `https://app:8000/` on the very first top-level navigation to any hostname that is neither `localhost` nor an IP literal, then hard-fails when the plain-HTTP server can't complete a TLS handshake — this is Chromium's "HTTPS-Upgrades" feature, and it does NOT fall back to HTTP on an actual SSL protocol error (only on generic network failures like connection-refused/timeout, by design, since an SSL error could indicate an active downgrade attack). `curl` against the identical `http://app:8000/api/health` URL from the same network returned a normal `200 OK` with no redirect, confirming the app itself does zero HTTPS redirection — this is purely Chromium-side.
- **Fix, attempt 1 (did not work):** Added `launchOptions: { args: ["--disable-features=HttpsUpgrades"] }` to `playwright.config.ts`'s `use` block. Confirmed via `chrome://version`'s command-line output that the flag was genuinely present in the effective Chromium invocation (alongside Playwright's own default `--disable-features=...HttpsUpgrades...` list) — the throttle still fired anyway, ruling out a flag-not-applied explanation. `page.route()` interception was also tested and does not see the synthetic upgrade request (it fires below Playwright's CDP-level Fetch domain).
- **Fix, attempt 2 (worked):** Empirically confirmed Chromium exempts IP-literal navigation targets from the throttle (`page.goto("http://172.24.0.2:8000/")` for the same app container succeeded where the hostname form failed). Rewrote `playwright.config.ts` to resolve `BASE_URL`'s hostname to its IP once via `getent hosts` (synchronous, since Playwright loads this CommonJS config without top-level `await` support) before constructing `use.baseURL`, skipping resolution for `localhost` and already-IP-literal values. `test/docker-compose.test.yml`'s `BASE_URL=http://app:8000` value is unchanged — this workaround lives entirely in the config file, not the compose file, and doesn't change which network path is used (the resolved address IS the app container's compose-network address).
- **Files modified:** `test/playwright.config.ts`
- **Verification:** Full `docker compose -f test/docker-compose.test.yml up --build --exit-code-from playwright` run went green after this fix.
- **Committed in:** `1df3dbf` (Task 1 commit)

**2. [Rule 1 - Bug] `getByRole` locator strict-mode violation on the remove-button accessible name**
- **Found during:** Task 1's "Prove it" step, second failed run (after fix #1 above got the app loading)
- **Issue:** `page.getByRole("button", { name: "Remove AAPL from watchlist" })` resolved to two elements: the watchlist row's own `role="button"` wrapper `<div>` (whose computed accessible name falls back to concatenated descendant content — "AAPL 190.07 +0.02% Remove AAPL from watchlist" — because it has no `aria-label` of its own) and the actual nested `<button aria-label="Remove AAPL from watchlist">`. Default (substring) `name` matching made both match.
- **Fix:** Added `exact: true` to the locator's `name` option. The row wrapper's full computed name is not an exact match, so only the intended button matches.
- **Files modified:** `test/e2e/01-fresh-start.spec.ts`
- **Verification:** All ten ticker assertions passed after the fix.
- **Committed in:** `1df3dbf` (Task 1 commit)

**3. [Rule 1 - Bug] Cash assertion matched two elements on a fresh portfolio**
- **Found during:** Task 1's "Prove it" step, third failed run
- **Issue:** `page.getByText("10,000.00")` resolved to two elements — the header's Cash figure and its Total Value figure — because a fresh $10,000 portfolio with zero positions has cash and total value at the same number.
- **Fix:** Scoped the assertion to the `<span>` immediately following the `Cash` label via an xpath `following-sibling::span[1]` locator, rather than an unscoped text match.
- **Files modified:** `test/e2e/01-fresh-start.spec.ts`
- **Verification:** Full suite run went green (`1 passed`) after this fix — the run recorded in the Task 1 commit's proof.
- **Committed in:** `1df3dbf` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bugs)
**Impact on plan:** All three were necessary to get the tracer's own `<verify>` block passing at all — without fix #1, no spec in this harness (including all of Plan 04's future scenarios) could ever navigate to the app. No scope creep: all three fixes are confined to `test/playwright.config.ts` and `test/e2e/01-fresh-start.spec.ts`; `test/docker-compose.test.yml` was never touched after its initial authoring.

## Issues Encountered

- **`docker compose up` without `down` in between reuses the existing stopped container and its writable-layer SQLite file, rather than recreating it.** Tested explicitly for Task 2's repeatability proof: two `up --build --exit-code-from playwright` invocations run back-to-back with no `down` in between both passed (`1 passed` each), and the second run's log showed `Opened existing database at /app/db/finally.db` instead of `Created and seeded a new database`. This is expected Compose behavior (an unmodified service config + an existing, stopped container gets started, not recreated) but it means the fresh-start spec's own read-only nature is the only reason this pair passed — it asserts values, it never mutates cash, positions, or the watchlist, so reusing the same (still-pristine) database produced an identical result. This does **not** demonstrate that teardown is safe to skip once Plan 04 adds mutating specs (buy/sell, watchlist add/remove): a mutating spec run against a reused container would leave state for the *next* run's fresh-start assertions to trip on. The canonical run command therefore keeps the `down -v --remove-orphans` step before `up`, as documented above.
- Sandbox note: every `docker`/`docker compose` invocation and the `npm install` used to generate `test/package-lock.json` required `dangerouslyDisableSandbox: true` — the default Bash sandbox denies the Docker daemon socket and the host npm cache directory, exactly as flagged in the plan's environment note.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The E2E harness infrastructure is proven correct end-to-end: `test/docker-compose.test.yml` and `test/playwright.config.ts` are ready to host Plan 04's four remaining scenarios (watchlist add/remove, buy/sell, AI chat trade, SSE reconnection) with zero further compose or config changes required.
- Plan 04's specs inherit the `getent`-based IP-resolution workaround automatically — no per-spec navigation workaround needed, since it lives in `playwright.config.ts`'s shared `baseURL`.
- Plan 04 and the README's testing section should use the canonical run command recorded above (teardown before `up`, teardown after) verbatim — do not drop the pre-run teardown even though this session's read-only spec tolerated its absence.
- No blockers for Plan 04.

---
*Phase: 05-one-command-launch*
*Completed: 2026-08-19*

## Self-Check: PASSED

- FOUND: test/docker-compose.test.yml
- FOUND: test/playwright.config.ts
- FOUND: test/package.json
- FOUND: test/package-lock.json
- FOUND: test/.gitignore
- FOUND: test/e2e/01-fresh-start.spec.ts
- FOUND commit: 1df3dbf
