"""Portfolio value over time, the series behind the P&L chart."""

import sqlite3

from .models import DEFAULT_USER_ID, Snapshot, new_id, utc_now


def append(conn: sqlite3.Connection, total_value: float) -> Snapshot:
    """Record the portfolio total at this moment."""
    snapshot = Snapshot(total_value=total_value, recorded_at=utc_now())
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)"
        " VALUES (?, ?, ?, ?)",
        (new_id(), DEFAULT_USER_ID, snapshot.total_value, snapshot.recorded_at),
    )
    return snapshot


def list_recent(conn: sqlite3.Connection, limit: int = 500) -> list[Snapshot]:
    """The newest `limit` snapshots, returned oldest first so a chart can plot them."""
    rows = conn.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots"
        " WHERE user_id = ? ORDER BY recorded_at DESC, rowid DESC LIMIT ?",
        (DEFAULT_USER_ID, limit),
    ).fetchall()
    return [_snapshot(row) for row in reversed(rows)]


def _snapshot(row: sqlite3.Row) -> Snapshot:
    return Snapshot(total_value=row["total_value"], recorded_at=row["recorded_at"])
