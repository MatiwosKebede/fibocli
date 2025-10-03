# models.py
from db import get_conn
from typing import Optional, Dict, Any, List
from utils import iso_now
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

def add_sync_queue(user_id: int, operation: str, data: dict, target_type: str = None, target_id: int | None = None):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sync_queue (user_id, operation, target_type, target_id, data, created_at, status, retry_count) VALUES (?, ?, ?, ?, ?, datetime('now'), 'pending', 0)",
                  (user_id, operation, target_type, target_id, json.dumps(data)))

# -- Query helpers --
def get_leaves_for_user(user_id:int):
    with get_conn() as conn:
        c = conn.cursor()
        # join hierarchy to ensure user scoping: leaves -> sub_branch -> branch -> ... -> ecology -> user
        query = """
            SELECT l.* FROM leaves l
            JOIN sub_branches sb ON sb.id = l.sub_branch_id
            JOIN branches b ON b.id = sb.branch_id
            JOIN super_branches sb2 ON sb2.id = b.super_branch_id
            JOIN trees t ON t.id = sb2.tree_id
            JOIN forests f ON f.id = t.forest_id
            JOIN ecologies e ON e.id = f.ecology_id
            WHERE e.user_id = ? AND l.is_deleted = 0
        """
        c.execute(query, (user_id,))
        return [dict(row) for row in c.fetchall()]

def get_hierarchy_overview(user_id:int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM v_hierarchy_overview WHERE root_id IN (SELECT id FROM ecologies WHERE user_id=?)", (user_id,))
        return [dict(r) for r in c.fetchall()]

def get_pending_reviews_for_user(user_id:int):
    with get_conn() as conn:
        c = conn.cursor()
        # select reviews where target belongs to user
        query = """
            SELECT r.* FROM reviews r
            WHERE r.status='pending' AND EXISTS (
                SELECT 1 FROM ecologies e
                WHERE e.user_id = ? AND (
                    (r.target_type='ecology' AND r.target_id = e.id)
                    OR (r.target_type='forest' AND r.target_id IN (SELECT id FROM forests WHERE ecology_id=e.id))
                    OR (r.target_type='tree' AND r.target_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id=e.id)))
                    OR (r.target_type='super_branch' AND r.target_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id=e.id))))
                    OR (r.target_type='branch' AND r.target_id IN (SELECT id FROM branches WHERE super_branch_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id=e.id)) )))
                    OR (r.target_type='sub_branch' AND r.target_id IN (SELECT id FROM sub_branches WHERE branch_id IN (SELECT id FROM branches WHERE super_branch_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id=e.id))))))
                    OR (r.target_type='leaf' AND r.target_id IN (SELECT id FROM leaves WHERE sub_branch_id IN (SELECT id FROM sub_branches WHERE branch_id IN (SELECT id FROM branches WHERE super_branch_id IN (SELECT id FROM super_branches WHERE tree_id IN (SELECT id FROM trees WHERE forest_id IN (SELECT id FROM forests WHERE ecology_id=e.id)))))))
                )
            )
        """
        c.execute(query, (user_id,))
        return [dict(r) for r in c.fetchall()]

