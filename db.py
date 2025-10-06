import sqlite3
from contextlib import contextmanager
import os
from typing import Iterator

DB_PATH = os.environ.get("ECOLOGY_DB", "/mnt/c/Users/HP/Documents/METS/forest-v4/fibocli/ecology.db")
SCHEMA_FILE = os.environ.get("ECOLOGY_SCHEMA", "/mnt/c/Users/HP/Documents/METS/forest-v4/fibocli/schema.sql")

def _make_conn():
    """Create a new SQLite connection with row factory and foreign key support."""
    try:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        raise RuntimeError(f"Database connection error: {e}. Ensure DB_PATH is correct and accessible: {DB_PATH}")

@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context manager for SQLite connections, handling commit and rollback."""
    conn = _make_conn()
    try:
        yield conn
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Database operation error: {e}. Check database schema and data integrity.")
    finally:
        conn.commit()
        conn.close()

def init_db(overwrite: bool = False) -> None:
    """
    Create or initialize the database using schema.sql.
    Overwrite deletes the existing database first.
    """
    if overwrite and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"Deleted existing database: {DB_PATH}")
        except OSError as e:
            raise RuntimeError(f"Error deleting database: {e}. Check file permissions for {DB_PATH}")
    if not os.path.exists(DB_PATH):
        if not os.path.exists(SCHEMA_FILE):
            raise FileNotFoundError(f"Schema file not found at {SCHEMA_FILE}. Ensure ECOLOGY_SCHEMA is set correctly.")
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema = f.read()
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.executescript(schema)
            conn.commit()
            print("✅ Database initialized successfully with schema.")
        except sqlite3.Error as e:
            conn.rollback()
            raise RuntimeError(f"Database initialization error: {e}. Verify schema.sql syntax and constraints.")
        finally:
            conn.close()
    else:
        with get_conn() as conn:
            conn.execute("PRAGMA optimize;")
            print("Database already exists, optimized for performance.")