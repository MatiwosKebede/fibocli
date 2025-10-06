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
    get_logged_in_user, get_user_ecology, get_user_stats, get_available_parents,
    add_prerequisite, get_prerequisites
)
from utils import (
    hash_password, check_password, create_token, save_session_token, load_session_token,
    clear_session, iso_now, validate_status, are_prerequisites_completed, estimate_review_duration
)
from algorithms import plant_wave, schedule_reviews_for_user, pack_schedule_for_week, perform_review, schedule_integration_review
from output import print_tree, print_reviews, print_schedule, print_progress_chart

console = Console()

status_icons = {
    "locked": "[grey]🔒 Locked[/grey]",
    "unlocked": "[yellow]○ Unlocked[/yellow]",
    "active": "[blue]▶ Active[/blue]",
    "completed": "[green]✅ Completed[/green]"
}

@click.group()
def cli():
    """Ecology CLI — Offline, WSL-friendly learning ecology with spaced repetition and sequential learning"""
    pass

@cli.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing database")
def init(overwrite):
    """Initialize database from schema.sql"""
    try:
        init_db(overwrite=overwrite)
        console.print("[green]✅ Database initialized successfully.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error initializing database: {e}[/red]")
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
        console.print(f"[red]❌ Username '{username}' already exists.[/red]")
        raise click.Abort()
    try:
        ph = hash_password(password)
        uid = create_user(full_name, username, email, ph)
        console.print(f"[green]✅ Created user ID={uid} ({username})[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--username", prompt="Username", help="Your username")
@click.option("--password", prompt="Password", hide_input=True, help="Your password")
def login(username, password):
    """Log in to your account"""
    user = get_user_by_username(username)
    if not user:
        console.print(f"[red]❌ User '{username}' not found.[/red]")
        raise click.Abort()
    if not check_password(password, user["password_hash"]):
        console.print("[red]❌ Invalid credentials.[/red]")
        raise click.Abort()
    try:
        token = create_token()
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
        store_session_token(user["id"], token, expiry)
        save_session_token(token)
        console.print("[green]✅ Logged in and session saved.[/green]")
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

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
        raise click.ClickException("Invalid or expired session — please login again.")
    return uid

def prompt_for_parent_id(parent_type: str, user_id: int) -> int:
    """Prompt user to select a parent node by number"""
    parents = get_available_parents(parent_type, user_id)
    if not parents:
        raise click.ClickException(f"No {parent_type}s found. Create one first with 'fibocli create {parent_type}'.")
    table = Table(title=f"Available {parent_type.capitalize()}s")
    table.add_column("#", style="cyan", width=5)
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Name", style="green")
    table.add_column("Course Name", style="blue")
    table.add_column("Course Code")
    table.add_column("Status", style="yellow")
    table.add_column("Hierarchy", style="dim")
    for i, p in enumerate(parents, 1):
        table.add_row(
            str(i),
            str(p["id"]),
            p["name"],
            p.get("course_name", "N/A"),
            p.get("course_code", "N/A"),
            status_icons.get(p["status"], p["status"].capitalize()),
            p["path"]
        )
    console.print(table)
    choice = Prompt.ask("Select number", choices=[str(i) for i in range(1, len(parents)+1)])
    return parents[int(choice) - 1]["id"]

def parse_structure(structure: str) -> list:
    """
    Parse a structure string into a list of parts and chapters.
    Format: "Part 1 – Name:Chapter 1 – Title,Chapter 2 – Title;Part 2 – Name:Chapter 3 – Title"
    Returns: [(part_name, [chapter_name, ...]), ...]
    """
    if not structure:
        return []
    try:
        parts = structure.split(";")
        result = []
        for part in parts:
            if ":" not in part:
                continue
            part_name, chapters = part.split(":", 1)
            part_name = part_name.strip()
            chapter_list = [ch.strip() for ch in chapters.split(",") if ch.strip()]
            result.append((part_name, chapter_list))
        return result
    except Exception as e:
        raise ValueError(f"Invalid structure format: {e}. Expected format: 'Part 1 – Name:Chapter 1 – Title,Chapter 2 – Title;Part 2 – Name:Chapter 3 – Title'")

@cli.group()
def create():
    """Create hierarchy nodes (ecology, forest, tree, etc.)"""
    pass

