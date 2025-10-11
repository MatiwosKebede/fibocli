#!/usr/bin/env python3
# cli.py
import rich_click as click
import datetime
import sqlite3
import json
import hashlib
import secrets
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()

status_icons = {
    "pending": "[grey]🔒 Pending[/grey]",
    "active": "[blue]▶ Active[/blue]",
    "completed": "[green]✅ Completed[/green]"
}

@click.group()
def cli():
    """FIBOCLI — Offline, WSL-friendly learning ecology with spaced repetition and sequential learning"""
    pass

@cli.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing database")
def init(overwrite):
    """Initialize database from schema.sql"""
    try:
        with open("schema.sql", 'r') as f:
            sql_script = f.read()
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        if overwrite:
            cursor.execute("DROP TABLE IF EXISTS Users; DROP TABLE IF EXISTS Nodes; DROP TABLE IF EXISTS Waves; DROP TABLE IF EXISTS Reviews; DROP TABLE IF EXISTS Schedules; DROP TABLE IF EXISTS Fibonacci;")
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        console.print("[green]✅ Database initialized successfully.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error initializing database: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option("--username", prompt="Username", help="Unique username")
@click.password_option("--password", prompt="Password", confirmation_prompt=True, help="Secure password")
def signup(username, password):
    """Create a new user account"""
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        console.print(f"[red]❌ Username '{username}' already exists.[/red]")
        raise click.Abort()
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO Users (username, password_hash, available_minutes_per_day, streak_days, streak_multiplier, learning_efficiency, fatigue_threshold) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, password_hash, json.dumps([120, 120, 120, 120, 120, 0, 0]), 1, 1.0, 1.0, 80)
        )
        conn.commit()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        user_id = cursor.fetchone()[0]
        console.print(f"[green]✅ Created user ID={user_id} ({username})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
@click.option("--username", prompt="Username", help="Your username")
@click.option("--password", prompt="Password", hide_input=True, help="Your password")
def login(username, password):
    """Log in to your account"""
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, password_hash FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user or hashlib.sha256(password.encode()).hexdigest() != user[1]:
        conn.close()
        console.print("[red]❌ Invalid credentials.[/red]")
        raise click.Abort()
    try:
        token = secrets.token_hex(16)
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
        cursor.execute("INSERT INTO Sessions (user_id, token, expiry) VALUES (?, ?, ?)", (user[0], token, expiry))
        conn.commit()
        with open(".fibocli_session", "w") as f:
            f.write(token)
        console.print("[green]✅ Logged in and session saved.[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
def logout():
    """Log out and clear local session"""
    try:
        with open(".fibocli_session", "w") as f:
            f.write("")
        console.print("[green]✅ Local session cleared.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()

@cli.command()
def whoami():
    """Show logged-in user"""
    user_id = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, streak_days, learning_efficiency FROM Users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        console.print("[red]❌ User not found.[/red]")
        raise click.Abort()
    console.print(f"User: [cyan]{user[0]}[/cyan], Streak Days: {user[1]}, Learning Efficiency: {user[2]}")

def require_user():
    """Ensure user is logged in, return user_id"""
    try:
        with open(".fibocli_session", "r") as f:
            token = f.read().strip()
        if not token:
            raise click.ClickException("No session found — please login.")
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Sessions WHERE token = ? AND expiry > ?", (token, datetime.datetime.utcnow().isoformat()))
        user_id = cursor.fetchone()
        conn.close()
        if not user_id:
            raise click.ClickException("Invalid or expired session — please login again.")
        return user_id[0]
    except FileNotFoundError:
        raise click.ClickException("No session found — please login.")

def prompt_for_parent_id(parent_type: str, user_id: int) -> int:
    """Prompt user to select a parent node by number"""
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT node_id, name, course, course_code, status FROM Nodes WHERE user_id = ? AND node_type = ?",
        (user_id, parent_type)
    )
    parents = cursor.fetchall()
    conn.close()
    if not parents:
        raise click.ClickException(f"No {parent_type}s found. Create one first with 'fibocli create {parent_type}'.")
    table = Table(title=f"Available {parent_type.capitalize()}s")
    table.add_column("#", style="cyan", width=5)
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Name", style="green")
    table.add_column("Course Name", style="blue")
    table.add_column("Course Code")
    table.add_column("Status", style="yellow")
    for i, p in enumerate(parents, 1):
        table.add_row(str(i), str(p[0]), p[1], p[2] or "N/A", p[3] or "N/A", status_icons.get(p[4], p[4].capitalize()))
    console.print(table)
    choice = Prompt.ask("Select number", choices=[str(i) for i in range(1, len(parents)+1)])
    return parents[int(choice) - 1][0]

def get_weighted_fibonacci(n, performance_weight):
    """Calculate weighted Fibonacci number, capped at 250"""
    if n <= 0:
        return 0
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM Fibonacci WHERE n = ?", (n,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return min(result[0] * performance_weight, 250)
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return min(b * performance_weight, 250)

@cli.group()
def create():
    """Create hierarchy nodes (ecology, forest, tree, etc.)"""
    pass

@create.command("ecology")
@click.option("--name", prompt="Ecology name", help="Name of the ecology")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
def create_ecology_cmd(name, course, course_code):
    """Create a new ecology"""
    uid = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "ecology", name, course, course_code, "pending", 50, 50, 50, 50, 50, 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        eid = cursor.fetchone()[0]
        console.print(f"[green]✅ Ecology created ID={eid} ({name})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("forest")
@click.option("--ecology-id", type=int, default=None, help="Ecology ID (prompt if not provided)")
@click.option("--name", prompt="Forest name", help="Name of the forest")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
def create_forest_cmd(ecology_id, name, course, course_code):
    """Create a new forest under an ecology"""
    uid = require_user()
    if ecology_id is None:
        ecology_id = prompt_for_parent_id("ecology", uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "forest", name, course, course_code, "pending", 50, 50, 50, 50, 50, 2, ecology_id)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        fid = cursor.fetchone()[0]
        console.print(f"[green]✅ Forest created ID={fid} ({name})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("tree")
@click.option("--forest-id", type=int, default=None, help="Forest ID (prompt if not provided)")
@click.option("--name", prompt="Tree name", help="Name of the tree")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
def create_tree_cmd(forest_id, name, course, course_code):
    """Create a new tree under a forest"""
    uid = require_user()
    if forest_id is None:
        forest_id = prompt_for_parent_id("forest", uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "tree", name, course, course_code, "pending", 50, 50, 50, 50, 50, 3, forest_id)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        tid = cursor.fetchone()[0]
        console.print(f"[green]✅ Tree created ID={tid} ({name})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("super")
@click.option("--tree-id", type=int, default=None, help="Tree ID (prompt if not provided)")
@click.option("--name", prompt="Super-branch name", help="Name of the super-branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
def create_super_cmd(tree_id, name, course, course_code):
    """Create a new super-branch under a tree"""
    uid = require_user()
    if tree_id is None:
        tree_id = prompt_for_parent_id("tree", uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "super_branch", name, course, course_code, "pending", 50, 50, 50, 50, 50, 4, tree_id)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        sbid = cursor.fetchone()[0]
        console.print(f"[green]✅ Super-branch created ID={sbid} ({name})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("branch")
@click.option("--super-id", type=int, default=None, help="Super-branch ID (prompt if not provided)")
@click.option("--name", prompt="Branch name", help="Name of the branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
def create_branch_cmd(super_id, name, course, course_code):
    """Create a new branch under a super-branch"""
    uid = require_user()
    if super_id is None:
        super_id = prompt_for_parent_id("super_branch", uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "branch", name, course, course_code, "pending", 50, 50, 50, 50, 50, 5, super_id)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        bid = cursor.fetchone()[0]
        console.print(f"[green]✅ Branch created ID={bid} ({name})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("subbranch")
@click.option("--branch-id", type=int, default=None, help="Branch ID (prompt if not provided)")
@click.option("--name", prompt="Sub-branch name", help="Name of the sub-branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
def create_subbranch_cmd(branch_id, name, course, course_code):
    """Create a new sub-branch under a branch"""
    uid = require_user()
    if branch_id is None:
        branch_id = prompt_for_parent_id("branch", uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "sub_branch", name, course, course_code, "pending", 50, 50, 50, 50, 50, 6, branch_id)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        sbid = cursor.fetchone()[0]
        console.print(f"[green]✅ Sub-branch created ID={sbid} ({name})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("leaf")
@click.option("--subbranch-id", type=int, default=None, help="Sub-branch ID (prompt if not provided)")
@click.option("--name", prompt="Leaf name", help="Name of the leaf")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
@click.option("--difficulty", type=float, default=50, help="Difficulty level (1-100)")
@click.option("--understanding", type=float, default=50, help="Initial understanding level (1-100)")
def create_leaf_cmd(subbranch_id, name, course, course_code, importance, difficulty, understanding):
    """Create a new leaf under a sub-branch"""
    uid = require_user()
    if subbranch_id is None:
        subbranch_id = prompt_for_parent_id("sub_branch", uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
        if not (1 <= difficulty <= 100):
            raise ValueError("Difficulty must be between 1 and 100")
        if not (1 <= understanding <= 100):
            raise ValueError("Understanding must be between 1 and 100")
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "leaf", name, course, course_code, "pending", importance, understanding, difficulty, 50, 50, 7, subbranch_id)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        lid = cursor.fetchone()[0]
        console.print(f"[green]✅ Leaf created ID={lid} ({name}, Importance={importance}, Difficulty={difficulty}, Understanding={understanding})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
def hierarchy():
    """Show hierarchy for current user"""
    uid = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT node_id, node_type, name, parent_id
        FROM Nodes
        WHERE user_id = ?
        ORDER BY CASE node_type
            WHEN 'ecology' THEN 1
            WHEN 'forest' THEN 2
            WHEN 'tree' THEN 3
            WHEN 'super_branch' THEN 4
            WHEN 'branch' THEN 5
            WHEN 'sub_branch' THEN 6
            WHEN 'leaf' THEN 7
            ELSE 8
        END
        """,
        (uid,)
    )
    nodes = cursor.fetchall()
    conn.close()
    if not nodes:
        console.print("[yellow]No hierarchy nodes found. Create an ecology with 'fibocli create ecology'.[/yellow]")
        return
    table = Table(title="Hierarchy Overview")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Parent ID", style="yellow")
    for node in nodes:
        table.add_row(node[1].capitalize(), node[2], str(node[3]) if node[3] else "None")
    console.print(table)

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf']))
def list_nodes(node_type):
    """List nodes of a given type for the current user"""
    uid = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT node_id, name, course, course_code, status, importance, difficulty, understanding FROM Nodes WHERE user_id = ? AND node_type = ?",
        (uid, node_type)
    )
    nodes = cursor.fetchall()
    conn.close()
    if not nodes:
        console.print(f"[yellow]No {node_type} nodes found. Create one with 'fibocli create {node_type}'.[/yellow]")
        return
    table = Table(title=f"{node_type.capitalize()} List")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Name", style="green")
    table.add_column("Course Name", style="blue")
    table.add_column("Course Code")
    table.add_column("Status", style="yellow")
    if node_type == "leaf":
        table.add_column("Importance", style="magenta")
        table.add_column("Difficulty", style="red")
        table.add_column("Understanding", style="blue")
    for node in nodes:
        row = [str(node[0]), node[1], node[2] or "N/A", node[3] or "N/A", status_icons.get(node[4], node[4].capitalize())]
        if node_type == "leaf":
            row.extend([str(node[5]), str(node[6]), str(node[7])])
        table.add_row(*row)
    console.print(table)

@cli.command()
@click.option("--node-type", type=click.Choice(['sub_branch', 'leaf']), help="Node type (prompt if not provided)")
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
@click.option("--engagement", type=float, required=True, help="Engagement level (1-100)")
@click.option("--fatigue", type=float, required=True, help="Fatigue level (1-100)")
@click.option("--duration", type=int, required=True, help="Study duration in minutes")
@click.option("--focus", type=float, default=50, help="Focus level (1-100)")
@click.option("--understanding", type=float, default=50, help="Updated understanding level (1-100)")
def study(node_type, node_id, engagement, fatigue, duration, focus, understanding):
    """Record a study session for a sub-branch or leaf and schedule next review"""
    uid = require_user()
    if node_type is None:
        node_type = Prompt.ask("Select node type", choices=['sub_branch', 'leaf'])
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        if not (1 <= engagement <= 100 and 1 <= fatigue <= 100 and 1 <= focus <= 100 and 1 <= understanding <= 100):
            raise ValueError("Metrics must be between 1 and 100")
        if duration <= 0:
            raise ValueError("Duration must be positive")
        cursor.execute(
            "SELECT node_id, status, importance, difficulty, total_active_minutes, fibonacci_index, streak_multiplier, learning_efficiency "
            "FROM Nodes n JOIN Users u ON n.user_id = u.user_id WHERE node_id = ? AND n.user_id = ? AND node_type = ?",
            (node_id, uid, node_type)
        )
        node = cursor.fetchone()
        if not node:
            raise ValueError(f"{node_type.capitalize()} ID={node_id} not found")
        if node[1] not in ("pending", "active"):
            raise ValueError(f"Cannot study {node_type} ID={node_id} with status {node[1]}")
        k_f, k_e, k_t, k_u, k_d, k_i = 0.5, 0.5, 0.5, 0.5, 0.5, 0.5  # Constants
        focus_factor = 1 + k_f * (focus / 100 - 0.5)
        engagement_factor = 1 + k_e * (engagement / 100 - 0.5)
        fatigue_factor = 1 + k_t * (fatigue / 100 - 0.5)
        understanding_factor = 1 + k_u * (understanding / 100 - 0.5)
        difficulty_factor = 1 + k_d * (node[3] / 100 - 0.5)
        importance_factor = 1 + k_i * (node[2] / 100 - 0.5)
        performance_weight = (understanding / 100) * node[6] * (engagement / 100) / (fatigue / 100)
        next_interval = duration * get_weighted_fibonacci(node[5] + 1, performance_weight) * understanding_factor * difficulty_factor * importance_factor * focus_factor * engagement_factor * node[7] / fatigue_factor
        next_duration = node[4] * (node[3] / 100) * (node[2] / 100) / (understanding / 100) * focus_factor * engagement_factor * node[7] / fatigue_factor + 5
        cursor.execute(
            "INSERT INTO Reviews (node_id, node_type, scheduled_date, estimated_duration, status, focus_level, engagement, fatigue) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (node_id, node_type, datetime.date.today().isoformat(), duration, "completed", focus, engagement, fatigue)
        )
        cursor.execute(
            "UPDATE Nodes SET total_active_minutes = total_active_minutes + ?, engagement = ?, fatigue = ?, status = 'active', understanding = ? WHERE node_id = ?",
            (duration, engagement, fatigue, understanding, node_id)
        )
        cursor.execute(
            "INSERT INTO Reviews (node_id, node_type, scheduled_date, estimated_duration, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (node_id, node_type, (datetime.date.today() + datetime.timedelta(days=next_interval)).isoformat(), next_duration, "pending")
        )
        # Update streak
        cursor.execute("SELECT AVG(engagement), AVG(fatigue) FROM Reviews WHERE node_id IN (SELECT node_id FROM Nodes WHERE user_id = ?) AND scheduled_date = ?", 
                      (uid, datetime.date.today().isoformat()))
        metrics = cursor.fetchone()
        avg_engagement, avg_fatigue = metrics if metrics[0] is not None else (50, 50)
        cursor.execute("SELECT streak_days, streak_multiplier FROM Users WHERE user_id = ?", (uid,))
        streak_days, current_multiplier = cursor.fetchone()
        streak_days = streak_days + 1 if metrics[0] is not None else 1
        streak_multiplier = 1.0 + 0.25 * min(streak_days, 10) * (avg_engagement / 100) / (avg_fatigue / 100)
        cursor.execute("UPDATE Users SET streak_days = ?, streak_multiplier = ? WHERE user_id = ?", (streak_days, streak_multiplier, uid))
        conn.commit()
        console.print(f"[green]✅ Recorded study session for {node_type} ID={node_id} (Engagement={engagement}, Fatigue={fatigue}, Duration={duration} min, Next Review in {next_interval:.1f} days, Streak={streak_days} days)[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
@click.option("--engagement", type=float, required=True, help="Current engagement level (1-100)")
@click.option("--fatigue", type=float, required=True, help="Current fatigue level (1-100)")
@click.option("--duration", type=int, required=True, help="Available study duration in minutes")
@click.option("--time-preference", type=click.Choice(['morning', 'afternoon', 'evening']), default='morning', help="Preferred time slot")
def prioritize_study(engagement, fatigue, duration, time_preference):
    """Prioritize study tasks based on metrics and suggest what to study"""
    uid = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        if not (1 <= engagement <= 100 and 1 <= fatigue <= 100):
            raise ValueError("Engagement and fatigue must be between 1 and 100")
        if duration <= 0:
            raise ValueError("Duration must be positive")
        
        # Get user metrics
        cursor.execute("SELECT available_minutes_per_day, streak_multiplier, learning_efficiency, fatigue_threshold FROM Users WHERE user_id = ?", (uid,))
        user_data = cursor.fetchone()
        available_minutes = json.loads(user_data[0])[datetime.date.today().weekday()]
        streak_multiplier, learning_efficiency, fatigue_threshold = user_data[1], user_data[2], user_data[3]
        
        # Get pending/active nodes and reviews
        cursor.execute(
            """
            SELECT n.node_id, n.node_type, n.name, n.importance, n.difficulty, n.understanding, n.total_active_minutes, n.fibonacci_index,
                   r.estimated_duration, r.scheduled_date
            FROM Nodes n
            LEFT JOIN Reviews r ON n.node_id = r.node_id AND r.status = 'pending'
            WHERE n.user_id = ? AND n.node_type IN ('leaf', 'sub_branch') AND n.status IN ('pending', 'active')
            ORDER BY n.importance DESC, n.difficulty ASC, n.understanding ASC
            """,
            (uid,)
        )
        tasks = cursor.fetchall()
        if not tasks:
            console.print("[yellow]No pending or active study tasks found. Create nodes with 'fibocli create'.[/yellow]")
            return

        # Constants
        k_f, k_e, k_t, k_u, k_d, k_i = 0.5, 0.5, 0.5, 0.5, 0.5, 0.5
        time_preference_factor = 1.3 if time_preference == 'morning' else 1.0
        slot_weight = time_preference_factor * (1 - fatigue / 200)
        engagement_factor = 1 + k_e * (engagement / 100 - 0.5)
        fatigue_factor = 1 + k_t * (fatigue / 100 - 0.5)

        # Calculate priority scores
        prioritized_tasks = []
        total_duration_needed = 0
        for task in tasks:
            node_id, node_type, name, importance, difficulty, understanding, total_active_minutes, fibonacci_index, estimated_duration, scheduled_date = task
            estimated_duration = estimated_duration or 30  # Default duration if no review
            performance_weight = (understanding / 100) * streak_multiplier * (engagement / 100) / (fatigue / 100)
            understanding_factor = 1 + k_u * (understanding / 100 - 0.5)
            difficulty_factor = 1 + k_d * (difficulty / 100 - 0.5)
            importance_factor = 1 + k_i * (importance / 100 - 0.5)
            
            # Priority score
            final_score = (importance / 100) * (1 - understanding / 100) * difficulty_factor * importance_factor * engagement_factor * learning_efficiency / fatigue_factor
            variance_factor = abs(understanding - difficulty) / 100  # Measure of metric imbalance
            confidence_score = (final_score / 2) * (engagement / 100) * learning_efficiency / (fatigue / 100) * (1 - variance_factor)
            
            # Adjust duration based on available time and slot weight
            suggested_minutes = min(estimated_duration * (available_minutes / (total_duration_needed + estimated_duration)) * slot_weight, duration)
            total_duration_needed += estimated_duration
            
            prioritized_tasks.append({
                "node_id": node_id,
                "node_type": node_type,
                "name": name,
                "suggested_minutes": round(suggested_minutes),
                "confidence_score": confidence_score,
                "estimated_duration": estimated_duration
            })

        # Sort tasks by confidence score
        prioritized_tasks.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        # Schedule tasks within available duration
        remaining_duration = duration
        scheduled_tasks = []
        current_time = datetime.datetime.now().replace(hour=8 if time_preference == 'morning' else 14 if time_preference == 'afternoon' else 20, minute=0, second=0)
        for task in prioritized_tasks:
            if remaining_duration <= 0:
                break
            task_duration = min(task["suggested_minutes"], remaining_duration)
            if task_duration <= 0:
                continue
            # Schedule break if fatigue is high
            break_duration = 0
            if fatigue > fatigue_threshold:
                break_duration = 5 + 10 * (fatigue / 100 - fatigue_threshold / 100)
                cursor.execute(
                    "INSERT INTO Schedules (user_id, task_id, task_type, start_time, duration, status) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, task["node_id"], "break", current_time.isoformat(), break_duration, "planned")
                )
                current_time += datetime.timedelta(minutes=break_duration)
            # Schedule study task
            cursor.execute(
                "INSERT INTO Schedules (user_id, task_id, task_type, start_time, duration, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (uid, task["node_id"], "study", current_time.isoformat(), task_duration, "planned")
            )
            scheduled_tasks.append({
                "node_id": task["node_id"],
                "node_type": task["node_type"],
                "name": task["name"],
                "start_time": current_time.isoformat(),
                "duration": task_duration,
                "confidence_score": task["confidence_score"]
            })
            current_time += datetime.timedelta(minutes=task_duration)
            remaining_duration -= task_duration
            # Update node status to active if pending
            cursor.execute("UPDATE Nodes SET status = 'active' WHERE node_id = ? AND status = 'pending'", (task["node_id"],))

        conn.commit()
        
        # Display prioritized tasks
        table = Table(title="Prioritized Study Schedule")
        table.add_column("Node ID", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Name", style="green")
        table.add_column("Start Time", style="yellow")
        table.add_column("Duration (min)", style="magenta")
        table.add_column("Confidence", style="white")
        for task in scheduled_tasks:
            table.add_row(
                str(task["node_id"]),
                task["node_type"].capitalize(),
                task["name"],
                task["start_time"],
                str(task["duration"]),
                f"{task['confidence_score']:.2f}"
            )
        
        console.print(table)
        if remaining_duration > 0:
            console.print(f"[yellow]Note: {remaining_duration} minutes still available for study.[/yellow]")
        if not scheduled_tasks:
            console.print("[yellow]No tasks scheduled. Consider adjusting duration or creating new nodes.[/yellow]")

    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf']))
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
def status(node_type, node_id):
    """Show advanced status for a node"""
    uid = require_user()
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT name, course, course_code, status, importance, difficulty, understanding, engagement, fatigue, total_active_minutes "
            "FROM Nodes WHERE node_id = ? AND user_id = ? AND node_type = ?",
            (node_id, uid, node_type)
        )
        node = cursor.fetchone()
        if not node:
            raise ValueError(f"{node_type.capitalize()} ID={node_id} not found")
        table = Table(title=f"{node_type.capitalize()} Status (ID: {node_id})")
        table.add_column("Attribute", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Name", node[0])
        table.add_row("Course Name", node[1] or "N/A")
        table.add_row("Course Code", node[2] or "N/A")
        table.add_row("Status", status_icons.get(node[3], node[3].capitalize()))
        table.add_row("Importance", str(node[4]))
        table.add_row("Difficulty", str(node[5]))
        table.add_row("Understanding", str(node[6]))
        table.add_row("Engagement", str(node[7]))
        table.add_row("Fatigue", str(node[8]))
        table.add_row("Total Active Minutes", str(node[9]))
        cursor.execute(
            "SELECT engagement, fatigue, estimated_duration, scheduled_date FROM Reviews WHERE node_type = ? AND node_id = ? ORDER BY scheduled_date DESC",
            (node_type, node_id)
        )
        sessions = cursor.fetchall()
        console.print(table)
        if sessions:
            session_table = Table(title="Recent Study Sessions")
            session_table.add_column("Date", style="cyan")
            session_table.add_column("Engagement", style="blue")
            session_table.add_column("Fatigue", style="red")
            session_table.add_column("Duration (min)", style="green")
            for session in sessions:
                session_table.add_row(session[3], str(session[0]), str(session[1]), str(session[2]))
            console.print(session_table)
        else:
            console.print("[yellow]No study sessions found for this node.[/yellow]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
@click.argument("available_minutes", type=int)
@click.option("--all", is_flag=True, help="Apply to all 7 days")
def set(available_minutes, all):
    """Set available study minutes per day"""
    uid = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        if available_minutes < 0:
            raise ValueError("Available minutes must be non-negative")
        cursor.execute("SELECT available_minutes_per_day FROM Users WHERE user_id = ?", (uid,))
        current_calendar = json.loads(cursor.fetchone()[0])
        if len(current_calendar) != 7:
            raise ValueError("Invalid calendar format")
        if all:
            new_calendar = [available_minutes] * 7
        else:
            day = Prompt.ask("Select day (0=Sun, 1=Mon, ..., 6=Sat)", type=int, choices=[str(i) for i in range(7)])
            new_calendar = current_calendar.copy()
            new_calendar[day] = available_minutes
        cursor.execute("UPDATE Users SET available_minutes_per_day = ? WHERE user_id = ?", (json.dumps(new_calendar), uid))
        conn.commit()
        console.print(f"[green]✅ Updated available study minutes to {available_minutes} min {'for all days' if all else 'for selected day'}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
@click.option("--parent-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch']))
@click.option("--parent-id", type=int, default=None, help="Parent node ID (prompt if not provided)")
@click.option("--planned-units", type=int, required=True, help="Planned units to plant")
def plant_wave(parent_type, parent_id, planned_units):
    """Create a planting wave for a node"""
    uid = require_user()
    if parent_id is None:
        parent_id = prompt_for_parent_id(parent_type, uid)
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(wave_number) FROM Waves WHERE parent_type = ? AND parent_id = ?", (parent_type, parent_id))
        max_wave = cursor.fetchone()[0] or 0
        wave_number = max_wave + 1
        cursor.execute(
            "SELECT AVG(understanding), AVG(engagement), AVG(fatigue) FROM Nodes WHERE user_id = ? AND node_type = 'leaf' "
            "AND parent_id IN (SELECT node_id FROM Nodes WHERE user_id = ? AND node_type = ? AND node_id = ?)",
            (uid, uid, parent_type, parent_id)
        )
        avg_metrics = cursor.fetchone()
        avg_understanding, avg_engagement, avg_fatigue = avg_metrics if avg_metrics else (50, 50, 50)
        cursor.execute("SELECT streak_multiplier FROM Users WHERE user_id = ?", (uid,))
        streak_multiplier = cursor.fetchone()[0]
        performance_weight = (avg_understanding / 100) * streak_multiplier * (avg_engagement / 100) / (avg_fatigue / 100)
        if parent_type == "sub_branch":
            cursor.execute("SELECT COUNT(*) FROM Nodes WHERE parent_id = ? AND node_type = 'leaf'", (parent_id,))
            leaf_sum = cursor.fetchone()[0]
            k = 0
            while get_weighted_fibonacci(k, performance_weight) <= leaf_sum:
                k += 1
            k = max(k - 1, 1)
            actual_units = min(planned_units, get_weighted_fibonacci(k, performance_weight))
        else:
            actual_units = min(planned_units, get_weighted_fibonacci(wave_number, performance_weight))
        cursor.execute(
            "INSERT INTO Waves (parent_type, parent_id, wave_number, planned_units_count, actual_units_planted) VALUES (?, ?, ?, ?, ?)",
            (parent_type, parent_id, wave_number, planned_units, actual_units)
        )
        conn.commit()
        cursor.execute("SELECT wave_id FROM Waves WHERE parent_type = ? AND parent_id = ? AND wave_number = ?", (parent_type, parent_id, wave_number))
        wave_id = cursor.fetchone()[0]
        console.print(f"[green]✅ Wave created ID={wave_id} (Units Planted={actual_units}/{planned_units})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

@cli.command()
@click.option("--node-id", type=int, required=True, help="Node ID for forecasting")
@click.option("--node-type", required=True, type=click.Choice(['leaf', 'sub_branch']))
def forecast(node_id, node_type):
    """Forecast progress for a node"""
    uid = require_user()
    conn = sqlite3.connect("fibocli.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT AVG(understanding), AVG(difficulty), AVG(engagement), AVG(fatigue) FROM Reviews WHERE node_id = ? AND node_type = ?", (node_id, node_type))
        recent_metrics = cursor.fetchone()
        recent_understanding, recent_difficulty, recent_engagement, recent_fatigue = recent_metrics if recent_metrics[0] is not None else (50, 50, 50, 50)
        cursor.execute("SELECT understanding, streak_days, learning_efficiency FROM Nodes n JOIN Users u ON n.user_id = u.user_id WHERE node_id = ? AND node_type = ?", (node_id, node_type))
        node_data = cursor.fetchone()
        if not node_data:
            raise ValueError(f"{node_type.capitalize()} ID={node_id} not found")
        prior_understanding, streak_days, learning_efficiency = node_data
        forecasted_understanding = prior_understanding * (recent_understanding / 100) * learning_efficiency / (recent_difficulty / 100)
        base_completion_days = 30
        k_e, k_t = 0.5, 0.5
        engagement_factor = 1 + k_e * (recent_engagement / 100 - 0.5)
        fatigue_factor = 1 + k_t * (recent_fatigue / 100 - 0.5)
        forecasted_days = base_completion_days * (recent_difficulty / 100) / (recent_understanding / 100) / (1 + 0.25 * min(streak_days, 10)) / (recent_engagement / 100) / learning_efficiency * fatigue_factor
        console.print(f"[green]✅ Forecast for {node_type} ID={node_id}: Understanding={forecasted_understanding:.1f}, Completion in {forecasted_days:.1f} days[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    finally:
        conn.close()

if __name__ == "__main__":
    cli()
