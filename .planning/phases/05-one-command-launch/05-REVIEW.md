---
phase: 05-one-command-launch
reviewed: 2026-08-19T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - .dockerignore
  - Dockerfile
  - README.md
  - backend/app/db/database.py
  - docker-compose.yml
  - frontend/package-lock.json
  - scripts/start_mac.sh
  - scripts/start_windows.ps1
  - scripts/stop_mac.sh
  - scripts/stop_windows.ps1
  - test/.gitignore
  - test/docker-compose.test.yml
  - test/e2e/01-fresh-start.spec.ts
  - test/e2e/02-watchlist.spec.ts
  - test/e2e/03-trade.spec.ts
  - test/e2e/04-ai-chat.spec.ts
  - test/e2e/05-sse-reconnect.spec.ts
  - test/package-lock.json
  - test/package.json
  - test/playwright.config.ts
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-08-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 19 (`.env.example` could not be read — see note below)
**Status:** issues_found

## Summary

This phase delivers the one-command Docker launch experience: a multi-stage Dockerfile, `docker-compose.yml`, macOS/Windows start/stop scripts, lazy SQLite initialization, and a Playwright E2E suite with its own isolated compose harness. Overall the work is careful and well-documented — comments throughout explain non-obvious decisions (base-image choice, healthcheck tool selection, YAML boolean quoting, Chromium's HTTPS-Upgrades throttle). However, `scripts/start_mac.sh` — explicitly documented as covering "macOS/Linux" in its own header comment and in README.md — uses the macOS-only `open` command with no Linux fallback, which crashes the script on Linux after `set -euo pipefail` even though the container itself started successfully. Since this phase's entire purpose is one-command launch, and the script's own comment and the README both promise Linux support, this is a functional bug that breaks the stated deliverable for a documented platform. There is also a base-OS mismatch risk between the Dockerfile's build stage (Debian trixie) and runtime stage (floating `python:3.12-slim` tag) that should be pinned explicitly to avoid silent glibc-compatibility breakage.

**Note on scope:** `.env.example` could not be read in this session — both the `Read` tool and `Bash cat` were denied by the sandbox's `.env.*` deny pattern (see `<sandbox_note>` in the task). This file was not reviewed; if it contains anything beyond placeholder values, a follow-up pass with elevated permissions is needed.

## Critical Issues

### CR-01: `scripts/start_mac.sh` uses macOS-only `open`, crashing under `set -e` on Linux despite claiming Linux support

**File:** `scripts/start_mac.sh:2` (comment claim) and `scripts/start_mac.sh:59` (bug)

**Issue:** The script's own header comment says "Idempotent one-command launcher for macOS/Linux," and `README.md:28-37` presents this exact script as the "macOS / Linux" quick-start path (there is no separate `start_linux.sh`). But line 59 calls `open http://localhost:8000`, a macOS-specific binary that does not exist on any mainstream Linux distribution. Because the script runs under `set -euo pipefail` (line 7), when `open` is not found the command exits non-zero and the whole script aborts immediately after printing "finally is ready..." (line 58) — it never reaches `exit 0` (line 60). A Linux user following the documented one-command launch path gets a container that actually started successfully, but the script itself fails loudly, contradicting the "one-command launch" premise of this phase and the explicit macOS/Linux claim in both the script comment and the README.

**Fix:** Detect the platform and fall back to `xdg-open` (or skip opening a browser) on Linux:
```bash
if command -v open >/dev/null 2>&1; then
  open http://localhost:8000
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://localhost:8000
else
  echo "Open http://localhost:8000 in your browser."
fi
exit 0
```

## Warnings

### WR-01: Dockerfile build and runtime stages use different, loosely-pinned Debian bases

**File:** `Dockerfile:18` and `Dockerfile:38`

**Issue:** `backend-builder` (line 18) is built from `ghcr.io/astral-sh/uv:python3.12-trixie-slim` (Debian trixie), and its fully-populated `.venv` — including any compiled/native wheel dependencies — is copied wholesale into the `runtime` stage (line 43), which is based on the floating tag `python:3.12-slim` (line 38). `python:3.12-slim` is not pinned to a Debian codename, so its underlying release can differ from trixie today, and can silently change on a future rebuild even if this Dockerfile is never touched again. Copying a venv built against one glibc/Debian release into a container based on a different release is a known footgun (native extensions can fail at runtime with `GLIBC_x.xx not found`, or subtly misbehave). Since this project has no CI that rebuilds the image regularly, such a break could go unnoticed until a student runs a fresh build after the base tag moves.

**Fix:** Pin the runtime stage to the same Debian release as the builder stage, e.g.:
```dockerfile
FROM python:3.12-slim-trixie AS runtime
```
or better, build runtime from the same `ghcr.io/astral-sh/uv` image family used for the builder so both stages are guaranteed to share a base.

### WR-02: `start_windows.ps1` / `stop_windows.ps1` are unverified and diverge in one detail from the macOS script's comment

**File:** `scripts/start_windows.ps1:1-4`, `scripts/stop_windows.ps1:1-4`

**Issue:** Both files carry a header comment stating they have never been executed on Windows and asking the reader to "verify their behavior before relying on them for a live demo" — this is also called out in `README.md:55`. This is an explicit, acknowledged gap rather than a silent one, but it means the phase's stated cross-platform "one-command launch" goal is unverified for half its target platforms (Windows PowerShell). Given this is the capstone deliverable students/graders will run, an unverified script carries real risk of silently failing in front of an audience.

**Fix:** At minimum, dry-run the PowerShell scripts in a Windows VM or GitHub Actions `windows-latest` runner before calling the phase complete; the CLAUDE.md/PLAN.md documents this project as agent-built and testable, so a CI job that runs `start_windows.ps1`/`stop_windows.ps1` against a Docker Desktop-equipped Windows runner would close this gap cheaply.

## Info

### IN-01: `.dockerignore` runtime-data exclusion only matches the exact `db/finally.db` path

**File:** `.dockerignore:34`

**Issue:** `db/finally.db` is excluded from the build context, but any SQLite sidecar files that could appear alongside it (e.g., `-journal`, `-wal`, `-shm`, or a renamed/backup `.db` file a developer creates while debugging) would not be excluded and could accidentally be baked into an image if someone runs `docker build` from a dirty working tree.

**Fix:** Broaden the pattern: `db/*.db*` (or `db/*`) to future-proof against any file that ends up in the runtime data directory.

### IN-02: Persistence mechanism deviates from `planning/PLAN.md` section 11 without a corresponding plan update reference

**File:** `docker-compose.yml:10-11`, `scripts/start_mac.sh:49`, `scripts/start_windows.ps1:54`

**Issue:** `planning/PLAN.md` section 11 specifies a named Docker volume (`docker run -v finally-data:/app/db ...`). The actual implementation across all three launch mechanisms uses a host bind mount (`./db:/app/db` / `"$REPO_ROOT/db:/app/db"`) instead. `README.md:66-68` documents this choice deliberately and explains the rationale (visibility in the checkout, survives rebuilds), so this looks like an intentional, reasoned deviation rather than an oversight — but it is a spec deviation from PLAN.md that isn't reflected back into PLAN.md itself, which could confuse a future reader reconciling the two documents.

**Fix:** No code change needed; consider a one-line update to `planning/PLAN.md` section 11 (or an ADR) recording that bind-mount was chosen over named volume, so the two documents stay in sync.

### IN-03: No `HEALTHCHECK` instruction in the Dockerfile itself

**File:** `Dockerfile` (whole file)

**Issue:** Both `docker-compose.yml` and `test/docker-compose.test.yml` define a healthcheck externally, and `scripts/start_mac.sh`/`start_windows.ps1` poll `/api/health` directly, so functionality is not impacted. But a user who runs `docker run` directly (bypassing both compose and the provided scripts) gets no `docker inspect`-visible health status at all, which is a minor discoverability/operability gap for an image intended to "just work."

**Fix:** Add a `HEALTHCHECK` instruction to the Dockerfile mirroring the compose files' check, so `docker ps` and `docker inspect` report health regardless of how the container is launched:
```dockerfile
HEALTHCHECK --interval=2s --timeout=2s --retries=30 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
```

---

_Reviewed: 2026-08-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
