from db import get_conn
from settings import DEFAULTS
from typing import List, Dict, Any
import datetime, math, json
from models import get_user_settings

# --- Fibonacci --- #
def fibonacci(n: int) -> int:
    if n <= 0:
        return 0
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a

def get_fib_from_table(n: int) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM fibonacci WHERE fib_index = ?", (n,))
        row = c.fetchone()
        if row:
            return int(row["value"])
    return fibonacci(n)

# --- Planting Wave --- #
def plant_wave(user_id: int, parent_type: str, parent_id: int, planned_units_count: int):
    """
    Create a planting wave with Fibonacci progression for the given parent.
    Supports: ecology → forest → tree → super_branch → branch → sub_branch → leaf
    """
    with get_conn() as conn:
        c = conn.cursor()

        # Next wave number
        c.execute("SELECT COALESCE(MAX(wave_number), 0) + 1 as next_wave FROM waves WHERE parent_type = ? AND parent_id = ?", (parent_type, parent_id))
        wn = c.fetchone()["next_wave"]

        # Fibonacci quota
        fib_units = get_fib_from_table(wn)
        quota = min(planned_units_count, fib_units)

        created_ids = []
        now = datetime.datetime.utcnow().isoformat()

        last_id = None
        table_name = parent_type + "s" if parent_type != "sub_branch" else "sub_branches"
        child_table = {
            "ecology": "forests",
            "forest": "trees",
            "tree": "super_branches",
            "super_branch": "branches",
            "branch": "sub_branches",
            "sub_branch": "leaves"
        }[parent_type]
        foreign_key = parent_type + "_id" if parent_type != "sub_branch" else "branch_id"
        next_field = "next_" + child_table[:-1] + "_id" if child_table != "leaves" else "next_leaf_id"

        for i in range(quota):
            name = f"{child_table[:-1].capitalize()} wave{wn}-{i + 1}"
            if child_table == "leaves":
                c.execute(
                    f"INSERT INTO {child_table} ({foreign_key}, user_id, name, created_at, status, resource_type, {next_field}) "
                    f"VALUES (?, ?, ?, ?, 'pending', 'other', ?)",
                    (parent_id, user_id, name, now, last_id)
                )
            else:
                c.execute(
                    f"INSERT INTO {child_table} ({foreign_key}, user_id, name, created_at, status, {next_field}) "
                    f"VALUES (?, ?, ?, ?, 'pending', ?)",
                    (parent_id, user_id, name, now, last_id)
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
            c.execute(
                f"SELECT id FROM waves WHERE parent_type = ? AND parent_id = (SELECT {parent_foreign_key} FROM {table_name} WHERE id = ?)",
                (parent_type[:-1] if parent_type != "sub_branch" else "branch", parent_id)
            )
            parent_wave_row = c.fetchone()
            if parent_wave_row:
                parent_wave_id = parent_wave_row["id"]
                c.execute(
                    "INSERT INTO wave_relationships (parent_wave_id, child_wave_id, created_at) VALUES (?, ?, datetime('now'))",
                    (parent_wave_id, wave_id)
                )

        return {"wave_id": wave_id, "created": created_ids, "quota": quota}

# --- Review Scheduling --- #
def compute_leaf_completion_days(study_duration_minutes: int, base_completion_days: int, S_ref: int):
    if not study_duration_minutes or study_duration_minutes <= 0:
        study_duration_minutes = DEFAULTS.get("base_time_minutes", 30)
    comp_days = base_completion_days * (study_duration_minutes / S_ref)
    return max(1, int(math.ceil(comp_days)))

def _understanding_factor(u, k_u):
    return 1 + k_u * ((u or 0.0) - 0.5)

def _difficulty_factor(d, k_d):
    return 1 + k_d * ((d or 3) / 5 - 0.5)

def _importance_factor(i, k_i):
    return 1 + k_i * ((i or 0.5) - 0.5)

def estimate_review_duration(node_type: str, node: dict, user_settings: dict) -> int:
    base_time = node.get("base_time_minutes", user_settings.get("base_time_minutes", DEFAULTS["base_time_minutes"]))
    study_dur = node.get("study_duration_minutes", base_time)
    u = node.get("understanding_level", 0.0)
    rc = node.get("review_count", 0)
    d = node.get("difficulty", 3)
    imp = node.get("importance", 0.5)
    a_u = user_settings.get("a_u", DEFAULTS["a_u"])
    gamma = user_settings.get("gamma", DEFAULTS["gamma"])
    R_decay_cap = user_settings.get("R_decay_cap", DEFAULTS["R_decay_cap"])
    k_d = user_settings.get("k_d", DEFAULTS["k_d"])
    k_i = user_settings.get("k_i", DEFAULTS["k_i"])
    h_coeff = user_settings.get(f"h_coeff_{node_type}", DEFAULTS["h_coeff"][node_type])
    duration = max(base_time, int(study_dur * (1 + (1 - u) * a_u)))
    duration *= (1 + k_d * (d / 5)) * (1 + k_i * imp) * h_coeff
    decay = (1 - gamma * min(rc / R_decay_cap, 1))
    return max(1, int(math.ceil(duration * decay)))

def schedule_reviews_for_user(user_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    user_settings = get_user_settings(user_id)
    scheduled = []
    now = datetime.date.today()
    node_types = ["ecology", "forest", "tree", "super_branch", "branch", "sub_branch", "leaf"]
    with get_conn() as conn:
        c = conn.cursor()
        for node_type in node_types:
            table_name = node_type + "s" if node_type != "sub_branch" else "sub_branches"
            c.execute(
                f"SELECT id, name, course_name, understanding_level, difficulty, importance, completion_days, "
                f"fibonacci_index, review_count, base_time_minutes, study_duration_minutes "
                f"FROM {table_name} WHERE user_id = ? AND is_deleted = 0",
                (user_id,)
            )
            nodes = c.fetchall()
            for node in nodes:
                fib_idx = node["fibonacci_index"] or 1
                F = get_fib_from_table(fib_idx)
                completion_days = node["completion_days"] or user_settings.get("base_completion_days", 4)
                h = user_settings.get(f"h_coeff_{node_type}", DEFAULTS["h_coeff"][node_type])
                k_u = user_settings.get("k_u", DEFAULTS["k_u"])
                k_d = user_settings.get("k_d", DEFAULTS["k_d"])
                k_i = user_settings.get("k_i", DEFAULTS["k_i"])
                interval = int(round(F * completion_days * _understanding_factor(node["understanding_level"], k_u) *
                                    _difficulty_factor(node["difficulty"], k_d) * _importance_factor(node["importance"], k_i) * h))
                interval = max(1, interval)
                scheduled_date = (now + datetime.timedelta(days=interval)).isoformat()
                est_dur = estimate_review_duration(node_type, dict(node), user_settings)
                c.execute(
                    "INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))",
                    (node_type, node["id"], fib_idx + 1, scheduled_date, est_dur)
                )
                c.execute(
                    f"UPDATE {table_name} SET next_review_date = ?, fibonacci_index = ?, review_count = COALESCE(review_count, 0) + 1, "
                    f"review_estimated_duration_minutes = ? WHERE id = ?",
                    (scheduled_date, fib_idx + 1, est_dur, node["id"])
                )
                scheduled.append({
                    "target_type": node_type,
                    "target_id": node["id"],
                    "name": node["name"],
                    "course_name": node["course_name"],
                    "scheduled_date": scheduled_date,
                    "estimated_duration": est_dur
                })
    return scheduled

def schedule_integration_review(user_id: int, target_type: str, target_id: int, fib_index: int) -> None:
    user_settings = get_user_settings(user_id)
    with get_conn() as conn:
        c = conn.cursor()
        child_type = {
            "ecology": "forest",
            "forest": "tree",
            "tree": "super_branch",
            "super_branch": "branch",
            "branch": "sub_branch",
            "sub_branch": "leaf"
        }[target_type]
        child_table = child_type + "s" if child_type != "sub_branch" else "sub_branches"
        foreign_key = target_type + "_id" if child_type != "sub_branch" else "branch_id"
        c.execute(
            f"SELECT id, review_estimated_duration_minutes FROM {child_table} WHERE {foreign_key} = ? AND is_deleted = 0",
            (target_id,)
        )
        children = c.fetchall()
        if not children:
            return
        total_duration = sum(child["review_estimated_duration_minutes"] or 5 for child in children)
        h_coeff = user_settings.get(f"h_coeff_{target_type}", DEFAULTS["h_coeff"][target_type])
        est_duration = int(total_duration * h_coeff / len(children))
        scheduled_date = (datetime.date.today() + datetime.timedelta(days=get_fib_from_table(fib_index))).isoformat()
        c.execute(
            "INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, is_integration_review, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', 1, datetime('now'))",
            (target_type, target_id, fib_index, scheduled_date, est_duration)
        )
        table_name = target_type + "s" if target_type != "sub_branch" else "sub_branches"
        c.execute(
            f"UPDATE {table_name} SET next_review_date = ?, fibonacci_index = ? WHERE id = ?",
            (scheduled_date, fib_index + 1, target_id)
        )

def perform_review(review_id: int, understanding: float, duration: int, notes: str) -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE reviews SET status = 'completed', performed_date = datetime('now'), understanding_after = ?, "
            "actual_duration = ?, notes = ? WHERE id = ?",
            (understanding, duration, notes, review_id)
        )
        c.execute(
            "SELECT target_type, target_id FROM reviews WHERE id = ?",
            (review_id,)
        )
        review = c.fetchone()
        target_type = review["target_type"]
        target_id = review["target_id"]
        table_name = target_type + "s" if target_type != "sub_branch" else "sub_branches"
        c.execute(f"SELECT user_id FROM {table_name} WHERE id = ?", (target_id,))
        user_id_row = c.fetchone()
        if user_id_row:
            user_id = user_id_row["user_id"]
            today = datetime.date.today().isoformat()
            c.execute("SELECT streak_start, current_length, longest_length FROM streaks WHERE user_id = ?", (user_id,))
            streak = c.fetchone()
            if streak:
                if streak["streak_start"] == (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat():
                    new_length = streak["current_length"] + 1
                    new_longest = max(new_length, streak["longest_length"])
                    c.execute(
                        "UPDATE streaks SET current_length = ?, longest_length = ?, streak_end = ? WHERE user_id = ?",
                        (new_length, new_longest, today, user_id)
                    )
                else:
                    c.execute(
                        "UPDATE streaks SET current_length = 1, longest_length = MAX(1, longest_length), streak_start = ?, streak_end = ? WHERE user_id = ?",
                        (today, today, user_id)
                    )
            else:
                c.execute(
                    "INSERT INTO streaks (user_id, streak_start, streak_end, current_length, longest_length) VALUES (?, ?, ?, 1, 1)",
                    (user_id, today, today)
                )
            c.execute("SELECT weighted_readiness_score FROM v_ecology_progress WHERE user_id = ?", (user_id,))
            score_row = c.fetchone()
            score = score_row["weighted_readiness_score"] if score_row else 0.0
            c.execute(
                "INSERT OR REPLACE INTO daily_readiness (user_id, date, readiness_score) VALUES (?, ?, ?)",
                (user_id, today, score)
            )

# --- Weekly Packing --- #
def pack_schedule_for_week(user_id: int, week_start_date: str):
    user_settings = get_user_settings(user_id)
    with get_conn() as conn:
        c = conn.cursor()
        cal = json.loads(user_settings.get("calendar_max_hours_per_day", DEFAULTS["calendar_max_hours_per_day"]))
        daily_minutes = [int(h * 60) for h in cal]

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
            (user_id, user_id, user_id, user_id, user_id, user_id, user_id, (datetime.date.fromisoformat(week_start_date) + datetime.timedelta(days=7)).isoformat())
        )
        reviews = c.fetchall()

        tasks = []
        for r in reviews:
            target = r["target_type"]
            tid = r["target_id"]
            table_name = target + "s" if target != "sub_branch" else "sub_branches"
            c.execute(f"SELECT importance, difficulty, review_estimated_duration_minutes FROM {table_name} WHERE id = ?", (tid,))
            n = c.fetchone()
            importance = n["importance"] or 0.5
            difficulty = n["difficulty"] or 3
            dur = n["review_estimated_duration_minutes"] or r["estimated_duration"]
            days_until = (datetime.date.fromisoformat(r["scheduled_date"]) - datetime.date.fromisoformat(week_start_date)).days
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
                    day = datetime.date.fromisoformat(week_start_date) + datetime.timedelta(days=i)
                    start_dt = datetime.datetime.combine(day, datetime.time(8, 0)).isoformat()
                    end_dt = (datetime.datetime.fromisoformat(start_dt) + datetime.timedelta(minutes=task["duration"])).isoformat()
                    c.execute(
                        """INSERT INTO schedules 
                           (user_id, start_datetime, end_datetime, type, related_type, related_id, priority, status, created_at, notes) 
                           VALUES (?, ?, ?, 'review', ?, ?, ?, 'planned', datetime('now'), ?)""",
                        (user_id, start_dt, end_dt, task["target_type"], task["target_id"], task["priority"], f"{task['name']} ({task['course_name'] or 'No Course'})")
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
                    "INSERT INTO notifications (user_id, message, type, created_at, related_type, related_id) "
                    "VALUES (?, ?, 'warning', datetime('now'), ?, ?)",
                    (user_id, f"Could not schedule review {task['review_id']} for {task['name']} within week starting {week_start_date}",
                     task["target_type"], task["target_id"])
                )
        return placements
