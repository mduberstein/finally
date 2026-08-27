from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.app_state import AppState, get_app_state
from app.schemas import PortfolioResponse, TradeRequest
from app.services.portfolio import execute_trade, list_portfolio_with_market_data

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    state: AppState = Depends(get_app_state),
) -> Any:
    return list_portfolio_with_market_data(state.database, state.price_cache)


@router.post("/trade")
async def post_trade(
    request: TradeRequest,
    state: AppState = Depends(get_app_state),
) -> dict[str, Any]:
    execution = execute_trade(
        state.database,
        state.price_cache,
        request.ticker,
        request.side,
        request.quantity,
    )
    portfolio = list_portfolio_with_market_data(state.database, state.price_cache)
    state.schedule_snapshot(portfolio["total_value"])
    return {"execution": execution, "portfolio": portfolio}


@router.get("/history")
async def get_portfolio_history(
    state: AppState = Depends(get_app_state),
) -> list[dict[str, Any]]:
    snapshots = state.database.list_portfolio_snapshots()
    return snapshots
