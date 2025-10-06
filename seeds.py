from db import init_db, get_conn
from models import create_user, create_ecology, create_forest, create_tree, create_super_branch, create_branch, create_sub_branch, insert_leaf, add_prerequisite
from utils import hash_password, iso_now
import click

@click.group()
def cli():
    """Seed the Ecology CLI database with test data."""
    pass

@cli.command()
def seed_all():
    """Seed the database with test data, including sequential prerequisites."""
    init_db(overwrite=False)
    try:
        # Create user
        pw = hash_password("password123")
        uid = create_user("Seed User", "seeduser", "seed@example.com", pw)

        # Create ecology
        eid = create_ecology(
            uid, "Eco", course_name="Universal", course_code="UNI",
            base_time_minutes=30, study_duration_minutes=30,
            understanding_level=0.5, difficulty=3, importance=0.5,
            completion_days=4, fibonacci_index=1, status="unlocked"
        )

        # Create forest
        fid = create_forest(
            eid, "Seed Forest", course_name="Universal", course_code="UNI",
            base_time_minutes=30, study_duration_minutes=30,
            understanding_level=0.5, difficulty=3, importance=0.5,
            completion_days=4, fibonacci_index=1, status="locked"
        )

        # Create tree
        tid = create_tree(
            fid, "Seed Tree", course_name="Universal", course_code="UNI",
            base_time_minutes=30, study_duration_minutes=30,
            understanding_level=0.5, difficulty=3, importance=0.5,
            completion_days=4, fibonacci_index=1, status="locked"
        )

        # Create super-branch
        sbid = create_super_branch(
            tid, "Seed Super", course_name="Universal", course_code="UNI",
            base_time_minutes=30, study_duration_minutes=30,
            understanding_level=0.5, difficulty=3, importance=0.5,
            completion_days=4, fibonacci_index=1, status="locked"
        )

        # Create branch for resource
        bid = create_branch(
            sbid, "The Linux Command Line", course_name="Linux Fundamentals", course_code="LIN101",
            base_time_minutes=30, study_duration_minutes=30,
            understanding_level=0.5, difficulty=3, importance=0.5,
            completion_days=4, fibonacci_index=1, status="locked"
        )

        # Create sub-branches and leaves with sequential prerequisites
        structure = [
            ("Part 1 – Learning the Shell", [
                "Chapter 1 – What Is the Shell?",
                "Chapter 2 – Navigation",
                "Chapter 3 – Exploring the System"
            ]),
            ("Part 2 – Configuration", [
                "Chapter 11 – The Environment"
            ])
        ]

        now = iso_now()
        subbranch_ids = []
        leaf_ids = []

        for part_name, chapters in structure:
            # Create sub-branch for part
            sbb = create_sub_branch(
                bid, part_name, course_name="Linux Fundamentals", course_code="LIN101",
                base_time_minutes=30, study_duration_minutes=30,
                understanding_level=0.5, difficulty=3, importance=0.5,
                completion_days=4, fibonacci_index=1,
                status="unlocked" if not subbranch_ids else "locked"
            )
            subbranch_ids.append(sbb)

            # Create leaves for chapters
            for i, chapter in enumerate(chapters):
                status = "unlocked" if not leaf_ids and not i else "locked"
                lid = insert_leaf(
                    sbb, chapter, "Linux Fundamentals", "LIN101", now,
                    resource_type="book", base_time_minutes=30, study_duration_minutes=30,
                    understanding_level=0.5, difficulty=3, importance=0.5,
                    completion_days=4, fibonacci_index=1, status=status
                )
                leaf_ids.append(lid)
                # Add sequential prerequisites
                if i > 0:
                    add_prerequisite("leaf", lid, "leaf", leaf_ids[-2])

        click.echo(f"✅ Seeded user {uid}, ecology {eid} with {len(subbranch_ids)} parts and {len(leaf_ids)} chapters under branch {bid}")

    except Exception as e:
        click.echo(f"❌ Error seeding database: {e}")
        raise click.Abort()

if __name__ == "__main__":
    cli()