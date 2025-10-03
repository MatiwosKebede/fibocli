# algorithms.py
from db import get_conn
from settings import DEFAULTS
from typing import List, Dict, Any
import datetime, math, json
from models import get_user_settings

# --- Fibonacci --- #
def fibonacci(n:int) -> int:
    if n <= 0:
        return 0
    a,b = 1,1
    for _ in range(n-1):
        a,b = b,a+b
    return a

def get_fib_from_table(n:int) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM fibonacci WHERE fib_index = ?", (n,))
        row = c.fetchone()
        if row:
            return int(row["value"])
    return fibonacci(n)

# --- Planting Wave --- #
def plant_wave(user_id:int, parent_type:str, parent_id:int, planned_units_count:int):
    """
    Create a planting wave with Fibonacci progression for the given parent.
    Supports: ecology → forest → tree → super_branch → branch → sub_branch → leaf
    """
    with get_conn() as conn:
        c = conn.cursor()

        # next wave number
        c.execute("SELECT COALESCE(MAX(wave_number),0)+1 as next_wave FROM waves WHERE parent_type=? AND parent_id=?", (parent_type, parent_id))
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
            name = f"{child_table[:-1].capitalize()} wave{wn}-{i+1}"
            c.execute(f"INSERT INTO {child_table} ({foreign_key}, name, created_at, status, {next_field}) VALUES (?, ?, ?, 'pending', ?)",
                      (parent_id, name, now, last_id))
            new_id = c.lastrowid
            created_ids.append(new_id)
            last_id = new_id

        # create wave record
        c.execute("""INSERT INTO waves 
                     (user_id, parent_type, parent_id, wave_number, planned_units_count, actual_units_planted, status, planned_start_date, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, 'ready', datetime('now'), datetime('now'))""",
                  (user_id, parent_type, parent_id, wn, planned_units_count, len(created_ids)))
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
            c.execute(f"SELECT id FROM waves WHERE parent_type = (SELECT {parent_foreign_key} FROM {table_name} WHERE id = ?)", (parent_id,))
            parent_wave_row = c.fetchone()
            if parent_wave_row:
                parent_wave_id = parent_wave_row["id"]
                c.execute("INSERT INTO wave_relationships (parent_wave_id, child_wave_id) VALUES (?, ?)",
                          (parent_wave_id, wave_id))

        return {"wave_id": wave_id, "created": created_ids, "quota": quota}

# --- Review Scheduling --- #
def compute_leaf_completion_days(study_duration_minutes:int, base_completion_days:int, S_ref:int):
    if not study_duration_minutes or study_duration_minutes <= 0:
        study_duration_minutes = DEFAULTS.get("base_time_minutes", 30)
    comp_days = base_completion_days * (study_duration_minutes / S_ref)
    return max(1, int(math.ceil(comp_days)))

def _understanding_factor(u, k_u):
    return 1 + k_u * ((u or 0.0) - 0.5)

def _difficulty_factor(d, k_d):
    return 1 + k_d * ((d or 3)/5 - 0.5)

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

