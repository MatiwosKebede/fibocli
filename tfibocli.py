# test_cli.py
import pytest
import sqlite3
import os
import tempfile
import datetime
from click.testing import CliRunner
from cli import cli, require_user
from unittest.mock import patch

@pytest.fixture
def runner():
    """Fixture for Click CLI runner"""
    return CliRunner()

@pytest.fixture
def temp_db():
    """Fixture to create a temporary database and schema"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        db_path = os.path.join(tmpdirname, "fibocli.db")
        schema_path = os.path.join(tmpdirname, "schema.sql")
        with open(schema_path, "w") as f:
            f.write("""
CREATE TABLE Users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, available_minutes_per_day TEXT NOT NULL, streak_days INTEGER NOT NULL, streak_multiplier REAL NOT NULL, learning_efficiency REAL NOT NULL, fatigue_threshold REAL NOT NULL);
CREATE TABLE Sessions (session_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token TEXT NOT NULL, expiry TEXT NOT NULL);
CREATE TABLE Nodes (node_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, node_type TEXT NOT NULL, name TEXT NOT NULL, course TEXT, course_code TEXT, status TEXT NOT NULL, importance REAL NOT NULL, understanding REAL NOT NULL, difficulty REAL NOT NULL, engagement REAL NOT NULL, fatigue REAL NOT NULL, fibonacci_index INTEGER NOT NULL, parent_id INTEGER, total_active_minutes REAL DEFAULT 0);
CREATE TABLE Waves (wave_id INTEGER PRIMARY KEY AUTOINCREMENT, parent_type TEXT NOT NULL, parent_id INTEGER NOT NULL, wave_number INTEGER NOT NULL, planned_units_count INTEGER NOT NULL, actual_units_planted INTEGER NOT NULL);
CREATE TABLE Reviews (review_id INTEGER PRIMARY KEY AUTOINCREMENT, node_id INTEGER NOT NULL, node_type TEXT NOT NULL, scheduled_date TEXT NOT NULL, estimated_duration REAL NOT NULL, status TEXT NOT NULL, focus_level REAL, engagement REAL, fatigue REAL);
CREATE TABLE Schedules (schedule_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, task_id INTEGER NOT NULL, task_type TEXT NOT NULL, start_time TEXT NOT NULL, duration REAL NOT NULL, status TEXT NOT NULL);
CREATE TABLE Fibonacci (n INTEGER PRIMARY KEY, value INTEGER NOT NULL);
INSERT INTO Fibonacci (n, value) VALUES (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13), (8, 21), (9, 34), (10, 55);
            """)
        yield tmpdirname, db_path, schema_path
        # Cleanup is handled by TemporaryDirectory

@pytest.fixture
def setup_user(temp_db):
    """Fixture to set up a user and session"""
    tmpdirname, db_path, schema_path = temp_db
    runner = CliRunner()
    # Initialize database
    result = runner.invoke(cli, ["--no-warnings", "init"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    # Create user
    result = runner.invoke(cli, ["--no-warnings", "signup", "--username", "testuser", "--password", "testpass"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    # Login
    result = runner.invoke(cli, ["--no-warnings", "login", "--username", "testuser", "--password", "testpass"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    yield tmpdirname, db_path

def test_init_success(temp_db, runner):
    """Test database initialization"""
    tmpdirname, db_path, _ = temp_db
    result = runner.invoke(cli, ["--no-warnings", "init"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Database initialized successfully" in result.output
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
    assert cursor.fetchone() is not None
    conn.close()

def test_init_overwrite(temp_db, runner):
    """Test database initialization with overwrite"""
    tmpdirname, db_path, _ = temp_db
    # First initialization
    result = runner.invoke(cli, ["--no-warnings", "init"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    # Add a user
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Users (username, password_hash, available_minutes_per_day, streak_days, streak_multiplier, learning_efficiency, fatigue_threshold) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("testuser", hashlib.sha256("testpass".encode()).hexdigest(), json.dumps([120]*7), 1, 1.0, 1.0, 80))
    conn.commit()
    conn.close()
    # Overwrite
    result = runner.invoke(cli, ["--no-warnings", "init", "--overwrite"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Database initialized successfully" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Users")
    assert cursor.fetchone()[0] == 0
    conn.close()

def test_init_no_schema(temp_db, runner):
    """Test initialization when schema.sql is missing"""
    tmpdirname, db_path, schema_path = temp_db
    os.remove(schema_path)
    result = runner.invoke(cli, ["--no-warnings", "init"], env={"HOME": tmpdirname})
    assert result.exit_code != 0
    assert "schema.sql file not found" in result.output

def test_signup_success(temp_db, runner):
    """Test successful user signup"""
    tmpdirname, db_path, _ = temp_db
    result = runner.invoke(cli, ["--no-warnings", "init"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--no-warnings", "signup", "--username", "testuser", "--password", "testpass"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Created user ID=1 (testuser)" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT username, streak_days, learning_efficiency, fatigue_threshold FROM Users WHERE user_id = 1")
    user = cursor.fetchone()
    assert user == ("testuser", 1, 1.0, 80)
    conn.close()

def test_signup_duplicate_username(temp_db, runner):
    """Test signup with duplicate username"""
    tmpdirname, db_path, _ = temp_db
    result = runner.invoke(cli, ["--no-warnings", "init"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--no-warnings", "signup", "--username", "testuser", "--password", "testpass"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--no-warnings", "signup", "--username", "testuser", "--password", "testpass2"], env={"HOME": tmpdirname})
    assert result.exit_code != 0
    assert "Username 'testuser' already exists" in result.output

def test_signup_no_db(runner):
    """Test signup without initialized database"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        result = runner.invoke(cli, ["--no-warnings", "signup", "--username", "testuser", "--password", "testpass"], env={"HOME": tmpdirname})
        assert result.exit_code != 0
        assert "Database not found" in result.output

