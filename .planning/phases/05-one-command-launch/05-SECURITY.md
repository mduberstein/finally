---
phase: 5
slug: one-command-launch
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-19
---

# Phase 5 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| repository working tree → Docker build context | Everything not excluded by `.dockerignore` is copied into immutable image layers | `.env` would cross here unless stopped |
| host filesystem → container `/app/db` | The bind mount is the only writable host path the container touches | SQLite portfolio data |
| host network → container port 8000 | The app has no authentication by design; whichever interface the port publishes on defines who can reach it | Unauthenticated API/SSE traffic |
| container process → host user namespace | The image's `USER` determines what the container may write on the bind mount | Filesystem write permissions |
| shell script → host `db/` directory | Start/stop scripts run with the invoking user's full filesystem rights next to live portfolio data | SQLite file lifecycle |
| `.env.example` → `.env` seeding | An automated file write into the location that holds the real credential | OpenRouter API key |
| repository root environment file → test app container | The only path by which a real inference credential could reach a test run | OpenRouter API key |
| test harness → developer's live host database | The only path by which a test run could destroy real portfolio data | SQLite portfolio data |
| compose network → host network | Whether the test app is reachable outside the compose project | Unauthenticated API/SSE traffic |
| npm registry → test container | A new third-party dependency and base image enter the project here | Supply chain |
| test specs → production frontend markup | A spec that cannot find a locator creates pressure to change shipping components for test convenience | Component structure |
| test specs → the LLM call boundary | The chat scenario is the one place a test could reach a paid external provider | OpenRouter API key / cost |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Information Disclosure | Docker build context and image layers | high | mitigate | `.dockerignore` excludes `.env`, `.env.*`, `.git`, `.venv`, `db/finally.db`; credential injected only at run time via `--env-file`. Confirmed present in `.dockerignore` | closed |
| T-05-02 | Elevation of Privilege | container runtime user | medium | mitigate | Non-root `finally` user created in runtime stage; `/app` and `/app/db` chowned to it, `USER finally` precedes `CMD`. Confirmed in `Dockerfile` (`--chown=finally:finally`, `USER finally`) | closed |
| T-05-03 | Information Disclosure | container startup logs | medium | mitigate | `initialize()` log record emits filesystem path and existence flag only, no credential. Confirmed in `backend/app/db/database.py:96,98` (`logger.info("Opened existing database at %s", path)` / `"Created and seeded a new database at %s"`) | closed |
| T-05-04 | Denial of Service / Information Disclosure | published host port | high | mitigate | Port published as `127.0.0.1:8000:8000`, not `8000:8000`, closing SSE/trade-endpoint exposure to the local network. Confirmed in `scripts/start_mac.sh:48`, `docker-compose.yml:6` | closed |
| T-05-05 | Tampering | bind-mounted host `db/` writable by the container | low | accept | Single-user local demo; container writes exactly one SQLite file into an operator-chosen directory (explicit D-01 decision) | closed |
| T-05-06 | Tampering | base image supply chain (`node:22-slim`, `ghcr.io/astral-sh/uv`, `python:3.12-slim`) | medium | accept | Official first-party publisher images pulled by tag; digest pinning judged disproportionate for a local course-demo container | closed |
| T-05-07 | Information Disclosure | published port on all launch paths | high | mitigate | Every launch path publishes `127.0.0.1:8000:8000`. Confirmed in `scripts/start_mac.sh:48`, `scripts/start_windows.ps1:53`, `docker-compose.yml:6` | closed |
| T-05-08 | Tampering | the seeding step that writes `.env` | high | mitigate | Copy guarded on target file's absence (`if [ ! -f "$REPO_ROOT/.env" ]`), so a real credential can never be clobbered. Confirmed in `scripts/start_mac.sh:26-28`, `scripts/start_windows.ps1:27-31` | closed |
| T-05-09 | Denial of Service (data loss) | stop path | high | mitigate | Stop path stops and never removes; issues no filesystem operation against `db/`. Confirmed in `scripts/stop_mac.sh` (`docker stop` only, comment confirms data preserved) | closed |
| T-05-10 | Repudiation | container identity across cycles | low | accept | Reusing one container across stop/start keeps its logs by design; no audit trail beyond `docker logs` in scope for a local single-user demo | closed |
| T-05-11 | Tampering | unverified PowerShell scripts on Windows | medium | transfer | Cannot be validated on this machine (D-04); risk transferred to the Windows operator via mandatory in-file header disclosure and README note | closed |
| T-05-12 | Information Disclosure | script console output | medium | mitigate | Scripts print URLs, container states, and file paths only, no environment variable values. Confirmed via grep of `scripts/start_mac.sh` and `scripts/start_windows.ps1` echo/Write-Host lines | closed |
| T-05-13 | Information Disclosure | test app container environment | high | mitigate | Test compose file declares no environment-file reference, sets only the mock flag. Confirmed in `test/docker-compose.test.yml` (no `env_file`/`.env` reference) | closed |
| T-05-14 | Spoofing / cost abuse | outbound LLM calls from a test run | high | mitigate | `LLM_MOCK` set to the quoted string `"true"`, forcing `backend/app/chat/llm.py`'s deterministic mock path. Confirmed in `test/docker-compose.test.yml:9` | closed |
| T-05-SC | Tampering | `@playwright/test` npm install and the Playwright base image | high | mitigate | Package legitimacy verified (official Microsoft package, no postinstall); `npm ci` against committed lockfile; image tag pinned to matching Playwright version. Confirmed `test/package-lock.json` exists, `test/package.json` pins `^1.62.1`, compose image is `mcr.microsoft.com/playwright:v1.62.1-noble` | closed |
| T-05-15 | Denial of Service (data loss) | developer's host database during a test run | high | mitigate | Harness declares no mount reaching outside the test directory. Confirmed in `test/docker-compose.test.yml` (app service has no `volumes:`, writes to ephemeral container layer) | closed |
| T-05-16 | Information Disclosure | test app reachable on the host network | medium | mitigate | Harness publishes no host port; reachability confined to the compose project's bridge network. Confirmed in `test/docker-compose.test.yml` (app service has no `ports:`) | closed |
| T-05-17 | Tampering | Linux-native `node_modules` written into the bind-mounted test directory | low | accept | Playwright container installs into the host-visible test directory; gitignored, never committed | closed |
| T-05-18 | Spoofing / cost abuse | the AI-chat scenario | high | mitigate | Scenario runs only inside the mock-flagged harness; no credential reaches the container. Confirmed via `test/docker-compose.test.yml` `LLM_MOCK=true` and `test/e2e/04-ai-chat.spec.ts` asserting the mock's deterministic fallback | closed |
| T-05-19 | Tampering | production frontend components | medium | mitigate | Specs use production selectors, not test-only attributes — a spec that cannot locate an element must change its locator, not the application. Confirmed zero `data-testid`/`getByTestId` usage across `test/e2e/*.spec.ts` | closed |
| T-05-20 | Repudiation | flaky assertions masked by retries | medium | mitigate | `retries` kept at zero so intermittent failures surface rather than being averaged away. Confirmed in `test/playwright.config.ts:60` (`retries: 0`) | closed |
| T-05-21 | Denial of Service (data loss) | the developer's own database | high | mitigate | Inherited from T-05-15: harness declares no mount reaching outside the test directory; specs add no filesystem access of their own | closed |
| T-05-22 | Information Disclosure | Playwright traces retained on failure | low | accept | Failed-run traces contain only simulated prices and a fake portfolio, no real credential or personal data; traces are gitignored | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-05 | Single-user local demo; container writes exactly one SQLite file into an operator-chosen bind-mounted directory (D-01 decision favoring a visible, inspectable file over an opaque named volume) | Phase 5 plan | 2026-08-19 |
| AR-05-02 | T-05-06 | Official first-party publisher base images pulled by tag; digest pinning judged disproportionate friction for a local course-demo container | Phase 5 plan | 2026-08-19 |
| AR-05-03 | T-05-10 | Reusing one container across stop/start cycles is intentional; no audit trail beyond `docker logs` is in scope for a local single-user demo | Phase 5 plan | 2026-08-19 |
| AR-05-04 | T-05-11 | PowerShell scripts cannot be validated on this (non-Windows) machine (D-04); risk transferred to the Windows operator via mandatory in-file header disclosure and a repeated README note | Phase 5 plan | 2026-08-19 |
| AR-05-05 | T-05-17 | Linux-native `node_modules` written into the bind-mounted, gitignored test directory — accepted as the cost of not maintaining a second Dockerfile for the test runner | Phase 5 plan | 2026-08-19 |
| AR-05-06 | T-05-22 | Playwright failure traces contain only simulated/fake data, no real credentials; traces are gitignored | Phase 5 plan | 2026-08-19 |

**Carried-forward re-confirmation:** Phase 1-3 accepted risks flagged in `STATE.md` for "revisit at Phase 5 container publish" — T-01-06 (error responses), T-01-07 (unauthenticated SSE), T-02-06 (trade rejection detail), T-02-10 (no trade rate limit), T-03-05 (no watchlist audit trail), T-03-10 (portfolio history discloses only the local user's own data) — remain **accepted**. Re-confirmation rests on T-05-04/T-05-07's mitigation: Phase 5 publishes to loopback (`127.0.0.1`) only, so "container publish" means reachable from this machine, not the internet. Any future change publishing on a routable interface reopens all six; see the originating phase SECURITY.md files for full entries.

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-19 | 23 | 23 | 0 | /gsd-secure-phase (orchestrator, L1 grep-depth verification; short-circuit rule applied — no auditor subagent required) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-19
