from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.config import APP_USER_ID, DEFAULT_TICKERS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_ticker(value: str) -> str:
    return value.strip().upper()


def _schema_sql() -> str:
    schema_path = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
    return schema_path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Position:
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str


@dataclass(frozen=True)
class Trade:
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


class Database:
    """SQLite data access with explicit locking and lightweight helpers."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_as_dict(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def initialize(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.executescript(_schema_sql())
                conn.commit()

                profile = conn.execute(
                    "SELECT id FROM users_profile WHERE id = ?",
                    (APP_USER_ID,),
                ).fetchone()
                if not profile:
                    conn.execute(
                        """
                        INSERT INTO users_profile (id, cash_balance, created_at)
                        VALUES (?, ?, ?)
                        """,
                        (APP_USER_ID, 10000.0, _now()),
                    )

                existing = conn.execute(
                    "SELECT COUNT(*) AS c FROM watchlist WHERE user_id = ?",
                    (APP_USER_ID,),
                ).fetchone()
                if existing and existing["c"] == 0:
                    for ticker in DEFAULT_TICKERS:
                        conn.execute(
                            """
                            INSERT INTO watchlist (id, user_id, ticker, added_at)
                            VALUES (?, ?, ?, ?)
                            """,
                            (str(uuid.uuid4()), APP_USER_ID, ticker, _now()),
                        )
                conn.commit()

    # User profile ---------------------------------------------------------
    def get_profile(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
                (APP_USER_ID,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="User profile missing")
            return self._row_as_dict(row)

    def set_cash_balance(self, cash_balance: float) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users_profile
                SET cash_balance = ?
                WHERE id = ?
                """,
                (cash_balance, APP_USER_ID),
            )
            conn.commit()
            return self.get_profile()

    # Watchlist ------------------------------------------------------------
    def list_watchlist(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at",
                (APP_USER_ID,),
            ).fetchall()
            return [_normalize_ticker(r["ticker"]) for r in rows]

    def add_watchlist_ticker(self, ticker: str) -> bool:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn, self._lock:
            conn.execute(
                """
                INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), APP_USER_ID, normalized, _now()),
            )
            conn.commit()
            inserted = conn.total_changes > 0
            return inserted

    def remove_watchlist_ticker(self, ticker: str) -> bool:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn, self._lock:
            cursor = conn.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
                (APP_USER_ID, normalized),
            )
            conn.commit()
            return cursor.rowcount > 0

    # Positions ------------------------------------------------------------
    def list_positions(self) -> list[Position]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ticker, quantity, avg_cost, updated_at
                FROM positions
                WHERE user_id = ?
                """,
                (APP_USER_ID,),
            ).fetchall()
            return [Position(r["ticker"], float(r["quantity"]), float(r["avg_cost"]), r["updated_at"]) for r in rows]

    def add_chat_message(self, role: str, content: str, actions: Any | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            message_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, APP_USER_ID, role, content, json.dumps(actions) if actions is not None else None, _now()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, role, content, actions, created_at FROM chat_messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Failed to record chat message")
            return self._row_as_dict(row)

    def recent_chat_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, actions, created_at
                FROM chat_messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (APP_USER_ID, limit),
            ).fetchall()
            return [self._row_as_dict(r) for r in rows][::-1]

    # Trades ----------------------------------------------------------------
    def record_trade(self, ticker: str, side: str, quantity: float, price: float) -> Trade:
        trade = Trade(
            id=str(uuid.uuid4()),
            ticker=_normalize_ticker(ticker),
            side=side,
            quantity=quantity,
            price=price,
            executed_at=_now(),
        )
        with self._connect() as conn, self._lock:
            conn.execute(
                """
                INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trade.id, APP_USER_ID, trade.ticker, trade.side, trade.quantity, trade.price, trade.executed_at),
            )
            conn.commit()
            return trade

    def upsert_position_after_fill(
        self,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
    ) -> Position:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn, self._lock:
            row = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                (APP_USER_ID, normalized),
            ).fetchone()

            if row is None:
                if side == "sell":
                    raise HTTPException(status_code=400, detail=f"Insufficient shares for {normalized} sell")
                if quantity <= 0:
                    raise HTTPException(status_code=400, detail="Quantity must be positive")
                new_quantity = quantity
                new_avg_cost = price
                conn.execute(
                    """
                    INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), APP_USER_ID, normalized, new_quantity, new_avg_cost, _now()),
                )
            else:
                existing_qty = float(row["quantity"])
                existing_avg = float(row["avg_cost"])
                if side == "buy":
                    new_quantity = existing_qty + quantity
                    if new_quantity == 0:
                        new_avg_cost = 0.0
                    else:
                        new_avg_cost = (existing_qty * existing_avg + quantity * price) / new_quantity
                else:
                    new_quantity = existing_qty - quantity
                    if new_quantity < -1e-9:
                        raise HTTPException(status_code=400, detail=f"Insufficient shares for {normalized} sell")
                    new_avg_cost = existing_avg

                if abs(new_quantity) <= 1e-9:
                    conn.execute(
                        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                        (APP_USER_ID, normalized),
                    )
                    conn.commit()
                    # return zero quantity position for immediate cache consistency
                    return Position(normalized, 0.0, new_avg_cost, _now())

                conn.execute(
                    """
                    UPDATE positions
                    SET quantity = ?, avg_cost = ?, updated_at = ?
                    WHERE user_id = ? AND ticker = ?
                    """,
                    (new_quantity, new_avg_cost, _now(), APP_USER_ID, normalized),
                )

            conn.commit()
            updated = conn.execute(
                "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND ticker = ?",
                (APP_USER_ID, normalized),
            ).fetchone()
            return Position(updated["ticker"], float(updated["quantity"]), float(updated["avg_cost"]), updated["updated_at"])

    def execute_market_order(self, ticker: str, side: str, quantity: float, price: float) -> dict[str, Any]:
        normalized = _normalize_ticker(ticker)
        if side not in {"buy", "sell"}:
            raise HTTPException(status_code=400, detail="Invalid trade side")
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        if price <= 0:
            raise HTTPException(status_code=400, detail="Invalid price")

        with self._connect() as conn, self._lock:
            profile = conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id = ?",
                (APP_USER_ID,),
            ).fetchone()
            if not profile:
                raise HTTPException(status_code=500, detail="User profile missing")

            cash = float(profile["cash_balance"])
            side = side.lower()

            row = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                (APP_USER_ID, normalized),
            ).fetchone()
            current_qty = float(row["quantity"]) if row else 0.0
            current_avg = float(row["avg_cost"]) if row else 0.0

            if side == "buy":
                notional = quantity * price
                if cash + 1e-9 < notional:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient cash to buy {quantity} shares of {normalized}",
                    )
                cash -= notional
            elif side == "sell":
                if current_qty + 1e-9 < quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient shares to sell {quantity} shares of {normalized}",
                    )
                cash += quantity * price

            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (cash, APP_USER_ID),
            )

            if current_qty == 0 and side == "buy":
                new_qty = quantity
                new_avg = price
                conn.execute(
                    """
                    INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), APP_USER_ID, normalized, new_qty, new_avg, _now()),
                )
            elif side == "buy":
                new_qty = current_qty + quantity
                new_avg = ((current_qty * current_avg) + (quantity * price)) / new_qty
                conn.execute(
                    """
                    UPDATE positions
                    SET quantity = ?, avg_cost = ?, updated_at = ?
                    WHERE user_id = ? AND ticker = ?
                    """,
                    (new_qty, new_avg, _now(), APP_USER_ID, normalized),
                )
            elif side == "sell":
                new_qty = current_qty - quantity
                if new_qty <= 1e-9:
                    conn.execute(
                        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                        (APP_USER_ID, normalized),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE positions
                        SET quantity = ?, avg_cost = ?, updated_at = ?
                        WHERE user_id = ? AND ticker = ?
                        """,
                        (new_qty, current_avg, _now(), APP_USER_ID, normalized),
                    )

            trade = Trade(
                id=str(uuid.uuid4()),
                ticker=normalized,
                side=side,
                quantity=quantity,
                price=price,
                executed_at=_now(),
            )
            conn.execute(
                """
                INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trade.id, APP_USER_ID, trade.ticker, trade.side, trade.quantity, trade.price, trade.executed_at),
            )

            conn.commit()
            updated_profile = conn.execute(
                "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
                (APP_USER_ID,),
            ).fetchone()
            position = self._fetch_position(conn, normalized)
            return {
                "trade": trade,
                "user": self._row_as_dict(updated_profile),
                "position": self._row_as_dict(position),
            }

    def _fetch_position(self, conn: sqlite3.Connection, ticker: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND ticker = ?",
            (APP_USER_ID, _normalize_ticker(ticker)),
        ).fetchone()

    # Portfolio snapshots --------------------------------------------------
    def list_portfolio_snapshots(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, total_value, recorded_at
                FROM portfolio_snapshots
                WHERE user_id = ?
                ORDER BY recorded_at ASC
                """,
                (APP_USER_ID,),
            ).fetchall()
            return [self._row_as_dict(r) for r in rows]

    def append_portfolio_snapshot(self, total_value: float) -> None:
        with self._connect() as conn, self._lock:
            conn.execute(
                """
                INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), APP_USER_ID, total_value, _now()),
            )
            conn.commit()
