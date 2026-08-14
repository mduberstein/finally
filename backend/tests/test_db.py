import sqlite3

from app.db import database


def _use_tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))
    return db_file


class TestInitialize:
    def test_fresh_init_creates_file_and_tables(self, tmp_path, monkeypatch):
        db_file = _use_tmp_db(tmp_path, monkeypatch)

        database.initialize()

        assert db_file.exists()
        with sqlite3.connect(db_file) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        expected = {
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        }
        assert expected <= tables

    def test_fresh_init_seeds_ten_watchlist_rows_in_order(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)

        database.initialize()

        assert database.watchlist_tickers() == list(database.DEFAULT_TICKERS)

    def test_fresh_init_seeds_one_users_profile_row(self, tmp_path, monkeypatch):
        db_file = _use_tmp_db(tmp_path, monkeypatch)

        database.initialize()

        with sqlite3.connect(db_file) as conn:
            rows = conn.execute("SELECT id, cash_balance FROM users_profile").fetchall()

        assert rows == [(database.DEFAULT_USER_ID, database.DEFAULT_CASH_BALANCE)]

    def test_second_init_preserves_mutated_cash_balance(self, tmp_path, monkeypatch):
        db_file = _use_tmp_db(tmp_path, monkeypatch)

        database.initialize()
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (4242.0, database.DEFAULT_USER_ID),
            )
            conn.commit()

        database.initialize()

        with sqlite3.connect(db_file) as conn:
            (cash_balance,) = conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id = ?",
                (database.DEFAULT_USER_ID,),
            ).fetchone()
        assert cash_balance == 4242.0
        assert len(database.watchlist_tickers()) == 10

    def test_missing_table_is_recreated_without_discarding_existing_rows(
        self, tmp_path, monkeypatch
    ):
        db_file = _use_tmp_db(tmp_path, monkeypatch)

        database.initialize()
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (7777.0, database.DEFAULT_USER_ID),
            )
            conn.execute("DROP TABLE trades")
            conn.commit()

        database.initialize()

        with sqlite3.connect(db_file) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            (cash_balance,) = conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id = ?",
                (database.DEFAULT_USER_ID,),
            ).fetchone()

        assert "trades" in tables
        assert cash_balance == 7777.0
        assert len(database.watchlist_tickers()) == 10


class TestWatchlistTickers:
    def test_returns_empty_list_before_initialize(self, tmp_path, monkeypatch):
        db_file = _use_tmp_db(tmp_path, monkeypatch)
        with sqlite3.connect(db_file) as conn:
            conn.executescript((database._SCHEMA_PATH).read_text())
            conn.commit()

        assert database.watchlist_tickers() == []
