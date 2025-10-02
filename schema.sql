-- User, settings, and core nodes
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    calendar_max_hours_per_day TEXT, -- JSON array of 7 ints
    -- ... other settings
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS leaves (
    id INTEGER PRIMARY KEY,
    sub_branch_id INTEGER,
    name TEXT NOT NULL,
    course_name TEXT,
    course_code TEXT,
    created_at DATETIME,
    study_date DATETIME,
    understanding_level REAL DEFAULT 0,
    study_duration_minutes INTEGER,
    base_time_minutes INTEGER DEFAULT 5,
    base_completion_days INTEGER DEFAULT 4,
    completion_days INTEGER,
    review_count INTEGER DEFAULT 0,
    fibonacci_index INTEGER DEFAULT 1,
    next_review_date DATETIME,
    review_estimated_duration_minutes INTEGER,
    importance REAL DEFAULT 0.5,
    difficulty INTEGER DEFAULT 3,
    status TEXT,
    size_target INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Add all other schema tables as needed for your hierarchy, reviews, schedules, etc.
