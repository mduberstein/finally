# Technology Stack

**Analysis Date:** 2026-08-12

## Languages

**Primary:**
- Python 3.12+ - Backend API, market data, portfolio logic
- TypeScript/JavaScript - Frontend (planned, not yet implemented)

**Secondary:**
- Bash - Start/stop scripts for Docker

## Runtime

**Environment:**
- Python 3.12+ (required by `backend/pyproject.toml`)
- Node 20+ (for Next.js build; not yet used)

**Package Manager:**
- uv (Python) - Fast, modern project manager with reproducible lockfile
  - Lockfile: `backend/uv.lock` (present)
- npm/pnpm (for Next.js frontend; not yet configured)

## Frameworks

**Core Backend:**
- FastAPI 0.141.1 - REST API framework, SSE streaming, static file serving
- Uvicorn 0.52.1 - ASGI server for FastAPI
- Starlette 1.4.1 - ASGI framework (FastAPI dependency)

**Frontend (Planned):**
- Next.js (static export mode, `output: 'export'`) - Static site generation
- TypeScript - Frontend type safety
- Tailwind CSS - Dark theme styling

**Testing:**
- pytest 9.1.1 - Test runner
- pytest-asyncio 1.4.0 - Async test support
- pytest-cov 7.1.0 - Coverage reporting

**Build/Dev:**
- ruff 0.16.2 - Fast Python linter and formatter
- python-dotenv 1.2.2 - Environment variable loading from `.env`

## Key Dependencies

**Critical:**
- httpx 0.28.1 - Async HTTP client for both Massive API polling and future LLM calls via LiteLLM
- sse-starlette 3.4.8 - Server-Sent Events streaming for `/api/stream/prices`
- pydantic 2.13.4 - Data validation and structured outputs (used for market data models and LLM response parsing)

**Infrastructure:**
- uvloop 0.22.1 - High-performance event loop replacement for asyncio
- watchfiles 1.2.0 - File change detection (dev dependency via uvicorn)
- websockets 17.0.1 - WebSocket support (included via uvicorn)

**CLI/Demo:**
- rich 15.0.0 - Terminal rendering for `market_data_demo.py`

**Utilities:**
- certifi 2026.7.22 - SSL certificate bundle for HTTPS
- typing-extensions 4.16.0 - Type hint backports for Python 3.12

## Configuration

**Environment:**
- `.env` file at project root (gitignored) - Contains API keys and configuration
- Environment variables:
  - `MASSIVE_API_KEY` (optional) - Massive/Polygon.io API key; if present, uses real market data; if absent or empty, uses built-in simulator
  - `MARKET_POLL_INTERVAL` (optional) - Override default poll interval (default: 15s for Massive)
  - `MARKET_SEED` (optional) - Seed for simulator RNG for deterministic testing
  - `OPENROUTER_API_KEY` (planned) - OpenRouter API key for LLM via LiteLLM
  - `LLM_MOCK` (planned, optional) - Set to `true` for deterministic mock LLM responses (testing)

**Build:**
- `backend/pyproject.toml` - Python project metadata, dependencies, and tool configuration
- Ruff config in `pyproject.toml`:
  - Line length: 100
  - Target Python: 3.12
  - Linters: E (errors), F (pyflakes), I (isort), N (naming), W (warnings)
- pytest config in `pyproject.toml`:
  - Test paths: `tests/`
  - Test discovery: `test_*.py` files, `Test*` classes, `test_*` functions
  - Asyncio mode: auto

## Platform Requirements

**Development:**
- Python 3.12+ (must be installed; system has 3.9.6)
- uv (installed via system package manager or from https://github.com/astral-sh/uv)
- Docker (for containerized deployment)

**Production:**
- Docker container (single image, multi-stage build planned)
- Port: 8000
- SQLite database (self-contained, no external DB server)
- Volume mount: `finally-data:/app/db` for database persistence

---

*Stack analysis: 2026-08-12*
