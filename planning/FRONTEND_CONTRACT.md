# Frontend Contract

What the rest of the team needs from `frontend/` without reading its source:
the build interface for `devops-engineer`, and the frozen test ids for
`integration-tester`.

Owned by `frontend-engineer`. The test ids below are **frozen** — Playwright
specs bind to them, so renaming one silently breaks the E2E suite. Changing any
entry requires messaging `integration-tester` first.

Companion documents: `API_CONTRACT.md` (frontend/backend JSON),
`TEAM.md` (ownership and waves).

## Build interface

| | |
|---|---|
| Working directory | `frontend/` |
| Install | `npm ci` (`package-lock.json` is committed) |
| Build | `npm run build` — this is `next build`; `output: 'export'` is set in `next.config.ts`, so there is **no** separate `next export` step |
| Output | `frontend/out/` — copy the whole directory into the Python image's static dir |
| Entry point | `out/index.html`, assets under `out/_next/`, plus `out/404.html` |
| Node | 20, 22 or 24 slim — `devops-engineer`'s choice. No version-specific APIs |
| Network at build time | None. No `next/font`, no CDN, no remote assets |
| Env vars at build time | None required |

**Do not set `NEXT_PUBLIC_MOCK` in the image.** That flag switches the app to
in-memory fixtures and would ship a demo that never talks to the backend.

Any of those Node versions builds correctly. `npm ci` installs devDependencies —
`typescript` and the Tailwind PostCSS plugin are build-time requirements, so
`--omit=dev` is not an option — and one of them, `jsdom` 30, declares
`engines: ^22.22.2 || ^24.15.0 || >=26.0.0`. On Node 20 that is an EBADENGINE
warning, not an error; newer Node only silences it.

## Regenerating the lockfile

`package-lock.json` must be **platform-complete**: it has to carry the
linux-x64 binaries (`@next/swc-linux-x64-gnu`, `@tailwindcss/oxide-linux-x64-gnu`
and friends) and the top-level `@emnapi/*` entries the optional wasm32 packages
declare, or the image build fails.

Both failure signatures mislead, so check for them by name:

- A lock generated on darwin/arm64 can pass `npm ci` on the host and fail
  `npm ci` inside a Linux container, on every npm version.
- Running plain `npm install` in `frontend/` with an existing `node_modules`
  resolves against what is installed locally. That lock passes `npm ci`
  everywhere and **then** fails `next build` in the container with no
  linux-x64 binaries — so it looks like a fix.

Regenerate from scratch instead — `npm install --package-lock-only` in an empty
directory containing only `package.json`, or run it on Linux — and check the new
lock has non-zero linux-x64 entries before committing it.

This is `frontend-engineer`'s call. Do not work around a bad lockfile by
relaxing `npm ci` in the Dockerfile.

## Static serving requirement

The app has a single route, `/`. FastAPI serves `index.html` for `/` and falls
back to it for unknown non-`/api` paths. `/api/*` always takes precedence.

## Test ids

All are `data-testid` attributes. `{TICKER}` is the upper-case symbol.

**Header** — `header`, `header-total-value`, `header-pnl`, `header-cash`,
`connection-status`, `api-notice`

`connection-status` also carries `data-status="connected|reconnecting|disconnected"`.

**Watchlist** — `watchlist`, `watchlist-empty`, `watchlist-row-{TICKER}`,
`watchlist-price-{TICKER}`, `watchlist-change-{TICKER}`, `sparkline-{TICKER}`,
`watchlist-remove-{TICKER}`, `watchlist-add-input`, `watchlist-add-submit`,
`watchlist-add-error`

`watchlist-row-{TICKER}` also carries `data-selected="true|false"`.

**Main chart** — `main-chart`, `main-chart-price`, `main-chart-canvas`

**Heatmap** — `heatmap`, `heatmap-empty`, `heatmap-tile-{TICKER}`

**P&L chart** — `pnl-chart`, `pnl-chart-canvas`, `pnl-chart-empty`

**Positions** — `positions-table`, `positions-empty`, `position-row-{TICKER}`,
`position-price-{TICKER}`, `position-pnl-{TICKER}`

**Trade bar** — `trade-bar`, `trade-ticker-input`, `trade-quantity-input`,
`trade-buy`, `trade-sell`, `trade-status`

**Chat** — `chat-panel`, `chat-messages`, `chat-message`, `chat-action-chip`,
`chat-loading`, `chat-input`, `chat-send`, `chat-empty`, `chat-error`

`chat-message` repeats and carries `data-role="user|assistant"`.
`chat-action-chip` carries `data-status="executed|failed"`.

## Asserting the price flash

A price cell always carries the class `flashable`. On a tick it gains
`flash-up` or `flash-down` for about 60ms, which is then removed while the
background fades out over the next ~460ms. The class is applied straight to the
DOM node rather than through React state, so a tick costs no extra render.

Assert on the **class**, not on a computed color — the color is mid-transition
for most of the window and will produce a flaky test.

## Mock transport

`npm run dev:mock` runs the app against an in-memory transport speaking the
exact `API_CONTRACT.md` shapes, so the UI can be worked on with no backend
running. Real `fetch` and `EventSource` calls against `/api/*` are already the
production code path — `npm run build` needs no change to talk to the live
backend, and the fixtures are compiled out of that build.
