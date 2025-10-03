# seeds.py - create example user + ecology + some hierarchy and leaves for testing
from db import init_db
from models import create_user, create_ecology, create_forest, create_tree, create_super_branch, create_branch, create_sub_branch, insert_leaf
from utils import hash_password, iso_now
import click

@click.group()
def cli():
    pass

@cli.command()
def seed_all():
    init_db(overwrite=False)
    pw = hash_password("password123")
    uid = create_user("Seed User", "seeduser", "seed@example.com", pw)
    eid = create_ecology(uid, "Seed Ecology")
    fid = create_forest(eid, "Seed Forest")
    tid = create_tree(fid, "Seed Tree")
    sbid = create_super_branch(tid, "Seed Super")
    bid = create_branch(sbid, "Seed Branch")
    sbb = create_sub_branch(bid, "Seed SubBranch")
    now = iso_now()
    last_leaf_id = None
    for i in range(1,8):
        lid = insert_leaf(sbb, f"Seed Leaf {i}", "Seed Course", f"SC{i:02}", now)
        if last_leaf_id:
            with get_conn() as conn:
                c = conn.cursor()
                c.execute("UPDATE leaves SET next_leaf_id = ? WHERE id = ?", (lid, last_leaf_id))
        last_leaf_id = lid
    click.echo(f"✅ Seeded user {uid}, ecology {eid} with chained leaves under subbranch {sbb}")

if __name__ == "__main__":
    cli()
