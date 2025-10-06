```python
import unittest
from db import init_db, get_conn
from models import (
    create_user, get_user_by_username, create_ecology, create_forest, create_tree,
    create_super_branch, create_branch, create_sub_branch, insert_leaf, add_prerequisite,
    get_prerequisites
)
from utils import hash_password, validate_status, are_prerequisites_completed
from algorithms import get_fib_from_table

class TestEcologySystem(unittest.TestCase):
    def setUp(self):
        """Initialize a fresh database before each test."""
        init_db(overwrite=True)

    def test_fibonacci(self):
        """Test Fibonacci sequence generation."""
        self.assertEqual(get_fib_from_table(1), 1)
        self.assertEqual(get_fib_from_table(5), 5)
        self.assertEqual(get_fib_from_table(10), 55)

    def test_user_creation(self):
        """Test user creation and retrieval."""
        pw = hash_password("testpass")
        uid = create_user("Test User", "testuser", "test@example.com", pw)
        user = get_user_by_username("testuser")
        self.assertEqual(user["id"], uid)
        self.assertEqual(user["full_name"], "Test User")
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["email"], "test@example.com")

    def test_status_validation(self):
        """Test status validation function."""
        self.assertTrue(validate_status("locked"))
        self.assertTrue(validate_status("unlocked"))
        self.assertTrue(validate_status("active"))
        self.assertTrue(validate_status("completed"))
        with self.assertRaises(ValueError):
            validate_status("pending")

    def test_prerequisite_management(self):
        """Test adding and checking prerequisites."""
        pw = hash_password("testpass")
        uid = create_user("Test User", "testuser", "test@example.com", pw)
        eid = create_ecology(uid, "Eco", status="unlocked")
        fid = create_forest(eid, "Forest", status="locked")
        tid = create_tree(fid, "Tree", status="locked")
        sbid = create_super_branch(tid, "Super", status="locked")
        bid = create_branch(sbid, "Branch", status="locked")
        sbb = create_sub_branch(bid, "SubBranch", status="unlocked")
        
        # Create leaves
        lid1 = insert_leaf(sbb, "Chapter 1", "Course", "C01", "2025-10-06T00:00:00", resource_type="book", status="unlocked")
        lid2 = insert_leaf(sbb, "Chapter 2", "Course", "C01", "2025-10-06T00:00:00", resource_type="book", status="locked")
        
        # Add prerequisite
        add_prerequisite("leaf", lid2, "leaf", lid1)
        
        # Check prerequisites
        prereqs = get_prerequisites("leaf", lid2)
        self.assertEqual(len(prereqs), 1)
        self.assertEqual(prereqs[0]["prerequisite_id"], lid1)
        self.assertEqual(prereqs[0]["prerequisite_type"], "leaf")
        self.assertEqual(prereqs[0]["name"], "Chapter 1")
        self.assertFalse(prereqs[0]["is_completed"])
        
        # Test prerequisite completion
        self.assertFalse(are_prerequisites_completed("leaf", lid2))
        
        # Mark prerequisite as completed
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE leaves SET status = 'completed' WHERE id = ?", (lid1,))
            c.execute("UPDATE prerequisites SET is_completed = 1 WHERE prerequisite_type = 'leaf' AND prerequisite_id = ?", (lid1,))
            conn.commit()
        
        self.assertTrue(are_prerequisites_completed("leaf", lid2))

    def test_status_transitions(self):
        """Test valid and invalid status transitions."""
        pw = hash_password("testpass")
        uid = create_user("Test User", "testuser", "test@example.com", pw)
        eid = create_ecology(uid, "Eco", status="unlocked")
        fid = create_forest(eid, "Forest", status="locked")
        tid = create_tree(fid, "Tree", status="locked")
        sbid = create_super_branch(tid, "Super", status="locked")
        bid = create_branch(sbid, "Branch", status="locked")
        sbb = create_sub_branch(bid, "SubBranch", status="unlocked")
        lid = insert_leaf(sbb, "Leaf", "Course", "C01", "2025-10-06T00:00:00", resource_type="book", status="unlocked")
        
        with get_conn() as conn:
            c = conn.cursor()
            # Valid transition: unlocked -> active
            c.execute("UPDATE leaves SET status = 'active' WHERE id = ?", (lid,))
            conn.commit()
            c.execute("SELECT status FROM leaves WHERE id = ?", (lid,))
            self.assertEqual(c.fetchone()["status"], "active")
            
            # Valid transition: active -> completed
            c.execute("UPDATE leaves SET status = 'completed' WHERE id = ?", (lid,))
            conn.commit()
            c.execute("SELECT status FROM leaves WHERE id = ?", (lid,))
            self.assertEqual(c.fetchone()["status"], "completed")
            
            # Invalid transition: completed -> unlocked (should be caught by set_status in cli)
            with self.assertRaises(sqlite3.Error):
                c.execute("UPDATE leaves SET status = 'unlocked' WHERE id = ?", (lid,))
                conn.commit()

if __name__ == "__main__":
    unittest.main()