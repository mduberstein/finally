"""Every database test runs against its own temporary file."""

import pytest

from app.db import transaction


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh file so the real db/finally.db is never touched."""
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path


@pytest.fixture
def conn(db_path):
    """An initialized, seeded database inside one open transaction."""
    with transaction() as connection:
        yield connection
