import math
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from db import get_conn
from settings import DEFAULTS
from models import get_user_settings
from utils import iso_now

# --- Table Name Mapping ---
TABLE_MAP = {
    "ecology": "ecologies",
    "forest": "forests",
    "tree": "trees",
    "super_branch": "super_branches",
    "branch": "branches",
    "sub_branch": "sub_branches",
    "leaf": "leaves"
}

# --- Fibonacci ---
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if not isinstance(n, int):
        raise ValueError(f"Invalid input for Fibonacci: {n}")
    if n <= 0:
        return 0
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a

def get_fib_from_table(n: int) -> int:
    """Retrieve Fibonacci value from table or calculate it."""
    if not isinstance(n, int) or n < 0:
        raise ValueError(f"Invalid Fibonacci index: {n}")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM fibonacci WHERE fib_index = ?", (n,))
        row = c.fetchone()
        if row:
            return int(row["value"])
    return fibonacci(n)

# --- Factor Calculations ---
def _understanding_factor(u: Optional[float], k_u: float) -> float:
    """Calculate understanding factor for review interval."""
    if not isinstance(k_u, (int, float)) or not (0 <= k_u <= 1):
        print(f"Warning: Invalid k_u {k_u}, defaulting to {DEFAULTS['k_u']}")
        k_u = DEFAULTS["k_u"]
    u_val = u if u is not None and isinstance(u, (int, float)) else 0.0
    if not (0 <= u_val <= 1):
        print(f"Warning: Invalid understanding_level {u_val}, defaulting to 0.0")
        u_val = 0.0
    return 1 + k_u * (u_val - 0.5)

def _difficulty_factor(d: Optional[int], k_d: float) -> float:
    """Calculate difficulty factor for review interval."""
    if not isinstance(k_d, (int, float)) or not (0 <= k_d <= 1):
        print(f"Warning: Invalid k_d {k_d}, defaulting to {DEFAULTS['k_d']}")
        k_d = DEFAULTS["k_d"]
    d_val = d if d is not None and isinstance(d, (int, float)) else 3
    if not (1 <= d_val <= 5):
        print(f"Warning: Invalid difficulty {d_val}, defaulting to 3")
        d_val = 3
    return 1 + k_d * (d_val / 5 - 0.5)

def _importance_factor(i: Optional[float], k_i: float) -> float:
    """Calculate importance factor for review interval."""
    if not isinstance(k_i, (int, float)) or not (0 <= k_i <= 1):
        print(f"Warning: Invalid k_i {k_i}, defaulting to {DEFAULTS['k_i']}")
        k_i = DEFAULTS["k_i"]
    i_val = i if i is not None and isinstance(i, (int, float)) else 0.5
    if not (0 <= i_val <= 1):
        print(f"Warning: Invalid importance {i_val}, defaulting to 0.5")
        i_val = 0.5
    return 1 + k_i * (i_val - 0.5)

def iso_days_from_now(days: int) -> str:
    """Return the datetime in ISO format for the current date plus the specified number of days."""
    return (datetime.now() + timedelta(days=days)).isoformat()

