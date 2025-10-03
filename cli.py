#!/usr/bin/env python3
# cli.py
import rich_click as click
import datetime
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
        return
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
        return
    if not check_password(password, user["password_hash"]):
        console.print("[red]❌ Invalid credentials.[/red]")
        return
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
    table.add_column("#", style="cyan")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Course Name")
    table.add_column("Course Code")
    table.add_column("Hierarchy", style="dim")
    for i, p in enumerate(parents, 1):
        table.add_row(str(i), str(p['id']), p['name'], p.get('course_name', 'N/A'), p.get('course_code', 'N/A'), p['path'])
    console.print(table)
    choice = Prompt.ask("Select number", choices=[str(i) for i in range(1, len(parents)+1)])
    return parents[int(choice) - 1]['id']

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
    res = plant_wave(uid, parent_type, parent_id, units)
    console.print(f"[green]✅ Wave created ID={res['wave_id']} created items: {res['created']} (quota {res['quota']})[/green]")

@cli.command()
def schedule():
    """Schedule reviews and show pending reviews"""
    uid = require_user()
    scheduled = schedule_reviews_for_user(uid)
    console.print(f"[green]✅ Scheduled {len(scheduled)} reviews.[/green]")
    revs = get_pending_reviews_for_user(uid)
    print_reviews(revs)

@cli.command()
@click.option("--week-start", default=None, help="YYYY-MM-DD start of week (default today)")
def pack(week_start):
    """Pack reviews into weekly calendar"""
    uid = require_user()
    if not week_start:
        week_start = datetime.date.today().isoformat()
    placements = pack_schedule_for_week(uid, week_start)
    console.print(f"[green]✅ Packed {len(placements)} items into calendar for week starting {week_start}[/green]")

@cli.command()
def whoami():
    """Show logged-in user and current ecology"""
    user = get_logged_in_user()
    if not user:
        console.print("[red]❌ Not logged in[/red]")
        return
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
        return
    week_start = week_start or datetime.date.today().isoformat()
    stats = get_user_stats(user["id"], week_start)
    console.print(f"[blue]Stats for week starting {week_start}[/blue]")
    console.print(f"Total Leaves: {stats['total_leaves']}")
    console.print(f"Pending Reviews: {stats['pending_reviews']}")
    console.print(f"Scheduled Minutes: {stats['scheduled_minutes']}")
    console.print(f"Completed Reviews: {stats['completed_reviews']}")

@cli.command()
@click.argument("review_id", type=int)
@click.argument("understanding", type=float)
@click.argument("duration", type=int)
@click.option("--notes", default="", prompt="Notes (optional)")
def review(review_id, understanding, duration, notes):
    """Mark a review as completed"""
    uid = require_user()
    perform_review(review_id, understanding, duration, notes)
    console.print("[green]✅ Review recorded[/green]")

@cli.command()
def review_next():
    """Mark the next pending review as completed"""
    uid = require_user()
    revs = get_pending_reviews_for_user(uid)
    if not revs:
        console.print("[red]No pending reviews.[/red]")
        return
    next_review = min(revs, key=lambda r: r["scheduled_date"])
    console.print(f"Next review: {next_review['target_type']} ID={next_review['target_id']} due {next_review['scheduled_date']}")
    understanding = Prompt.ask("Understanding level (0-1)", type=float)
    duration = Prompt.ask("Duration (minutes)", type=int)
    notes = Prompt.ask("Notes", default="")
    perform_review(next_review["id"], understanding, duration, notes)
    console.print("[green]✅ Review recorded[/green]")

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['sub_branch', 'branch', 'super_branch', 'tree', 'forest', 'ecology']))
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
def schedule_integration(node_type, node_id):
    """Schedule an integration review for a specific node"""
    uid = require_user()
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    schedule_integration_review(uid, node_type, node_id, fib_index=1)
    console.print(f"[green]✅ Scheduled integration review for {node_type} ID={node_id}[/green]")

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf']))
def list_nodes(node_type):
    """List nodes of a given type for the current user"""
    uid = require_user()
    # Fix for ecology table name
    if node_type == "ecology":
        table_name = "ecologies"
    else:
        table_name = node_type + "s" if node_type != "sub_branch" else "sub_branches"
    with get_conn() as conn:
        c = conn.cursor()
        query = f"""
            SELECT id, name, course_name, course_code
            FROM {table_name}
            WHERE user_id = ? AND is_deleted = 0
        """
        c.execute(query, (uid,))
        nodes = c.fetchall()
        table = Table(title=f"{node_type.capitalize()} List")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Course Name")
        table.add_column("Course Code")
        if node_type == "leaf":
            table.add_column("Resource Type")
        for node in nodes:
            row = [str(node["id"]), node["name"], node.get("course_name", "N/A"), node.get("course_code", "N/A")]
            if node_type == "leaf":
                c.execute("SELECT resource_type FROM leaves WHERE id = ?", (node["id"],))
                resource_type = c.fetchone()
                row.append(resource_type["resource_type"] if resource_type else "other")
            table.add_row(*row)
        console.print(table)

@cli.command()
def progress_chart():
    """Show progress chart for leaves"""
    uid = require_user()
    print_progress_chart(uid)

if __name__ == "__main__":
    cli()