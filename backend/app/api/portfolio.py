"""Portfolio, trade, and history endpoints."""

from fastapi import APIRouter, Query

from app.db import snapshots, transaction
from app.market import PriceCache
from app.portfolio import execute_trade, load_portfolio

from .schemas import HistoryResponse, PortfolioResponse, SnapshotOut, TradeRequest, TradeResponse


def create_portfolio_router(cache: PriceCache) -> APIRouter:
    """Build the `/api/portfolio` router bound to a specific price cache.

    Handlers are plain `def`, not `async def`, so FastAPI runs them in its
    threadpool. `sqlite3` blocks the thread it runs on, and this process also
    holds long-lived SSE connections on the event loop -- blocking that loop
    would stall every streaming client. Each transaction opens its own
    connection, so no connection ever crosses a thread.
    """
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("", response_model=PortfolioResponse)
    def get_portfolio() -> PortfolioResponse:
        return PortfolioResponse.model_validate(load_portfolio(cache))

    @router.post("/trade", response_model=TradeResponse)
    def post_trade(body: TradeRequest) -> TradeResponse:
        """Fill a market order now. A rule failure raises TradeError, handled as a 400."""
        result = execute_trade(cache, body.ticker, body.side, body.quantity)
        return TradeResponse.model_validate(result)

    @router.get("/history", response_model=HistoryResponse)
    def get_history(limit: int = Query(500, ge=1, le=5000)) -> HistoryResponse:
        with transaction() as conn:
            recorded = snapshots.list_recent(conn, limit)
        return HistoryResponse(snapshots=[SnapshotOut.model_validate(s) for s in recorded])

    return router
