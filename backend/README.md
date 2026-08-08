# Backend — FinAlly

## Project Setup

```bash
cd backend
uv sync --extra dev   # Install all dependencies including test/lint tools
```

## Market Data

The market data subsystem lives in `app/market/`, built against
`planning/MARKET_DATA_DESIGN.md`. Public API:

```python
from app.market import (
    MarketDataSource,
    MarketFeed,
    PriceCache,
    PriceUpdate,
    Quote,
    create_source,
)
```

- `create_source()` — the one environment-aware seam. Returns `MassiveSource`
  if `MASSIVE_API_KEY` is set (non-blank), otherwise `SimulatorSource`.
- `MarketFeed` — background polling task that reads a `MarketDataSource` on
  its own cadence and writes into a `PriceCache`. Falls back from Massive to
  the simulator on HTTP 401/403, and backs off the poll interval on HTTP 429.
- `PriceCache` — in-memory store of latest/previous price per ticker; the
  only component that computes `direction`.
- SSE streaming for `/api/stream/prices` lives in `app/market/stream.py`.

## Running Tests

```bash
uv run pytest -v              # All tests
uv run pytest --cov=app       # With coverage
uv run ruff check app/ tests/ # Lint
```
