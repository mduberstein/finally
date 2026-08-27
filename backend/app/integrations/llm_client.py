from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import LLM_MOCK, OPENROUTER_API_KEY, OPENROUTER_MODEL
from app.schemas import ChatActionResult, ChatStructuredResponse


@dataclass(frozen=True)
class ParsedChatResponse:
    message: str
    trades: list[dict[str, str | float]]
    watchlist_changes: list[dict[str, str]]
    raw_response: str


def _mock_response(message: str) -> str:
    text = message.strip().lower()
    trades = []
    watchlist = []
    if "buy" in text:
        match = re.search(r"buy\s+([a-zA-Z]{1,5})\s+([0-9]*\.?[0-9]+)", text)
        if match:
            trades.append({"ticker": match.group(1).upper(), "side": "buy", "quantity": float(match.group(2))})
        else:
            match = re.search(r"buy\s+([0-9]*\.?[0-9]+)\s+([a-zA-Z]{1,5})", text)
            if match:
                trades.append({"ticker": match.group(2).upper(), "side": "buy", "quantity": float(match.group(1))})
    if "sell" in text:
        match = re.search(r"sell\s+([a-zA-Z]{1,5})\s+([0-9]*\.?[0-9]+)", text)
        if match:
            trades.append({"ticker": match.group(1).upper(), "side": "sell", "quantity": float(match.group(2))})
        else:
            match = re.search(r"sell\s+([0-9]*\.?[0-9]+)\s+([a-zA-Z]{1,5})", text)
            if match:
                trades.append({"ticker": match.group(2).upper(), "side": "sell", "quantity": float(match.group(1))})
    add_match = re.search(r"add\s+([a-zA-Z]{1,6})", text)
    if add_match and "remove" not in text:
        watchlist.append({"ticker": add_match.group(1).upper(), "action": "add"})
    remove_match = re.search(r"remove\s+([a-zA-Z]{1,6})", text)
    if remove_match:
        watchlist.append({"ticker": remove_match.group(1).upper(), "action": "remove"})

    return json.dumps(
        {
            "message": (
                f"Analyzed request: {message}. "
                "Executed deterministic mock action plan."
            ),
            "trades": trades,
            "watchlist_changes": watchlist,
        }
    )


def _build_system_prompt(portfolio: dict, watchlist: list[str]) -> str:
    total_value = portfolio.get("total_value", 0)
    cash = portfolio.get("cash_balance", 0)
    return (
        "You are FinAlly, an AI trading assistant. "
        "Return strict JSON with the fields: message, trades, watchlist_changes.\n"
        "Do not include markdown. Do not output code fences.\n"
        f"Portfolio: total_value={total_value}, cash={cash}. "
        f"Watchlist: {', '.join(watchlist)}."
    )


def _load_conversation(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return messages


async def get_chat_completion(
    user_message: str,
    portfolio: dict,
    watchlist: list[str],
    history: list[dict[str, str]],
    recent_prices: dict[str, float] | None = None,
) -> ParsedChatResponse:
    if LLM_MOCK or not os.getenv("OPENROUTER_API_KEY"):
        raw = _mock_response(user_message)
    else:
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": _load_conversation(
                [{"role": "system", "content": _build_system_prompt(portfolio, watchlist)}]
                + history
                + [{"role": "user", "content": user_message}]
            ),
            "response_format": {"type": "json_object"},
        }
        if recent_prices:
            payload["messages"].append(
                {
                    "role": "system",
                    "content": f"Latest prices: {json.dumps(recent_prices)}",
                }
            )
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "FinAlly",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"LLM service error: {response.status_code}",
                )
            data = response.json()
            choices = data.get("choices") or []
            raw = choices[0].get("message", {}).get("content", "{}") if choices else "{}"

    parsed = _parse_structured_json(raw)
    return parsed


def _parse_structured_json(raw: str) -> ParsedChatResponse:
    try:
        payload = json.loads(raw)
        obj = ChatStructuredResponse.model_validate(payload)
        message = obj.message
        trades = [t.model_dump() for t in obj.trades]
        watchlist = [w.model_dump() for w in obj.watchlist_changes]
        return ParsedChatResponse(
            message=message,
            trades=trades,
            watchlist_changes=watchlist,
            raw_response=raw,
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Malformed LLM JSON: {exc}",
        ) from exc


def action_results(
    trades: list[dict],
    watchlist_changes: list[dict],
) -> list[dict]:
    results: list[ChatActionResult] = []
    for trade in trades:
        results.append(
            ChatActionResult(
                type="trade",
                detail=f"{trade['side']} {trade['quantity']} {trade['ticker']}",
            )
        )
    for change in watchlist_changes:
        results.append(
            ChatActionResult(
                type="watchlist",
                detail=f"{change['action']} {change['ticker']}",
            )
        )
    return [r.model_dump() for r in results]
