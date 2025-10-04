import pytest
from db import get_conn, init_db

def test_db_initialization(setup_db):
    """Test database initialization."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert c.fetchone() is not None

def test_foreign_keys_enabled(setup_db):
    """Test that foreign keys are enabled."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys")
    assert c.fetchone()[0] == 1
