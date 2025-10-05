-- schema.sql for ecology.db
-- Enhanced SQLite3 schema for fully offline Learning Ecology System
-- Optimized for offline use with performance, integrity, and data consistency
-- Run with: sqlite3 ecology.db < schema.sql

-- PRAGMA settings optimized for offline single-user application
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -20000;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
PRAGMA optimize;

-- Users table: Stores user accounts with full profile information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash BLOB NOT NULL,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    is_deleted BOOLEAN DEFAULT FALSE,
    last_login DATETIME,
    CONSTRAINT chk_username_length CHECK (length(username) >= 3),
    CONSTRAINT chk_email_format CHECK (email LIKE '%@%')
);

-- Sessions table: Manages active user sessions with JWT tokens
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_token_length CHECK (length(token) > 10)
);

-- Password reset tokens table: Handles password reset functionality
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_token_expiry CHECK (expires_at > created_at)
);

-- Settings table: User-specific configuration, including weekly calendar hours as JSON
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    k_u REAL DEFAULT 0.2 CHECK (k_u BETWEEN 0 AND 1),
    k_d REAL DEFAULT 0.3 CHECK (k_d BETWEEN 0 AND 1),
    k_i REAL DEFAULT 0.3 CHECK (k_i BETWEEN 0 AND 1),
    S_ref INTEGER DEFAULT 30 CHECK (S_ref > 0),
    h_coeff_leaf REAL DEFAULT 1.0 CHECK (h_coeff_leaf > 0),
    h_coeff_sub_branch REAL DEFAULT 1.5 CHECK (h_coeff_sub_branch > 0),
    h_coeff_branch REAL DEFAULT 2.0 CHECK (h_coeff_branch > 0),
    h_coeff_super_branch REAL DEFAULT 2.5 CHECK (h_coeff_super_branch > 0),
    h_coeff_tree REAL DEFAULT 3.0 CHECK (h_coeff_tree > 0),
    h_coeff_forest REAL DEFAULT 3.5 CHECK (h_coeff_forest > 0),
    h_coeff_ecology REAL DEFAULT 4.0 CHECK (h_coeff_ecology > 0),
    a_u REAL DEFAULT 0.5 CHECK (a_u BETWEEN 0 AND 1),
    gamma REAL DEFAULT 0.2 CHECK (gamma BETWEEN 0 AND 1),
    R_decay_cap INTEGER DEFAULT 10 CHECK (R_decay_cap > 0),
    R_threshold REAL DEFAULT 0.7 CHECK (R_threshold BETWEEN 0 AND 1),
    calendar_max_hours_per_day TEXT DEFAULT '[8,8,8,8,8,8,8]' CHECK (json_valid(calendar_max_hours_per_day)),
    base_time_minutes INTEGER DEFAULT 30 CHECK (base_time_minutes > 0),
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Fibonacci sequence table: Pre-populated lookup for Fibonacci values (first 50 for long-term use)
CREATE TABLE IF NOT EXISTS fibonacci (
    fib_index INTEGER PRIMARY KEY CHECK (fib_index > 0),
    value INTEGER NOT NULL CHECK (value >= 0)
);

-- Insert Fibonacci sequence (unchanged)
INSERT OR IGNORE INTO fibonacci (fib_index, value) VALUES
(1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13), (8, 21), (9, 34), (10, 55),
(11, 89), (12, 144), (13, 233), (14, 377), (15, 610), (16, 987), (17, 1597), (18, 2584), (19, 4181), (20, 6765),
(21, 10946), (22, 17711), (23, 28657), (24, 46368), (25, 75025), (26, 121393), (27, 196418), (28, 317811), (29, 514229), (30, 832040),
(31, 1346269), (32, 2178309), (33, 3524578), (34, 5702887), (35, 9227465), (36, 14930352), (37, 24157817), (38, 39088169), (39, 63245986), (40, 102334155),
(41, 165580141), (42, 267914296), (43, 433494437), (44, 701408733), (45, 1134903170), (46, 1836311903), (47, 2971215073), (48, 4807526976), (49, 7778742049), (50, 12586269025);

-- Ecologies table: Top-level node (one per user) with comprehensive metadata
CREATE TABLE IF NOT EXISTS ecologies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0),
    next_forest_id INTEGER,  -- Added for chaining
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_forest_id) REFERENCES forests(id) ON DELETE SET NULL
);

