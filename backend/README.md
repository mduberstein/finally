# Backend — Market Data

The market data subsystem lives in `app/market/`, per
`planning/MARKET_DATA_DESIGN.md`. It exposes one abstract source contract
(`MarketDataSource.fetch(tickers) -> list[Quote]`) with two implementations —
a built-in GBM simulator (default) and a Massive (Polygon.io) REST poller
(when `MASSIVE_API_KEY` is set) — feeding a `PriceCache` through a
`MarketFeed` background task.

## Setup

```bash
cd backend
uv sync --extra dev
```

## Usage

```python
from app.market import MarketFeed, PriceCache, create_source

cache = PriceCache()
feed = MarketFeed(create_source(), cache, lambda: ["AAPL", "GOOGL"])
feed.start()
...
await feed.stop()
```

## Tests

```bash
uv run pytest -v
uv run pytest --cov=app
uv run ruff check app/ tests/
```