def schedule_reviews_for_user(user_id:int, limit:int=500) -> List[Dict[str,Any]]:
    user_settings = get_user_settings(user_id)
    scheduled = []
    now = datetime.date.today()
    node_types = ["leaf", "sub_branch", "branch", "super_branch", "tree", "forest", "ecology"]
    with get_conn() as conn:
        c = conn.cursor()
        for node_type in node_types:
            # Dynamic query to fetch nodes for user
            query = f"""
                SELECT {node_type}s.* FROM {node_type}s
            """
            joins = ""
            if node_type != "ecology":
                prev_types = node_types[node_types.index(node_type) - 1]
                joins = f"JOIN {prev_types}s ON {prev_types}s.id = {node_type}s.{prev_types}_id "
                while prev_types != "ecology":
                    next_prev = node_types[node_types.index(prev_types) - 1]
                    joins += f"JOIN {next_prev}s ON {next_prev}s.id = {prev_types}s.{next_prev}_id "
                    prev_types = next_prev
                joins += "JOIN ecologies ON ecologies.id = ecology_id "
            query += joins + f"WHERE ecologies.user_id = ? AND {node_type}s.is_deleted = 0"
            c.execute(query, (user_id,))
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
                c.execute("INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, created_at) VALUES ('{node_type}', ?, ?, ?, ?, 'pending', datetime('now'))",
                          (node["id"], fib_idx+1, scheduled_date, est_dur))
                c.execute(f"UPDATE {node_type}s SET next_review_date = ?, fibonacci_index = ?, review_count = COALESCE(review_count,0)+1, review_estimated_duration_minutes = ? WHERE id = ?",
                          (scheduled_date, fib_idx+1, est_dur, node["id"]))
                scheduled.append({"target_type":node_type, "target_id": node["id"], "name": node["name"], "scheduled_date": scheduled_date, "estimated_duration": est_dur})
    return scheduled

def schedule_integration_review(user_id: int, target_type: str, target_id: int, fib_index: int) -> None:
    user_settings = get_user_settings(user_id)
    with get_conn() as conn:
        c = conn.cursor()
        # Get child nodes
        child_type = {
            "ecology": "forest",
            "forest": "tree",
            "tree": "super_branch",
            "super_branch": "branch",
            "branch": "sub_branch",
            "sub_branch": "leaf"
        }[target_type]
        child_table = child_type + "s" if child_type != "sub_branch" else "sub_branches"
        foreign_key = target_type + "_id"
        c.execute(f"SELECT id, review_estimated_duration_minutes FROM {child_table} WHERE {foreign_key} = ? AND is_deleted = 0", (target_id,))
        children = c.fetchall()
        if not children:
            return
        # Calculate aggregated duration
        total_duration = sum(child["review_estimated_duration_minutes"] or 5 for child in children)
        h_coeff = user_settings.get(f"h_coeff_{target_type}", DEFAULTS["h_coeff"][target_type])
        est_duration = int(total_duration * h_coeff / len(children))
        scheduled_date = (datetime.date.today() + datetime.timedelta(days=get_fib_from_table(fib_index))).isoformat()
        c.execute(
            "INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, is_integration_review, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', 1, datetime('now'))",
            (target_type, target_id, fib_index, scheduled_date, est_duration)
        )
        # Update node's next_review_date and fibonacci_index
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
        # Update streak
        c.execute(
            "SELECT target_type, target_id FROM reviews WHERE id = ?",
            (review_id,)
        )
        review = c.fetchone()
        target_type = review["target_type"]
        target_id = review["target_id"]
        # Find user_id (simplified for leaf; extend for others)
        query = f"SELECT user_id FROM ecologies WHERE id = (SELECT ecology_id FROM forests WHERE id = (SELECT forest_id FROM trees WHERE id = (SELECT tree_id FROM super_branches WHERE id = (SELECT super_branch_id FROM branches WHERE id = (SELECT branch_id FROM sub_branches WHERE id = (SELECT sub_branch_id FROM leaves WHERE id = ?))))))" if target_type == "leaf" else "SELECT user_id FROM ecologies WHERE id = ?"  # Extend for other types
        c.execute(query, (target_id,))
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
                    c.execute("UPDATE streaks SET current_length = ?, longest_length = ?, streak_end = ? WHERE user_id = ?",
                              (new_length, new_longest, today, user_id))
                else:
                    c.execute("UPDATE streaks SET current_length = 1, longest_length = MAX(1, longest_length), streak_start = ?, streak_end = ? WHERE user_id = ?",
                              (today, today, user_id))
            else:
                c.execute("INSERT INTO streaks (user_id, streak_start, streak_end, current_length, longest_length) VALUES (?, ?, ?, 1, 1)",
                          (user_id, today, today))
        # Update daily readiness
        c.execute("SELECT weighted_readiness_score FROM v_ecology_progress WHERE user_id = ?", (user_id,))
        score_row = c.fetchone()
        score = score_row["weighted_readiness_score"] if score_row else 0.0
        c.execute(
            "INSERT OR REPLACE INTO daily_readiness (user_id, date, readiness_score) VALUES (?, ?, ?)",
            (user_id, today, score)
        )

