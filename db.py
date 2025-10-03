# db.py
import sqlite3
from contextlib import contextmanager
import os
from typing import Iterator

DB_PATH = os.environ.get("ECOLOGY_DB", "/mnt/c/Users/HP/Documents/METS/forest-v4/fibocli/ecology.db")
SCHEMA_FILE = os.environ.get("ECOLOGY_SCHEMA", "/mnt/c/Users/HP/Documents/METS/forest-v4/fibocli/schema.sql")

def _make_conn():
    try:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        raise RuntimeError(f"Database connection error: {e}")

@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _make_conn()
    try:
        yield conn
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Database operation error: {e}")
    finally:
        conn.commit()
        conn.close()

def init_db(overwrite: bool = False) -> None:
    """Create DB file using schema.sql. Overwrite deletes existing DB first."""
    if overwrite and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"Deleted existing database: {DB_PATH}")
        except OSError as e:
            raise RuntimeError(f"Error deleting database: {e}")
    if not os.path.exists(DB_PATH):
        if not os.path.exists(SCHEMA_FILE):
            raise FileNotFoundError(f"schema.sql not found at {SCHEMA_FILE}")
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema = f.read()
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.executescript(schema)
            conn.commit()
            print("✅ Database initialized successfully.")
        except sqlite3.Error as e:
            conn.rollback()
            raise RuntimeError(f"Database initialization error: {e}\nCheck schema.sql for syntax errors.")
        finally:
            conn.close()
    else:
        with get_conn() as conn:
            conn.execute("PRAGMA optimize;")
            print("Database already exists, optimized.")