@create.command("ecology")
@click.option("--name", prompt="Ecology name", help="Name of the ecology")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="unlocked", help="Initial status (default: unlocked)")
def create_ecology_cmd(name, course, course_code, status):
    """Create a new ecology"""
    uid = require_user()
    try:
        eid = create_ecology(uid, name, course_name=course, course_code=course_code, status=status)
        console.print(f"[green]✅ Ecology created ID={eid} ({name}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("forest")
@click.option("--ecology-id", type=int, default=None, help="Ecology ID (prompt if not provided)")
@click.option("--name", prompt="Forest name", help="Name of the forest")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial status (default: locked)")
def create_forest_cmd(ecology_id, name, course, course_code, status):
    """Create a new forest under an ecology"""
    uid = require_user()
    if ecology_id is None:
        ecology_id = prompt_for_parent_id("ecology", uid)
    try:
        fid = create_forest(ecology_id, name, course_name=course, course_code=course_code, status=status)
        console.print(f"[green]✅ Forest created ID={fid} ({name}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("tree")
@click.option("--forest-id", type=int, default=None, help="Forest ID (prompt if not provided)")
@click.option("--name", prompt="Tree name", help="Name of the tree")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial status (default: locked)")
def create_tree_cmd(forest_id, name, course, course_code, status):
    """Create a new tree under a forest"""
    uid = require_user()
    if forest_id is None:
        forest_id = prompt_for_parent_id("forest", uid)
    try:
        tid = create_tree(forest_id, name, course_name=course, course_code=course_code, status=status)
        console.print(f"[green]✅ Tree created ID={tid} ({name}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("super")
@click.option("--tree-id", type=int, default=None, help="Tree ID (prompt if not provided)")
@click.option("--name", prompt="Super-branch name", help="Name of the super-branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial status (default: locked)")
def create_super_cmd(tree_id, name, course, course_code, status):
    """Create a new super-branch under a tree"""
    uid = require_user()
    if tree_id is None:
        tree_id = prompt_for_parent_id("tree", uid)
    try:
        sbid = create_super_branch(tree_id, name, course_name=course, course_code=course_code, status=status)
        console.print(f"[green]✅ Super-branch created ID={sbid} ({name}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("branch")
@click.option("--super-id", type=int, default=None, help="Super-branch ID (prompt if not provided)")
@click.option("--name", prompt="Branch name", help="Name of the branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial status (default: locked)")
def create_branch_cmd(super_id, name, course, course_code, status):
    """Create a new branch under a super-branch"""
    uid = require_user()
    if super_id is None:
        super_id = prompt_for_parent_id("super_branch", uid)
    try:
        bid = create_branch(super_id, name, course_name=course, course_code=course_code, status=status)
        console.print(f"[green]✅ Branch created ID={bid} ({name}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("subbranch")
@click.option("--branch-id", type=int, default=None, help="Branch ID (prompt if not provided)")
@click.option("--name", prompt="Sub-branch name", help="Name of the sub-branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial status (default: locked)")
def create_subbranch_cmd(branch_id, name, course, course_code, status):
    """Create a new sub-branch under a branch"""
    uid = require_user()
    if branch_id is None:
        branch_id = prompt_for_parent_id("branch", uid)
    try:
        sbid = create_sub_branch(branch_id, name, course_name=course, course_code=course_code, status=status)
        console.print(f"[green]✅ Sub-branch created ID={sbid} ({name}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("leaf")
@click.option("--subbranch-id", type=int, default=None, help="Sub-branch ID (prompt if not provided)")
@click.option("--name", prompt="Leaf name", help="Name of the leaf")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--resource-type", type=click.Choice(['book', 'video', 'web_course', 'other']),
              default='other', help="Type of learning resource")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial status (default: locked)")
def create_leaf_cmd(subbranch_id, name, course, course_code, resource_type, status):
    """Create a new leaf under a sub-branch"""
    uid = require_user()
    if subbranch_id is None:
        subbranch_id = prompt_for_parent_id("sub_branch", uid)
    try:
        now = iso_now()
        lid = insert_leaf(subbranch_id, name, course, course_code, now, resource_type=resource_type, status=status)
        console.print(f"[green]✅ Leaf created ID={lid} ({name}, {resource_type}, {status})[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@create.command("resource")
@click.option("--super-id", type=int, default=None, help="Super-branch ID (prompt if not provided)")
@click.option("--name", prompt="Resource name", help="Name of the resource (e.g., book title)")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--resource-type", type=click.Choice(['book', 'video', 'web_course', 'other']),
              default='book', help="Type of learning resource")
@click.option("--structure", prompt="Structure (e.g., 'Part 1:Chapter 1,Chapter 2;Part 2:Chapter 3')",
              help="Resource structure with parts and chapters")
@click.option("--prerequisites", type=click.Choice(['sequential', 'none']), default='none',
              help="Whether chapters have sequential prerequisites")
@click.option("--status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']), default="locked", help="Initial branch status (default: locked)")
def create_resource_cmd(super_id, name, course, course_code, resource_type, structure, prerequisites, status):
    """
    Create a resource with parts and chapters (sub-branches and leaves).
    Structure format: 'Part 1 – Name:Chapter 1 – Title,Chapter 2 – Title;Part 2 – Name:Chapter 3 – Title'
    """
    uid = require_user()
    if super_id is None:
        super_id = prompt_for_parent_id("super_branch", uid)
    try:
        # Create branch for the resource
        bid = create_branch(super_id, name, course_name=course, course_code=course_code, status=status)
        now = iso_now()
        
        # Parse structure
        parts = parse_structure(structure)
        if not parts:
            raise ValueError("No valid parts found in structure")

        subbranch_ids = []
        leaf_ids = []
        for part_name, chapters in parts:
            # Create sub-branch for each part
            sbid = create_sub_branch(bid, part_name, course_name=course, course_code=course_code, status="unlocked" if not subbranch_ids else "locked")
            subbranch_ids.append(sbid)
            # Create leaves for each chapter
            for i, chapter in enumerate(chapters):
                lid = insert_leaf(sbid, chapter, course, course_code, now, resource_type=resource_type, status="unlocked" if i == 0 and not subbranch_ids else "locked")
                leaf_ids.append(lid)
                # Add sequential prerequisites if specified
                if prerequisites == "sequential" and i > 0:
                    add_prerequisite("leaf", lid, "leaf", leaf_ids[-2])

        console.print(f"[green]✅ Resource created: Branch ID={bid}, {len(subbranch_ids)} parts, {len(leaf_ids)} chapters[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
def hierarchy():
    """Show hierarchy for current user"""
    uid = require_user()
    try:
        nodes = get_hierarchy_overview(uid)
        if not nodes:
            console.print("[yellow]No hierarchy nodes found. Create an ecology with 'fibocli create ecology'.[/yellow]")
            return
        print_tree(nodes)
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

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
        console.print(f"[green]✅ Scheduled {scheduled} reviews for {date}.[/green]")
        revs = get_pending_reviews_for_user(uid)
        if not revs:
            console.print("[yellow]No pending reviews found.[/yellow]")
            return
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
        if not placements:
            console.print(f"[yellow]No reviews to pack for week starting {week_start}.[/yellow]")
            return
        print_schedule(placements)
        console.print(f"[green]✅ Packed {len(placements)} reviews for week starting {week_start}[/green]")
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
        console.print(f"Current Ecology: [green]{ecology['name']}[/green] (ID: {ecology['id']}, Status: {status_icons.get(ecology['status'], ecology['status'].capitalize())})")
    else:
        console.print("[yellow]No ecology found. Create one with 'fibocli create ecology'.[/yellow]")

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
        table = Table(title=f"Stats for Week Starting {week_start}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Leaves", str(stats['total_leaves']))
        table.add_row("Pending Reviews", str(stats['pending_reviews']))
        table.add_row("Scheduled Minutes", str(stats['scheduled_minutes']))
        table.add_row("Completed Reviews", str(stats['completed_reviews']))
        table.add_row("Average Understanding", f"{stats['avg_understanding']:.2f}" if stats['avg_understanding'] else "N/A")
        console.print(table)
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.argument("review_id", type=int)
@click.argument("understanding", type=float)
@click.argument("duration", type=int)
@click.option("--notes", default="", help="Optional notes for the review")
def review(review_id, understanding, duration, notes):
    """Mark a review as completed and update node status"""
    uid = require_user()
    try:
        if not (0 <= understanding <= 1):
            raise ValueError("Understanding must be between 0 and 1.")
        if duration <= 0:
            raise ValueError("Duration must be a positive integer.")
        perform_review(review_id, understanding, duration, notes)
        console.print(f"[green]✅ Review {review_id} marked as completed with understanding {understanding:.2f}, duration {duration} minutes.[/green]")
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
        return
    next_review = min(revs, key=lambda r: r["scheduled_date"])
    console.print(f"Next review: {next_review['target_type'].capitalize()} ID={next_review['target_id']} ({next_review['name']}) due {next_review['scheduled_date']}")
    try:
        understanding = Prompt.ask("Understanding level (0-1)", type=float, default=0.8)
        if not (0 <= understanding <= 1):
            raise ValueError("Understanding must be between 0 and 1.")
        duration = Prompt.ask("Duration (minutes)", type=int, default=next_review["estimated_duration"])
        if duration <= 0:
            raise ValueError("Duration must be a positive integer.")
        notes = Prompt.ask("Notes (optional)", default="")
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
    table_name = (
        "ecologies" if node_type == "ecology" else
        "forests" if node_type == "forest" else
        "trees" if node_type == "tree" else
        "super_branches" if node_type == "super_branch" else
        "branches" if node_type == "branch" else
        "sub_branches" if node_type == "sub_branch" else
        "leaves"
    )
    try:
        with get_conn() as conn:
            c = conn.cursor()
            query = f"""
                SELECT id, name, course_name, course_code, status
                FROM {table_name}
                WHERE user_id = ? AND is_deleted = 0
            """
            c.execute(query, (uid,))
            nodes = c.fetchall()
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
                table.add_column("Resource Type")
            for node in nodes:
                row = [
                    str(node["id"]),
                    node["name"],
                    node["course_name"] if node["course_name"] else "N/A",
                    node["course_code"] if node["course_code"] else "N/A",
                    status_icons.get(node["status"], node["status"].capitalize())
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
        table.add_column("Status", style="yellow")
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
                status_icons.get(review["status"], review["status"].capitalize()),
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
            c.execute("SELECT created_at, status FROM reviews WHERE id = ? AND user_id = ? AND is_deleted = 0", (review_id, uid))
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
def progress():
    """Show progress chart for leaves"""
    uid = require_user()
    try:
        print_progress_chart(uid)
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['sub_branch', 'leaf']))
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
@click.option("--prereq-type", required=True, type=click.Choice(['sub_branch', 'leaf']))
@click.option("--prereq-id", type=int, default=None, help="Prerequisite ID (prompt if not provided)")
def add_prerequisite_cmd(node_type, node_id, prereq_type, prereq_id):
    """Add a prerequisite for a sub-branch or leaf"""
    uid = require_user()
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    if prereq_id is None:
        prereq_id = prompt_for_parent_id(prereq_type, uid)
    try:
        add_prerequisite(node_type, node_id, prereq_type, prereq_id)
        console.print(f"[green]✅ Added prerequisite {prereq_type} ID={prereq_id} for {node_type} ID={node_id}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.option("--node-type", required=True, type=click.Choice(['sub_branch', 'leaf']))
@click.option("--node-id", type=int, default=None, help="Node ID (prompt if not provided)")
def list_prerequisites(node_type, node_id):
    """List prerequisites for a sub-branch or leaf"""
    uid = require_user()
    if node_id is None:
        node_id = prompt_for_parent_id(node_type, uid)
    try:
        prereqs = get_prerequisites(node_type, node_id)
        if not prereqs:
            console.print(f"[yellow]No prerequisites found for {node_type} ID={node_id}.[/yellow]")
            return
        table = Table(title=f"Prerequisites for {node_type.capitalize()} ID={node_id}")
        table.add_column("Type", style="cyan", width=10)
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Name", style="green")
        table.add_column("Course Name", style="blue")
        table.add_column("Completed", style="yellow")
        for prereq in prereqs:
            table.add_row(
                prereq["prerequisite_type"].capitalize(),
                str(prereq["prerequisite_id"]),
                prereq["name"],
                prereq["course_name"] or "N/A",
                "Yes" if prereq["is_completed"] else "No"
            )
        console.print(table)
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

@cli.command()
@click.argument("node-type", type=click.Choice(['sub_branch', 'leaf']))
@click.argument("node-id", type=int)
@click.argument("status", type=click.Choice(['locked', 'unlocked', 'active', 'completed']))
def set_status(node_type, node_id, status):
    """Set the status of a sub-branch or leaf"""
    uid = require_user()
    try:
        validate_status(status)
        table_name = "sub_branches" if node_type == "sub_branch" else "leaves"
        with get_conn() as conn:
            c = conn.cursor()
            c.execute(f"SELECT id, status FROM {table_name} WHERE id = ? AND user_id = ? AND is_deleted = 0", (node_id, uid))
            node = c.fetchone()
            if not node:
                raise ValueError(f"{node_type.capitalize()} ID={node_id} not found")
            if status == "unlocked" and not are_prerequisites_completed(node_type, node_id):
                raise ValueError(f"Cannot set {node_type} ID={node_id} to 'unlocked' until all prerequisites are completed")
            if status == "completed" and node["status"] != "active":
                raise ValueError(f"Cannot set {node_type} ID={node_id} to 'completed' from {node['status']}, must be 'active'")
            c.execute(f"UPDATE {table_name} SET status = ? WHERE id = ?", (status, node_id))
            if status == "completed":
                c.execute(
                    """
                    UPDATE prerequisites SET is_completed = 1
                    WHERE prerequisite_type = ? AND prerequisite_id = ?
                    """,
                    (node_type, node_id)
                )
            conn.commit()
        console.print(f"[green]✅ Set {node_type} ID={node_id} status to {status}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()
    except sqlite3.OperationalError as e:
        console.print(f"[red]❌ Database error: {e}. Please check if the database is initialized with 'fibocli init'.[/red]")
        raise click.Abort()

if __name__ == "__main__":
    cli()
