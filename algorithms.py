# algorithms.py
from db import get_conn
from settings import DEFAULTS
from typing import List, Dict, Any
import datetime, math, json

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

        if parent_type == "sub_branch":
            for i in range(quota):
                name = f"Leaf wave{wn}-{i+1}"
                c.execute("""INSERT INTO leaves (sub_branch_id, name, created_at, status, base_time_minutes, base_completion_days)
                             VALUES (?, ?, ?, 'pending', 5, 4)""", (parent_id, name, now))
                leaf_id = c.lastrowid
                created_ids.append(leaf_id)

                # schedule simple study session
                start = now
                end_dt = (datetime.datetime.utcnow() + datetime.timedelta(minutes=5)).isoformat()
                c.execute("""INSERT INTO schedules 
                             (user_id, start_datetime, end_datetime, type, related_type, related_id, priority, status, created_at) 
                             VALUES (?, ?, ?, 'study', 'leaf', ?, ?, 'planned', datetime('now'))""",
                          (user_id, start, end_dt, leaf_id, 0.5))

        elif parent_type == "branch":
            for i in range(quota):
                name = f"SubBranch wave{wn}-{i+1}"
                c.execute("INSERT INTO sub_branches (branch_id, name, created_at, status) VALUES (?, ?, ?, 'pending')",
                          (parent_id, name, now))
                created_ids.append(c.lastrowid)

        elif parent_type == "super_branch":
            for i in range(quota):
                name = f"Branch wave{wn}-{i+1}"
                c.execute("INSERT INTO branches (super_branch_id, name, created_at, status) VALUES (?, ?, ?, 'pending')",
                          (parent_id, name, now))
                created_ids.append(c.lastrowid)

        elif parent_type == "tree":
            for i in range(quota):
                name = f"SuperBranch wave{wn}-{i+1}"
                c.execute("INSERT INTO super_branches (tree_id, name, created_at, status) VALUES (?, ?, ?, 'pending')",
                          (parent_id, name, now))
                created_ids.append(c.lastrowid)

        elif parent_type == "forest":
            for i in range(quota):
                name = f"Tree wave{wn}-{i+1}"
                c.execute("INSERT INTO trees (forest_id, name, created_at, status) VALUES (?, ?, ?, 'pending')",
                          (parent_id, name, now))
                created_ids.append(c.lastrowid)

        elif parent_type == "ecology":
            for i in range(quota):
                name = f"Forest wave{wn}-{i+1}"
                c.execute("INSERT INTO forests (ecology_id, name, created_at, status) VALUES (?, ?, ?, 'pending')",
                          (parent_id, name, now))
                created_ids.append(c.lastrowid)

        else:
            raise ValueError(f"Unsupported parent_type: {parent_type}")

        # create wave record
        c.execute("""INSERT INTO waves 
                     (user_id, parent_type, parent_id, wave_number, planned_units_count, actual_units_planted, status, planned_start_date, created_at)
                     VALUES (?, ?, ?, ?, ?, 0, 'ready', datetime('now'), datetime('now'))""",
                  (user_id, parent_type, parent_id, wn, planned_units_count))
        wave_id = c.lastrowid

        return {"wave_id": wave_id, "created": created_ids, "quota": quota}

# --- Review Scheduling --- #
def compute_leaf_completion_days(study_duration_minutes:int, base_completion_days:int):
    if not study_duration_minutes or study_duration_minutes <= 0:
        study_duration_minutes = DEFAULTS.get("base_time_minutes", 30)
    comp_days = base_completion_days * (study_duration_minutes / DEFAULTS["S_ref"])
    return max(1, int(math.ceil(comp_days)))

def _understanding_factor(u):
    return 1 + DEFAULTS["k_u"] * ((u or 0.0) - 0.5)

def _difficulty_factor(d):
    return 1 + DEFAULTS["k_d"] * ((d or 3)/5 - 0.5)

def _importance_factor(i):
    return 1 + DEFAULTS["k_i"] * ((i or 0.5) - 0.5)