# --- Prerequisite Checks ---
def check_prerequisites(node_type: str, node_id: int) -> bool:
    """Check if all prerequisites for a node are completed."""
    if not isinstance(node_type, str) or node_type not in TABLE_MAP:
        raise ValueError(f"Invalid node_type: {node_type}")
    if not isinstance(node_id, int) or node_id <= 0:
        raise ValueError(f"Invalid node_id: {node_id}")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT COUNT(*) as pending_count
            FROM prerequisites
            WHERE node_type = ? AND node_id = ? AND is_completed = FALSE
            """,
            (node_type, node_id)
        )
        result = c.fetchone()
        return result["pending_count"] == 0

def unlock_node(node_type: str, node_id: int) -> None:
    """Unlock a node if its prerequisites are met."""
    if not isinstance(node_type, str) or node_type not in TABLE_MAP:
        raise ValueError(f"Invalid node_type: {node_type}")
    if not isinstance(node_id, int) or node_id <= 0:
        raise ValueError(f"Invalid node_id: {node_id}")

    if check_prerequisites(node_type, node_id):
        table_name = TABLE_MAP[node_type]
        with get_conn() as conn:
            c = conn.cursor()
            c.execute(
                f"UPDATE {table_name} SET status = 'unlocked' WHERE id = ? AND status = 'locked'",
                (node_id,)
            )
            conn.commit()
            if c.rowcount > 0:
                print(f"Unlocked {node_type} ID={node_id}")
            else:
                print(f"No update needed for {node_type} ID={node_id} (already unlocked or not found)")

# --- Wave Planting ---
def plant_wave(user_id: int, parent_type: str, parent_id: int, planned_units_count: int, prerequisites: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Create a planting wave with Fibonacci progression for the given parent.
    Supports: ecology → forest → tree → super_branch → branch → sub_branch → leaf
    Handles prerequisites for sequential learning.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    if parent_type not in TABLE_MAP:
        raise ValueError(f"Invalid parent_type: {parent_type}")
    if not isinstance(parent_id, int) or parent_id <= 0:
        raise ValueError(f"Invalid parent_id: {parent_id}")
    if not isinstance(planned_units_count, int) or planned_units_count <= 0:
        raise ValueError(f"Invalid planned_units_count: {planned_units_count}")

    with get_conn() as conn:
        c = conn.cursor()
        # Verify parent exists and is not deleted
        table_name = TABLE_MAP[parent_type]
        c.execute(f"SELECT id, status FROM {table_name} WHERE id = ? AND user_id = ? AND is_deleted = 0", (parent_id, user_id))
        parent = c.fetchone()
        if not parent:
            raise ValueError(f"Parent {parent_type} ID={parent_id} not found or deleted for user_id={user_id}")
        if parent["status"] not in ("unlocked", "active", "completed"):
            raise ValueError(f"Parent {parent_type} ID={parent_id} is {parent['status']}, must be unlocked, active, or completed")

        # Next wave number
        c.execute(
            "SELECT COALESCE(MAX(wave_number), 0) + 1 as next_wave FROM waves WHERE parent_type = ? AND parent_id = ?",
            (parent_type, parent_id)
        )
        wn = c.fetchone()["next_wave"]

        # Fibonacci quota
        fib_units = get_fib_from_table(wn)
        actual_units_planted = min(planned_units_count, fib_units)

        child_type = {
            "ecology": "forest",
            "forest": "tree",
            "tree": "super_branch",
            "super_branch": "branch",
            "branch": "sub_branch",
            "sub_branch": "leaf"
        }[parent_type]
        child_table = TABLE_MAP[child_type]
        foreign_key = f"{parent_type}_id" if parent_type != "sub_branch" else "sub_branch_id"
        next_field = f"next_{child_type}_id" if child_type != "leaf" else "next_leaf_id"

        created_ids = []
        now = iso_now()
        last_id = None

        for i in range(actual_units_planted):
            name = f"{child_type.capitalize()} Wave{wn}-{i + 1}"
            c.execute(
                f"""
                INSERT INTO {child_table} ({foreign_key}, user_id, name, created_at, status, fibonacci_index)
                VALUES (?, ?, ?, ?, 'locked', ?)
                """,
                (parent_id, user_id, name, now, wn)
            )
            last_id = c.lastrowid
            created_ids.append(last_id)

        # Insert prerequisites if provided
        if prerequisites and child_type in ("sub_branch", "leaf"):
            for idx, prereq in enumerate(prerequisites):
                if idx >= len(created_ids):
                    break
                node_id = created_ids[idx]
                prereq_type = prereq.get("prerequisite_type")
                prereq_id = prereq.get("prerequisite_id")
                if prereq_type not in TABLE_MAP or not isinstance(prereq_id, int) or prereq_id <= 0:
                    print(f"Warning: Invalid prerequisite for {child_type} ID={node_id}, skipping")
                    continue
                c.execute(
                    """
                    INSERT OR IGNORE INTO prerequisites (node_type, node_id, prerequisite_type, prerequisite_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (child_type, node_id, prereq_type, prereq_id, now)
                )

        # Unlock first node if no prerequisites or parent is completed
        if created_ids:
            first_node_id = created_ids[0]
            if not prerequisites or parent["status"] == "completed":
                c.execute(
                    f"UPDATE {child_table} SET status = 'unlocked' WHERE id = ?",
                    (first_node_id,)
                )

        c.execute(
            f"""
            INSERT INTO waves (user_id, parent_type, parent_id, wave_number, planned_units_count, actual_units_planted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, parent_type, parent_id, wn, planned_units_count, actual_units_planted, now)
        )
        wave_id = c.lastrowid

        # Update parent's next_child_id
        c.execute(f"UPDATE {table_name} SET {next_field} = ? WHERE id = ?", (last_id, parent_id))

        # For leaves, schedule initial reviews if unlocked
        if child_type == "leaf":
            settings = get_user_settings(user_id)
            base_time = settings.get("base_time_minutes", DEFAULTS["base_time_minutes"])
            base_completion_days = settings.get("base_completion_days", DEFAULTS["base_completion_days"])
            for leaf_id in created_ids:
                c.execute(f"SELECT status FROM leaves WHERE id = ?", (leaf_id,))
                if c.fetchone()["status"] == "unlocked":
                    c.execute(
                        """
                        INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, created_at)
                        VALUES (?, ?, ?, ?, ?, 'pending', ?)
                        """,
                        ("leaf", leaf_id, wn, iso_days_from_now(base_completion_days), base_time, now)
                    )

        conn.commit()
        return {
            "wave_id": wave_id,
            "wave_number": wn,
            "planned_units_count": planned_units_count,
            "actual_units_planted": actual_units_planted,
            "child_type": child_type,
            "created_ids": created_ids
        }

# --- Review Scheduling ---
def compute_leaf_completion_days(study_duration_minutes: int, base_completion_days: int, S_ref: int) -> int:
    """Calculate completion days for a leaf based on study duration."""
    if not isinstance(study_duration_minutes, (int, float)) or study_duration_minutes <= 0:
        print(f"Warning: Invalid study_duration_minutes {study_duration_minutes}, defaulting to {DEFAULTS['base_time_minutes']}")
        study_duration_minutes = DEFAULTS["base_time_minutes"]
    if not isinstance(base_completion_days, (int, float)) or base_completion_days <= 0:
        print(f"Warning: Invalid base_completion_days {base_completion_days}, defaulting to {DEFAULTS['base_completion_days']}")
        base_completion_days = DEFAULTS["base_completion_days"]
    if not isinstance(S_ref, (int, float)) or S_ref <= 0:
        print(f"Warning: Invalid S_ref {S_ref}, defaulting to {DEFAULTS['S_ref']}")
        S_ref = DEFAULTS["S_ref"]
    comp_days = base_completion_days * (study_duration_minutes / S_ref)
    return max(1, int(math.ceil(comp_days)))

def estimate_review_duration(node_type: str, node: dict, user_settings: dict) -> int:
    """Estimate the duration of a review in minutes for a given node."""
    if not isinstance(node_type, str) or node_type not in TABLE_MAP:
        raise ValueError(f"Invalid node_type: {node_type}")
    if not isinstance(node, dict):
        raise ValueError("Node must be a dictionary")
    if not isinstance(user_settings, dict):
        raise ValueError("User settings must be a dictionary")

    base_time = node.get("base_time_minutes", user_settings.get("base_time_minutes", DEFAULTS["base_time_minutes"]))
    if not isinstance(base_time, (int, float)) or base_time <= 0:
        print(f"Warning: Invalid base_time_minutes {base_time}, defaulting to {DEFAULTS['base_time_minutes']}")
        base_time = DEFAULTS["base_time_minutes"]

    study_dur = node.get("study_duration_minutes", base_time)
    if not isinstance(study_dur, (int, float)) or study_dur <= 0:
        print(f"Warning: Invalid study_duration_minutes {study_dur}, defaulting to {base_time}")
        study_dur = base_time

    u = node.get("understanding_level", 0.0)
    if u is None or not isinstance(u, (int, float)) or not (0 <= u <= 1):
        print(f"Warning: Invalid understanding_level {u} for node {node.get('id')}, defaulting to 0.0")
        u = 0.0

    rc = node.get("review_count", 0)
    if not isinstance(rc, (int, float)) or rc < 0:
        print(f"Warning: Invalid review_count {rc}, defaulting to 0")
        rc = 0

    d = node.get("difficulty", 3)
    if not isinstance(d, (int, float)) or not (1 <= d <= 5):
        print(f"Warning: Invalid difficulty {d}, defaulting to 3")
        d = 3

    imp = node.get("importance", 0.5)
    if imp is None or not isinstance(imp, (int, float)) or not (0 <= imp <= 1):
        print(f"Warning: Invalid importance {imp}, defaulting to 0.5")
        imp = 0.5

    a_u = user_settings.get("a_u", DEFAULTS["a_u"])
    if not isinstance(a_u, (int, float)) or not (0 <= a_u <= 1):
        print(f"Warning: Invalid a_u {a_u}, defaulting to {DEFAULTS['a_u']}")
        a_u = DEFAULTS["a_u"]

    gamma = user_settings.get("gamma", DEFAULTS["gamma"])
    if not isinstance(gamma, (int, float)) or not (0 <= gamma <= 1):
        print(f"Warning: Invalid gamma {gamma}, defaulting to {DEFAULTS['gamma']}")
        gamma = DEFAULTS["gamma"]

    R_decay_cap = user_settings.get("R_decay_cap", DEFAULTS["R_decay_cap"])
    if not isinstance(R_decay_cap, (int, float)) or R_decay_cap <= 0:
        print(f"Warning: Invalid R_decay_cap {R_decay_cap}, defaulting to {DEFAULTS['R_decay_cap']}")
        R_decay_cap = DEFAULTS["R_decay_cap"]

    k_d = user_settings.get("k_d", DEFAULTS["k_d"])
    if not isinstance(k_d, (int, float)) or not (0 <= k_d <= 1):
        print(f"Warning: Invalid k_d {k_d}, defaulting to {DEFAULTS['k_d']}")
        k_d = DEFAULTS["k_d"]

    k_i = user_settings.get("k_i", DEFAULTS["k_i"])
    if not isinstance(k_i, (int, float)) or not (0 <= k_i <= 1):
        print(f"Warning: Invalid k_i {k_i}, defaulting to {DEFAULTS['k_i']}")
        k_i = DEFAULTS["k_i"]

    h_coeff = user_settings.get(f"h_coeff_{node_type}", DEFAULTS["h_coeff"][node_type])
    if not isinstance(h_coeff, (int, float)) or h_coeff <= 0:
        print(f"Warning: Invalid h_coeff_{node_type} {h_coeff}, defaulting to {DEFAULTS['h_coeff'][node_type]}")
        h_coeff = DEFAULTS["h_coeff"][node_type]

    duration = max(base_time, int(study_dur * (1 + (1 - u) * a_u)))
    duration *= (1 + k_d * (d / 5)) * (1 + k_i * imp) * h_coeff
    decay = (1 - gamma * min(rc / R_decay_cap, 1))
    return max(1, int(math.ceil(duration * decay)))

def schedule_reviews_for_user(user_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    """Schedule reviews for a user based on node attributes, settings, and prerequisites."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"Invalid limit: {limit}")

    user_settings = get_user_settings(user_id)
    scheduled = []
    now = date.today()
    node_types = ["ecology", "forest", "tree", "super_branch", "branch", "sub_branch", "leaf"]

    with get_conn() as conn:
        c = conn.cursor()
        for node_type in node_types:
            table_name = TABLE_MAP.get(node_type)
            if not table_name:
                raise ValueError(f"Invalid node_type: {node_type}")
            
            c.execute(
                f"""SELECT id, name, course_name, understanding_level, difficulty, importance, completion_days,
                    fibonacci_index, review_count, base_time_minutes, study_duration_minutes, status
                    FROM {table_name} WHERE user_id = ? AND is_deleted = 0 AND status IN ('unlocked', 'active')""",
                (user_id,)
            )
            nodes = c.fetchall()
            for node in nodes:
                node_dict = dict(node)
                if not check_prerequisites(node_type, node_dict["id"]):
                    print(f"Skipping {node_type} ID={node_dict['id']} due to incomplete prerequisites")
                    continue

                # Check for existing pending reviews
                c.execute(
                    "SELECT id FROM reviews WHERE target_type = ? AND target_id = ? AND status = 'pending'",
                    (node_type, node_dict["id"])
                )
                if c.fetchone():
                    print(f"Skipping {node_type} ID={node_dict['id']} as it already has a pending review")
                    continue

                # Log if critical fields are None for debugging
                if node_dict.get("understanding_level") is None:
                    print(f"Warning: understanding_level is None for {node_type} ID={node_dict['id']}, name={node_dict['name']}")
                if node_dict.get("difficulty") is None:
                    print(f"Warning: difficulty is None for {node_type} ID={node_dict['id']}, name={node_dict['name']}")
                if node_dict.get("importance") is None:
                    print(f"Warning: importance is None for {node_type} ID={node_dict['id']}, name={node_dict['name']}")

                fib_idx = node_dict.get("fibonacci_index", 1)
                if not isinstance(fib_idx, int) or fib_idx < 1:
                    print(f"Warning: Invalid fibonacci_index {fib_idx} for {node_type} ID={node_dict['id']}, defaulting to 1")
                    fib_idx = 1

                F = get_fib_from_table(fib_idx)
                completion_days = node_dict.get("completion_days", user_settings.get("base_completion_days", DEFAULTS["base_completion_days"]))
                if not isinstance(completion_days, (int, float)) or completion_days < 0:
                    print(f"Warning: Invalid completion_days {completion_days} for {node_type} ID={node_dict['id']}, defaulting to {DEFAULTS['base_completion_days']}")
                    completion_days = DEFAULTS["base_completion_days"]

                h = user_settings.get(f"h_coeff_{node_type}", DEFAULTS["h_coeff"][node_type])
                k_u = user_settings.get("k_u", DEFAULTS["k_u"])
                k_d = user_settings.get("k_d", DEFAULTS["k_d"])
                k_i = user_settings.get("k_i", DEFAULTS["k_i"])

                interval = int(round(F * completion_days * 
                                    _understanding_factor(node_dict.get("understanding_level", 0.0), k_u) *
                                    _difficulty_factor(node_dict.get("difficulty", 3), k_d) * 
                                    _importance_factor(node_dict.get("importance", 0.5), k_i) * h))
                interval = max(1, interval)
                scheduled_date = (now + timedelta(days=interval)).isoformat()
                est_dur = estimate_review_duration(node_type, node_dict, user_settings)

                c.execute(
                    """INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, created_at)
                       VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))""",
                    (node_type, node_dict["id"], fib_idx + 1, scheduled_date, est_dur)
                )
                c.execute(
                    f"""UPDATE {table_name} SET next_review_date = ?, fibonacci_index = ?, review_count = COALESCE(review_count, 0) + 1,
                        review_estimated_duration_minutes = ?, status = 'active' WHERE id = ?""",
                    (scheduled_date, fib_idx + 1, est_dur, node_dict["id"])
                )
                scheduled.append({
                    "target_type": node_type,
                    "target_id": node_dict["id"],
                    "name": node_dict["name"],
                    "course_name": node_dict.get("course_name"),
                    "scheduled_date": scheduled_date,
                    "estimated_duration": est_dur
                })

                if len(scheduled) >= limit:
                    break
            if len(scheduled) >= limit:
                break
        conn.commit()
    return scheduled