# --- Weekly Packing --- #
def pack_schedule_for_week(user_id:int, week_start_date: str):
    user_settings = get_user_settings(user_id)
    with get_conn() as conn:
        c = conn.cursor()
        cal = json.loads(user_settings.get("calendar_max_hours_per_day", DEFAULTS["calendar_max_hours_per_day"]))
        daily_minutes = [int(h*60) for h in cal]

        # Pending reviews with proper joins to get user
        c.execute("""
            SELECT r.*, e.user_id
            FROM reviews r
            LEFT JOIN leaves l ON r.target_type='leaf' AND r.target_id=l.id
            LEFT JOIN sub_branches sb ON l.sub_branch_id=sb.id
            LEFT JOIN branches b ON sb.branch_id=b.id
            LEFT JOIN super_branches s ON b.super_branch_id=s.id
            LEFT JOIN trees t ON s.tree_id=t.id
            LEFT JOIN forests f ON t.forest_id=f.id
            LEFT JOIN ecologies e ON f.ecology_id=e.id
            WHERE r.status='pending'
            ORDER BY r.scheduled_date ASC
        """)
        reviews = c.fetchall()

        tasks = []
        for r in reviews:
            target = r["target_type"]
            tid = r["target_id"]
            importance = 0.5; difficulty = 3
            if target == "leaf":
                c.execute("SELECT importance, difficulty, review_estimated_duration_minutes FROM leaves WHERE id=?", (tid,))
                n = c.fetchone()
                if n:
                    importance = n["importance"] or importance
                    difficulty = n["difficulty"] or difficulty
                    dur = n["review_estimated_duration_minutes"] or r["estimated_duration"]
                else:
                    dur = r["estimated_duration"]
            else:
                dur = r["estimated_duration"]

            days_until = (datetime.date.fromisoformat(r["scheduled_date"]) - datetime.date.fromisoformat(week_start_date)).days
            days_until = max(0, days_until)
            priority_score = importance * (difficulty/5) * (1.0 / (days_until + 1))
            tasks.append({"review_id": r["id"], "duration": dur, "priority": priority_score, "scheduled_date": r["scheduled_date"], "target_type": target, "target_id": tid})

        tasks.sort(key=lambda x: x["priority"], reverse=True)
        placements = []

        for task in tasks:
            placed=False
            for i in range(7):
                if daily_minutes[i] >= task["duration"]:
                    day = datetime.date.fromisoformat(week_start_date) + datetime.timedelta(days=i)
                    start_dt = datetime.datetime.combine(day, datetime.time(8,0)).isoformat()
                    end_dt = (datetime.datetime.fromisoformat(start_dt) + datetime.timedelta(minutes=task["duration"])).isoformat()
                    c.execute("""INSERT INTO schedules 
                                 (user_id, start_datetime, end_datetime, type, related_type, related_id, priority, status, created_at) 
                                 VALUES (?, ?, ?, 'review', ?, ?, ?, 'planned', datetime('now'))""",
                              (user_id, start_dt, end_dt, task["target_type"], task["target_id"], task["priority"]))
                    daily_minutes[i] -= task["duration"]
                    placements.append({"review_id": task["review_id"], "day": day.isoformat(), "duration": task["duration"]})
                    placed=True
                    break
            if not placed:
                c.execute("INSERT INTO notifications (user_id, message, type, created_at) VALUES (?, ?, 'warning', datetime('now'))",
                          (user_id, f"Could not schedule review {task['review_id']} within week starting {week_start_date}"))
        return placements
