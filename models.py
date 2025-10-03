import sqlite3
from db import get_conn
from utils import hash_password, check_password, iso_now
from typing import Optional, List, Dict, Any
import datetime
from settings import DEFAULTS

# -- Users & Sessions --
def create_user(full_name: str, username: str, email: str, password_hash: bytes) -> int:
    """Create a new user and return their ID."""
    with get_conn() as conn:
        c = conn.cursor()
        now = iso_now()
        c.execute(
            "INSERT INTO users (full_name, username, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (full_name, username, email, password_hash, now, now)
        )
        return c.lastrowid

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve a user by username if not deleted."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND is_deleted = 0", (username,))
        row = c.fetchone()
        return dict(row) if row else None

def check_user_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify username and password, return user if valid."""
    user = get_user_by_username(username)
    if user and check_password(password, user["password_hash"]):
        return user
    return None

def store_session_token(user_id: int, token: str, expires_at: str) -> None:
    """Store a new session token, invalidating previous ones."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE sessions SET is_valid = 0 WHERE user_id = ?", (user_id,))
        c.execute(
            "INSERT INTO sessions (user_id, token, expires_at, is_valid, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, token, expires_at, 1, iso_now())
        )

def get_user_from_token(token: str) -> Optional[int]:
    """Get user ID from a valid session token."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT user_id FROM sessions WHERE token = ? AND is_valid = 1 AND expires_at > ?",
            (token, iso_now())
        )
        row = c.fetchone()
        return int(row["user_id"]) if row else None

def get_logged_in_user() -> Optional[Dict[str, Any]]:
    """Get the currently logged-in user based on session token."""
    from utils import load_session_token
    token = load_session_token()
    if not token:
        return None
    uid = get_user_from_token(token)
    if not uid:
        return None
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ? AND is_deleted = 0", (uid,))
        row = c.fetchone()
        return dict(row) if row else None

# -- Hierarchy CRUD --
def create_ecology(user_id: int, name: str, course_name: Optional[str] = None, course_code: Optional[str] = None) -> int:
    """Create a new ecology and return its ID."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO ecologies (user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, ?, 'pending')",
            (user_id, name, course_name, course_code, iso_now())
        )
        return c.lastrowid

def create_forest(ecology_id: int, name: str, course_name: Optional[str] = None, course_code: Optional[str] = None) -> int:
    """Create a new forest under an ecology and return its ID."""
    user_id = get_user_from_ecology(ecology_id)
    if not user_id:
        raise ValueError(f"Ecology ID {ecology_id} not found.")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO forests (ecology_id, user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (ecology_id, user_id, name, course_name, course_code, iso_now())
        )
        return c.lastrowid

def create_tree(forest_id: int, name: str, course_name: Optional[str] = None, course_code: Optional[str] = None) -> int:
    """Create a new tree under a forest and return its ID."""
    user_id = get_user_from_forest(forest_id)
    if not user_id:
        raise ValueError(f"Forest ID {forest_id} not found.")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO trees (forest_id, user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (forest_id, user_id, name, course_name, course_code, iso_now())
        )
        return c.lastrowid

def create_super_branch(tree_id: int, name: str, course_name: Optional[str] = None, course_code: Optional[str] = None) -> int:
    """Create a new super-branch under a tree and return its ID."""
    user_id = get_user_from_tree(tree_id)
    if not user_id:
        raise ValueError(f"Tree ID {tree_id} not found.")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO super_branches (tree_id, user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (tree_id, user_id, name, course_name, course_code, iso_now())
        )
        return c.lastrowid

def create_branch(super_branch_id: int, name: str, course_name: Optional[str] = None, course_code: Optional[str] = None) -> int:
    """Create a new branch under a super-branch and return its ID."""
    user_id = get_user_from_super_branch(super_branch_id)
    if not user_id:
        raise ValueError(f"Super-branch ID {super_branch_id} not found.")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO branches (super_branch_id, user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (super_branch_id, user_id, name, course_name, course_code, iso_now())
        )
        return c.lastrowid