def schedule_integration_review(user_id: int, target_type: str, target_id: int, fib_index: int) -> None:
    """Schedule an integration review for a specific node if prerequisites are met."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    if target_type not in TABLE_MAP:
        raise ValueError(f"Invalid target_type: {target_type}")
    if not isinstance(target_id, int) or target_id <= 0:
        raise ValueError(f"Invalid target_id: {target_id}")
    if not isinstance(fib_index, int) or fib_index < 1:
        raise ValueError(f"Invalid fib_index: {fib_index}")

    if not check_prerequisites(target_type, target_id):
        raise ValueError(f"Cannot schedule integration review for {target_type} ID={target_id} due to incomplete prerequisites")

    user_settings = get_user_settings(user_id)
    table_name = TABLE_MAP[target_type]
    
    with get_conn() as conn:
        c = conn.cursor()
        # Verify target exists, is not deleted, and is unlocked or active
        c.execute(f"SELECT id, status FROM {table_name} WHERE id = ? AND user_id = ? AND is_deleted = 0", (target_id, user_id))
        target = c.fetchone()
        if not target:
            raise ValueError(f"Target {target_type} ID={target_id} not found or deleted for user_id={user_id}")
        if target["status"] not in ("unlocked", "active"):
            raise ValueError(f"Target {target_type} ID={target_id} is {target['status']}, must be unlocked or active")

        child_type = {
            "ecology": "forest",
            "forest": "tree",
            "tree": "super_branch",
            "super_branch": "branch",
            "branch": "sub_branch",
            "sub_branch": "leaf"
        }[target_type]
        child_table = TABLE_MAP[child_type]
        foreign_key = f"{target_type}_id" if target_type != "sub_branch" else "branch_id"

        c.execute(
            f"SELECT id, review_estimated_duration_minutes FROM {child_table} WHERE {foreign_key} = ? AND is_deleted = 0",
            (target_id,)
        )
        children = c.fetchall()
        if not children:
            return

        total_duration = sum(child["review_estimated_duration_minutes"] or 5 for child in children)
        h_coeff = user_settings.get(f"h_coeff_{target_type}", DEFAULTS["h_coeff"][target_type])
        if not isinstance(h_coeff, (int, float)) or h_coeff <= 0:
            print(f"Warning: Invalid h_coeff_{target_type} {h_coeff}, defaulting to {DEFAULTS['h_coeff'][target_type]}")
            h_coeff = DEFAULTS["h_coeff"][target_type]

        est_duration = int(total_duration * h_coeff / len(children))
        scheduled_date = (date.today() + timedelta(days=get_fib_from_table(fib_index))).isoformat()

        c.execute(
            """INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, is_integration_review, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', 1, datetime('now'))""",
            (target_type, target_id, fib_index, scheduled_date, est_duration)
        )
        c.execute(
            f"UPDATE {table_name} SET next_review_date = ?, fibonacci_index = ?, status = 'active' WHERE id = ?",
            (scheduled_date, fib_index + 1, target_id)
        )
        conn.commit()

