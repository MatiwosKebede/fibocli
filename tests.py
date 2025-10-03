# tests.py - very small integration checks
import subprocess, sys, os
from db import init_db
from seeds import seed_all
from models import get_hierarchy_overview, get_pending_reviews_for_user
from algorithms import schedule_reviews_for_user
from utils import hash_password
import click

def run_all():
    # init DB fresh
    init_db(overwrite=True)
    # create user via models
    from models import create_user
    pw = hash_password("testpw")
    uid = create_user("Test", "testuser", "test@example.com", pw)
    # create basic hierarchy
    from models import create_ecology, create_forest, create_tree, create_super_branch, create_branch, create_sub_branch, insert_leaf
    eid = create_ecology(uid, "Test Ecology")
    fid = create_forest(eid, "Test Forest")
    tid = create_tree(fid, "Test Tree")
    sbid = create_super_branch(tid, "Super")
    bid = create_branch(sbid, "Branch")
    sbb = create_sub_branch(bid, "Sub")
    now = __import__('utils').iso_now()
    lid = insert_leaf(sbb, "TLeaf", "TCourse", "TC01", now)
    # schedule reviews
    scheduled = schedule_reviews_for_user(uid)
    assert len(scheduled) >= 1, "At least 1 review scheduled"
    print("✅ schedule_reviews produced", len(scheduled), "items")
    # pack week
    from algorithms import pack_schedule_for_week
    placements = pack_schedule_for_week(uid, __import__('datetime').date.today().isoformat())
    print("✅ pack_schedule placed", len(placements), "items")
    print("All tests passed")

if __name__ == "__main__":
    run_all()

