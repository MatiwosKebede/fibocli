# tests.py
import unittest
from db import init_db, get_conn
from models import create_user, get_user_by_username
from utils import hash_password
from algorithms import get_fib_from_table

class TestEcologySystem(unittest.TestCase):
    def setUp(self):
        init_db(overwrite=True)

    def test_fibonacci(self):
        self.assertEqual(get_fib_from_table(1), 1)
        self.assertEqual(get_fib_from_table(5), 5)
        self.assertEqual(get_fib_from_table(10), 55)

    def test_user_creation(self):
        pw = hash_password("testpass")
        uid = create_user("Test User", "testuser", "test@example.com", pw)
        user = get_user_by_username("testuser")
        self.assertEqual(user["id"], uid)
        self.assertEqual(user["full_name"], "Test User")

if __name__ == "__main__":
    unittest.main()
