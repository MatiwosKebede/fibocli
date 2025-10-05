import sqlite3
from db import get_conn

def migrate_null_fields():
    """Update NULL fields in node tables with default values."""
    tables = [
        "ecologies", "forests", "trees", "super_branches",
        "branches", "sub_branches", "leaves"
    ]
    defaults = {
        "understanding_level": 0.5,
        "difficulty": 3,
        "importance": 0.5,
        "base_time_minutes": 30,
        "study_duration_minutes": 30,
        "completion_days": 4,
        "fibonacci_index": 1
    }

    with get_conn() as conn:
        c = conn.cursor()
        for table in tables:
            updates = ", ".join(f"{field} = COALESCE({field}, {value})" for field, value in defaults.items())
            c.execute(f"UPDATE {table} SET {updates} WHERE is_deleted = 0")
            print(f"Updated {table}: {c.rowcount} rows affected")
        conn.commit()

if __name__ == "__main__":
    migrate_null_fields()