-- Forests table
CREATE TABLE IF NOT EXISTS forests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ecology_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0),
    next_tree_id INTEGER,  -- Added for chaining
    FOREIGN KEY (ecology_id) REFERENCES ecologies(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_tree_id) REFERENCES trees(id) ON DELETE SET NULL
);

-- Trees table
CREATE TABLE IF NOT EXISTS trees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forest_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    next_tree_id INTEGER,  -- Added for chaining
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0),
    next_super_branch_id INTEGER,  -- Added for chaining
    FOREIGN KEY (forest_id) REFERENCES forests(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_tree_id) REFERENCES trees(id) ON DELETE SET NULL,
    FOREIGN KEY (next_super_branch_id) REFERENCES super_branches(id) ON DELETE SET NULL
);

-- Super Branches table
CREATE TABLE IF NOT EXISTS super_branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0),
    next_branch_id INTEGER,  -- Added for chaining
    FOREIGN KEY (tree_id) REFERENCES trees(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_branch_id) REFERENCES branches(id) ON DELETE SET NULL
);

-- Branches table
CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    super_branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0),
    next_sub_branch_id INTEGER,  -- Added for chaining
    FOREIGN KEY (super_branch_id) REFERENCES super_branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_sub_branch_id) REFERENCES sub_branches(id) ON DELETE SET NULL
);

-- Sub Branches table
CREATE TABLE IF NOT EXISTS sub_branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0),
    next_leaf_id INTEGER,  -- Already present for chaining leaves
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_leaf_id) REFERENCES leaves(id) ON DELETE SET NULL
);

-- Leaves table
CREATE TABLE leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sub_branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(name) > 0),
    course_name TEXT,
    course_code TEXT,
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    study_date DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    is_deleted BOOLEAN DEFAULT FALSE,
    understanding_level REAL CHECK (understanding_level BETWEEN 0 AND 1),
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    importance REAL CHECK (importance BETWEEN 0 AND 1),
    completion_days INTEGER CHECK (completion_days >= 0),
    fibonacci_index INTEGER CHECK (fibonacci_index >= 1),
    review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
    review_estimated_duration_minutes INTEGER CHECK (review_estimated_duration_minutes >= 0),
    next_review_date DATETIME,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    resource_type TEXT CHECK (resource_type IN ('book', 'video', 'text', 'quiz', 'exercise', 'other')),
    next_leaf_id INTEGER,
    base_time_minutes INTEGER CHECK (base_time_minutes > 0),
    study_duration_minutes INTEGER CHECK (study_duration_minutes > 0), base_completion_days INTEGER DEFAULT 3,
    FOREIGN KEY (sub_branch_id) REFERENCES sub_branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (next_leaf_id) REFERENCES leaves(id) ON DELETE SET NULL
);
CREATE TRIGGER trg_leaves_user_id
AFTER INSERT ON leaves
FOR EACH ROW
BEGIN
    UPDATE leaves SET user_id = (SELECT user_id FROM sub_branches WHERE id = NEW.sub_branch_id) WHERE id = NEW.id;
END;
CREATE INDEX idx_leaves_sub_branch_id ON leaves(sub_branch_id);
CREATE INDEX idx_leaves_user_id ON leaves(user_id);
CREATE INDEX idx_leaves_next_leaf_id ON leaves(next_leaf_id);
CREATE INDEX idx_leaves_next_review_date ON leaves(next_review_date);
CREATE INDEX idx_leaves_status ON leaves(status);
CREATE TRIGGER trg_validate_metadata_json_leaf_insert
BEFORE INSERT ON leaves
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;
CREATE TRIGGER trg_validate_metadata_json_leaf_update
BEFORE UPDATE ON leaves
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;
CREATE TABLE IF NOT EXISTS waves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    parent_type TEXT NOT NULL CHECK (parent_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch')),
    parent_id INTEGER NOT NULL,
    wave_number INTEGER NOT NULL CHECK (wave_number > 0),
    planned_units_count INTEGER NOT NULL CHECK (planned_units_count > 0),
    actual_units_planted INTEGER DEFAULT 0 CHECK (actual_units_planted >= 0),
    status TEXT DEFAULT 'ready' CHECK (status IN ('ready', 'active', 'completed', 'cancelled')),
    planned_start_date DATETIME,
    actual_start_date DATETIME,
    actual_end_date DATETIME,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_wave_dates CHECK (
        (actual_start_date IS NULL) OR 
        (actual_end_date IS NULL OR actual_end_date >= actual_start_date)
    )
);

