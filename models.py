# models.py
from db import get_conn
from utils import load_session_token, iso_now
from typing import Optional, Dict, Any, List
import json
import datetime

# -- Users & sessions --
def create_user(full_name: str, username: str, email: str, password_hash: bytes) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        now = iso_now()
        c.execute("INSERT INTO users (full_name, username, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (full_name, username, email, password_hash.decode('utf-8'), now, now))
        return c.lastrowid

def get_user_by_username(username: str) -> Optional[Dict[str,Any]]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND is_deleted = 0", (username,))
        row = c.fetchone()
        return dict(row) if row else None

def store_session_token(user_id: int, token: str, expires_at: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (user_id, token, expires_at, is_valid, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                  (user_id, token, expires_at, 1))

def get_user_from_token(token: str) -> Optional[int]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM sessions WHERE token = ? AND is_valid = 1", (token,))
        row = c.fetchone()
        return int(row["user_id"]) if row else None

def get_logged_in_user() -> Optional[Dict[str,Any]]:
    token = load_session_token()
    if not token:
        return None
    uid = get_user_from_token(token)
    if not uid:
        return None
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (uid,))
        row = c.fetchone()
        return dict(row) if row else None

# -- Hierarchy CRUD --
def create_ecology(user_id: int, name: str, course_name: str = "", course_code: str = "") -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO ecologies (user_id, name, course_name, course_code, created_at, status) VALUES (?, ?, ?, ?, datetime('now'), 'pending')",
                  (user_id, name, course_name, course_code))
        return c.lastrowid

def create_forest(ecology_id:int, name:str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO forests (ecology_id, name, created_at, status) VALUES (?, ?, datetime('now'), 'pending')",
                  (ecology_id, name))
        return c.lastrowid

def create_tree(forest_id:int, name:str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO trees (forest_id, name, created_at, status) VALUES (?, ?, datetime('now'), 'pending')",
                  (forest_id, name))
        return c.lastrowid

def create_super_branch(tree_id:int, name:str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO super_branches (tree_id, name, created_at, status) VALUES (?, ?, datetime('now'), 'pending')",
                  (tree_id, name))
        return c.lastrowid

def create_branch(super_branch_id:int, name:str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO branches (super_branch_id, name, created_at, status) VALUES (?, ?, datetime('now'), 'pending')",
                  (super_branch_id, name))
        return c.lastrowid

def create_sub_branch(branch_id:int, name:str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sub_branches (branch_id, name, created_at, status) VALUES (?, ?, datetime('now'), 'pending')",
                  (branch_id, name))
        return c.lastrowid

def insert_leaf(sub_branch_id: int, name: str, course_name: str, course_code: str, created_at: str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO leaves (sub_branch_id, name, course_name, course_code, created_at, status, base_time_minutes, base_completion_days)
            VALUES (?, ?, ?, ?, ?, 'pending', 5, 4)
        """, (sub_branch_id, name, course_name, course_code, created_at))
        return c.lastrowid

def get_user_settings(user_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return dict(row) if row else DEFAULTS

def get_user_ecology(user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ecologies WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return dict(row) if row else None

def get_user_stats(user_id: int, week_start: str) -> Dict[str, int]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) AS total_leaves 
            FROM leaves 
            WHERE sub_branch_id IN (
                SELECT id FROM sub_branches 
                WHERE branch_id IN (
                    SELECT id FROM branches 
                    WHERE super_branch_id IN (
                        SELECT id FROM super_branches 
                        WHERE tree_id IN (
                            SELECT id FROM trees 
                            WHERE forest_id IN (
                                SELECT id FROM forests 
                                WHERE ecology_id IN (
                                    SELECT id FROM ecologies 
                                    WHERE user_id = ?
                                )
                            )
                        )
                    )
                )
            )
        """, (user_id,))
        total_leaves = c.fetchone()["total_leaves"]
        c.execute("""
            SELECT COUNT(*) AS pending_reviews 
            FROM reviews 
            WHERE status = 'pending' 
            AND target_id IN (
                SELECT id FROM leaves 
                WHERE sub_branch_id IN (
                    SELECT id FROM sub_branches 
                    WHERE branch_id IN (
                        SELECT id FROM branches 
                        WHERE super_branch_id IN (
                            SELECT id FROM super_branches 
                            WHERE tree_id IN (
                                SELECT id FROM trees 
                                WHERE forest_id IN (
                                    SELECT id FROM forests 
                                    WHERE ecology_id IN (
                                        SELECT id FROM ecologies 
                                        WHERE user_id = ?
                                    )
                                )
                            )
                        )
                    )
                )
            )
        """, (user_id,))
        pending_reviews = c.fetchone()["pending_reviews"]
        c.execute("""
            SELECT SUM(estimated_duration) AS scheduled_minutes 
            FROM reviews 
            WHERE status = 'pending' 
            AND target_id IN (
                SELECT id FROM leaves 
                WHERE sub_branch_id IN (
                    SELECT id FROM sub_branches 
                    WHERE branch_id IN (
                        SELECT id FROM branches 
                        WHERE super_branch_id IN (
                            SELECT id FROM super_branches 
                            WHERE tree_id IN (
                                SELECT id FROM trees 
                                WHERE forest_id IN (
                                    SELECT id FROM forests 
                                    WHERE ecology_id IN (
                                        SELECT id FROM ecologies 
                                        WHERE user_id = ?
                                    )
                                )
                            )
                        )
                    )
                )
            )
        """, (user_id,))
        scheduled_minutes = c.fetchone()["scheduled_minutes"] or 0
        c.execute("SELECT reviews_completed FROM weekly_stats WHERE week_number = strftime('%W', ?)", (week_start,))
        row = c.fetchone()
        completed_reviews = row["reviews_completed"] if row else 0
        return {
            "total_leaves": total_leaves,
            "pending_reviews": pending_reviews,
            "scheduled_minutes": scheduled_minutes,
            "completed_reviews": completed_reviews
        }

def get_hierarchy_overview(user_id:int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM v_hierarchy_overview WHERE root_id IN (SELECT id FROM ecologies WHERE user_id=?)", (user_id,))
        return [dict(r) for r in c.fetchall()]

def get_pending_reviews_for_user(user_id:int):
    with get_conn() as conn:
        c = conn.cursor()
        query = """
            SELECT r.* 
            FROM reviews r
            WHERE r.status='pending' AND EXISTS (
                SELECT 1 FROM ecologies e
                WHERE e.user_id = ? AND (
                    (r.target_type='ecology' AND r.target_id = e.id) OR
                    (r.target_type='forest' AND r.target_id IN (SELECT id FROM forests WHERE ecology_id = e.id)) OR
                    (r.target_type='tree' AND r.target_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id = e.id))) OR
                    (r.target_type='super_branch' AND r.target_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id = e.id)))) OR
                    (r.target_type='branch' AND r.target_id IN (SELECT id FROM branches WHERE super_branch_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id = e.id))))) OR
                    (r.target_type='sub_branch' AND r.target_id IN (SELECT id FROM sub_branches WHERE branch_id IN (SELECT id FROM branches WHERE super_branch_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id = e.id)))))) OR
                    (r.target_type='leaf' AND r.target_id IN (SELECT id FROM leaves WHERE sub_branch_id IN (SELECT id FROM sub_branches WHERE branch_id IN (SELECT id FROM branches WHERE super_branch_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id = e.id)))))))
                )
            )
        """
        c.execute(query, (user_id,))
        return [dict(r) for r in c.fetchall()]