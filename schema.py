-- Creating Users table with stricter constraints and optimized column types
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE CHECK (LENGTH(username) >= 3 AND LENGTH(username) <= 50),
    password_hash TEXT NOT NULL CHECK (LENGTH(password_hash) = 64), -- SHA-256 hash length
    available_minutes_per_day TEXT NOT NULL CHECK (json_valid(available_minutes_per_day) AND json_array_length(available_minutes_per_day) = 7),
    streak_days INTEGER NOT NULL DEFAULT 1 CHECK (streak_days >= 1),
    streak_multiplier REAL NOT NULL DEFAULT 1.0 CHECK (streak_multiplier BETWEEN 1.0 AND 3.5),
    learning_efficiency REAL NOT NULL DEFAULT 1.0 CHECK (learning_efficiency BETWEEN 0.4 AND 2.5),
    fatigue_threshold REAL NOT NULL DEFAULT 80.0 CHECK (fatigue_threshold BETWEEN 1.0 AND 100.0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Creating Nodes table with added understanding column and timestamps
CREATE TABLE Nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf')),
    name TEXT NOT NULL CHECK (LENGTH(name) >= 1 AND LENGTH(name) <= 100),
    course TEXT CHECK (LENGTH(course) <= 100),
    course_code TEXT CHECK (LENGTH(course_code) <= 20),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed')),
    importance REAL NOT NULL DEFAULT 50.0 CHECK (importance BETWEEN 1.0 AND 100.0),
    understanding REAL NOT NULL DEFAULT 50.0 CHECK (understanding BETWEEN 1.0 AND 100.0),
    difficulty REAL NOT NULL DEFAULT 50.0 CHECK (difficulty BETWEEN 1.0 AND 100.0),
    engagement REAL NOT NULL DEFAULT 50.0 CHECK (engagement BETWEEN 1.0 AND 100.0),
    fatigue REAL NOT NULL DEFAULT 50.0 CHECK (fatigue BETWEEN 1.0 AND 100.0),
    total_active_minutes INTEGER NOT NULL DEFAULT 0 CHECK (total_active_minutes >= 0),
    completion_ratio REAL NOT NULL DEFAULT 0.0 CHECK (completion_ratio BETWEEN 0.0 AND 1.0),
    fibonacci_index INTEGER NOT NULL CHECK (fibonacci_index >= 1),
    parent_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE SET NULL
);

-- Creating Waves table with stricter constraints
CREATE TABLE Waves (
    wave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_type TEXT NOT NULL CHECK (parent_type IN ('ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch')),
    parent_id INTEGER NOT NULL,
    wave_number INTEGER NOT NULL CHECK (wave_number >= 1),
    planned_units_count INTEGER NOT NULL CHECK (planned_units_count >= 0),
    actual_units_planted REAL NOT NULL CHECK (actual_units_planted >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Creating Reviews table with understanding column and stricter constraints
CREATE TABLE Reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN ('leaf', 'sub_branch', 'branch', 'super_branch', 'tree', 'forest', 'ecology')),
    scheduled_date TEXT NOT NULL CHECK (scheduled_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
    estimated_duration INTEGER NOT NULL CHECK (estimated_duration >= 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    focus_level REAL CHECK (focus_level BETWEEN 1.0 AND 100.0),
    engagement REAL CHECK (engagement BETWEEN 1.0 AND 100.0),
    fatigue REAL CHECK (fatigue BETWEEN 1.0 AND 100.0),
    understanding REAL CHECK (understanding BETWEEN 1.0 AND 100.0),
    completed_at TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Creating Schedules table with updated task_type options
CREATE TABLE Schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('study', 'break', 'leaf_review', 'integration')),
    start_time TEXT NOT NULL CHECK (start_time GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'),
    duration INTEGER NOT NULL CHECK (duration >= 0),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'completed')),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Creating Fibonacci table with larger values
CREATE TABLE Fibonacci (
    n INTEGER PRIMARY KEY,
    value BIGINT NOT NULL CHECK (value >= 0)
);

-- Creating indexes for performance
CREATE INDEX idx_users_username ON Users(username);
CREATE INDEX idx_nodes_user_id_type ON Nodes(user_id, node_type);
CREATE INDEX idx_nodes_parent_id ON Nodes(parent_id);
CREATE INDEX idx_reviews_node_id_type ON Reviews(node_id, node_type);
CREATE INDEX idx_reviews_scheduled_date_status ON Reviews(scheduled_date, status);
CREATE INDEX idx_schedules_user_id_task_id ON Schedules(user_id, task_id);
CREATE INDEX idx_waves_parent_id_type ON Waves(parent_id, parent_type);

-- Populating Fibonacci table (up to n=30 for robustness)
INSERT INTO Fibonacci (n, value) VALUES
(0, 0), (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13), (8, 21), (9, 34),
(10, 55), (11, 89), (12, 144), (13, 233), (14, 377), (15, 610), (16, 987), (17, 1597),
(18, 2584), (19, 4181), (20, 6765), (21, 10946), (22, 17711), (23, 28657), (24, 46368),
(25, 75025), (26, 121393), (27, 196418), (28, 317811), (29, 514229), (30, 832040);