-- Reviews table: Perpetual Fibonacci-based reviews for all nodes
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL CHECK (target_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf')),
    target_id INTEGER NOT NULL,
    fib_index INTEGER NOT NULL CHECK (fib_index > 0),
    scheduled_date DATETIME NOT NULL,
    performed_date DATETIME,
    understanding_after REAL CHECK (understanding_after BETWEEN 0 AND 1),
    estimated_duration INTEGER NOT NULL CHECK (estimated_duration > 0),
    actual_duration INTEGER CHECK (actual_duration IS NULL OR actual_duration >= 0),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled', 'skipped')),
    created_at DATETIME DEFAULT (datetime('now')),
    notes TEXT,
    is_integration_review BOOLEAN DEFAULT FALSE,
    CONSTRAINT chk_review_dates CHECK (
        (performed_date IS NULL) OR (performed_date >= scheduled_date)
    ),
    CONSTRAINT chk_duration_match CHECK (
        (status != 'completed') OR (actual_duration IS NOT NULL)
    )
);

-- Schedules table: Study and review sessions with priority and conflict handling
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('study', 'review')),
    related_type TEXT CHECK (related_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf')),
    related_id INTEGER,
    priority REAL DEFAULT 0.5 CHECK (priority BETWEEN 0 AND 1),
    status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'completed', 'cancelled', 'rescheduled')),
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_schedule_duration CHECK (end_datetime > start_datetime),
    CONSTRAINT chk_related_reference CHECK (
        (related_type IS NULL AND related_id IS NULL) OR 
        (related_type IS NOT NULL AND related_id IS NOT NULL)
    )
);

-- Notifications table: User notifications for conflicts, reminders, etc.
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL CHECK (length(message) > 0),
    type TEXT DEFAULT 'info' CHECK (type IN ('info', 'warning', 'error', 'success', 'reminder')),
    created_at DATETIME DEFAULT (datetime('now')),
    read BOOLEAN DEFAULT FALSE,
    expires_at DATETIME,
    related_type TEXT,
    related_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_expiry CHECK (expires_at IS NULL OR expires_at > created_at)
);

-- Sync queue table: Offline operation queue for synchronization
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN (
        'create_user', 'update_user', 'delete_user',
        'create_node', 'update_node', 'delete_node',
        'create_review', 'update_review', 'delete_review',
        'create_schedule', 'update_schedule', 'delete_schedule',
        'create_wave', 'update_wave', 'complete_wave',
        'create_notification', 'update_notification',
        'sync_settings', 'reset_password'
    )),
    target_type TEXT,
    target_id INTEGER,
    data TEXT NOT NULL CHECK (json_valid(data)),
    created_at DATETIME DEFAULT (datetime('now')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'synced', 'failed', 'conflicted')),
    retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0),
    last_error TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_retry_limit CHECK (retry_count <= 5)
);

