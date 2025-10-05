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

# --- Planting Wave ---
def plant_wave(user_id: int, parent_type: str, parent_id: int, planned_units_count: int) -> Dict[str, Any]:
    """
    Create a planting wave with Fibonacci progression for the given parent.
    Supports: ecology → forest → tree → super_branch → branch → sub_branch → leaf
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
        c.execute(f"SELECT id FROM {table_name} WHERE id = ? AND user_id = ? AND is_deleted = 0", (parent_id, user_id))
        if not c.fetchone():
            raise ValueError(f"Parent {parent_type} ID={parent_id} not found or deleted for user_id={user_id}")

        # Next wave number
        c.execute(
            "SELECT COALESCE(MAX(wave_number), 0) + 1 as next_wave FROM waves WHERE parent_type = ? AND parent_id = ?",
            (parent_type, parent_id)
        )
        wn = c.fetchone()["next_wave"]

        # Fibonacci quota
        fib_units = get_fib_from_table(wn)
        quota = min(planned_units_count, fib_units)

        child_type = {
            "ecology": "forest",
            "forest": "tree",
            "tree": "super_branch",
            "super_branch": "branch",
            "branch": "sub_branch",
            "sub_branch": "leaf"
        }[parent_type]
        child_table = TABLE_MAP[child_type]
        foreign_key = f"{parent_type}_id" if parent_type != "sub_branch" else "branch_id"
        next_field = f"next_{child_type}_id" if child_type != "leaf" else "next_leaf_id"

        created_ids = []
        now = iso_now()
        last_id = None

        for i in range(quota):
            name = f"{child_type.capitalize()} Wave{wn}-{i + 1}"
            if child_table == "leaves":
                c.execute(
                    f"""INSERT INTO {child_table} ({foreign_key}, user_id, name, created_at, status, resource_type, {next_field},
                        understanding_level, difficulty, importance, base_time_minutes, study_duration_minutes)
                        VALUES (?, ?, ?, ?, 'pending', 'other', ?, ?, ?, ?, ?, ?)""",
                    (parent_id, user_id, name, now, last_id, 0.5, 3, 0.5, 30, 30)
                )
            else:
                c.execute(
                    f"""INSERT INTO {child_table} ({foreign_key}, user_id, name, created_at, status, {next_field},
                        understanding_level, difficulty, importance, base_time_minutes, study_duration_minutes)
                        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)""",
                    (parent_id, user_id, name, now, last_id, 0.5, 3, 0.5, 30, 30)
                )
            new_id = c.lastrowid
            created_ids.append(new_id)
            last_id = new_id

        # Create wave record
        c.execute(
            """INSERT INTO waves 
               (user_id, parent_type, parent_id, wave_number, planned_units_count, actual_units_planted, status, planned_start_date, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'ready', datetime('now'), datetime('now'))""",
            (user_id, parent_type, parent_id, wn, planned_units_count, len(created_ids))
        )
        wave_id = c.lastrowid

        # Link to parent wave if exists
        if parent_type != "ecology":
            parent_foreign_key = {
                "forest": "ecology_id",
                "tree": "forest_id",
                "super_branch": "tree_id",
                "branch": "super_branch_id",
                "sub_branch": "branch_id"
            }[parent_type]
            parent_table = TABLE_MAP[parent_type]
            parent_child_type = parent_type[:-1] if parent_type != "sub_branch" else "branch"
            c.execute(
                f"SELECT id FROM waves WHERE parent_type = ? AND parent_id = (SELECT {parent_foreign_key} FROM {parent_table} WHERE id = ?)",
                (parent_child_type, parent_id)
            )
            parent_wave_row = c.fetchone()
            if parent_wave_row:
                parent_wave_id = parent_wave_row["id"]
                c.execute(
                    "INSERT INTO wave_relationships (parent_wave_id, child_wave_id, created_at) VALUES (?, ?, datetime('now'))",
                    (parent_wave_id, wave_id)
                )

        conn.commit()
        return {"wave_id": wave_id, "created": created_ids, "quota": quota}

# --- Review Scheduling ---
def compute_leaf_completion_days(study_duration_minutes: int, base_completion_days: int, S_ref: int) -> int:
    """Calculate completion days for a leaf based on study duration."""
    if not isinstance(study_duration_minutes, (int, float)) or study_duration_minutes <= 0:
        print(f"Warning: Invalid study_duration_minutes {study_duration_minutes}, defaulting to {DEFAULTS['base_time_minutes']}")
        study_duration_minutes = DEFAULTS["base_time_minutes"]
    if not isinstance(base_completion_days, (int, float)) or base_completion_days <= 0:
        print(f"Warning: Invalid base_completion_days {base_completion_days}, defaulting to 4")
        base_completion_days = 4
    if not isinstance(S_ref, (int, float)) or S_ref <= 0:
        print(f"Warning: Invalid S_ref {S_ref}, defaulting to {DEFAULTS['S_ref']}")
        S_ref = DEFAULTS["S_ref"]
    comp_days = base_completion_days * (study_duration_minutes / S_ref)
    return max(1, int(math.ceil(comp_days)))

def estimate_review_duration(node_type: str, node: dict, user_settings: dict) -> int:
    """Estimate the duration of a review in minutes for a given node."""
    # Validate inputs
    if not isinstance(node_type, str) or node_type not in TABLE_MAP:
        raise ValueError(f"Invalid node_type: {node_type}")
    if not isinstance(node, dict):
        raise ValueError("Node must be a dictionary")
    if not isinstance(user_settings, dict):
        raise ValueError("User settings must be a dictionary")

    # Retrieve and validate parameters
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

    # Calculate duration
    duration = max(base_time, int(study_dur * (1 + (1 - u) * a_u)))
    duration *= (1 + k_d * (d / 5)) * (1 + k_i * imp) * h_coeff
    decay = (1 - gamma * min(rc / R_decay_cap, 1))
    return max(1, int(math.ceil(duration * decay)))

def schedule_reviews_for_user(user_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    """Schedule reviews for a user based on node attributes and settings."""
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
                    fibonacci_index, review_count, base_time_minutes, study_duration_minutes
                    FROM {table_name} WHERE user_id = ? AND is_deleted = 0""",
                (user_id,)
            )
            nodes = c.fetchall()
            for node in nodes:
                node_dict = dict(node)
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
                completion_days = node_dict.get("completion_days", user_settings.get("base_completion_days", 4))
                if not isinstance(completion_days, (int, float)) or completion_days < 0:
                    print(f"Warning: Invalid completion_days {completion_days} for {node_type} ID={node_dict['id']}, defaulting to 4")
                    completion_days = 4

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
                        review_estimated_duration_minutes = ? WHERE id = ?""",
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
    """Schedule an integration review for a specific node."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    if target_type not in TABLE_MAP:
        raise ValueError(f"Invalid target_type: {target_type}")
    if not isinstance(target_id, int) or target_id <= 0:
        raise ValueError(f"Invalid target_id: {target_id}")
    if not isinstance(fib_index, int) or fib_index < 1:
        raise ValueError(f"Invalid fib_index: {fib_index}")

    user_settings = get_user_settings(user_id)
    table_name = TABLE_MAP[target_type]
    
    with get_conn() as conn:
        c = conn.cursor()
        # Verify target exists and is not deleted
        c.execute(f"SELECT id FROM {table_name} WHERE id = ? AND user_id = ? AND is_deleted = 0", (target_id, user_id))
        if not c.fetchone():
            raise ValueError(f"Target {target_type} ID={target_id} not found or deleted for user_id={user_id}")

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
            f"UPDATE {table_name} SET next_review_date = ?, fibonacci_index = ? WHERE id = ?",
            (scheduled_date, fib_index + 1, target_id)
        )
        conn.commit()