def test_login_success(setup_user, runner):
    """Test successful login"""
    tmpdirname, db_path = setup_user
    result = runner.invoke(cli, ["--no-warnings", "login", "--username", "testuser", "--password", "testpass"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Logged in and session saved" in result.output
    assert os.path.exists(os.path.join(tmpdirname, ".fibocli_session"))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Sessions WHERE user_id = 1")
    assert cursor.fetchone()[0] == 1
    conn.close()

def test_login_invalid_credentials(setup_user, runner):
    """Test login with invalid credentials"""
    tmpdirname, _ = setup_user
    result = runner.invoke(cli, ["--no-warnings", "login", "--username", "testuser", "--password", "wrongpass"], env={"HOME": tmpdirname})
    assert result.exit_code != 0
    assert "Invalid credentials" in result.output

def test_logout_success(setup_user, runner):
    """Test successful logout"""
    tmpdirname, _ = setup_user
    result = runner.invoke(cli, ["--no-warnings", "logout"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Local session cleared" in result.output
    with open(os.path.join(tmpdirname, ".fibocli_session"), "r") as f:
        assert f.read().strip() == ""

def test_logout_no_session(temp_db, runner):
    """Test logout with no session file"""
    tmpdirname, _, _ = temp_db
    result = runner.invoke(cli, ["--no-warnings", "logout"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "No session file found" in result.output

def test_whoami_success(setup_user, runner):
    """Test whoami command"""
    tmpdirname, _ = setup_user
    result = runner.invoke(cli, ["--no-warnings", "whoami"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "User: testuser, Streak Days: 1, Learning Efficiency: 1.0" in result.output

def test_whoami_no_session(temp_db, runner):
    """Test whoami without session"""
    tmpdirname, _, _ = temp_db
    result = runner.invoke(cli, ["--no-warnings", "whoami"], env={"HOME": tmpdirname})
    assert result.exit_code != 0
    assert "No session found" in result.output

def test_create_ecology_success(setup_user, runner):
    """Test creating an ecology"""
    tmpdirname, db_path = setup_user
    result = runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies", "--course", "Computer Science", "--course-code", "CS101"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Ecology created ID=1 (CS Studies)" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT node_type, name, course, course_code, status, fibonacci_index FROM Nodes WHERE node_id = 1")
    assert cursor.fetchone() == ("ecology", "CS Studies", "Computer Science", "CS101", "pending", 1)
    conn.close()

def test_create_leaf_success(setup_user, runner):
    """Test creating a leaf with hierarchy"""
    tmpdirname, db_path = setup_user
    # Create hierarchy
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    result = runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm", "--importance", "80", "--difficulty", "60", "--understanding", "50"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Leaf created ID=7 (Bubble Sort Algorithm, Importance=80, Difficulty=60, Understanding=50)" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT node_type, name, importance, difficulty, understanding, parent_id FROM Nodes WHERE node_id = 7")
    assert cursor.fetchone() == ("leaf", "Bubble Sort Algorithm", 80, 60, 50, 6)
    conn.close()

def test_create_leaf_invalid_metrics(setup_user, runner):
    """Test creating a leaf with invalid metrics"""
    tmpdirname, _ = setup_user
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    result = runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm", "--importance", "150"], env={"HOME": tmpdirname})
    assert result.exit_code != 0
    assert "Importance, difficulty, and understanding must be between 1 and 100" in result.output

@patch('cli.Prompt.ask')
def test_study_success(mock_prompt, setup_user, runner):
    """Test successful study session"""
    tmpdirname, db_path = setup_user
    # Create hierarchy
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm", "--importance", "80", "--difficulty", "60", "--understanding", "50"], env={"HOME": tmpdirname})
    mock_prompt.return_value = "leaf"
    result = runner.invoke(cli, ["--no-warnings", "study", "--node-id", "7", "--engagement", "85", "--fatigue", "40", "--duration", "30", "--focus", "90", "--understanding", "70"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Recorded study session for leaf ID=7" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT engagement, fatigue, estimated_duration, status, focus_level FROM Reviews WHERE node_id = 7 AND node_type = 'leaf'")
    review = cursor.fetchone()
    assert review == (85, 40, 30, "completed", 90)
    cursor.execute("SELECT status, total_active_minutes, understanding FROM Nodes WHERE node_id = 7")
    node = cursor.fetchone()
    assert node[0] == "active"
    assert node[1] == 30
    assert node[2] == 70
    conn.close()

def test_study_invalid_metrics(setup_user, runner):
    """Test study with invalid metrics"""
    tmpdirname, _ = setup_user
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm"], env={"HOME": tmpdirname})
    result = runner.invoke(cli, ["--no-warnings", "study", "--node-type", "leaf", "--node-id", "7", "--engagement", "150", "--fatigue", "40", "--duration", "30"], env={"HOME": tmpdirname})
    assert result.exit_code != 0
    assert "Metrics must be between 1 and 100" in result.output

@patch('cli.Prompt.ask')
@patch('cli.IntPrompt.ask')
def test_prioritize_study_success(mock_int_prompt, mock_prompt, setup_user, runner):
    """Test prioritize_study command"""
    tmpdirname, db_path = setup_user
    # Create hierarchy
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm", "--importance", "80", "--difficulty", "60", "--understanding", "50"], env={"HOME": tmpdirname})
    mock_prompt.return_value = "leaf"
    mock_int_prompt.return_value = 7
    result = runner.invoke(cli, ["--no-warnings", "prioritize-study", "--engagement", "85", "--fatigue", "40", "--duration", "60", "--time-preference", "morning"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Prioritized Study Schedule" in result.output
    assert "Bubble Sort Algorithm" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Schedules WHERE user_id = 1 AND task_type = 'study'")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT status FROM Nodes WHERE node_id = 7")
    assert cursor.fetchone()[0] == "active"
    conn.close()

def test_prioritize_study_no_tasks(setup_user, runner):
    """Test prioritize_study with no tasks"""
    tmpdirname, _ = setup_user
    result = runner.invoke(cli, ["--no-warnings", "prioritize-study", "--engagement", "85", "--fatigue", "40", "--duration", "60"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "No pending or active study tasks found" in result.output

def test_update_learning_efficiency(setup_user, runner):
    """Test update_learning_efficiency command"""
    tmpdirname, db_path = setup_user
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET streak_days = 5 WHERE user_id = 1")
    conn.commit()
    conn.close()
    result = runner.invoke(cli, ["--no-warnings", "update-learning-efficiency"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Updated learning efficiency to 2.00" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT learning_efficiency FROM Users WHERE user_id = 1")
    assert cursor.fetchone()[0] == 2.0
    conn.close()

def test_adjust_difficulty_no_reviews(setup_user, runner):
    """Test adjust_difficulty with no reviews"""
    tmpdirname, _ = setup_user
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm"], env={"HOME": tmpdirname})
    result = runner.invoke(cli, ["--no-warnings", "adjust-difficulty", "--node-id", "7", "--node-type", "leaf"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "No recent reviews to compute trend" in result.output

def test_schedule_reviews_success(setup_user, runner):
    """Test schedule_reviews command"""
    tmpdirname, db_path = setup_user
    runner.invoke(cli, ["--no-warnings", "create", "ecology", "--name", "CS Studies"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "forest", "--ecology-id", "1", "--name", "Algorithms"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "tree", "--forest-id", "2", "--name", "Sorting"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "super", "--tree-id", "3", "--name", "Comparison Sorts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "branch", "--super-id", "4", "--name", "Bubble Sort"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "subbranch", "--branch-id", "5", "--name", "Basic Concepts"], env={"HOME": tmpdirname})
    runner.invoke(cli, ["--no-warnings", "create", "leaf", "--subbranch-id", "6", "--name", "Bubble Sort Algorithm"], env={"HOME": tmpdirname})
    result = runner.invoke(cli, ["--no-warnings", "schedule-reviews"], env={"HOME": tmpdirname})
    assert result.exit_code == 0
    assert "Scheduled reviews for 1 nodes" in result.output
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Reviews WHERE node_id = 7 AND node_type = 'leaf' AND status = 'pending'")
    assert cursor.fetchone()[0] == 1
    conn.close()