-- Streaks Table
CREATE TABLE IF NOT EXISTS streaks (
    user_id INTEGER PRIMARY KEY,
    streak_start DATE,
    streak_end DATE,
    current_length INTEGER DEFAULT 0,
    longest_length INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Readiness Heatmap Table
CREATE TABLE IF NOT EXISTS daily_readiness (
    user_id INTEGER,
    date DATE,
    readiness_score REAL,
    PRIMARY KEY(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Wave relationships table for linking parent-child waves
CREATE TABLE IF NOT EXISTS wave_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_wave_id INTEGER NOT NULL,
    child_wave_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parent_wave_id) REFERENCES waves(id),
    FOREIGN KEY(child_wave_id) REFERENCES waves(id)
);

-- Triggers for user_id propagation
CREATE TRIGGER IF NOT EXISTS trg_forests_user_id
AFTER INSERT ON forests
FOR EACH ROW
BEGIN
    UPDATE forests SET user_id = (SELECT user_id FROM ecologies WHERE id = NEW.ecology_id) WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_trees_user_id
AFTER INSERT ON trees
FOR EACH ROW
BEGIN
    UPDATE trees SET user_id = (SELECT user_id FROM forests WHERE id = NEW.forest_id) WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_super_branches_user_id
AFTER INSERT ON super_branches
FOR EACH ROW
BEGIN
    UPDATE super_branches SET user_id = (SELECT user_id FROM trees WHERE id = NEW.tree_id) WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_branches_user_id
AFTER INSERT ON branches
FOR EACH ROW
BEGIN
    UPDATE branches SET user_id = (SELECT user_id FROM super_branches WHERE id = NEW.super_branch_id) WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_sub_branches_user_id
AFTER INSERT ON sub_branches
FOR EACH ROW
BEGIN
    UPDATE sub_branches SET user_id = (SELECT user_id FROM branches WHERE id = NEW.branch_id) WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_leaves_user_id
AFTER INSERT ON leaves
FOR EACH ROW
BEGIN
    UPDATE leaves SET user_id = (SELECT user_id FROM sub_branches WHERE id = NEW.sub_branch_id) WHERE id = NEW.id;
END;

-- Indexes for performance optimization in offline scenario
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_ecologies_user_id ON ecologies(user_id);
CREATE INDEX IF NOT EXISTS idx_forests_ecology_id ON forests(ecology_id);
CREATE INDEX IF NOT EXISTS idx_forests_user_id ON forests(user_id);
CREATE INDEX IF NOT EXISTS idx_forests_next_tree_id ON forests(next_tree_id);
CREATE INDEX IF NOT EXISTS idx_trees_forest_id ON trees(forest_id);
CREATE INDEX IF NOT EXISTS idx_trees_user_id ON trees(user_id);
CREATE INDEX IF NOT EXISTS idx_trees_next_super_branch_id ON trees(next_super_branch_id);
CREATE INDEX IF NOT EXISTS idx_super_branches_tree_id ON super_branches(tree_id);
CREATE INDEX IF NOT EXISTS idx_super_branches_user_id ON super_branches(user_id);
CREATE INDEX IF NOT EXISTS idx_super_branches_next_branch_id ON super_branches(next_branch_id);
CREATE INDEX IF NOT EXISTS idx_branches_super_branch_id ON branches(super_branch_id);
CREATE INDEX IF NOT EXISTS idx_branches_user_id ON branches(user_id);
CREATE INDEX IF NOT EXISTS idx_branches_next_sub_branch_id ON branches(next_sub_branch_id);
CREATE INDEX IF NOT EXISTS idx_sub_branches_branch_id ON sub_branches(branch_id);
CREATE INDEX IF NOT EXISTS idx_sub_branches_user_id ON sub_branches(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_branches_next_leaf_id ON sub_branches(next_leaf_id);
CREATE INDEX IF NOT EXISTS idx_leaves_sub_branch_id ON leaves(sub_branch_id);
CREATE INDEX IF NOT EXISTS idx_leaves_user_id ON leaves(user_id);
CREATE INDEX IF NOT EXISTS idx_leaves_next_leaf_id ON leaves(next_leaf_id);
CREATE INDEX IF NOT EXISTS idx_waves_user_id ON waves(user_id);
CREATE INDEX IF NOT EXISTS idx_waves_parent ON waves(parent_type, parent_id);
CREATE INDEX IF NOT EXISTS idx_waves_status ON waves(status);
CREATE INDEX IF NOT EXISTS idx_reviews_target ON reviews(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_reviews_scheduled_date ON reviews(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_start_datetime ON schedules(start_datetime);
CREATE INDEX IF NOT EXISTS idx_schedules_type ON schedules(type);
CREATE INDEX IF NOT EXISTS idx_schedules_status ON schedules(status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
CREATE INDEX IF NOT EXISTS idx_sync_queue_user_id ON sync_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status);
CREATE INDEX IF NOT EXISTS idx_sync_queue_operation ON sync_queue(operation);
CREATE INDEX IF NOT EXISTS idx_sync_queue_created_at ON sync_queue(created_at);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_reviews_target_scheduled ON reviews(target_type, target_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_schedules_user_datetime ON schedules(user_id, start_datetime, end_datetime);
CREATE INDEX IF NOT EXISTS idx_waves_parent_wave ON waves(parent_type, parent_id, wave_number);

CREATE INDEX IF NOT EXISTS idx_ecologies_next_review_date ON ecologies(next_review_date);
CREATE INDEX IF NOT EXISTS idx_forests_next_review_date ON forests(next_review_date);
CREATE INDEX IF NOT EXISTS idx_trees_next_review_date ON trees(next_review_date);
CREATE INDEX IF NOT EXISTS idx_super_branches_next_review_date ON super_branches(next_review_date);
CREATE INDEX IF NOT EXISTS idx_branches_next_review_date ON branches(next_review_date);
CREATE INDEX IF NOT EXISTS idx_sub_branches_next_review_date ON sub_branches(next_review_date);
CREATE INDEX IF NOT EXISTS idx_leaves_next_review_date ON leaves(next_review_date);

CREATE INDEX IF NOT EXISTS idx_ecologies_status ON ecologies(status);
CREATE INDEX IF NOT EXISTS idx_forests_status ON forests(status);
CREATE INDEX IF NOT EXISTS idx_trees_status ON trees(status);
CREATE INDEX IF NOT EXISTS idx_super_branches_status ON super_branches(status);
CREATE INDEX IF NOT EXISTS idx_branches_status ON branches(status);
CREATE INDEX IF NOT EXISTS idx_sub_branches_status ON sub_branches(status);
CREATE INDEX IF NOT EXISTS idx_leaves_status ON leaves(status);

-- Views for progress tracking and readiness
CREATE VIEW IF NOT EXISTS v_leaf_status AS
SELECT 
    l.id,
    l.sub_branch_id,
    l.name,
    l.resource_type,
    COUNT(r.id) AS total_scheduled_reviews,
    COUNT(CASE WHEN r.status = 'completed' THEN 1 END) AS completed_reviews,
    CASE 
        WHEN COUNT(r.id) > 0 THEN ROUND(CAST(COUNT(CASE WHEN r.status = 'completed' THEN 1 END) AS REAL) / COUNT(r.id), 4)
        ELSE 0 
    END AS completion_ratio,
    l.understanding_level,
    l.importance,
    l.difficulty,
    l.completion_days,
    l.status
FROM leaves l
LEFT JOIN reviews r ON r.target_type = 'leaf' AND r.target_id = l.id
WHERE l.is_deleted = FALSE
GROUP BY l.id;

CREATE VIEW IF NOT EXISTS v_sub_branch_progress AS
SELECT 
    sb.id,
    sb.branch_id,
    sb.name,
    COUNT(l.id) AS leaf_count,
    SUM(CASE WHEN l.status = 'completed' THEN 1 ELSE 0 END) AS completed_leaves,
    AVG(vls.completion_ratio) AS avg_completion_ratio,
    COALESCE(SUM(vls.completion_ratio * vls.importance * vls.difficulty) / NULLIF(SUM(vls.importance * vls.difficulty), 0), 0) AS weighted_readiness_score,
    COALESCE(SUM(vls.understanding_level * vls.importance * vls.difficulty) / NULLIF(SUM(vls.importance * vls.difficulty), 0), 0) AS weighted_understanding_level,
    sb.completion_days,
    sb.status,
    sb.importance,
    sb.difficulty
FROM sub_branches sb
LEFT JOIN leaves l ON l.sub_branch_id = sb.id AND l.is_deleted = FALSE
LEFT JOIN v_leaf_status vls ON vls.id = l.id
WHERE sb.is_deleted = FALSE
GROUP BY sb.id;

CREATE VIEW IF NOT EXISTS v_branch_progress AS
SELECT 
    b.id,
    b.super_branch_id,
    b.name,
    COUNT(sb.id) AS sub_branch_count,
    SUM(CASE WHEN sb.status = 'completed' THEN 1 ELSE 0 END) AS completed_sub_branches,
    AVG(vsbp.weighted_readiness_score) AS avg_readiness_score,
    COALESCE(SUM(vsbp.weighted_readiness_score * vsbp.importance * vsbp.difficulty) / NULLIF(SUM(vsbp.importance * vsbp.difficulty), 0), 0) AS weighted_readiness_score,
    b.completion_days,
    b.status,
    b.importance,
    b.difficulty
FROM branches b
LEFT JOIN sub_branches sb ON sb.branch_id = b.id AND sb.is_deleted = FALSE
LEFT JOIN v_sub_branch_progress vsbp ON vsbp.id = sb.id
WHERE b.is_deleted = FALSE
GROUP BY b.id;

CREATE VIEW IF NOT EXISTS v_super_branch_progress AS
SELECT 
    sb.id,
    sb.tree_id,
    sb.name,
    COUNT(b.id) AS branch_count,
    AVG(vbp.weighted_readiness_score) AS avg_readiness_score,
    COALESCE(SUM(vbp.weighted_readiness_score * vbp.importance * vbp.difficulty) / NULLIF(SUM(vbp.importance * vbp.difficulty), 0), 0) AS weighted_readiness_score,
    sb.completion_days,
    sb.status,
    sb.importance,
    sb.difficulty
FROM super_branches sb
LEFT JOIN branches b ON b.super_branch_id = sb.id AND b.is_deleted = FALSE
LEFT JOIN v_branch_progress vbp ON vbp.id = b.id
WHERE sb.is_deleted = FALSE
GROUP BY sb.id;

CREATE VIEW IF NOT EXISTS v_tree_progress AS
SELECT 
    t.id,
    t.forest_id,
    t.name,
    COUNT(sb.id) AS super_branch_count,
    AVG(vsbp.weighted_readiness_score) AS avg_readiness_score,
    COALESCE(SUM(vsbp.weighted_readiness_score * vsbp.importance * vsbp.difficulty) / NULLIF(SUM(vsbp.importance * vbp.difficulty), 0), 0) AS weighted_readiness_score,
    t.completion_days,
    t.status,
    t.importance,
    t.difficulty
FROM trees t
LEFT JOIN super_branches sb ON sb.tree_id = t.id AND sb.is_deleted = FALSE
LEFT JOIN v_super_branch_progress vsbp ON vsbp.id = sb.id
WHERE t.is_deleted = FALSE
GROUP BY t.id;

CREATE VIEW IF NOT EXISTS v_forest_progress AS
SELECT 
    f.id,
    f.ecology_id,
    f.name,
    COUNT(t.id) AS tree_count,
    AVG(vtp.weighted_readiness_score) AS avg_readiness_score,
    COALESCE(SUM(vtp.weighted_readiness_score * vtp.importance * vtp.difficulty) / NULLIF(SUM(vtp.importance * vtp.difficulty), 0), 0) AS weighted_readiness_score,
    f.completion_days,
    f.status,
    f.importance,
    f.difficulty
FROM forests f
LEFT JOIN trees t ON t.forest_id = f.id AND t.is_deleted = FALSE
LEFT JOIN v_tree_progress vtp ON vtp.id = t.id
WHERE f.is_deleted = FALSE
GROUP BY f.id;

CREATE VIEW IF NOT EXISTS v_ecology_progress AS
SELECT 
    e.id,
    e.user_id,
    e.name,
    COUNT(f.id) AS forest_count,
    AVG(vfp.weighted_readiness_score) AS avg_readiness_score,
    COALESCE(SUM(vfp.weighted_readiness_score * vfp.importance * vfp.difficulty) / NULLIF(SUM(vfp.importance * vfp.difficulty), 0), 0) AS weighted_readiness_score,
    e.completion_days,
    e.status,
    e.importance,
    e.difficulty
FROM ecologies e
LEFT JOIN forests f ON f.ecology_id = e.id AND f.is_deleted = FALSE
LEFT JOIN v_forest_progress vfp ON vfp.id = f.id
WHERE e.is_deleted = FALSE
GROUP BY e.id;

CREATE VIEW IF NOT EXISTS v_hierarchy_overview AS
SELECT 'ecology' AS node_type, id, NULL AS parent_id, user_id AS root_id, name, status, importance, difficulty, completion_days, weighted_readiness_score AS readiness_score FROM v_ecology_progress
UNION ALL
SELECT 'forest' AS node_type, id, ecology_id AS parent_id, ecology_id AS root_id, name, status, importance, difficulty, completion_days, weighted_readiness_score AS readiness_score FROM v_forest_progress
UNION ALL
SELECT 'tree' AS node_type, id, forest_id AS parent_id, forest_id AS root_id, name, status, importance, difficulty, completion_days, weighted_readiness_score AS readiness_score FROM v_tree_progress
UNION ALL
SELECT 'super_branch' AS node_type, id, tree_id AS parent_id, tree_id AS root_id, name, status, importance, difficulty, completion_days, weighted_readiness_score AS readiness_score FROM v_super_branch_progress
UNION ALL
SELECT 'branch' AS node_type, id, super_branch_id AS parent_id, super_branch_id AS root_id, name, status, importance, difficulty, completion_days, weighted_readiness_score AS readiness_score FROM v_branch_progress
UNION ALL
SELECT 'sub_branch' AS node_type, id, branch_id AS parent_id, branch_id AS root_id, name, status, importance, difficulty, completion_days, weighted_readiness_score AS readiness_score FROM v_sub_branch_progress
UNION ALL
SELECT 'leaf' AS node_type, id, sub_branch_id AS parent_id, sub_branch_id AS root_id, name, status, importance, difficulty, completion_days, completion_ratio AS readiness_score FROM v_leaf_status;

CREATE VIEW IF NOT EXISTS weekly_stats AS
SELECT
    strftime('%W', performed_date) AS week_number,
    COUNT(*) AS reviews_completed,
    AVG(understanding_after) AS avg_understanding,
    SUM(actual_duration) AS total_minutes
FROM reviews
WHERE status = 'completed'
GROUP BY week_number;

-- Triggers to maintain data integrity and timestamps
CREATE TRIGGER IF NOT EXISTS trg_update_users_updated_at
AFTER UPDATE ON users
FOR EACH ROW BEGIN
    UPDATE users SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_update_settings_updated_at
AFTER UPDATE ON settings
FOR EACH ROW BEGIN
    UPDATE settings SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_update_waves_updated_at
AFTER UPDATE ON waves
FOR EACH ROW BEGIN
    UPDATE waves SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_update_schedules_updated_at
AFTER UPDATE ON schedules
FOR EACH ROW BEGIN
    UPDATE schedules SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Auto-increment wave_number for new waves of same parent
CREATE TRIGGER IF NOT EXISTS trg_waves_auto_increment
BEFORE INSERT ON waves
FOR EACH ROW WHEN NEW.wave_number IS NULL
BEGIN
    UPDATE waves SET wave_number = (
        SELECT COALESCE(MAX(wave_number), 0) + 1
        FROM waves
        WHERE parent_type = NEW.parent_type AND parent_id = NEW.parent_id
    ) WHERE rowid = NEW.rowid;
END;

-- Validate JSON in metadata fields on insert/update
CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_ecology_insert
BEFORE INSERT ON ecologies
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_ecology_update
BEFORE UPDATE ON ecologies
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_forest_insert
BEFORE INSERT ON forests
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_forest_update
BEFORE UPDATE ON forests
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_tree_insert
BEFORE INSERT ON trees
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_tree_update
BEFORE UPDATE ON trees
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_super_branch_insert
BEFORE INSERT ON super_branches
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_super_branch_update
BEFORE UPDATE ON super_branches
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_branch_insert
BEFORE INSERT ON branches
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_branch_update
BEFORE UPDATE ON branches
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_sub_branch_insert
BEFORE INSERT ON sub_branches
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_sub_branch_update
BEFORE UPDATE ON sub_branches
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_leaf_insert
BEFORE INSERT ON leaves
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_validate_metadata_json_leaf_update
BEFORE UPDATE ON leaves
FOR EACH ROW WHEN NEW.metadata IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT json_valid(NEW.metadata) THEN RAISE(ABORT, 'Invalid JSON in metadata') END;
END;

-- Ensure only one ecology per user
CREATE TRIGGER IF NOT EXISTS trg_enforce_single_ecology
BEFORE INSERT ON ecologies
FOR EACH ROW WHEN EXISTS (SELECT 1 FROM ecologies WHERE user_id = NEW.user_id AND is_deleted = FALSE)
BEGIN
    SELECT RAISE(ABORT, 'User can only have one ecology');
END;

-- Initialize default settings for new users
CREATE TRIGGER IF NOT EXISTS trg_create_default_settings
AFTER INSERT ON users
FOR EACH ROW
BEGIN 
    INSERT INTO settings (user_id) VALUES (NEW.id);
END;

ALTER TABLE leaves ADD COLUMN base_completion_days INTEGER DEFAULT 3;


-- End of schema