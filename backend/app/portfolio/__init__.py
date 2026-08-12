"""Portfolio valuation and market-order execution.

The API routes and the LLM assistant both call these directly:

    from app.market import PriceCache
    from app.portfolio import TradeError, execute_trade, load_portfolio

    portfolio = load_portfolio(cache)
    result = execute_trade(cache, "AAPL", "buy", 10)

Every function here is synchronous, because `sqlite3` is. From an async caller,
wrap it in `starlette.concurrency.run_in_threadpool`.
"""

from .errors import TradeError
from .models import PortfolioView, PositionView, TradeResult
from .recorder import SNAPSHOT_INTERVAL, SnapshotRecorder, record_snapshot
from .trading import execute_trade
from .valuation import build_portfolio, load_portfolio

__all__ = [
    "SNAPSHOT_INTERVAL",
    "PortfolioView",
    "PositionView",
    "SnapshotRecorder",
    "TradeError",
    "TradeResult",
    "build_portfolio",
    "execute_trade",
    "load_portfolio",
    "record_snapshot",
]