def perform_review(review_id: int, understanding: float, duration: int, notes: str) -> None:
    """Update a review with completion details and maintain user streaks."""
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
        # Update review
        c.execute(
            """UPDATE reviews SET status = 'completed', performed_date = datetime('now'), understanding_after = ?,
               actual_duration = ?, notes = ? WHERE id = ?""",
            (understanding, duration, notes, review_id)
        )
        if c.rowcount == 0:
            raise ValueError(f"Review ID={review_id} not found")

        # Get target details
        c.execute("SELECT target_type, target_id FROM reviews WHERE id = ?", (review_id,))
        review = c.fetchone()
        if not review:
            raise ValueError(f"Review ID={review_id} not found")
        target_type, target_id = review["target_type"], review["target_id"]
        table_name = TABLE_MAP[target_type]

        # Get user_id
        c.execute(f"SELECT user_id FROM {table_name} WHERE id = ?", (target_id,))
        user_id_row = c.fetchone()
        if not user_id_row:
            raise ValueError(f"Target {target_type} ID={target_id} not found")
        user_id = user_id_row["user_id"]

        # Update streaks
        today = date.today().isoformat()
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
    """Pack reviews into a weekly schedule based on priority and availability."""
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
            SELECT r.*, n.name, n.course_name
            FROM reviews r
            JOIN (
                SELECT 'ecology' AS target_type, id, name, course_name FROM ecologies WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'forest' AS target_type, id, name, course_name FROM forests WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'tree' AS target_type, id, name, course_name FROM trees WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'super_branch' AS target_type, id, name, course_name FROM super_branches WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'branch' AS target_type, id, name, course_name FROM branches WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'sub_branch' AS target_type, id, name, course_name FROM sub_branches WHERE user_id = ? AND is_deleted = 0
                UNION
                SELECT 'leaf' AS target_type, id, name, course_name FROM leaves WHERE user_id = ? AND is_deleted = 0
            ) n ON r.target_type = n.target_type AND r.target_id = n.id
            WHERE r.status = 'pending' AND r.scheduled_date <= ?
            ORDER BY r.scheduled_date ASC
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id, week_end)
        )
        reviews = c.fetchall()

        tasks = []
        for r in reviews:
            target = r["target_type"]
            tid = r["target_id"]
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
