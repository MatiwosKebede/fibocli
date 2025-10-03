#!/usr/bin/env python3
# cli.py
import click
from db import init_db
from models import create_user, get_user_by_username, store_session_token, get_user_from_token, create_ecology, create_forest, create_tree, create_super_branch, create_branch, create_sub_branch, insert_leaf, get_hierarchy_overview, get_pending_reviews_for_user
from utils import hash_password, check_password, create_token, save_session_token, load_session_token, clear_session, iso_now
from algorithms import plant_wave, schedule_reviews_for_user, schedule_reviews_for_user as schedule_reviews, pack_schedule_for_week
from output import print_tree, print_reviews
import datetime


status_icons = {
    "pending": click.style("⚠ Pending", fg="yellow"),
    "completed": click.style("✅ Completed", fg="green"),
    "new": click.style("🌱 Newly planted", fg="cyan")
}


@click.group()
def cli():
    """Ecology CLI — Offline, WSL-friendly, powerful learning ecology"""
    pass

@cli.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing DB")
def init(overwrite):
    """Initialize DB from schema.sql"""
    init_db(overwrite=overwrite)
    click.echo("✅ Database initialized.")

@cli.command()
@click.option("--full-name", prompt=True)
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.password_option("--password", confirmation_prompt=True)
def signup(full_name, username, email, password):
    existing = get_user_by_username(username)
    if existing:
        click.echo("❌ username exists")
        return
    ph = hash_password(password)
    uid = create_user(full_name, username, email, ph)
    click.echo(f"✅ Created user id={uid}")

@cli.command()
@click.option("--username", prompt=True)
@click.password_option("--password")
def login(username, password):
    user = get_user_by_username(username)
    if not user:
        click.echo("❌ user not found")
        return
    if not check_password(password, user["password_hash"].encode('utf-8')):
        click.echo("❌ invalid credentials")
        return
    token = create_token()
    expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
    store_session_token(user["id"], token, expiry)
    save_session_token(token)
    click.echo("✅ Logged in and session saved locally.")

@cli.command()
def logout():
    clear_session()
    click.echo("✅ Local session cleared.")

def require_user():
    token = load_session_token()
    if not token:
        raise click.ClickException("No session found — please login.")
    uid = get_user_from_token(token)
    if not uid:
        raise click.ClickException("Invalid session — login again.")
    return uid

@cli.group()
def create():
    """Create hierarchy nodes"""
    pass

@create.command("ecology")
@click.option("--name", prompt=True)
def create_ecology_cmd(name):
    uid = require_user()
    eid = create_ecology(uid, name)
    click.echo(f"✅ Ecology created id={eid}")

@create.command("forest")
@click.option("--ecology-id", type=int, required=True)
@click.option("--name", prompt=True)
def create_forest_cmd(ecology_id, name):
    fid = create_forest(ecology_id, name)
    click.echo(f"✅ Forest created id={fid}")

@create.command("tree")
@click.option("--forest-id", type=int, required=True)
@click.option("--name", prompt=True)
def create_tree_cmd(forest_id, name):
    tid = create_tree(forest_id, name)
    click.echo(f"✅ Tree created id={tid}")

@create.command("super")
@click.option("--tree-id", type=int, required=True)
@click.option("--name", prompt=True)
def create_super_cmd(tree_id, name):
    sbid = create_super_branch(tree_id, name)
    click.echo(f"✅ Super-branch created id={sbid}")

@create.command("branch")
@click.option("--super-id", type=int, required=True)
@click.option("--name", prompt=True)
def create_branch_cmd(super_id, name):
    bid = create_branch(super_id, name)
    click.echo(f"✅ Branch created id={bid}")

@create.command("subbranch")
@click.option("--branch-id", type=int, required=True)
@click.option("--name", prompt=True)
def create_subbranch_cmd(branch_id, name):
    sbid = create_sub_branch(branch_id, name)
    click.echo(f"✅ Sub-branch created id={sbid}")

@create.command("leaf")
@click.option("--subbranch-id", type=int, required=True)
@click.option("--name", prompt=True)
@click.option("--course", default="")
@click.option("--code", default="")
def create_leaf_cmd(subbranch_id, name, course, code):
    now = iso_now()
    lid = insert_leaf(subbranch_id, name, course, code, now)
    click.echo(f"✅ Leaf created id={lid}")

@cli.command()
def tree():
    """Show hierarchy for current user"""
    uid = require_user()
    nodes = get_hierarchy_overview(uid)
    print_tree(nodes)

@cli.command()
@click.option("--parent-type", required=True, type=click.Choice(['ecology','forest','tree','super_branch','branch','sub_branch']))
@click.option("--parent-id", required=True, type=int)
@click.option("--units", required=True, type=int)
def plant(parent_type, parent_id, units):
    """Plant a wave (Fibonacci) under a parent"""
    uid = require_user()
    res = plant_wave(uid, parent_type, parent_id, units)
    click.echo(f"✅ Wave created id={res['wave_id']} created items: {res['created']} (quota {res['quota']})")

@cli.command()
def schedule():
    """Schedule reviews (compute & insert) and show pending reviews"""
    uid = require_user()
    scheduled = schedule_reviews(uid)
    click.echo(f"✅ Scheduled {len(scheduled)} reviews.")
    # show
    from models import get_pending_reviews_for_user
    revs = get_pending_reviews_for_user(uid)
    print_reviews(revs)

@cli.command()
@click.option("--week-start", default=None, help="YYYY-MM-DD start of week (default today)")
def pack(week_start):
    uid = require_user()
    if not week_start:
        week_start = datetime.date.today().isoformat()
    placements = pack_schedule_for_week(uid, week_start)
    click.echo(f"✅ Packed {len(placements)} items into calendar for week starting {week_start}")
@click.command()
def whoami():
    """Show logged-in user and current ecology"""
    from models import get_logged_in_user, get_user_ecology
    user = get_logged_in_user()
    if not user:
        click.echo("❌ Not logged in")
        return
    click.echo(f"User: {click.style(user['username'], fg='cyan')} ({user['full_name']})")
    ecology = get_user_ecology(user["id"])
    click.echo(f"Current Ecology: {click.style(ecology['name'], fg='green')} (ID: {ecology['id']})")
@click.command()
@click.option("--week-start", default=None, help="Start date of the week YYYY-MM-DD")
def stats(week_start):
    """Show weekly study/review stats"""
    from models import get_user_stats
    import datetime
    user = get_logged_in_user()
    if not user:
        click.echo("❌ Not logged in")
        return
    week_start = week_start or datetime.date.today().isoformat()
    stats = get_user_stats(user["id"], week_start)
    
    click.echo(click.style(f"Stats for week starting {week_start}", fg="blue"))
    click.echo(f"Total Leaves: {stats['total_leaves']}")
    click.echo(f"Pending Reviews: {stats['pending_reviews']}")
    click.echo(f"Scheduled Minutes: {stats['scheduled_minutes']}")
    click.echo(f"Completed Reviews: {stats['completed_reviews']}")

@cli.command()
@click.argument("review_id", type=int)
@click.argument("understanding", type=float)
@click.argument("duration", type=int)
@click.option("--notes", default="")
def review(review_id, understanding, duration, notes):
    """Mark a review completed"""
    from algorithms import perform_review
    uid = require_user()
    perform_review(review_id, understanding, duration, notes)
    click.echo("✅ Review recorded")

if __name__ == "__main__":
    cli()