def create_sub_branch(branch_id: int, name: str, course_name: Optional[str] = None, course_code: Optional[str] = None) -> int:
    """Create a new sub-branch under a branch and return its ID."""
    user_id = get_user_from_branch(branch_id)
    if not user_id:
        raise ValueError(f"Branch ID {branch_id} not found.")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO sub_branches (branch_id, user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (branch_id, user_id, name, course_name, course_code, iso_now())
        )
        return c.lastrowid

def insert_leaf(sub_branch_id: int, name: str, course_name: Optional[str], course_code: Optional[str], created_at: str, resource_type: str = 'other') -> int:
    """Create a new leaf under a sub-branch and return its ID."""
    valid_resource_types = ['book', 'video', 'web_course', 'other']
    if resource_type not in valid_resource_types:
        raise ValueError(f"Invalid resource_type: {resource_type}. Must be one of {valid_resource_types}")
    user_id = get_user_from_sub_branch(sub_branch_id)
    if not user_id:
        raise ValueError(f"Sub-branch ID {sub_branch_id} not found.")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO leaves (sub_branch_id, user_id, name, course_name, course_code, resource_type, created_at, status, 
            base_time_minutes, base_completion_days, understanding_level, importance, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 5, 4, 0.0, 0.5, 3)
            """,
            (sub_branch_id, user_id, name, course_name, course_code, resource_type, created_at)
        )
        return c.lastrowid

# -- Helper Functions for User ID --
def get_user_from_ecology(ecology_id: int) -> Optional[int]:
    """Get user ID from an ecology ID, raise ValueError if not found."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM ecologies WHERE id = ? AND is_deleted = 0", (ecology_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Ecology ID {ecology_id} not found.")
        return row["user_id"]

def get_user_from_forest(forest_id: int) -> Optional[int]:
    """Get user ID from a forest ID, raise ValueError if not found."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM forests WHERE id = ? AND is_deleted = 0", (forest_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Forest ID {forest_id} not found.")
        return row["user_id"]

def get_user_from_tree(tree_id: int) -> Optional[int]:
    """Get user ID from a tree ID, raise ValueError if not found."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM trees WHERE id = ? AND is_deleted = 0", (tree_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Tree ID {tree_id} not found.")
        return row["user_id"]

def get_user_from_super_branch(super_branch_id: int) -> Optional[int]:
    """Get user ID from a super-branch ID, raise ValueError if not found."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM super_branches WHERE id = ? AND is_deleted = 0", (super_branch_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Super-branch ID {super_branch_id} not found.")
        return row["user_id"]

def get_user_from_branch(branch_id: int) -> Optional[int]:
    """Get user ID from a branch ID, raise ValueError if not found."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM branches WHERE id = ? AND is_deleted = 0", (branch_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Branch ID {branch_id} not found.")
        return row["user_id"]

def get_user_from_sub_branch(sub_branch_id: int) -> Optional[int]:
    """Get user ID from a sub-branch ID, raise ValueError if not found."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM sub_branches WHERE id = ? AND is_deleted = 0", (sub_branch_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Sub-branch ID {sub_branch_id} not found.")
        return row["user_id"]

# -- Settings --
def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Get user settings or return defaults if none exist."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return dict(row) if row else DEFAULTS

# -- Ecology --
def get_user_ecology(user_id: int) -> Optional[Dict[str, Any]]:
    """Get the user's ecology if not deleted."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ecologies WHERE user_id = ? AND is_deleted = 0", (user_id,))
        row = c.fetchone()
        return dict(row) if row else None

# -- Hierarchy Overview with Path --
def get_hierarchy_overview(user_id: int) -> List[Dict[str, Any]]:
    """Get a complete hierarchy overview for the user with paths."""
    with get_conn() as conn:
        c = conn.cursor()
        nodes = []
        # Ecologies
        c.execute(
            """
            SELECT id, name, course_name, course_code, 'ecology' AS node_type, 0 AS parent_id, NULL AS parent_type, 
                   status, understanding_level, importance, difficulty, name AS path
            FROM ecologies 
            WHERE user_id = ? AND is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        # Forests
        c.execute(
            """
            SELECT f.id, f.name, f.course_name, f.course_code, 'forest' AS node_type, f.ecology_id AS parent_id, 
                   'ecology' AS parent_type, f.status, f.understanding_level, f.importance, f.difficulty,
                   e.name || ' > ' || f.name AS path
            FROM forests f JOIN ecologies e ON f.ecology_id = e.id
            WHERE f.user_id = ? AND f.is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        # Trees
        c.execute(
            """
            SELECT t.id, t.name, t.course_name, t.course_code, 'tree' AS node_type, t.forest_id AS parent_id, 
                   'forest' AS parent_type, t.status, t.understanding_level, t.importance, t.difficulty,
                   e.name || ' > ' || f.name || ' > ' || t.name AS path
            FROM trees t JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
            WHERE t.user_id = ? AND t.is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        # Super-branches
        c.execute(
            """
            SELECT s.id, s.name, s.course_name, s.course_code, 'super_branch' AS node_type, s.tree_id AS parent_id, 
                   'tree' AS parent_type, s.status, s.understanding_level, s.importance, s.difficulty,
                   e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name AS path
            FROM super_branches s JOIN trees t ON s.tree_id = t.id
            JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
            WHERE s.user_id = ? AND s.is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        # Branches
        c.execute(
            """
            SELECT b.id, b.name, b.course_name, b.course_code, 'branch' AS node_type, b.super_branch_id AS parent_id, 
                   'super_branch' AS parent_type, b.status, b.understanding_level, b.importance, b.difficulty,
                   e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name || ' > ' || b.name AS path
            FROM branches b JOIN super_branches s ON b.super_branch_id = s.id
            JOIN trees t ON s.tree_id = t.id JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
            WHERE b.user_id = ? AND b.is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        # Sub-branches
        c.execute(
            """
            SELECT sb.id, sb.name, sb.course_name, sb.course_code, 'sub_branch' AS node_type, sb.branch_id AS parent_id, 
                   'branch' AS parent_type, sb.status, sb.understanding_level, sb.importance, sb.difficulty,
                   e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name || ' > ' || b.name || ' > ' || sb.name AS path
            FROM sub_branches sb JOIN branches b ON sb.branch_id = b.id
            JOIN super_branches s ON b.super_branch_id = s.id JOIN trees t ON s.tree_id = t.id
            JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
            WHERE sb.user_id = ? AND sb.is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        # Leaves
        c.execute(
            """
            SELECT l.id, l.name, l.course_name, l.course_code, l.resource_type, 'leaf' AS node_type, l.sub_branch_id AS parent_id, 
                   'sub_branch' AS parent_type, l.status, l.understanding_level, l.importance, l.difficulty,
                   e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name || ' > ' || b.name || ' > ' || sb.name || ' > ' || l.name AS path
            FROM leaves l JOIN sub_branches sb ON l.sub_branch_id = sb.id
            JOIN branches b ON sb.branch_id = b.id JOIN super_branches s ON b.super_branch_id = s.id
            JOIN trees t ON s.tree_id = t.id JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
            WHERE l.user_id = ? AND l.is_deleted = 0
            """, 
            (user_id,)
        )
        nodes.extend([dict(row) for row in c.fetchall()])
        return nodes

# -- Stats --
def get_user_stats(user_id: int, week_start: str) -> Dict[str, Any]:
    """Get user statistics for a given week."""
    try:
        datetime.date.fromisoformat(week_start)
    except ValueError:
        raise ValueError(f"Invalid week_start format: {week_start}. Must be YYYY-MM-DD.")
    with get_conn() as conn:
        c = conn.cursor()
        # Total leaves
        c.execute("SELECT COUNT(*) as cnt FROM leaves WHERE user_id = ? AND is_deleted = 0", (user_id,))
        total_leaves = c.fetchone()["cnt"]
        # Pending reviews
        c.execute(
            """
            SELECT COUNT(*) as cnt 
            FROM reviews r
            JOIN (
                SELECT 'leaf' AS target_type, id, user_id FROM leaves WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'sub_branch' AS target_type, id, user_id FROM sub_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'branch' AS target_type, id, user_id FROM branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'super_branch' AS target_type, id, user_id FROM super_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'tree' AS target_type, id, user_id FROM trees WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'forest' AS target_type, id, user_id FROM forests WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'ecology' AS target_type, id, user_id FROM ecologies WHERE user_id = ? AND is_deleted = 0
            ) n ON r.target_type = n.target_type AND r.target_id = n.id
            WHERE r.status = 'pending'
            """, 
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id)
        )
        pending_reviews = c.fetchone()["cnt"]
        # Scheduled minutes
        c.execute(
            """
            SELECT SUM(r.actual_duration) as total
            FROM schedules s JOIN reviews r ON s.related_id = r.id AND s.type = 'review'
            JOIN (
                SELECT 'leaf' AS target_type, id, user_id FROM leaves WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'sub_branch' AS target_type, id, user_id FROM sub_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'branch' AS target_type, id, user_id FROM branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'super_branch' AS target_type, id, user_id FROM super_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'tree' AS target_type, id, user_id FROM trees WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'forest' AS target_type, id, user_id FROM forests WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'ecology' AS target_type, id, user_id FROM ecologies WHERE user_id = ? AND is_deleted = 0
            ) n ON r.target_type = n.target_type AND r.target_id = n.id
            WHERE s.start_datetime >= ? AND s.start_datetime < ?
            """, 
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id, week_start, 
             (datetime.date.fromisoformat(week_start) + datetime.timedelta(days=7)).isoformat())
        )
        scheduled_minutes = c.fetchone()["total"] or 0
        # Completed reviews and average understanding
        c.execute(
            """
            SELECT COUNT(*) as cnt, AVG(r.understanding_after) as avg_understanding
            FROM reviews r
            JOIN (
                SELECT 'leaf' AS target_type, id, user_id FROM leaves WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'sub_branch' AS target_type, id, user_id FROM sub_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'branch' AS target_type, id, user_id FROM branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'super_branch' AS target_type, id, user_id FROM super_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'tree' AS target_type, id, user_id FROM trees WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'forest' AS target_type, id, user_id FROM forests WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'ecology' AS target_type, id, user_id FROM ecologies WHERE user_id = ? AND is_deleted = 0
            ) n ON r.target_type = n.target_type AND r.target_id = n.id
            WHERE r.status = 'completed'
            """, 
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id)
        )
        completed_stats = c.fetchone()
        completed_reviews = completed_stats["cnt"]
        avg_understanding = round(completed_stats["avg_understanding"], 2) if completed_stats["avg_understanding"] else 0.0
        # Streaks
        c.execute(
            "SELECT current_length, longest_length FROM streaks WHERE user_id = ?",
            (user_id,)
        )
        streak = c.fetchone()
        # Readiness
        c.execute(
            "SELECT AVG(readiness_score) as avg_readiness FROM daily_readiness WHERE user_id = ? AND date >= ? AND date < ?",
            (user_id, week_start, (datetime.date.fromisoformat(week_start) + datetime.timedelta(days=7)).isoformat())
        )
        readiness = c.fetchone()
        return {
            "total_leaves": total_leaves,
            "pending_reviews": pending_reviews,
            "scheduled_minutes": scheduled_minutes,
            "completed_reviews": completed_reviews,
            "avg_understanding": avg_understanding,
            "current_streak": streak["current_length"] if streak else 0,
            "longest_streak": streak["longest_length"] if streak else 0,
            "avg_readiness": round(readiness["avg_readiness"], 2) if readiness and readiness["avg_readiness"] else 0.0
        }

# -- Reviews --
def get_pending_reviews_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all pending reviews for the user across all node types."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT r.*, t.name, t.course_name, t.course_code,
                   CASE 
                       WHEN r.target_type = 'leaf' THEN t.resource_type
                       ELSE NULL 
                   END as resource_type
            FROM reviews r
            JOIN (
                SELECT 'leaf' AS target_type, id, user_id, name, course_name, course_code, resource_type
                FROM leaves WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'sub_branch' AS target_type, id, user_id, name, course_name, course_code, NULL
                FROM sub_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'branch' AS target_type, id, user_id, name, course_name, course_code, NULL
                FROM branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'super_branch' AS target_type, id, user_id, name, course_name, course_code, NULL
                FROM super_branches WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'tree' AS target_type, id, user_id, name, course_name, course_code, NULL
                FROM trees WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'forest' AS target_type, id, user_id, name, course_name, course_code, NULL
                FROM forests WHERE user_id = ? AND is_deleted = 0
                UNION ALL
                SELECT 'ecology' AS target_type, id, user_id, name, course_name, course_code, NULL
                FROM ecologies WHERE user_id = ? AND is_deleted = 0
            ) t ON r.target_type = t.target_type AND r.target_id = t.id
            WHERE r.status = 'pending'
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id)
        )
        return [dict(row) for row in c.fetchall()]

# -- Interactive Parent Selection --
def get_available_parents(parent_type: str, user_id: int) -> List[Dict[str, Any]]:
    """Get available parent nodes for the given type and user."""
    with get_conn() as conn:
        c = conn.cursor()
        table = parent_type + "s" if parent_type != "sub_branch" else "sub_branches"
        if parent_type == "ecology":
            c.execute(
                f"""
                SELECT id, name, course_name, course_code, name AS path
                FROM {table}
                WHERE user_id = ? AND is_deleted = 0
                """, 
                (user_id,)
            )
        elif parent_type == "forest":
            c.execute(
                f"""
                SELECT f.id, f.name, f.course_name, f.course_code, e.name || ' > ' || f.name AS path
                FROM {table} f JOIN ecologies e ON f.ecology_id = e.id
                WHERE f.user_id = ? AND f.is_deleted = 0
                """, 
                (user_id,)
            )
        elif parent_type == "tree":
            c.execute(
                f"""
                SELECT t.id, t.name, t.course_name, t.course_code, e.name || ' > ' || f.name || ' > ' || t.name AS path
                FROM {table} t JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
                WHERE t.user_id = ? AND t.is_deleted = 0
                """, 
                (user_id,)
            )
        elif parent_type == "super_branch":
            c.execute(
                f"""
                SELECT s.id, s.name, s.course_name, s.course_code, e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name AS path
                FROM {table} s JOIN trees t ON s.tree_id = t.id
                JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
                WHERE s.user_id = ? AND s.is_deleted = 0
                """, 
                (user_id,)
            )
        elif parent_type == "branch":
            c.execute(
                f"""
                SELECT b.id, b.name, b.course_name, b.course_code, e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name || ' > ' || b.name AS path
                FROM {table} b JOIN super_branches s ON b.super_branch_id = s.id
                JOIN trees t ON s.tree_id = t.id JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
                WHERE b.user_id = ? AND b.is_deleted = 0
                """, 
                (user_id,)
            )
        elif parent_type == "sub_branch":
            c.execute(
                f"""
                SELECT sb.id, sb.name, sb.course_name, sb.course_code, e.name || ' > ' || f.name || ' > ' || t.name || ' > ' || s.name || ' > ' || b.name || ' > ' || sb.name AS path
                FROM {table} sb JOIN branches b ON sb.branch_id = b.id
                JOIN super_branches s ON b.super_branch_id = s.id JOIN trees t ON s.tree_id = t.id
                JOIN forests f ON t.forest_id = f.id JOIN ecologies e ON f.ecology_id = e.id
                WHERE sb.user_id = ? AND is_deleted = 0
                """, 
                (user_id,)
            )
        else:
            raise ValueError(f"Invalid parent_type: {parent_type}")
        return [dict(row) for row in c.fetchall()]
