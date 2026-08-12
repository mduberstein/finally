"""Connection configuration and lazy schema creation."""

from pathlib import Path

from app.db import connect, database_path, initialize, transaction
from app.db.seed import DEFAULT_TICKERS, STARTING_CASH

TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


def table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_database_path_defaults_to_db_finally_db(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    assert database_path() == Path("db/finally.db")


def test_database_path_reads_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "other.db"))
    assert database_path() == tmp_path / "other.db"


def test_connect_creates_missing_parent_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "nested" / "deep" / "finally.db"))
    connect().close()
    assert (tmp_path / "nested" / "deep").is_dir()


def test_initialize_seeds_when_the_parent_directory_is_missing(tmp_path, monkeypatch):
    """A fresh clone has no db/ directory, and a volume mount can land on an empty path."""
    target = tmp_path / "absent" / "finally.db"
    monkeypatch.setenv("DB_PATH", str(target))
    assert not target.parent.exists()

    initialize()

    assert target.exists()
    conn = connect()
    tables = table_names(conn)
    tickers = conn.execute("SELECT ticker FROM watchlist ORDER BY rowid").fetchall()
    conn.close()
    assert tables >= TABLES
    assert [row["ticker"] for row in tickers] == list(DEFAULT_TICKERS)


def test_connect_enables_wal(db_path):
    conn = connect()
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"


def test_initialize_creates_every_table(db_path):
    initialize()
    conn = connect()
    assert table_names(conn) >= TABLES
    conn.close()


def test_initialize_seeds_profile_and_watchlist(db_path):
    initialize()
    conn = connect()
    cash = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()
    tickers = conn.execute("SELECT ticker FROM watchlist ORDER BY rowid").fetchall()
    conn.close()
    assert cash["cash_balance"] == STARTING_CASH
    assert [row["ticker"] for row in tickers] == list(DEFAULT_TICKERS)


def test_seed_rows_are_written_once(db_path):
    initialize()
    initialize()
    initialize()
    conn = connect()
    profiles = conn.execute("SELECT COUNT(*) AS n FROM users_profile").fetchone()["n"]
    tickers = conn.execute("SELECT COUNT(*) AS n FROM watchlist").fetchone()["n"]
    conn.close()
    assert profiles == 1
    assert tickers == len(DEFAULT_TICKERS)


def test_initialize_does_not_resurrect_removed_seed_data(db_path):
    with transaction() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = 'AAPL'")

    initialize()

    with transaction() as conn:
        remaining = conn.execute("SELECT COUNT(*) AS n FROM watchlist").fetchone()["n"]
    assert remaining == len(DEFAULT_TICKERS) - 1


def test_initialize_preserves_existing_data(db_path):
    with transaction() as conn:
        conn.execute("UPDATE users_profile SET cash_balance = 42.0 WHERE id = 'default'")

    initialize()

    with transaction() as conn:
        cash = conn.execute("SELECT cash_balance FROM users_profile").fetchone()["cash_balance"]
    assert cash == 42.0


def test_transaction_initializes_on_first_use(db_path):
    assert not db_path.exists()
    with transaction() as conn:
        assert table_names(conn) >= TABLES


def test_an_empty_file_is_treated_as_a_new_database(db_path):
    db_path.touch()
    initialize()
    conn = connect()
    tickers = conn.execute("SELECT COUNT(*) AS n FROM watchlist").fetchone()["n"]
    conn.close()
    assert tickers == len(DEFAULT_TICKERS)