def estimate_review_duration_for_leaf(base_time_minutes:int, study_duration_minutes:int, understanding_level:float, review_count:int, difficulty:int, importance:float):
    base_time = base_time_minutes or 5
    study_dur = study_duration_minutes or base_time
    u = understanding_level or 0.0
    rc = review_count or 0
    d = difficulty or 3
    imp = importance or 0.5
    duration = max(base_time, int(study_dur * (1 + (1 - u) * DEFAULTS["a_u"])))
    duration = duration * (1 + DEFAULTS["k_d"] * (d/5))
    duration = duration * (1 + DEFAULTS["k_i"] * imp)
    decay = (1 - DEFAULTS["gamma"] * min(rc / DEFAULTS["R_decay_cap"], 1))
    duration = int(math.ceil(duration * decay))
    return max(1, duration)

def schedule_reviews_for_user(user_id:int, limit:int=500) -> List[Dict[str,Any]]:
    scheduled = []
    now = datetime.date.today()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT l.* FROM leaves l
            JOIN sub_branches sb ON sb.id = l.sub_branch_id
            JOIN branches b ON b.id = sb.branch_id
            JOIN super_branches s ON s.id = b.super_branch_id
            JOIN trees t ON t.id = s.tree_id
            JOIN forests f ON f.id = t.forest_id
            JOIN ecologies e ON e.id = f.ecology_id
            WHERE e.user_id = ? AND l.is_deleted = 0
        """, (user_id,))
        leaves = c.fetchall()
        for l in leaves:
            fib_idx = l["fibonacci_index"] or 1
            F = get_fib_from_table(fib_idx)
            completion_days = l["completion_days"] or compute_leaf_completion_days(l["study_duration_minutes"] or l["base_time_minutes"], l["base_completion_days"] or 4)
            h = DEFAULTS["h_coeff"]["leaf"]
            interval = int(round(F * completion_days * _understanding_factor(l["understanding_level"]) * _difficulty_factor(l["difficulty"]) * _importance_factor(l["importance"]) * h))
            interval = max(1, interval)
            scheduled_date = (now + datetime.timedelta(days=interval)).isoformat()
            est_dur = estimate_review_duration_for_leaf(l["base_time_minutes"], l["study_duration_minutes"], l["understanding_level"], l["review_count"], l["difficulty"], l["importance"])
            c.execute("INSERT INTO reviews (target_type, target_id, fib_index, scheduled_date, estimated_duration, status, created_at) VALUES ('leaf', ?, ?, ?, ?, 'pending', datetime('now'))",
                      (l["id"], fib_idx+1, scheduled_date, est_dur))
            c.execute("UPDATE leaves SET next_review_date = ?, fibonacci_index = ?, review_count = COALESCE(review_count,0)+1, review_estimated_duration_minutes = ? WHERE id = ?",
                      (scheduled_date, fib_idx+1, est_dur, l["id"]))
            scheduled.append({"target_type":"leaf", "target_id": l["id"], "name": l["name"], "scheduled_date": scheduled_date, "estimated_duration": est_dur})
    return scheduled

# --- Weekly Packing --- #
def pack_schedule_for_week(user_id:int, week_start_date: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT calendar_max_hours_per_day FROM settings WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if row and row["calendar_max_hours_per_day"]:
            try:
                cal = json.loads(row["calendar_max_hours_per_day"])
            except Exception:
                cal = DEFAULTS["calendar_max_hours_per_day"]
        else:
            cal = DEFAULTS["calendar_max_hours_per_day"]
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
                    start_dt = datetime.datetime.combine(day, datetime.time(8,0))
                    end_dt = start_dt + datetime.timedelta(minutes=task["duration"])
                    c.execute("""INSERT INTO schedules 
                                 (user_id, start_datetime, end_datetime, type, related_type, related_id, priority, status, created_at) 
                                 VALUES (?, ?, ?, 'review', ?, ?, ?, 'planned', datetime('now'))""",
                              (user_id, start_dt.isoformat(), end_dt.isoformat(), task["target_type"], task["target_id"], task["priority"]))
                    daily_minutes[i] -= task["duration"]
                    placements.append({"review_id": task["review_id"], "day": day.isoformat(), "duration": task["duration"]})
                    placed=True
                    break
            if not placed:
                c.execute("INSERT INTO notifications (user_id, message, type, created_at) VALUES (?, ?, 'warning', datetime('now'))",
                          (user_id, f"Could not schedule review {task['review_id']} within week starting {week_start_date}"))
        return placements
