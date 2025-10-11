-- Creating Users table
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    available_minutes_per_day JSON NOT NULL CHECK (json_valid(available_minutes_per_day)),
    streak_days INTEGER NOT NULL DEFAULT 1 CHECK (streak_days >= 1),
    streak_multiplier FLOAT NOT NULL DEFAULT 1.0 CHECK (streak_multiplier BETWEEN 1.0 AND 3.5),
    learning_efficiency FLOAT NOT NULL DEFAULT 1.0 CHECK (learning_efficiency BETWEEN 0.4 AND 2.5),
    fatigue_threshold FLOAT NOT NULL DEFAULT 80 CHECK (fatigue_threshold BETWEEN 1 AND 100)
);

-- Creating Sessions table
CREATE TABLE Sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL,
    expiry TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Creating Nodes table
CREATE TABLE Nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    node_type TEXT CHECK (node_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf')) NOT NULL,
    name VARCHAR(100) NOT NULL,
    course VARCHAR(100),
    course_code VARCHAR(20),
    status TEXT CHECK (status IN ('pending', 'active', 'completed')) NOT NULL DEFAULT 'pending',
    importance FLOAT NOT NULL DEFAULT 50 CHECK (importance BETWEEN 1 AND 100),
    understanding FLOAT NOT NULL DEFAULT 50 CHECK (understanding BETWEEN 1 AND 100),
    difficulty FLOAT NOT NULL DEFAULT 50 CHECK (difficulty BETWEEN 1 AND 100),
    engagement FLOAT NOT NULL DEFAULT 50 CHECK (engagement BETWEEN 1 AND 100),
    fatigue FLOAT NOT NULL DEFAULT 50 CHECK (fatigue BETWEEN 1 AND 100),
    total_active_minutes INTEGER NOT NULL DEFAULT 0 CHECK (total_active_minutes >= 0),
    completion_ratio FLOAT NOT NULL DEFAULT 0 CHECK (completion_ratio BETWEEN 0 AND 1),
    fibonacci_index INTEGER,
    parent_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE SET NULL
);

-- Creating Waves table
CREATE TABLE Waves (
    wave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_type TEXT CHECK (parent_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch')) NOT NULL,
    parent_id INTEGER NOT NULL,
    wave_number INTEGER NOT NULL CHECK (wave_number >= 1),
    planned_units_count INTEGER NOT NULL CHECK (planned_units_count >= 0),
    actual_units_planted INTEGER NOT NULL CHECK (actual_units_planted >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Creating Reviews table
CREATE TABLE Reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    node_type TEXT CHECK (node_type IN ('leaf', 'sub_branch', 'branch', 'super_branch', 'tree', 'forest', 'ecology')) NOT NULL,
    scheduled_date DATE NOT NULL,
    estimated_duration INTEGER NOT NULL CHECK (estimated_duration >= 0),
    status TEXT CHECK (status IN ('pending', 'completed')) NOT NULL DEFAULT 'pending',
    focus_level FLOAT CHECK (focus_level BETWEEN 1 AND 100),
    engagement FLOAT CHECK (engagement BETWEEN 1 AND 100),
    fatigue FLOAT CHECK (fatigue BETWEEN 1 AND 100),
    completed_at TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Creating Schedules table
CREATE TABLE Schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    task_type TEXT CHECK (task_type IN ('study', 'leaf_review', 'integration')) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    duration INTEGER NOT NULL CHECK (duration >= 0),
    status TEXT CHECK (status IN ('planned', 'completed')) NOT NULL DEFAULT 'planned',
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Creating Fibonacci table
CREATE TABLE Fibonacci (
    n INTEGER PRIMARY KEY,
    value BIGINT NOT NULL CHECK (value >= 0)
);

-- Creating indexes for performance
CREATE INDEX idx_nodes_node_type_parent_id ON Nodes(node_type, parent_id);
CREATE INDEX idx_reviews_scheduled_date_status ON Reviews(scheduled_date, status);
CREATE INDEX idx_schedules_start_time_user_id ON Schedules(start_time, user_id);

-- Populating Fibonacci table (up to n=20 for brevity, extend to n=100 as needed)
INSERT INTO Fibonacci (n, value) VALUES
(0, 0), (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13), (8, 21), (9, 34),
(10, 55), (11, 89), (12, 144), (13, 233), (14, 377), (15, 610), (16, 987), (17, 1597),
(18, 2584), (19, 4181), (20, 6765);
