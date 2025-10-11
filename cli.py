#!/usr/bin/env python3
# cli.py
import rich_click as click
import datetime
import sqlite3
import json
import hashlib
import secrets
import os
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, IntPrompt

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
        if not os.path.exists("schema.sql"):
            console.print("[red]❌ schema.sql file not found.[/red]")
            raise click.Abort()
        with open("schema.sql", 'r') as f:
            sql_script = f.read()
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        if overwrite:
            cursor.execute("DROP TABLE IF EXISTS Users; DROP TABLE IF EXISTS Nodes; DROP TABLE IF EXISTS Waves; DROP TABLE IF EXISTS Reviews; DROP TABLE IF EXISTS Schedules; DROP TABLE IF EXISTS Fibonacci;")
        cursor.executescript(sql_script)
        conn.commit()
        console.print("[green]✅ Database initialized successfully.[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Error initializing database: {e}[/red]")
        raise click.Abort()
    finally:
        if 'conn' in locals():
            conn.close()

@cli.command()
@click.option("--username", prompt="Username", help="Unique username")
@click.password_option("--password", prompt="Password", confirmation_prompt=True, help="Secure password")
def signup(username, password):
    """Create a new user account"""
    if not os.path.exists("fibocli.db"):
        console.print("[red]❌ Database not found. Run 'fibocli init' first.[/red]")
        raise click.Abort()
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        if cursor.fetchone():
            console.print(f"[red]❌ Username '{username}' already exists.[/red]")
            raise click.Abort()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO Users (username, password_hash, available_minutes_per_day, streak_days, streak_multiplier, learning_efficiency, fatigue_threshold) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, password_hash, json.dumps([120, 120, 120, 120, 120, 0, 0]), 1, 1.0, 1.0, 80)
        )
        conn.commit()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        user_id = cursor.fetchone()[0]
        console.print(f"[green]✅ Created user ID={user_id} ({username})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
@click.option("--username", prompt="Username", help="Your username")
@click.option("--password", prompt="Password", hide_input=True, help="Your password")
def login(username, password):
    """Log in to your account"""
    if not os.path.exists("fibocli.db"):
        console.print("[red]❌ Database not found. Run 'fibocli init' first.[/red]")
        raise click.Abort()
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password_hash FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user or hashlib.sha256(password.encode()).hexdigest() != user[1]:
            console.print("[red]❌ Invalid credentials.[/red]")
            raise click.Abort()
        token = secrets.token_hex(16)
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
        cursor.execute("INSERT INTO Sessions (user_id, token, expiry) VALUES (?, ?, ?)", (user[0], token, expiry))
        conn.commit()
        with open(".fibocli_session", "w") as f:
            f.write(token)
        console.print("[green]✅ Logged in and session saved.[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except FileNotFoundError:
        console.print("[red]❌ Error writing session file.[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
def logout():
    """Log out and clear local session"""
    try:
        if os.path.exists(".fibocli_session"):
            with open(".fibocli_session", "w") as f:
                f.write("")
            console.print("[green]✅ Local session cleared.[/green]")
        else:
            console.print("[yellow]No session file found.[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()

@cli.command()
def whoami():
    """Show logged-in user"""
    try:
        user_id = require_user()
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT username, streak_days, learning_efficiency FROM Users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            console.print("[red]❌ User not found.[/red]")
            raise click.Abort()
        console.print(f"User: [cyan]{user[0]}[/cyan], Streak Days: {user[1]}, Learning Efficiency: {user[2]}")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if 'conn' in locals():
            conn.close()

def require_user():
    """Ensure user is logged in, return user_id"""
    try:
        if not os.path.exists(".fibocli_session"):
            raise click.ClickException("No session found — please login.")
        with open(".fibocli_session", "r") as f:
            token = f.read().strip()
        if not token:
            raise click.ClickException("No session found — please login.")
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Sessions WHERE token = ? AND expiry > ?", (token, datetime.datetime.utcnow().isoformat()))
        user_id = cursor.fetchone()
        if not user_id:
            raise click.ClickException("Invalid or expired session — please login again.")
        return user_id[0]
    except sqlite3.Error as e:
        raise click.ClickException(f"SQLite error: {e}")
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def prompt_for_parent_id(parent_type: str, user_id: int) -> int:
    """Prompt user to select a parent node by number"""
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT node_id, name, course, course_code, status FROM Nodes WHERE user_id = ? AND node_type = ?",
            (user_id, parent_type)
        )
        parents = cursor.fetchall()
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
        choice = IntPrompt.ask("Select number", choices=[str(i) for i in range(1, len(parents)+1)], show_choices=False)
        return parents[choice - 1][0]
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except ValueError:
        console.print("[red]❌ Invalid selection.[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

def get_weighted_fibonacci(n, performance_weight):
    """Calculate weighted Fibonacci number, capped at 250"""
    if n <= 0:
        return 0
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Fibonacci WHERE n = ?", (n,))
        result = cursor.fetchone()
        if result:
            return min(float(result[0]) * performance_weight, 250)
        a, b = 1.0, 1.0
        for _ in range(3, n + 1):
            a, b = b, a + b
        return min(b * performance_weight, 250)
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error in Fibonacci lookup: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error in Fibonacci calculation: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

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
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "ecology", name, course, course_code, "pending", 50, 50, 50, 50, 50, 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        eid = cursor.fetchone()
        if not eid:
            raise ValueError("Failed to retrieve created ecology ID")
        console.print(f"[green]✅ Ecology created ID={eid[0]} ({name})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = 'ecology' AND user_id = ?", (ecology_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Ecology ID={ecology_id} not found or not owned by user")
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (ecology_id,))
        max_order = cursor.fetchone()[0] or 0
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id, child_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "forest", name, course, course_code, "pending", 50, 50, 50, 50, 50, 2, ecology_id, max_order + 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        fid = cursor.fetchone()
        if not fid:
            raise ValueError("Failed to retrieve created forest ID")
        console.print(f"[green]✅ Forest created ID={fid[0]} ({name})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = 'forest' AND user_id = ?", (forest_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Forest ID={forest_id} not found or not owned by user")
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (forest_id,))
        max_order = cursor.fetchone()[0] or 0
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id, child_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "tree", name, course, course_code, "pending", 50, 50, 50, 50, 50, 3, forest_id, max_order + 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        tid = cursor.fetchone()
        if not tid:
            raise ValueError("Failed to retrieve created tree ID")
        console.print(f"[green]✅ Tree created ID={tid[0]} ({name})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = 'tree' AND user_id = ?", (tree_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Tree ID={tree_id} not found or not owned by user")
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (tree_id,))
        max_order = cursor.fetchone()[0] or 0
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id, child_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "super_branch", name, course, course_code, "pending", 50, 50, 50, 50, 50, 4, tree_id, max_order + 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        sbid = cursor.fetchone()
        if not sbid:
            raise ValueError("Failed to retrieve created super-branch ID")
        console.print(f"[green]✅ Super-branch created ID={sbid[0]} ({name})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = 'super_branch' AND user_id = ?", (super_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Super-branch ID={super_id} not found or not owned by user")
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (super_id,))
        max_order = cursor.fetchone()[0] or 0
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id, child_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "branch", name, course, course_code, "pending", 50, 50, 50, 50, 50, 5, super_id, max_order + 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        bid = cursor.fetchone()
        if not bid:
            raise ValueError("Failed to retrieve created branch ID")
        console.print(f"[green]✅ Branch created ID={bid[0]} ({name})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = 'branch' AND user_id = ?", (branch_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Branch ID={branch_id} not found or not owned by user")
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (branch_id,))
        max_order = cursor.fetchone()[0] or 0
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id, child_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "sub_branch", name, course, course_code, "pending", 50, 50, 50, 50, 50, 6, branch_id, max_order + 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        sbid = cursor.fetchone()
        if not sbid:
            raise ValueError("Failed to retrieve created sub-branch ID")
        console.print(f"[green]✅ Sub-branch created ID={sbid[0]} ({name})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        if not (1 <= importance <= 100 and 1 <= difficulty <= 100 and 1 <= understanding <= 100):
            raise ValueError("Importance, difficulty, and understanding must be between 1 and 100")
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = 'sub_branch' AND user_id = ?", (subbranch_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Sub-branch ID={subbranch_id} not found or not owned by user")
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (subbranch_id,))
        max_order = cursor.fetchone()[0] or 0
        cursor.execute(
            "INSERT INTO Nodes (user_id, node_type, name, course, course_code, status, importance, understanding, difficulty, engagement, fatigue, fibonacci_index, parent_id, child_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "leaf", name, course, course_code, "pending", importance, understanding, difficulty, 50, 50, 7, subbranch_id, max_order + 1)
        )
        conn.commit()
        cursor.execute("SELECT node_id FROM Nodes WHERE user_id = ? AND name = ?", (uid, name))
        lid = cursor.fetchone()
        if not lid:
            raise ValueError("Failed to retrieve created leaf ID")
        console.print(f"[green]✅ Leaf created ID={lid[0]} ({name}, Importance={importance}, Difficulty={difficulty}, Understanding={understanding})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
def hierarchy():
    """Show hierarchy for current user"""
    uid = require_user()
    conn = None
    try:
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
                END, child_order ASC, created_at ASC
            """,
            (uid,)
        )
        nodes = cursor.fetchall()
        table = Table(title="Hierarchy")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Name", style="green")
        table.add_column("Parent ID", style="yellow")
        for node in nodes:
            table.add_row(str(node[0]), node[1].capitalize(), node[2], str(node[3]) if node[3] else "N/A")
        console.print(table)
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

def get_active_session():
    """Get active study session from file"""
    try:
        if os.path.exists(".fibocli_active_study"):
            with open(".fibocli_active_study", "r") as f:
                return json.load(f)
    except Exception as e:
        console.print(f"[red]❌ Error reading active session: {e}[/red]")
        raise click.Abort()
    return None

def set_active_session(schedule_id, start_time):
    """Set active study session to file"""
    try:
        with open(".fibocli_active_study", "w") as f:
            json.dump({"schedule_id": schedule_id, "start_time": start_time.isoformat()}, f)
    except Exception as e:
        console.print(f"[red]❌ Error saving active session: {e}[/red]")
        raise click.Abort()

def clear_active_session():
    """Clear active study session file"""
    try:
        if os.path.exists(".fibocli_active_study"):
            os.remove(".fibocli_active_study")
    except Exception as e:
        console.print(f"[red]❌ Error clearing active session: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option("--engagement", type=float, default=50, help="Current engagement level (1-100)")
@click.option("--fatigue", type=float, default=20, help="Current fatigue level (1-100)")
@click.option("--duration", type=int, default=210, help="Available study duration in minutes")
@click.option("--time-preference", type=click.Choice(['morning', 'afternoon', 'evening']), default='morning', help="Preferred time slot")
@click.option("--understanding", type=float, default=80, help="Understanding level after study (1-100)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
@click.option("--difficulty", type=float, default=50, help="Difficulty level (1-100)")
@click.option("--completed", is_flag=True, help="Complete the current study session")
def study(engagement, fatigue, duration, time_preference, understanding, importance, difficulty, completed):
    """Study command: prioritizes and manages study sessions"""
    uid = require_user()
    conn = None
    try:
        if not (1 <= engagement <= 100 and 1 <= fatigue <= 100 and 1 <= understanding <= 100 and 1 <= importance <= 100 and 1 <= difficulty <= 100):
            raise ValueError("Engagement, fatigue, understanding, importance, and difficulty must be between 1 and 100")
        if duration <= 0:
            raise ValueError("Duration must be positive")
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()

        # Handle session completion
        active_session = get_active_session()
        if completed:
            if not active_session:
                console.print("[yellow]No active study session to complete.[/yellow]")
                return
            now = datetime.datetime.now()
            start_time = datetime.datetime.fromisoformat(active_session["start_time"])
            actual_duration = (now - start_time).total_seconds() / 60
            schedule_id = active_session["schedule_id"]
            cursor.execute("SELECT task_id, task_type, user_id FROM Schedules WHERE schedule_id = ? AND status = 'active'", (schedule_id,))
            schedule = cursor.fetchone()
            if not schedule or schedule[2] != uid:
                console.print("[red]❌ Invalid or non-owned active session.[/red]")
                clear_active_session()
                return
            task_id, task_type, _ = schedule
            if task_type == "break":
                cursor.execute("UPDATE Schedules SET status = 'completed', duration = ? WHERE schedule_id = ?", (actual_duration, schedule_id))
                console.print("[green]✅ Break session completed. Duration: {actual_duration:.1f} min[/green]")
            else:
                cursor.execute("SELECT node_type FROM Nodes WHERE node_id = ?", (task_id,))
                node_type_res = cursor.fetchone()
                if not node_type_res:
                    raise ValueError(f"Node ID={task_id} not found")
                node_type = node_type_res[0]
                cursor.execute(
                    "UPDATE Nodes SET total_active_minutes = total_active_minutes + ?, understanding = ?, importance = ?, difficulty = ?, engagement = ?, fatigue = ?, status = 'completed', completion_ratio = 1.0, completed_at = ? WHERE node_id = ?",
                    (actual_duration, understanding, importance, difficulty, engagement, fatigue, now.isoformat(), task_id)
                )
                cursor.execute(
                    "INSERT INTO Reviews (node_id, node_type, scheduled_date, estimated_duration, status, focus_level, engagement, fatigue, completed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (task_id, node_type, now.date().isoformat(), actual_duration, "completed", engagement, engagement, fatigue, now.isoformat())
                )
                cursor.execute("UPDATE Schedules SET status = 'completed', duration = ? WHERE schedule_id = ?", (actual_duration, schedule_id))
                cursor.execute("SELECT last_study_date, streak_days FROM Users WHERE user_id = ?", (uid,))
                user_data = cursor.fetchone()
                last_study_date, streak_days = user_data
                today = datetime.date.today()
                if last_study_date:
                    last_date = datetime.date.fromisoformat(last_study_date)
                    if today == last_date + datetime.timedelta(days=1):
                        streak_days += 1
                    elif today > last_date + datetime.timedelta(days=1):
                        streak_days = 1
                else:
                    streak_days = 1
                learning_efficiency = 1.0 * (1 + 0.2 * min(streak_days, 10))
                cursor.execute("UPDATE Users SET last_study_date = ?, streak_days = ?, learning_efficiency = ? WHERE user_id = ?",
                              (today.isoformat(), streak_days, learning_efficiency, uid))
                console.print(f"[green]✅ Study session for node ID={task_id} completed. Duration: {actual_duration:.1f} min[/green]")
            conn.commit()
            clear_active_session()
            # Start next scheduled task
            cursor.execute("SELECT schedule_id, task_type FROM Schedules WHERE user_id = ? AND status = 'planned' ORDER BY start_time ASC LIMIT 1", (uid,))
            next_task = cursor.fetchone()
            if next_task:
                next_schedule_id, next_task_type = next_task
                now = datetime.datetime.now()
                cursor.execute("UPDATE Schedules SET status = 'active' WHERE schedule_id = ?", (next_schedule_id,))
                set_active_session(next_schedule_id, now)
                console.print(f"[blue]Started next {next_task_type} session.[/blue]")
            conn.commit()
            return

        # Check for active session
        if active_session:
            now = datetime.datetime.now()
            start_time = datetime.datetime.fromisoformat(active_session["start_time"])
            elapsed = (now - start_time).total_seconds() / 60
            cursor.execute("SELECT task_type FROM Schedules WHERE schedule_id = ?", (active_session["schedule_id"],))
            task_type = cursor.fetchone()
            if task_type:
                console.print(f"[blue]Active {task_type[0]} session running for {elapsed:.1f} minutes.[/blue]")
            else:
                console.print("[yellow]Active session found but invalid. Clearing.[/yellow]")
                clear_active_session()
            return

        # Prioritize and schedule new study session
        cursor.execute("SELECT available_minutes_per_day, streak_multiplier, learning_efficiency, fatigue_threshold FROM Users WHERE user_id = ?", (uid,))
        user_data = cursor.fetchone()
        if not user_data:
            raise ValueError("User data not found")
        available_minutes_json, streak_multiplier, learning_efficiency, fatigue_threshold = user_data
        try:
            available_minutes_list = json.loads(available_minutes_json)
            if len(available_minutes_list) != 7:
                raise ValueError("Invalid available_minutes_per_day format")
            available_minutes = available_minutes_list[datetime.date.today().weekday()]
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in available_minutes_per_day")
        cursor.execute(
            """
            SELECT n.node_id, n.node_type, n.name, n.importance, n.difficulty, n.understanding, n.total_active_minutes, n.fibonacci_index,
                   r.estimated_duration, r.scheduled_date
            FROM Nodes n
            LEFT JOIN Reviews r ON n.node_id = r.node_id AND r.status = 'pending'
            WHERE n.user_id = ? AND n.node_type IN ('leaf', 'sub_branch') AND n.status IN ('pending', 'active')
            ORDER BY n.child_order ASC, n.created_at ASC
            """,
            (uid,)
        )
        tasks = cursor.fetchall()
        if not tasks:
            console.print("[yellow]No pending or active study tasks found. Create nodes with 'fibocli create'.[/yellow]")
            return
        k_f, k_e, k_t, k_u, k_d, k_i = 0.5, 0.5, 0.5, 0.5, 0.5, 0.5
        time_preference_factor = 1.3 if time_preference == 'morning' else 1.0
        slot_weight = time_preference_factor * (1 - fatigue / 200)
        engagement_factor = 1 + k_e * (engagement / 100 - 0.5)
        fatigue_factor = 1 + k_t * (fatigue / 100 - 0.5)
        prioritized_tasks = []
        total_duration_needed = 0
        for task in tasks:
            node_id, node_type, name, imp, diff, und, total_active_minutes, fibonacci_index, estimated_duration, scheduled_date = task
            estimated_duration = estimated_duration or 30
            performance_weight = (und / 100) * streak_multiplier * (engagement / 100) / (fatigue / 100)
            understanding_factor = 1 + k_u * (und / 100 - 0.5)
            difficulty_factor = 1 + k_d * (diff / 100 - 0.5)
            importance_factor = 1 + k_i * (imp / 100 - 0.5)
            final_score = (imp / 100) * (1 - und / 100) * difficulty_factor * importance_factor * engagement_factor * learning_efficiency / fatigue_factor
            variance_factor = abs(und - diff) / 100
            confidence_score = (final_score / 2) * (engagement / 100) * learning_efficiency / (fatigue / 100) * (1 - variance_factor)
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
        prioritized_tasks.sort(key=lambda x: x["confidence_score"], reverse=True)
        remaining_duration = duration
        scheduled_tasks = []
        current_time = datetime.datetime.now().replace(hour=8 if time_preference == 'morning' else 14 if time_preference == 'afternoon' else 20, minute=0, second=0, microsecond=0)
        for task in prioritized_tasks:
            if remaining_duration <= 0:
                break
            task_duration = min(task["suggested_minutes"], remaining_duration)
            if task_duration <= 0:
                continue
            break_duration = 0
            if fatigue > fatigue_threshold:
                break_duration = 5 + 10 * (fatigue / 100 - fatigue_threshold / 100)
                cursor.execute(
                    "INSERT INTO Schedules (user_id, task_id, task_type, start_time, duration, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, task["node_id"], "break", current_time.isoformat(), break_duration, "planned")
                )
                current_time += datetime.timedelta(minutes=break_duration)
            cursor.execute(
                "INSERT INTO Schedules (user_id, task_id, task_type, start_time, duration, status) VALUES (?, ?, ?, ?, ?, ?)",
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
            cursor.execute("UPDATE Nodes SET status = 'active' WHERE node_id = ? AND status = 'pending'", (task["node_id"],))
        conn.commit()
        if scheduled_tasks:
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
            cursor.execute("SELECT schedule_id, task_type FROM Schedules WHERE user_id = ? AND status = 'planned' ORDER BY start_time ASC LIMIT 1", (uid,))
            first_task = cursor.fetchone()
            if first_task:
                schedule_id, task_type = first_task
                now = datetime.datetime.now()
                cursor.execute("UPDATE Schedules SET status = 'active' WHERE schedule_id = ?", (schedule_id,))
                set_active_session(schedule_id, now)
                console.print(f"[green]✅ Started {task_type} session for node ID={scheduled_tasks[0]['node_id']}.[/green]")
        else:
            console.print("[yellow]No tasks scheduled. Consider adjusting duration or creating new nodes.[/yellow]")
        conn.commit()
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf']))
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
def status(node_type, node_id):
    """Show advanced status for a node"""
    uid = require_user()
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, course, course_code, status, importance, difficulty, understanding, engagement, fatigue, total_active_minutes "
            "FROM Nodes WHERE node_id = ? AND user_id = ? AND node_type = ?",
            (node_id, uid, node_type)
        )
        node = cursor.fetchone()
        if not node:
            raise ValueError(f"{node_type.capitalize()} ID={node_id} not found or not owned by user")
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
            "SELECT engagement, fatigue, estimated_duration, scheduled_date FROM Reviews WHERE node_type = ? AND node_id = ? ORDER BY scheduled_date DESC LIMIT 5",
            (node_type, node_id)
        )
        sessions = cursor.fetchall()
        console.print(table)
        if sessions:
            session_table = Table(title="Recent Study Sessions (Last 5)")
            session_table.add_column("Date", style="cyan")
            session_table.add_column("Engagement", style="blue")
            session_table.add_column("Fatigue", style="red")
            session_table.add_column("Duration (min)", style="green")
            for session in sessions:
                session_table.add_row(session[3], str(session[0]), str(session[1]), str(session[2]))
            console.print(session_table)
        else:
            console.print("[yellow]No study sessions found for this node.[/yellow]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
@click.argument("available_minutes", type=int)
@click.option("--all", is_flag=True, help="Apply to all 7 days")
def set(available_minutes, all):
    """Set available study minutes per day"""
    uid = require_user()
    conn = None
    try:
        if available_minutes < 0:
            raise ValueError("Available minutes must be non-negative")
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT available_minutes_per_day FROM Users WHERE user_id = ?", (uid,))
        current_data = cursor.fetchone()
        if not current_data:
            raise ValueError("User data not found")
        try:
            current_calendar = json.loads(current_data[0])
            if len(current_calendar) != 7:
                raise ValueError("Invalid calendar format")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in available_minutes_per_day")
        if all:
            new_calendar = [available_minutes] * 7
        else:
            day = IntPrompt.ask("Select day (0=Sun, 1=Mon, ..., 6=Sat)", choices=[str(i) for i in range(7)], show_choices=False)
            new_calendar = current_calendar.copy()
            new_calendar[day] = available_minutes
        cursor.execute("UPDATE Users SET available_minutes_per_day = ? WHERE user_id = ?", (json.dumps(new_calendar), uid))
        conn.commit()
        console.print(f"[green]✅ Updated available study minutes to {available_minutes} min {'for all days' if all else 'for selected day'}[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
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
    conn = None
    try:
        if planned_units < 0:
            raise ValueError("Planned units must be non-negative")
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = ? AND user_id = ?", (parent_id, parent_type, uid))
        if not cursor.fetchone():
            raise ValueError(f"{parent_type.capitalize()} ID={parent_id} not found or not owned by user")
        cursor.execute("SELECT MAX(wave_number) FROM Waves WHERE parent_type = ? AND parent_id = ?", (parent_type, parent_id))
        max_wave = cursor.fetchone()[0] or 0
        wave_number = max_wave + 1
        cursor.execute(
            "SELECT AVG(understanding), AVG(engagement), AVG(fatigue) FROM Nodes WHERE user_id = ? AND node_type = 'leaf' "
            "AND parent_id IN (SELECT node_id FROM Nodes WHERE user_id = ? AND node_type = ? AND node_id = ?)",
            (uid, uid, parent_type, parent_id)
        )
        avg_metrics = cursor.fetchone()
        avg_understanding, avg_engagement, avg_fatigue = avg_metrics if avg_metrics and avg_metrics[0] is not None else (50, 50, 50)
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
        wave_id = cursor.fetchone()
        if not wave_id:
            raise ValueError("Failed to retrieve created wave ID")
        console.print(f"[green]✅ Wave created ID={wave_id[0]} (Units Planted={actual_units}/{planned_units})[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
@click.option("--node-id", type=int, required=True, help="Node ID for forecasting")
@click.option("--node-type", required=True, type=click.Choice(['leaf', 'sub_branch']))
def forecast(node_id, node_type):
    """Forecast progress for a node"""
    uid = require_user()
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(understanding), AVG(difficulty), AVG(engagement), AVG(fatigue) FROM Reviews WHERE node_id = ? AND node_type = ?", (node_id, node_type))
        recent_metrics = cursor.fetchone()
        recent_understanding, recent_difficulty, recent_engagement, recent_fatigue = recent_metrics if recent_metrics and recent_metrics[0] is not None else (50, 50, 50, 50)
        cursor.execute("SELECT understanding, streak_days, learning_efficiency FROM Nodes n JOIN Users u ON n.user_id = u.user_id WHERE node_id = ? AND node_type = ? AND n.user_id = ?", (node_id, node_type, uid))
        node_data = cursor.fetchone()
        if not node_data:
            raise ValueError(f"{node_type.capitalize()} ID={node_id} not found or not owned by user")
        prior_understanding, streak_days, learning_efficiency = node_data
        forecasted_understanding = prior_understanding * (recent_understanding / 100) * learning_efficiency / (recent_difficulty / 100)
        base_completion_days = 30
        k_e, k_t = 0.5, 0.5
        engagement_factor = 1 + k_e * (recent_engagement / 100 - 0.5)
        fatigue_factor = 1 + k_t * (recent_fatigue / 100 - 0.5)
        forecasted_days = base_completion_days * (recent_difficulty / 100) / (recent_understanding / 100) / (1 + 0.25 * min(streak_days, 10)) / (recent_engagement / 100) / learning_efficiency * fatigue_factor
        console.print(f"[green]✅ Forecast for {node_type} ID={node_id}: Understanding={forecasted_understanding:.1f}, Completion in {forecasted_days:.1f} days[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
def update_learning_efficiency():
    """Update learning efficiency based on streak days"""
    uid = require_user()
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT streak_days FROM Users WHERE user_id = ?", (uid,))
        streak_days = cursor.fetchone()
        if not streak_days:
            raise ValueError("User data not found")
        streak_days = streak_days[0]
        base_efficiency = 1.0
        learning_efficiency = base_efficiency * (1 + 0.2 * min(streak_days, 10))
        cursor.execute("UPDATE Users SET learning_efficiency = ? WHERE user_id = ?", (learning_efficiency, uid))
        conn.commit()
        console.print(f"[green]✅ Updated learning efficiency to {learning_efficiency:.2f}[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
@click.option("--node-id", type=int, required=True, help="Node ID")
@click.option("--node-type", required=True, type=click.Choice(['leaf', 'sub_branch']))
def adjust_difficulty(node_id, node_type):
    """Adjust node difficulty based on performance trend"""
    uid = require_user()
    conn = None
    try:
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT node_id FROM Nodes WHERE node_id = ? AND node_type = ? AND user_id = ?", (node_id, node_type, uid))
        if not cursor.fetchone():
            raise ValueError(f"{node_type.capitalize()} ID={node_id} not found or not owned by user")
        cursor.execute(
            "SELECT AVG(understanding), AVG(difficulty) FROM Reviews WHERE node_id = ? AND node_type = ? AND scheduled_date >= ?",
            (node_id, node_type, (datetime.date.today() - datetime.timedelta(days=30)).isoformat())
        )
        metrics = cursor.fetchone()
        if not metrics or metrics[0] is None:
            console.print("[yellow]No recent reviews to compute trend.[/yellow]")
            return
        avg_understanding, avg_difficulty = metrics
        trend = avg_understanding / avg_difficulty if avg_difficulty > 0 else 1.0
        cursor.execute("SELECT difficulty FROM Nodes WHERE node_id = ? AND node_type = ?", (node_id, node_type))
        current_difficulty = cursor.fetchone()[0]
        if trend > 1.3:
            new_difficulty = min(current_difficulty * 1.15, 100)
        elif trend < 0.7:
            new_difficulty = max(current_difficulty * 0.85, 1)
        else:
            new_difficulty = current_difficulty
        cursor.execute("UPDATE Nodes SET difficulty = ? WHERE node_id = ? AND node_type = ?", (new_difficulty, node_id, node_type))
        conn.commit()
        console.print(f"[green]✅ Adjusted difficulty for {node_type} ID={node_id} to {new_difficulty:.1f}[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

@cli.command()
@click.option("--date", default=datetime.date.today().isoformat(), help="Start date for scheduling (YYYY-MM-DD)")
def schedule_reviews(date):
    """Schedule reviews for all pending nodes"""
    uid = require_user()
    conn = None
    try:
        start_date = datetime.date.fromisoformat(date)
        conn = sqlite3.connect("fibocli.db")
        cursor = conn.cursor()
        cursor.execute("SELECT streak_multiplier, learning_efficiency FROM Users WHERE user_id = ?", (uid,))
        user_data = cursor.fetchone()
        if not user_data:
            raise ValueError("User data not found")
        streak_multiplier, learning_efficiency = user_data
        cursor.execute(
            "SELECT node_id, node_type, total_active_minutes, difficulty, importance, understanding, fibonacci_index "
            "FROM Nodes WHERE user_id = ? AND node_type IN ('leaf', 'sub_branch') AND status IN ('pending', 'active')",
            (uid,)
        )
        nodes = cursor.fetchall()
        if not nodes:
            console.print("[yellow]No nodes available for review scheduling.[/yellow]")
            return
        k_e, k_t = 0.5, 0.5
        engagement_factor = 1 + k_e * (50 / 100 - 0.5)  # Default
        fatigue_factor = 1 + k_t * (50 / 100 - 0.5)  # Default
        performance_weight = (50 / 100) * streak_multiplier * (50 / 100) / (50 / 100)
        for node in nodes:
            node_id, node_type, total_active_minutes, difficulty, importance, understanding, fibonacci_index = node
            completion_duration = total_active_minutes or 30
            interval_days = completion_duration * get_weighted_fibonacci(fibonacci_index + 1, performance_weight) * engagement_factor * learning_efficiency / fatigue_factor
            scheduled_date = start_date + datetime.timedelta(days=interval_days)
            estimated_duration = total_active_minutes * (difficulty / 100) * (importance / 100) / (understanding / 100) * engagement_factor * learning_efficiency / fatigue_factor + 5
            cursor.execute(
                "INSERT INTO Reviews (node_id, node_type, scheduled_date, estimated_duration, status) VALUES (?, ?, ?, ?, ?)",
                (node_id, node_type, scheduled_date.isoformat(), estimated_duration, "pending")
            )
        conn.commit()
        console.print(f"[green]✅ Scheduled reviews for {len(nodes)} nodes starting from {date}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.Error as e:
        console.print(f"[red]❌ SQLite error: {e}. Please run 'fibocli init'.[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise click.Abort()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    cli()