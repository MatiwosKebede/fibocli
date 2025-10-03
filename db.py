# db.py
import sqlite3
from contextlib import contextmanager
import os
from typing import Iterator

DB_PATH = os.environ.get("ECOLOGY_DB", "ecology.db")
SCHEMA_FILE = os.environ.get("ECOLOGY_SCHEMA", "schema.sql")

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
            # Split schema into individual statements for better error reporting
            statements = schema.split(';')
            for stmt in statements:
                stmt = stmt.strip()
                if stmt:
                    try:
                        c.execute(stmt)
                    except sqlite3.Error as e:
                        raise RuntimeError(f"Error executing SQL: {stmt}\nError: {e}")
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise RuntimeError(f"Database initialization error: {e}")
        finally:
            conn.close()
    else:
        with get_conn() as conn:
            conn.execute("PRAGMA optimize;")