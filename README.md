# FinAlly — AI Trading Workstation

A visually stunning AI-powered trading workstation that streams live market data, simulates portfolio trading, and integrates an LLM chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as a capstone project for an agentic AI coding course.

## Features

- **Live price streaming** via SSE with green/red flash animations
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills
- **Portfolio visualizations** — heatmap (treemap), P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests and auto-executes trades
- **Watchlist management** — track tickers manually or via AI
- **Dark terminal aesthetic** — Bloomberg-inspired, data-dense layout

## Architecture

Single Docker container serving everything on port 8000:

- **Frontend**: Next.js (static export) with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python/uv) with SSE streaming
- **Database**: SQLite with lazy initialization
- **AI**: LiteLLM → OpenRouter (Cerebras inference) with structured outputs
- **Market data**: Built-in GBM simulator (default) or Massive API (optional)

## Quick Start

### macOS / Linux

```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env

./scripts/start_mac.sh
```

The start script seeds `.env` from `.env.example` automatically if you skip the copy step above, builds the image if it isn't built yet, waits for the app to come up, and opens your browser at http://localhost:8000. Run it again any time -- it reuses the existing container instead of creating a second one.

```bash
./scripts/stop_mac.sh
```

Stops the container without removing it or touching anything under `db/`. Safe to run repeatedly.

### Windows

```powershell
Copy-Item .env.example .env
# Add your OPENROUTER_API_KEY to .env

.\scripts\start_windows.ps1
.\scripts\stop_windows.ps1
```

These PowerShell scripts mirror the macOS/Linux scripts' Docker CLI logic one to one, but they have not been executed or verified on Windows -- the development machine for this build was macOS. Verify their behavior before relying on them for a live demo.

### Docker Compose (alternative)

```bash
docker compose up -d
docker compose down
```

Builds the same image, publishes the same loopback-only port, and bind-mounts the same `./db` directory as the scripts above.

### Data persistence

The SQLite database lives at `db/finally.db` through a host bind mount (not a named Docker volume), so it's visible directly in your checkout and survives container restarts, stops, and rebuilds.

### Reset to a fresh start

There is no reset flag on any script -- deleting a portfolio is a manual, deliberate action so nothing wipes your data by accident. To start over with a clean $10,000 balance and the ten default tickers:

```bash
./scripts/stop_mac.sh
rm db/finally.db
./scripts/start_mac.sh
```

The backend recreates and reseeds the database automatically on the next start.

### Linux note

On a Linux host, the container may need to run as your own user to write the bind-mounted `db/` directory, e.g. by adding `--user "$(id -u):$(id -g)"` to the `docker run` invocation. This was not needed on macOS Docker Desktop during development.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for AI chat |
| `MASSIVE_API_KEY` | No | Massive (Polygon.io) key for real market data; omit to use simulator |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

## Project Structure

```
finally/
├── frontend/    # Next.js static export
├── backend/     # FastAPI uv project
├── planning/    # Project documentation and agent contracts
├── test/        # Playwright E2E tests
├── db/          # SQLite volume mount (runtime)
└── scripts/     # Start/stop helpers
```

## License

See [LICENSE](LICENSE).
