import bcrypt
import uuid
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from db import get_conn

SESSION_FILE = Path.home() / ".ecology_cli_session"

def hash_password(plain: str) -> bytes:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt())

def check_password(plain: str, hashed: bytes) -> bool:
    """Check if a plain password matches a hashed password."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed)

def create_token() -> str:
    """Generate a random UUID4 token as a hex string."""
    return uuid.uuid4().hex

def save_session_token(token: str):
    """Save a session token to the session file."""
    SESSION_FILE.write_text(json.dumps({"token": token}))

def load_session_token() -> Optional[str]:
    """Load the session token from the session file, if it exists."""
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text())
        return data.get("token")
    except Exception:
        return None

def clear_session():
    """Remove the session file if it exists."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()

def iso_now() -> str:
    """Return the current UTC datetime in ISO format."""
    return datetime.utcnow().isoformat()

def iso_days_from_now(days: int) -> str:
    """Return the date in ISO format for the current UTC date plus the specified number of days."""
    return (datetime.utcnow() + timedelta(days=days)).date().isoformat()

def validate_status(status: str) -> bool:
    """Validate if a status is one of the allowed values."""
    valid_statuses = {"locked", "unlocked", "active", "completed"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
    return True

def are_prerequisites_completed(node_type: str, node_id: int) -> bool:
    """Check if all prerequisites for a node are completed."""
    valid_node_types = {"sub_branch", "leaf"}
    if node_type not in valid_node_types:
        raise ValueError(f"Invalid node_type: {node_type}. Must be one of {valid_node_types}")
    if not isinstance(node_id, int) or node_id <= 0:
        raise ValueError(f"Invalid node_id: {node_id}")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT COUNT(*) as total, SUM(is_completed) as completed
            FROM prerequisites
            WHERE node_type = ? AND node_id = ?
            """,
            (node_type, node_id)
        )
        result = c.fetchone()
        if not result:
            return True  # No prerequisites means all are "completed"
        total = result["total"]
        completed = result["completed"] or 0
        return total == completed

def estimate_review_duration(node_type: str, importance: float, difficulty: int, base_time_minutes: int = 5) -> int:
    """
    Estimate review duration based on node type, importance, and difficulty.
    Returns duration in minutes.
    """
    valid_node_types = {"leaf", "sub_branch", "branch", "super_branch", "tree", "forest", "ecology"}
    if node_type not in valid_node_types:
        raise ValueError(f"Invalid node_type: {node_type}. Must be one of {valid_node_types}")
    if not 0 <= importance <= 1:
        raise ValueError(f"Importance must be between 0 and 1, got {importance}")
    if not 1 <= difficulty <= 5:
        raise ValueError(f"Difficulty must be between 1 and 5, got {difficulty}")

    # Adjust base time based on node type hierarchy
    type_multipliers = {
        "leaf": 1.0,
        "sub_branch": 1.5,
        "branch": 2.0,
        "super_branch": 2.5,
        "tree": 3.0,
        "forest": 3.5,
        "ecology": 4.0
    }
    base_multiplier = type_multipliers.get(node_type, 1.0)
    
    # Adjust for importance and difficulty
    importance_factor = 1 + (importance * 0.5)  # Importance scales duration by up to 50%
    difficulty_factor = 1 + ((difficulty - 1) * 0.25)  # Difficulty scales duration by up to 100%
    
    # Calculate total duration
    duration = base_time_minutes * base_multiplier * importance_factor * difficulty_factor
    return max(5, int(round(duration)))  # Ensure minimum 5 minutes