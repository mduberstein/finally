"""Portfolio router: `GET /api/portfolio` and `POST /api/portfolio/trade`."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.market.cache import PriceCache

from .models import TradeRejected
from .service import execute_trade, get_portfolio


class TradeRequest(BaseModel):
    """The trade request body. Declares no fill-price field at all (D-01):
    the server always reads the fill price from `PriceCache`, never from
    the client."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)


def create_portfolio_router(cache: PriceCache) -> APIRouter:
    """Build the portfolio router bound to a specific cache.

    A factory (rather than a module-level router reading `request.app.state`)
    keeps these endpoints independently testable without a full app
    lifespan, matching `create_stream_router`.
    """
    router = APIRouter()

    @router.get("/api/portfolio")
    async def portfolio() -> dict:
        return await run_in_threadpool(get_portfolio, cache)

    @router.post("/api/portfolio/trade")
    async def trade(request: TradeRequest) -> dict:
        try:
            result = await run_in_threadpool(
                execute_trade, request.ticker, request.side, request.quantity, cache
            )
        except TradeRejected as error:
            raise HTTPException(status_code=400, detail=error.detail()) from error
        except sqlite3.OperationalError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "database_busy", "message": "trade could not be committed, try again"},
            ) from error
        return {
            "ticker": result.ticker,
            "side": result.side,
            "quantity": result.quantity,
            "price": result.price,
            "executed_at": result.executed_at,
            "cash_balance": result.cash_balance,
        }

    return router
