from utils import create_token, iso_now
from datetime import datetime, timedelta
import sqlite3
from datetime import UTC  # Add this import

DB_PATH = "/mnt/c/Users/HP/Documents/METS/forest-v4/fibocli/ecology.db"

def create_reset_token(user_id):
    token = create_token()
    expires_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()  # Updated line
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at, used, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, token, expires_at, 0, iso_now())
    )
    conn.commit()
    conn.close()
    print(f"Reset token for user ID {user_id}: {token}")

# Replace with the user ID
create_reset_token(1)
