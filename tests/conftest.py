import pytest
import sqlite3
from db import get_conn, init_db

@pytest.fixture(scope="session")
def db_connection():
    """Set up an in-memory SQLite database for tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with open("schema.sql", "r") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()

@pytest.fixture
def setup_db(db_connection, monkeypatch):
    """Monkeypatch get_conn to use in-memory database."""
    def mock_get_conn():
        return db_connection
    monkeypatch.setattr("db.get_conn", mock_get_conn)
    init_db()
