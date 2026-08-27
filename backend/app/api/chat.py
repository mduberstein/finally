from __future__ import annotations

from fastapi import APIRouter, Depends

from app.app_state import AppState, get_app_state
from app.integrations.llm_client import action_results, get_chat_completion
from app.schemas import ChatRequest, ChatResponse
from app.services.portfolio import list_portfolio_with_market_data

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def post_chat(
    payload: ChatRequest,
    state: AppState = Depends(get_app_state),
) -> ChatResponse:
    db = state.database
    watchlist = db.list_watchlist()
    portfolio = list_portfolio_with_market_data(db, state.price_cache)
    chat_history = db.recent_chat_messages(limit=12)

    structured = await get_chat_completion(
        user_message=payload.message,
        portfolio=portfolio,
        watchlist=watchlist,
        history=[m for m in chat_history if m["role"] in {"user", "assistant"}],
        recent_prices={tick: state.price_cache.get_price(tick) or 0.0 for tick in watchlist},
    )

    db.add_chat_message("user", payload.message)

    executed_actions = []
    errors: list[str] = []

    for action in structured.trades:
        try:
            state.execute_trade(
                ticker=action["ticker"],
                side=action["side"],
                quantity=action["quantity"],
            )
            executed_actions.append({"type": "trade", "detail": f"{action['side']} {action['quantity']} {action['ticker']}"})
        except Exception as exc:  # pragma: no cover - defensive runtime coverage
            errors.append(str(exc))

    for change in structured.watchlist_changes:
        try:
            ticker = change["ticker"]
            action = change["action"]
            if action == "add":
                added = db.add_watchlist_ticker(ticker)
                if added:
                    await state.market_data_source.add_ticker(ticker)
            else:
                removed = db.remove_watchlist_ticker(ticker)
                if removed:
                    await state.market_data_source.remove_ticker(ticker)
            executed_actions.append({"type": "watchlist", "detail": f"{action} {ticker}"})
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))

    db.add_chat_message(
        role="assistant",
        content=structured.message,
        actions={"trades": structured.trades, "watchlist_changes": structured.watchlist_changes, "errors": errors},
    )

    return ChatResponse(
        message=structured.message,
        trades=structured.trades,
        watchlist_changes=structured.watchlist_changes,
        executed_actions=action_results(structured.trades, structured.watchlist_changes),
        errors=errors,
    )