def perform_review(review_id: int, understanding: float, duration: int, notes: str) -> None:
    """Update a review with completion details, maintain streaks, and update node status."""
    if not isinstance(review_id, int) or review_id <= 0:
        raise ValueError(f"Invalid review_id: {review_id}")
    if not isinstance(understanding, (int, float)) or not (0 <= understanding <= 1):
        raise ValueError(f"Invalid understanding: {understanding}")
    if not isinstance(duration, int) or duration <= 0:
        raise ValueError(f"Invalid duration: {duration}")
    if not isinstance(notes, str):
        raise ValueError(f"Invalid notes: {notes}")

    with get_conn() as conn:
        c = conn.cursor()
        # Get review details
        c.execute(
            "SELECT scheduled_date, created_at, target_type, target_id FROM reviews WHERE id = ?",
            (review_id,)
        )
        review = c.fetchone()
        if not review:
            raise ValueError(f"Review ID={review_id} not found")

        # Validate scheduled_date
        scheduled_date = review["scheduled_date"]
        today = datetime.now().date().isoformat()
        if scheduled_date > today:
            raise ValueError(
                f"Cannot complete review ID={review_id} as it is scheduled for {scheduled_date}, which is in the future. "
                "Please wait until the scheduled date or reschedule the review."
            )

        # Verify node status
        target_type, target_id = review["target_type"], review["target_id"]
        table_name = TABLE_MAP[target_type]
        c.execute(f"SELECT status, user_id FROM {table_name} WHERE id = ?", (target_id,))
        node = c.fetchone()
        if not node:
            raise ValueError(f"Target {target_type} ID={target_id} not found")
        if node["status"] not in ("unlocked", "active"):
            raise ValueError(f"Cannot perform review on {target_type} ID={target_id} with status {node['status']}")

        # Update review
        c.execute(
            """UPDATE reviews SET status = 'completed', performed_date = ?, understanding_after = ?,
               actual_duration = ?, notes = ? WHERE id = ?""",
            (today, understanding, duration, notes, review_id)
        )
        if c.rowcount == 0:
            raise ValueError(f"Review ID={review_id} not found")

        # Update node status and understanding
        user_id = node["user_id"]
        new_status = "completed" if understanding >= DEFAULTS["R_threshold"] else "active"
        c.execute(
            f"UPDATE {table_name} SET understanding_level = ?, status = ? WHERE id = ?",
            (understanding, new_status, target_id)
        )

        # Unlock dependent nodes
        c.execute(
            """
            SELECT node_type, node_id
            FROM prerequisites
            WHERE prerequisite_type = ? AND prerequisite_id = ? AND is_completed = TRUE
            """,
            (target_type, target_id)
        )
        dependent_nodes = c.fetchall()
        for dep in dependent_nodes:
            unlock_node(dep["node_type"], dep["node_id"])

        # Update streaks
        c.execute("SELECT streak_start, current_length, longest_length FROM streaks WHERE user_id = ?", (user_id,))
        streak = c.fetchone()
        if streak:
            streak_start = date.fromisoformat(streak["streak_start"])
            if streak_start == date.fromisoformat(today) - timedelta(days=1):
                new_length = streak["current_length"] + 1
                new_longest = max(new_length, streak["longest_length"])
                c.execute(
                    "UPDATE streaks SET current_length = ?, longest_length = ?, streak_end = ? WHERE user_id = ?",
                    (new_length, new_longest, today, user_id)
                )
            else:
                c.execute(
                    """UPDATE streaks SET current_length = 1, longest_length = MAX(1, longest_length), 
                       streak_start = ?, streak_end = ? WHERE user_id = ?""",
                    (today, today, user_id)
                )
        else:
            c.execute(
                "INSERT INTO streaks (user_id, streak_start, streak_end, current_length, longest_length) VALUES (?, ?, ?, 1, 1)",
                (user_id, today, today)
            )

        # Update daily readiness
        c.execute("SELECT weighted_readiness_score FROM v_ecology_progress WHERE user_id = ?", (user_id,))
        score_row = c.fetchone()
        score = score_row["weighted_readiness_score"] if score_row else 0.0
        c.execute(
            "INSERT OR REPLACE INTO daily_readiness (user_id, date, readiness_score) VALUES (?, ?, ?)",
            (user_id, today, score)
        )
        conn.commit()

