# db.py
import sqlite3
from contextlib import contextmanager
import os
from typing import Iterator

DB_PATH = os.environ.get("ECOLOGY_DB", "ecology.db")
SCHEMA_FILE = os.environ.get("ECOLOGY_SCHEMA", "schema.sql")

def _make_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _make_conn()
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db(overwrite: bool = False) -> None:
    """Create DB file using schema.sql. overwrite deletes existing DB first."""
    if overwrite and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if not os.path.exists(DB_PATH):
        if not os.path.exists(SCHEMA_FILE):
            raise FileNotFoundError("schema.sql not found; please place your full schema at schema.sql")
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema = f.read()
        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.executescript(schema)
            conn.commit()
        finally:
            conn.close()
    else:
        # run optimize pragmas
        with get_conn() as conn:
            conn.execute("PRAGMA optimize;")

