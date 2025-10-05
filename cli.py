#!/usr/bin/env python3
# cli.py
import rich_click as click
import datetime
import sqlite3
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from db import init_db, get_conn
from models import (
    create_user, get_user_by_username, store_session_token, get_user_from_token,
    create_ecology, create_forest, create_tree, create_super_branch, create_branch,
    create_sub_branch, insert_leaf, get_hierarchy_overview, get_pending_reviews_for_user,
    get_logged_in_user, get_user_ecology, get_user_stats, get_available_parents
)
from utils import hash_password, check_password, create_token, save_session_token, load_session_token, clear_session, iso_now
from algorithms import plant_wave, schedule_reviews_for_user, pack_schedule_for_week, perform_review, schedule_integration_review
from output import print_tree, print_reviews, print_schedule, print_progress_chart

console = Console()

status_icons = {
    "pending": "[yellow]⚠ Pending[/yellow]",
    "completed": "[green]✅ Completed[/green]",
    "new": "[cyan]🌱 Newly planted[/cyan]"
}

@click.group()
def cli():
    """Ecology CLI — Offline, WSL-friendly learning ecology with spaced repetition"""
    pass

@cli.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing database")
def init(overwrite):
    """Initialize database from schema.sql"""
    try:
        init_db(overwrite=overwrite)
        console.print("[green]✅ Database initialized.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error initializing DB: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option("--full-name", prompt="Full name", help="Your full name")
@click.option("--username", prompt="Username", help="Unique username")
@click.option("--email", prompt="Email", help="Your email address")
@click.password_option("--password", prompt="Password", confirmation_prompt=True, help="Secure password")
def signup(full_name, username, email, password):
    """Create a new user account"""
    existing = get_user_by_username(username)
    if existing:
        console.print("[red]❌ Username already exists.[/red]")
        raise click.Abort()
    ph = hash_password(password)
    uid = create_user(full_name, username, email, ph)
    console.print(f"[green]✅ Created user ID={uid} ({username})[/green]")

@cli.command()
@click.option("--username", prompt="Username", help="Your username")
@click.option("--password", prompt="Password", hide_input=True, help="Your password")
def login(username, password):
    """Log in to your account"""
    user = get_user_by_username(username)
    if not user:
        console.print("[red]❌ User not found.[/red]")
        raise click.Abort()
    if not check_password(password, user["password_hash"]):
        console.print("[red]❌ Invalid credentials.[/red]")
        raise click.Abort()
    token = create_token()
    expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
    store_session_token(user["id"], token, expiry)
    save_session_token(token)
    console.print("[green]✅ Logged in and session saved.[/green]")

@cli.command()
def logout():
    """Log out and clear local session"""
    clear_session()
    console.print("[green]✅ Local session cleared.[/green]")

def require_user():
    """Ensure user is logged in, return user_id"""
    token = load_session_token()
    if not token:
        raise click.ClickException("No session found — please login.")
    uid = get_user_from_token(token)
    if not uid:
        raise click.ClickException("Invalid session — login again.")
    return uid

def prompt_for_parent_id(parent_type: str, user_id: int) -> int:
    """Prompt user to select a parent node by number"""
    parents = get_available_parents(parent_type, user_id)
    if not parents:
        raise click.ClickException(f"No {parent_type}s found. Create one first.")
    table = Table(title=f"Available {parent_type.capitalize()}s")
    table.add_column("#", style="cyan", width=5)
    table.add_column("ID", width=5)
    table.add_column("Name", style="green")
    table.add_column("Course Name", style="blue")
    table.add_column("Course Code")
    table.add_column("Hierarchy", style="dim")
    for i, p in enumerate(parents, 1):
        table.add_row(
            str(i),
            str(p["id"]),
            p["name"],
            p.get("course_name", "N/A"),
            p.get("course_code", "N/A"),
            p["path"]
        )
    console.print(table)
    choice = Prompt.ask("Select number", choices=[str(i) for i in range(1, len(parents)+1)])
    return parents[int(choice) - 1]["id"]

@cli.group()
def create():
    """Create hierarchy nodes (ecology, forest, tree, etc.)"""
    pass

@create.command("ecology")
@click.option("--name", prompt="Ecology name", help="Name of the ecology")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--course-code", default="", prompt="Course code (optional)", help="Course code")
def create_ecology_cmd(name, course, course_code):
    """Create a new ecology"""
    uid = require_user()
    eid = create_ecology(uid, name, course_name=course, course_code=course_code)
    console.print(f"[green]✅ Ecology created ID={eid} ({name})[/green]")

@create.command("forest")
@click.option("--ecology-id", type=int, default=None, help="Ecology ID (prompt if not provided)")
@click.option("--name", prompt="Forest name", help="Name of the forest")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--course-code", default="", prompt="Course code (optional)", help="Course code")
def create_forest_cmd(ecology_id, name, course, course_code):
    """Create a new forest under an ecology"""
    uid = require_user()
    if ecology_id is None:
        ecology_id = prompt_for_parent_id("ecology", uid)
    fid = create_forest(ecology_id, name, course_name=course, course_code=course_code)
    console.print(f"[green]✅ Forest created ID={fid} ({name})[/green]")

@create.command("tree")
@click.option("--forest-id", type=int, default=None, help="Forest ID (prompt if not provided)")
@click.option("--name", prompt="Tree name", help="Name of the tree")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--course-code", default="", prompt="Course code (optional)", help="Course code")
def create_tree_cmd(forest_id, name, course, course_code):
    """Create a new tree under a forest"""
    uid = require_user()
    if forest_id is None:
        forest_id = prompt_for_parent_id("forest", uid)
    tid = create_tree(forest_id, name, course_name=course, course_code=course_code)
    console.print(f"[green]✅ Tree created ID={tid} ({name})[/green]")

@create.command("super")
@click.option("--tree-id", type=int, default=None, help="Tree ID (prompt if not provided)")
@click.option("--name", prompt="Super-branch name", help="Name of the super-branch")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--course-code", default="", prompt="Course code (optional)", help="Course code")
def create_super_cmd(tree_id, name, course, course_code):
    """Create a new super-branch under a tree"""
    uid = require_user()
    if tree_id is None:
        tree_id = prompt_for_parent_id("tree", uid)
    sbid = create_super_branch(tree_id, name, course_name=course, course_code=course_code)
    console.print(f"[green]✅ Super-branch created ID={sbid} ({name})[/green]")

@create.command("branch")
@click.option("--super-id", type=int, default=None, help="Super-branch ID (prompt if not provided)")
@click.option("--name", prompt="Branch name", help="Name of the branch")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--course-code", default="", prompt="Course code (optional)", help="Course code")
def create_branch_cmd(super_id, name, course, course_code):
    """Create a new branch under a super-branch"""
    uid = require_user()
    if super_id is None:
        super_id = prompt_for_parent_id("super_branch", uid)
    bid = create_branch(super_id, name, course_name=course, course_code=course_code)
    console.print(f"[green]✅ Branch created ID={bid} ({name})[/green]")

@create.command("subbranch")
@click.option("--branch-id", type=int, default=None, help="Branch ID (prompt if not provided)")
@click.option("--name", prompt="Sub-branch name", help="Name of the sub-branch")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--course-code", default="", prompt="Course code (optional)", help="Course code")
def create_subbranch_cmd(branch_id, name, course, course_code):
    """Create a new sub-branch under a branch"""
    uid = require_user()
    if branch_id is None:
        branch_id = prompt_for_parent_id("branch", uid)
    sbid = create_sub_branch(branch_id, name, course_name=course, course_code=course_code)
    console.print(f"[green]✅ Sub-branch created ID={sbid} ({name})[/green]")

@create.command("leaf")
@click.option("--subbranch-id", type=int, default=None, help="Sub-branch ID (prompt if not provided)")
@click.option("--name", prompt="Leaf name", help="Name of the leaf")
@click.option("--course", default="", prompt="Course name (optional)", help="Associated course name")
@click.option("--code", default="", prompt="Course code (optional)", help="Course code")
@click.option("--resource-type", type=click.Choice(['book', 'video', 'web_course', 'other']),
              default='other', prompt="Resource type", help="Type of learning resource")
def create_leaf_cmd(subbranch_id, name, course, code, resource_type):
    """Create a new leaf under a sub-branch"""
    uid = require_user()
    if subbranch_id is None:
        subbranch_id = prompt_for_parent_id("sub_branch", uid)
    now = iso_now()
    lid = insert_leaf(subbranch_id, name, course, code, now, resource_type=resource_type)
    console.print(f"[green]✅ Leaf created ID={lid} ({name}, {resource_type})[/green]")

@cli.command()
def tree():
    """Show hierarchy for current user"""
    uid = require_user()
    nodes = get_hierarchy_overview(uid)
    print_tree(nodes)

@cli.command()
@click.option("--parent-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch']))
@click.option("--parent-id", type=int, default=None, help="Parent ID (prompt if not provided)")
@click.option("--units", required=True, type=int, help="Number of units to plant")
def plant(parent_type, parent_id, units):
    """Plant a wave of nodes (Fibonacci-based) under a parent"""
    uid = require_user()
    if parent_id is None:
        parent_id = prompt_for_parent_id(parent_type, uid)
    try:
        res = plant_wave(uid, parent_type, parent_id, units)
        console.print(f"[green]✅ Wave created ID={res['wave_id']} created items: {res['created']} (quota {res['quota']})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--date", default=None, help="YYYY-MM-DD date to schedule reviews (default today)")
def schedule(date):
    """Schedule reviews and show pending reviews"""
    uid = require_user()
    date = date or datetime.date.today().isoformat()
    try:
        scheduled = schedule_reviews_for_user(uid, date)
        console.print(f"[green]✅ Scheduled {scheduled} reviews.[/green]")
        revs = get_pending_reviews_for_user(uid)
        print_reviews(revs)
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--week-start", default=None, help="YYYY-MM-DD start of week (default today)")
def pack(week_start):
    """Pack reviews into weekly calendar"""
    uid = require_user()
    week_start = week_start or datetime.date.today().isoformat()
    try:
        placements = pack_schedule_for_week(uid, week_start)
        print_schedule(placements)
        console.print(f"[green]✅ Packed {len(placements['schedule'])} days with reviews for week starting {week_start}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
def whoami():
    """Show logged-in user and current ecology"""
    user = get_logged_in_user()
    if not user:
        console.print("[red]❌ Not logged in[/red]")
        raise click.Abort()
    console.print(f"User: [cyan]{user['username']}[/cyan] ({user['full_name']})")
    ecology = get_user_ecology(user["id"])
    if ecology:
        console.print(f"Current Ecology: [green]{ecology['name']}[/green] (ID: {ecology['id']})")
    else:
        console.print("No ecology found.")

@cli.command()
@click.option("--week-start", default=None, help="Start date of the week YYYY-MM-DD")
def stats(week_start):
    """Show weekly study/review stats"""
    user = get_logged_in_user()
    if not user:
        console.print("[red]❌ Not logged in[/red]")
        raise click.Abort()
    week_start = week_start or datetime.date.today().isoformat()
    try:
        stats = get_user_stats(user["id"], week_start)
        console.print(f"[blue]Stats for week starting {week_start}[/blue]")
        console.print(f"Total Leaves: {stats['total_leaves']}")
        console.print(f"Pending Reviews: {stats['pending_reviews']}")
        console.print(f"Scheduled Minutes: {stats['scheduled_minutes']}")
        console.print(f"Completed Reviews: {stats['completed_reviews']}")
        console.print(f"Average Understanding: {stats.get('avg_understanding', 'N/A')}")
        console.print(f"Current Streak: {stats.get('current_streak', 0)} days")
        console.print(f"Longest Streak: {stats.get('longest_streak', 0)} days")
        console.print(f"Average Readiness: {stats.get('avg_readiness', 'N/A')}")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.argument("review_id", type=int)
@click.argument("understanding", type=float)
@click.argument("duration", type=int)
@click.option("--notes", default="", prompt="Notes (optional)", help="Optional notes for the review")
def review(review_id, understanding, duration, notes):
    """Mark a review as completed"""
    uid = require_user()
    try:
        if not (0 <= understanding <= 1):
            raise ValueError("Understanding must be between 0 and 1.")
        if duration <= 0:
            raise ValueError("Duration must be a positive integer.")
        perform_review(review_id, understanding, duration, notes)
        console.print(f"[green]✅ Review {review_id} marked as completed with understanding {understanding}, duration {duration} minutes.[/green]")
    except ValueError as e:
        current_date = datetime.date.today().isoformat()
        if "not found" in str(e).lower():
            console.print(f"[red]❌ Error: Review ID={review_id} does not exist. Use 'fibocli list-reviews' to see available reviews.[/red]")
        elif "future" in str(e).lower():
            console.print(f"[red]❌ Error: {e} Current date is {current_date}. Use 'fibocli reschedule-review {review_id} {current_date}' to reschedule to today.[/red]")
        else:
            console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
def review_next():
    """Mark the next pending review as completed"""
    uid = require_user()
    revs = get_pending_reviews_for_user(uid)
    if not revs:
        console.print("[yellow]No pending reviews found.[/yellow]")
        raise click.Abort()
    next_review = min(revs, key=lambda r: r["scheduled_date"])
    console.print(f"Next review: {next_review['target_type'].capitalize()} ID={next_review['target_id']} ({next_review['name']}) due {next_review['scheduled_date']}")
    try:
        understanding = Prompt.ask("Understanding level (0-1)", type=float)
        if not (0 <= understanding <= 1):
            raise ValueError("Understanding must be between 0 and 1.")
        duration = Prompt.ask("Duration (minutes)", type=int)
        if duration <= 0:
            raise ValueError("Duration must be a positive integer.")
        notes = Prompt.ask("Notes", default="")
        perform_review(next_review["id"], understanding, duration, notes)
        console.print(f"[green]✅ Review {next_review['id']} marked as completed.[/green]")
    except ValueError as e:
        current_date = datetime.date.today().isoformat()
        if "not found" in str(e).lower():
            console.print(f"[red]❌ Error: Review ID={next_review['id']} does not exist. Use 'fibocli list-reviews' to see available reviews.[/red]")
        elif "future" in str(e).lower():
            console.print(f"[red]❌ Error: {e} Current date is {current_date}. Use 'fibocli reschedule-review {next_review['id']} {current_date}' to reschedule to today.[/red]")
        else:
            console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['sub_branch', 'branch', 'super_branch', 'tree', 'forest', 'ecology']))
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
def schedule_integration(node_type, node_id):
    """Schedule an integration review for a specific node"""
    uid = require_user()
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    try:
        schedule_integration_review(uid, node_type, node_id, datetime.date.today().isoformat())
        console.print(f"[green]✅ Scheduled integration review for {node_type} ID={node_id}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf']))
def list_nodes(node_type):
    """List nodes of a given type for the current user"""
    uid = require_user()
    # Correct table names for all node types
    table_name = (
        "ecologies" if node_type == "ecology" else
        "forests" if node_type == "forest" else
        "trees" if node_type == "tree" else
        "super_branches" if node_type == "super_branch" else
        "branches" if node_type == "branch" else
        "sub_branches" if node_type == "sub_branch" else
        "leaves"  # Corrected for leaf
    )
    try:
        with get_conn() as conn:
            c = conn.cursor()
            query = f"""
                SELECT id, name, course_name, course_code
                FROM {table_name}
                WHERE user_id = ? AND is_deleted = 0
            """
            c.execute(query, (uid,))
            nodes = c.fetchall()
            if not nodes:
                console.print(f"[yellow]No {node_type} nodes found.[/yellow]")
                return
            table = Table(title=f"{node_type.capitalize()} List")
            table.add_column("ID", style="cyan", width=5)
            table.add_column("Name", style="green")
            table.add_column("Course Name", style="blue")
            table.add_column("Course Code")
            if node_type == "leaf":
                table.add_column("Resource Type")
            for node in nodes:
                row = [
                    str(node["id"]),
                    node["name"],
                    node["course_name"] if node["course_name"] else "N/A",
                    node["course_code"] if node["course_code"] else "N/A"
                ]
                if node_type == "leaf":
                    c.execute("SELECT resource_type FROM leaves WHERE id = ?", (node["id"],))
                    resource_type = c.fetchone()
                    row.append(resource_type["resource_type"] if resource_type else "other")
                table.add_row(*row)
            console.print(table)
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
def list_reviews():
    """List all pending reviews for the user"""
    uid = require_user()
    try:
        revs = get_pending_reviews_for_user(uid)
        if not revs:
            console.print("[yellow]No pending reviews found.[/yellow]")
            return
        table = Table(title="Pending Reviews")
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Target", style="green")
        table.add_column("Type", style="magenta")
        table.add_column("Course", style="blue")
        table.add_column("Due", style="yellow")
        table.add_column("Duration (min)")
        table.add_column("Integration", style="red")
        for review in revs:
            target = f"{review['name']} (ID: {review['target_id']})"
            course = review['course_name'] or "N/A"
            integration = "Yes" if review.get('is_integration_review', 0) else "No"
            table.add_row(
                str(review["id"]),
                target,
                review["target_type"].capitalize(),
                course,
                review["scheduled_date"],
                str(review["estimated_duration"]),
                integration
            )
        console.print(table)
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.argument("review_id", type=int)
@click.argument("new_date", type=str)
def reschedule_review(review_id, new_date):
    """Reschedule a review to a new date"""
    uid = require_user()
    try:
        datetime.date.fromisoformat(new_date)
    except ValueError:
        console.print(f"[red]❌ Error: Invalid date format for {new_date}. Use YYYY-MM-DD.[/red]")
        raise click.Abort()
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT created_at, status FROM reviews WHERE id = ? AND status = 'pending'", (review_id,))
            review = c.fetchone()
            if not review:
                console.print(f"[red]❌ Error: Review ID={review_id} not found or is not pending. Use 'fibocli list-reviews' to see available reviews.[/red]")
                raise click.Abort()
            if new_date < review["created_at"]:
                console.print(f"[red]❌ Error: New date {new_date} cannot be before review creation date {review['created_at']}.[/red]")
                raise click.Abort()
            c.execute("UPDATE reviews SET scheduled_date = ? WHERE id = ?", (new_date, review_id))
            conn.commit()
            console.print(f"[green]✅ Review {review_id} rescheduled to {new_date}.[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
def progress_chart():
    """Show progress chart for leaves"""
    uid = require_user()
    try:
        print_progress_chart(uid)
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

if __name__ == "__main__":
    cli()