# --- Weekly Packing ---
def pack_schedule_for_week(user_id: int, week_start_date: str) -> List[Dict[str, Any]]:
    """Pack reviews into a weekly schedule based on priority, availability, and prerequisites."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    try:
        date.fromisoformat(week_start_date)
    except ValueError:
        raise ValueError(f"Invalid week_start_date: {week_start_date}")

    user_settings = get_user_settings(user_id)
    with get_conn() as conn:
        c = conn.cursor()
        cal = json.loads(user_settings.get("calendar_max_hours_per_day", DEFAULTS["calendar_max_hours_per_day"]))
        daily_minutes = [int(h * 60) for h in cal]

        week_end = (date.fromisoformat(week_start_date) + timedelta(days=7)).isoformat()
        c.execute(
            """
            SELECT r.*, n.name, n.course_name, n.status
            FROM reviews r
            JOIN (
                SELECT 'ecology' AS target_type, id, name, course_name, status FROM ecologies WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'forest' AS target_type, id, name, course_name, status FROM forests WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'tree' AS target_type, id, name, course_name, status FROM trees WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'super_branch' AS target_type, id, name, course_name, status FROM super_branches WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'branch' AS target_type, id, name, course_name, status FROM branches WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'sub_branch' AS target_type, id, name, course_name, status FROM sub_branches WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'leaf' AS target_type, id, name, course_name, status FROM leaves WHERE user_id = ? AND is_deleted = 0
            ) n ON r.target_type = n.target_type AND r.target_id = n.id
            WHERE r.status = 'pending' AND r.scheduled_date <= ? AND n.status IN ('unlocked', 'active')
            ORDER BY r.scheduled_date ASC
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id, week_end)
        )
        reviews = c.fetchall()

        tasks = []
        for r in reviews:
            target = r["target_type"]
            tid = r["target_id"]
            if not check_prerequisites(target, tid):
                print(f"Skipping review {r['id']} for {target} ID={tid} due to incomplete prerequisites")
                continue
            table_name = TABLE_MAP[target]
            c.execute(
                f"SELECT importance, difficulty, review_estimated_duration_minutes FROM {table_name} WHERE id = ? AND is_deleted = 0",
                (tid,)
            )
            n = c.fetchone()
            if not n:
                print(f"Warning: Target {target} ID={tid} not found or deleted")
                continue
            importance = n["importance"] if n["importance"] is not None else 0.5
            difficulty = n["difficulty"] if n["difficulty"] is not None else 3
            dur = n["review_estimated_duration_minutes"] if n["review_estimated_duration_minutes"] is not None else r["estimated_duration"]
            if not isinstance(dur, (int, float)) or dur <= 0:
                print(f"Warning: Invalid duration {dur} for {target} ID={tid}, defaulting to {r['estimated_duration']}")
                dur = r["estimated_duration"]
            days_until = (date.fromisoformat(r["scheduled_date"]) - date.fromisoformat(week_start_date)).days
            days_until = max(0, days_until)
            priority_score = importance * (difficulty / 5) * (1.0 / (days_until + 1))
            tasks.append({
                "review_id": r["id"],
                "duration": dur,
                "priority": priority_score,
                "scheduled_date": r["scheduled_date"],
                "target_type": target,
                "target_id": tid,
                "name": r["name"],
                "course_name": r["course_name"]
            })

        tasks.sort(key=lambda x: x["priority"], reverse=True)
        placements = []

        for task in tasks:
            placed = False
            for i in range(7):
                if daily_minutes[i] >= task["duration"]:
                    day = date.fromisoformat(week_start_date) + timedelta(days=i)
                    start_dt = datetime.combine(day, datetime.time(8, 0)).isoformat()
                    end_dt = (datetime.fromisoformat(start_dt) + timedelta(minutes=task["duration"])).isoformat()
                    c.execute(
                        """INSERT INTO schedules 
                           (user_id, start_datetime, end_datetime, type, related_type, related_id, priority, status, created_at, notes) 
                           VALUES (?, ?, ?, 'review', ?, ?, ?, 'planned', datetime('now'), ?)""",
                        (user_id, start_dt, end_dt, task["target_type"], task["target_id"], task["priority"], 
                         f"{task['name']} ({task['course_name'] or 'No Course'})")
                    )
                    daily_minutes[i] -= task["duration"]
                    placements.append({
                        "review_id": task["review_id"],
                        "day": day.isoformat(),
                        "duration": task["duration"],
                        "name": task["name"],
                        "course_name": task["course_name"]
                    })
                    placed = True
                    break
            if not placed:
                c.execute(
                    """INSERT INTO notifications (user_id, message, type, created_at, related_type, related_id)
                       VALUES (?, ?, 'warning', datetime('now'), ?, ?)""",
                    (user_id, f"Could not schedule review {task['review_id']} for {task['name']} within week starting {week_start_date}",
                     task["target_type"], task["target_id"])
                )
        conn.commit()
        return placements