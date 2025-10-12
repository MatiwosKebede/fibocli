-- FIBOCLI Enhanced Schema v3.0 - Complete Feature Integration
-- Includes: Gamification, Auto-Streaker, Auto-Duration, Hierarchical Restrictions, 
-- Dynamic Difficulty, Fatigue Management, Session Control, Notifications, and more

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Enhanced Users table with gamification and advanced features
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT,
    available_minutes_per_day TEXT DEFAULT '[120,120,120,120,120,90,60]',
    points INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    streak_multiplier REAL DEFAULT 1.0,
    last_study_date TEXT,
    learning_efficiency REAL DEFAULT 1.0,
    fatigue_threshold REAL DEFAULT 75.0,
    timezone TEXT DEFAULT 'UTC',
    
    -- Gamification fields
    daily_goal_minutes INTEGER DEFAULT 120,
    total_study_minutes INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    total_points_earned INTEGER DEFAULT 0,
    
    -- Auto-streaker fields
    longest_streak INTEGER DEFAULT 0,
    streak_updated_at TEXT,
    
    -- Learning analytics
    average_efficiency REAL DEFAULT 1.0,
    total_sessions_completed INTEGER DEFAULT 0,
    preferred_study_time TEXT DEFAULT 'morning',
    
    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- User availability with timezone support
CREATE TABLE IF NOT EXISTS UserAvailability (
    availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    minutes INTEGER NOT NULL CHECK (minutes >= 0),
    preferred_start_time TEXT, -- HH:MM format
    preferred_end_time TEXT,   -- HH:MM format
    timezone TEXT DEFAULT 'UTC',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, day_of_week)
);

-- Enhanced Sessions with device tracking
CREATE TABLE IF NOT EXISTS Sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expiry TEXT NOT NULL,
    device_info TEXT DEFAULT 'unknown',
    ip_address TEXT,
    last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Enhanced Achievements with categories and progression
CREATE TABLE IF NOT EXISTS Achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    points INTEGER NOT NULL,
    icon TEXT,
    category TEXT CHECK (category IN ('streak', 'study', 'mastery', 'consistency', 'speed', 'exploration', 'completion')),
    tier INTEGER DEFAULT 1 CHECK (tier BETWEEN 1 AND 5),
    progress_current INTEGER DEFAULT 0,
    progress_target INTEGER DEFAULT 1,
    unlocked_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

-- Enhanced Nodes with hierarchical restrictions and auto-duration
CREATE TABLE IF NOT EXISTS Nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN (
        'ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf'
    )),
    name TEXT NOT NULL,
    description TEXT,
    course TEXT,
    course_code TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'active', 'completed', 'paused', 'archived', 'review', 'locked'
    )),
    
    -- Core metrics
    importance REAL DEFAULT 50.0 CHECK (importance BETWEEN 1 AND 100),
    understanding REAL DEFAULT 50.0 CHECK (understanding BETWEEN 1 AND 100),
    difficulty REAL DEFAULT 50.0 CHECK (difficulty BETWEEN 1 AND 100),
    engagement REAL DEFAULT 50.0 CHECK (engagement BETWEEN 1 AND 100),
    fatigue REAL DEFAULT 50.0 CHECK (fatigue BETWEEN 1 AND 100),
    
    -- Advanced scheduling
    priority_score REAL DEFAULT 0.0,
    fibonacci_index INTEGER DEFAULT 1,
    parent_id INTEGER,
    total_active_minutes REAL DEFAULT 0.0,
    duration_days INTEGER,
    
    -- Hierarchical restrictions
    prerequisites TEXT DEFAULT '[]', -- JSON array of required node_ids
    required_completion REAL DEFAULT 0.0 CHECK (required_completion BETWEEN 0 AND 1),
    unlock_conditions TEXT DEFAULT '{}', -- JSON conditions for unlocking
    
    -- Auto-duration settings
    auto_duration_enabled BOOLEAN DEFAULT 1,
    min_duration INTEGER DEFAULT 15 CHECK (min_duration >= 5),
    max_duration INTEGER DEFAULT 90 CHECK (max_duration <= 240),
    estimated_duration INTEGER DEFAULT 30,
    
    -- Gamification
    points_value INTEGER DEFAULT 10,
    experience_value INTEGER DEFAULT 5,
    
    -- Organization
    child_order INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]', -- JSON array of tags
    metadata TEXT DEFAULT '{}', -- JSON for additional data
    
    -- Timestamps
    last_reviewed_at TEXT,
    completed_at TEXT,
    activated_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    CHECK (parent_id IS NULL OR node_type != 'ecology')
);

-- Enhanced Waves with progress tracking
CREATE TABLE IF NOT EXISTS Waves (
    wave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_type TEXT NOT NULL,
    parent_id INTEGER NOT NULL,
    wave_number INTEGER NOT NULL,
    planned_units_count INTEGER NOT NULL CHECK (planned_units_count >= 0),
    actual_units_planted INTEGER NOT NULL CHECK (actual_units_planted >= 0),
    status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'planting', 'completed', 'paused', 'cancelled')),
    progress REAL DEFAULT 0.0 CHECK (progress BETWEEN 0 AND 1),
    efficiency_score REAL,
    planted_at TEXT,
    completed_at TEXT,
    scheduled_end_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Enhanced Reviews with forecasting and pause/resume
CREATE TABLE IF NOT EXISTS Reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    node_type TEXT NOT NULL,
    scheduled_date TEXT NOT NULL,
    
    -- Duration tracking
    estimated_duration REAL CHECK (estimated_duration > 0),
    actual_duration REAL CHECK (actual_duration > 0),
    paused_duration REAL DEFAULT 0,
    
    -- Session metrics
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'completed', 'skipped', 'rescheduled', 'paused', 'in_progress'
    )),
    focus_level REAL CHECK (focus_level BETWEEN 1 AND 100),
    engagement REAL CHECK (engagement BETWEEN 1 AND 100),
    fatigue REAL CHECK (fatigue BETWEEN 1 AND 100),
    performance_score REAL CHECK (performance_score BETWEEN 0 AND 1),
    
    -- Forecasting and scheduling
    next_review_date TEXT,
    forecast_accuracy REAL,
    interval_days INTEGER,
    ease_factor REAL DEFAULT 2.5 CHECK (ease_factor >= 1.3),
    
    -- Session control
    completed_at TEXT,
    paused_at TEXT,
    resumed_at TEXT,
    started_at TEXT,
    
    -- Notes and metadata
    notes TEXT,
    session_quality INTEGER CHECK (session_quality BETWEEN 1 AND 5),
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Enhanced Schedules with flexible scheduling
CREATE TABLE IF NOT EXISTS Schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('study', 'break', 'review', 'wave_planting', 'maintenance')),
    start_time TEXT NOT NULL,
    duration REAL NOT NULL CHECK (duration > 0),
    
    -- Flexible scheduling
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN (
        'planned', 'active', 'completed', 'cancelled', 'paused', 'rescheduled'
    )),
    priority REAL DEFAULT 0.0,
    flexible_window INTEGER DEFAULT 15, -- minutes of flexibility
    timezone TEXT,
    can_reschedule BOOLEAN DEFAULT 1,
    
    -- Completion tracking
    completed_at TEXT,
    actual_start_time TEXT,
    actual_duration REAL,
    
    -- Metadata
    recurrence_pattern TEXT, -- JSON for recurring schedules
    notes TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Enhanced Study Sessions with pause/resume support
CREATE TABLE IF NOT EXISTS StudySessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Timing
    start_time TEXT NOT NULL,
    end_time TEXT,
    planned_duration REAL NOT NULL,
    actual_duration REAL DEFAULT 0,
    paused_duration REAL DEFAULT 0,
    
    -- Session metrics
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'abandoned')),
    focus_score REAL CHECK (focus_score BETWEEN 0 AND 1),
    efficiency_score REAL CHECK (efficiency_score BETWEEN 0 AND 1),
    satisfaction_score INTEGER CHECK (satisfaction_score BETWEEN 1 AND 5),
    
    -- Fatigue tracking
    fatigue_start REAL CHECK (fatigue_start BETWEEN 1 AND 100),
    fatigue_end REAL CHECK (fatigue_end BETWEEN 1 AND 100),
    fatigue_change REAL GENERATED ALWAYS AS (fatigue_end - fatigue_start) VIRTUAL,
    
    -- Gamification
    points_earned INTEGER DEFAULT 0,
    experience_earned INTEGER DEFAULT 0,
    
    -- Session details
    nodes_completed INTEGER DEFAULT 0,
    total_breaks INTEGER DEFAULT 0,
    device_used TEXT DEFAULT 'unknown',
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Enhanced Study Analytics with timezone support
CREATE TABLE IF NOT EXISTS StudyAnalytics (
    analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_id INTEGER,
    session_id INTEGER,
    
    -- Core metrics
    duration_minutes REAL NOT NULL CHECK (duration_minutes > 0),
    focus_score REAL CHECK (focus_score BETWEEN 0 AND 1),
    efficiency_score REAL CHECK (efficiency_score BETWEEN 0 AND 1),
    understanding_gain REAL, -- Change in understanding
    
    -- Time tracking
    completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    timezone TEXT,
    local_completed_time TEXT, -- Local time for user's timezone
    
    -- Performance metrics
    estimated_vs_actual REAL, -- Ratio of estimated vs actual duration
    pace_score REAL, -- How well pace was maintained
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES StudySessions(session_id) ON DELETE SET NULL
);

-- Fibonacci sequence for spaced repetition
CREATE TABLE IF NOT EXISTS Fibonacci (
    n INTEGER PRIMARY KEY CHECK (n >= 0),
    value INTEGER NOT NULL CHECK (value >= 0)
);

-- Learning Objectives with progress tracking
CREATE TABLE IF NOT EXISTS LearningObjectives (
    objective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    target_date TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'paused')),
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    progress REAL DEFAULT 0.0 CHECK (progress BETWEEN 0 AND 1),
    related_nodes TEXT DEFAULT '[]', -- JSON array of node_ids
    milestones TEXT DEFAULT '[]', -- JSON array of milestone objects
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Enhanced Notifications system
CREATE TABLE IF NOT EXISTS Notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('reminder', 'achievement', 'streak', 'review', 'goal', 'system', 'motivational')),
    is_read BOOLEAN DEFAULT 0,
    is_actionable BOOLEAN DEFAULT 0,
    action_url TEXT, -- URL or command for actionable notifications
    scheduled_time TEXT,
    expires_at TEXT,
    metadata TEXT DEFAULT '{}', -- JSON for additional data
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Data Export/Import tracking
CREATE TABLE IF NOT EXISTS Exports (
    export_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    export_type TEXT NOT NULL CHECK (export_type IN ('backup', 'analytics', 'hierarchy', 'full')),
    file_path TEXT NOT NULL,
    file_size INTEGER,
    includes_attachments BOOLEAN DEFAULT 0,
    encryption_key_hash TEXT, -- For encrypted exports
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Difficulty adjustment history
CREATE TABLE IF NOT EXISTS DifficultyHistory (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    old_difficulty REAL,
    new_difficulty REAL,
    adjustment_type TEXT CHECK (adjustment_type IN ('auto', 'manual', 'performance', 'fatigue')),
    reason TEXT,
    performance_data TEXT DEFAULT '{}', -- JSON of performance metrics used for adjustment
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- Fatigue patterns and recommendations
CREATE TABLE IF NOT EXISTS FatiguePatterns (
    pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6),
    hour_of_day INTEGER CHECK (hour_of_day BETWEEN 0 AND 23),
    average_fatigue REAL,
    study_efficiency REAL,
    recommended_max_duration INTEGER,
    sample_size INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, day_of_week, hour_of_day)
);

-- Study breaks tracking
CREATE TABLE IF NOT EXISTS StudyBreaks (
    break_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_minutes REAL,
    break_type TEXT CHECK (break_type IN ('short', 'long', 'meal', 'exercise', 'planned')),
    activities TEXT DEFAULT '[]', -- JSON array of break activities
    effectiveness_score INTEGER CHECK (effectiveness_score BETWEEN 1 AND 5),
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES StudySessions(session_id) ON DELETE SET NULL
);

-- Learning efficiency history
CREATE TABLE IF NOT EXISTS EfficiencyHistory (
    efficiency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    efficiency_score REAL NOT NULL,
    factors TEXT DEFAULT '{}', -- JSON of factors affecting efficiency
    recorded_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, recorded_date)
);

-- Node relationships for advanced hierarchy
CREATE TABLE IF NOT EXISTS NodeRelationships (
    relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    parent_node_id INTEGER NOT NULL,
    child_node_id INTEGER NOT NULL,
    relationship_type TEXT CHECK (relationship_type IN ('prerequisite', 'corequisite', 'recommended', 'alternative')),
    strength REAL DEFAULT 1.0 CHECK (strength BETWEEN 0 AND 1),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (child_node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    UNIQUE (parent_node_id, child_node_id, relationship_type)
);

-- Study goals and targets
CREATE TABLE IF NOT EXISTS StudyGoals (
    goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    goal_type TEXT CHECK (goal_type IN ('daily', 'weekly', 'monthly', 'node_completion', 'understanding', 'streak')),
    target_value REAL NOT NULL,
    current_value REAL DEFAULT 0,
    unit TEXT DEFAULT 'minutes',
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'cancelled')),
    reward_points INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- =====================================================================
-- INDEXES for Performance Optimization
-- =====================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON Users(username);
CREATE INDEX IF NOT EXISTS idx_users_streak ON Users(streak_days);
CREATE INDEX IF NOT EXISTS idx_users_level ON Users(level);
CREATE INDEX IF NOT EXISTS idx_users_points ON Users(points DESC);

-- Nodes indexes
CREATE INDEX IF NOT EXISTS idx_nodes_user_status ON Nodes(user_id, status);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON Nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_priority ON Nodes(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_nodes_type_user ON Nodes(node_type, user_id);
CREATE INDEX IF NOT EXISTS idx_nodes_importance ON Nodes(importance DESC);
CREATE INDEX IF NOT EXISTS idx_nodes_understanding ON Nodes(understanding);
CREATE INDEX IF NOT EXISTS idx_nodes_created ON Nodes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_nodes_completed ON Nodes(completed_at) WHERE completed_at IS NOT NULL;

-- Reviews indexes
CREATE INDEX IF NOT EXISTS idx_reviews_scheduled ON Reviews(scheduled_date, status);
CREATE INDEX IF NOT EXISTS idx_reviews_node ON Reviews(node_id, node_type);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON Reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_completed ON Reviews(completed_at) WHERE completed_at IS NOT NULL;

-- Schedules indexes
CREATE INDEX IF NOT EXISTS idx_schedules_user_time ON Schedules(user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_schedules_status ON Schedules(status);
CREATE INDEX IF NOT EXISTS idx_schedules_timezone ON Schedules(timezone);
CREATE INDEX IF NOT EXISTS idx_schedules_completed ON Schedules(completed_at) WHERE completed_at IS NOT NULL;

-- StudySessions indexes
CREATE INDEX IF NOT EXISTS idx_study_sessions_user ON StudySessions(user_id);
CREATE INDEX IF NOT EXISTS idx_study_sessions_status ON StudySessions(status);
CREATE INDEX IF NOT EXISTS idx_study_sessions_time ON StudySessions(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_study_sessions_paused ON StudySessions(status) WHERE status = 'paused';

-- StudyAnalytics indexes
CREATE INDEX IF NOT EXISTS idx_study_analytics_user_date ON StudyAnalytics(user_id, completed_at);
CREATE INDEX IF NOT EXISTS idx_study_analytics_node ON StudyAnalytics(node_id);
CREATE INDEX IF NOT EXISTS idx_study_analytics_session ON StudyAnalytics(session_id);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user ON Notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON Notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON Notifications(scheduled_time) WHERE scheduled_time IS NOT NULL;

-- UserAvailability indexes
CREATE INDEX IF NOT EXISTS idx_user_availability_user ON UserAvailability(user_id);
CREATE INDEX IF NOT EXISTS idx_user_availability_day ON UserAvailability(day_of_week);

-- Achievements indexes
CREATE INDEX IF NOT EXISTS idx_achievements_user ON Achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_category ON Achievements(category);
CREATE INDEX IF NOT EXISTS idx_achievements_unlocked ON Achievements(unlocked_at) WHERE unlocked_at IS NOT NULL;

-- Waves indexes
CREATE INDEX IF NOT EXISTS idx_waves_parent ON Waves(parent_id, parent_type);
CREATE INDEX IF NOT EXISTS idx_waves_status ON Waves(status);

-- Fibonacci indexes
CREATE INDEX IF NOT EXISTS idx_fibonacci_n ON Fibonacci(n);

-- =====================================================================
-- DEFAULT DATA
-- =====================================================================

-- Insert Fibonacci sequence (extended)
INSERT OR REPLACE INTO Fibonacci (n, value) VALUES
(0, 0), (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13), (8, 21), (9, 34),
(10, 55), (11, 89), (12, 144), (13, 233), (14, 377), (15, 610), (16, 987), (17, 1597),
(18, 2584), (19, 4181), (20, 6765), (21, 10946), (22, 17711), (23, 28657), (24, 46368),
(25, 75025);

-- Insert default achievements system
INSERT OR IGNORE INTO Achievements (name, description, points, icon, category, tier, progress_target) VALUES
-- Streak achievements
('First Steps', 'Complete your first study session', 10, '🎯', 'study', 1, 1),
('Streak Starter', 'Maintain a 3-day study streak', 25, '🔥', 'streak', 1, 3),
('Week Warrior', 'Study for 7 consecutive days', 50, '⚔️', 'streak', 2, 7),
('Marathon Learner', 'Study for 30 consecutive days', 100, '🏆', 'streak', 3, 30),
('Consistency King', 'Maintain a streak for 100 days', 250, '👑', 'streak', 4, 100),

-- Study time achievements
('Dedicated Learner', 'Complete 10 hours of total study time', 50, '⏱️', 'study', 1, 600),
('Time Master', 'Complete 50 hours of total study time', 150, '⏰', 'study', 2, 3000),
('Study Marathoner', 'Complete 200 hours of total study time', 500, '🏃', 'study', 3, 12000),

-- Mastery achievements
('Quick Learner', 'Achieve 90%+ understanding on any node', 30, '⚡', 'mastery', 1, 1),
('Subject Master', 'Achieve 90%+ understanding on 10 nodes', 75, '🧠', 'mastery', 2, 10),
('Knowledge Sage', 'Achieve 90%+ understanding on 50 nodes', 200, '🎓', 'mastery', 3, 50),

-- Completion achievements
('Node Explorer', 'Complete your first node', 15, '🌱', 'completion', 1, 1),
('Forest Ranger', 'Complete 25 nodes', 60, '🌲', 'completion', 2, 25),
('Ecology Master', 'Complete 100 nodes', 200, '🌍', 'completion', 3, 100),

-- Efficiency achievements
('Focused Mind', 'Achieve 80%+ focus score in a session', 20, '🎯', 'consistency', 1, 1),
('Efficiency Expert', 'Maintain 80%+ learning efficiency for a week', 45, '📊', 'consistency', 2, 7),
('Productivity Guru', 'Maintain 85%+ efficiency for 30 days', 120, '🚀', 'consistency', 3, 30),

-- Exploration achievements
('Branch Explorer', 'Create your first branch node', 10, '🔍', 'exploration', 1, 1),
('Tree Architect', 'Create a complete tree structure', 40, '🏗️', 'exploration', 2, 1),
('Ecology Designer', 'Create a complete ecology', 100, '🎨', 'exploration', 3, 1),

-- Speed achievements
('Speed Learner', 'Complete a node in half the estimated time', 35, '💨', 'speed', 1, 1),
('Time Bender', 'Complete 5 nodes ahead of schedule', 80, '⏳', 'speed', 2, 5),
('Efficiency Master', 'Maintain 120%+ pace on 10 nodes', 150, '🚀', 'speed', 3, 10);

-- Insert default study goals
INSERT OR IGNORE INTO StudyGoals (title, description, goal_type, target_value, unit, reward_points) VALUES
('Daily Study Habit', 'Study for at least 30 minutes every day', 'daily', 30, 'minutes', 5),
('Weekly Consistency', 'Study for at least 5 days in a week', 'weekly', 5, 'days', 25),
('Monthly Progress', 'Complete 10 nodes in a month', 'monthly', 10, 'nodes', 100),
('Understanding Master', 'Achieve 90%+ understanding on current nodes', 'understanding', 90, 'percent', 50);

-- =====================================================================
-- TRIGGERS for Data Integrity and Automation
-- =====================================================================

-- Update timestamps automatically
CREATE TRIGGER IF NOT EXISTS update_users_timestamp 
AFTER UPDATE ON Users
BEGIN
    UPDATE Users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
END;

CREATE TRIGGER IF NOT EXISTS update_nodes_timestamp 
AFTER UPDATE ON Nodes
BEGIN
    UPDATE Nodes SET updated_at = CURRENT_TIMESTAMP WHERE node_id = NEW.node_id;
END;

-- Auto-update total study minutes when analytics are added
CREATE TRIGGER IF NOT EXISTS update_total_study_minutes 
AFTER INSERT ON StudyAnalytics
BEGIN
    UPDATE Users 
    SET total_study_minutes = total_study_minutes + NEW.duration_minutes,
        total_sessions_completed = total_sessions_completed + 1
    WHERE user_id = NEW.user_id;
END;

-- Auto-level up based on experience points
CREATE TRIGGER IF NOT EXISTS auto_level_up 
AFTER UPDATE OF experience_points ON Users
BEGIN
    UPDATE Users 
    SET level = (
        SELECT MAX(level) + 1 
        FROM (SELECT 0 AS level UNION SELECT level FROM Users WHERE user_id = NEW.user_id) 
        WHERE experience_points >= (SELECT COALESCE(MAX(exp_threshold), 0) FROM (
            SELECT 100 * level * (level + 1) / 2 as exp_threshold 
            FROM (SELECT level FROM Users WHERE user_id = NEW.user_id)
        ))
    )
    WHERE user_id = NEW.user_id AND experience_points >= (
        SELECT level * 100 FROM Users WHERE user_id = NEW.user_id
    );
END;

-- Auto-create notification for streak milestones
CREATE TRIGGER IF NOT EXISTS streak_milestone_notification 
AFTER UPDATE OF streak_days ON Users
BEGIN
    -- Check for streak milestones
    INSERT OR IGNORE INTO Notifications (user_id, title, message, type, is_actionable)
    SELECT 
        NEW.user_id,
        '🔥 Streak Milestone!',
        'You''ve maintained a ' || NEW.streak_days || '-day study streak! Keep going!',
        'streak',
        1
    WHERE NEW.streak_days IN (3, 7, 14, 30, 60, 90, 100, 180, 365)
    AND NEW.streak_days > OLD.streak_days;
END;

-- Auto-update longest streak
CREATE TRIGGER IF NOT EXISTS update_longest_streak 
AFTER UPDATE OF streak_days ON Users
BEGIN
    UPDATE Users 
    SET longest_streak = MAX(longest_streak, NEW.streak_days),
        streak_updated_at = CURRENT_TIMESTAMP
    WHERE user_id = NEW.user_id AND NEW.streak_days > longest_streak;
END;

-- Auto-adjust difficulty based on performance history
CREATE TRIGGER IF NOT EXISTS auto_adjust_difficulty 
AFTER INSERT ON Reviews
WHEN NEW.performance_score IS NOT NULL AND NEW.status = 'completed'
BEGIN
    -- Only adjust if we have performance data
    INSERT INTO DifficultyHistory (node_id, old_difficulty, new_difficulty, adjustment_type, reason, performance_data)
    SELECT 
        NEW.node_id,
        (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id),
        CASE 
            WHEN NEW.performance_score > 0.8 THEN 
                MIN(100, (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id) * 1.15)
            WHEN NEW.performance_score < 0.4 THEN 
                MAX(10, (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id) * 0.85)
            ELSE (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id)
        END,
        'performance',
        CASE 
            WHEN NEW.performance_score > 0.8 THEN 'Excellent performance - increasing challenge'
            WHEN NEW.performance_score < 0.4 THEN 'Struggling - reducing difficulty'
            ELSE 'No adjustment needed'
        END,
        json_object('performance_score', NEW.performance_score, 'review_id', NEW.review_id)
    WHERE NEW.performance_score > 0.8 OR NEW.performance_score < 0.4;
    
    -- Update the actual difficulty
    UPDATE Nodes 
    SET difficulty = (
        SELECT new_difficulty 
        FROM DifficultyHistory 
        WHERE node_id = NEW.node_id 
        ORDER BY created_at DESC 
        LIMIT 1
    )
    WHERE node_id = NEW.node_id 
    AND EXISTS (
        SELECT 1 FROM DifficultyHistory 
        WHERE node_id = NEW.node_id 
        AND created_at = (SELECT MAX(created_at) FROM DifficultyHistory WHERE node_id = NEW.node_id)
    );
END;

-- Auto-schedule next review after completion
CREATE TRIGGER IF NOT EXISTS auto_schedule_next_review 
AFTER UPDATE OF status ON Reviews
WHEN NEW.status = 'completed' AND OLD.status != 'completed'
BEGIN
    -- Calculate next review date based on performance and Fibonacci spacing
    INSERT INTO Reviews (node_id, node_type, scheduled_date, estimated_duration, status)
    SELECT 
        NEW.node_id,
        NEW.node_type,
        date(NEW.completed_at, '+' || 
            (SELECT CAST(f.value AS INTEGER) 
             FROM Fibonacci f 
             WHERE f.n = (SELECT fibonacci_index FROM Nodes WHERE node_id = NEW.node_id)
            ) || ' days'),
        NEW.estimated_duration * (2.0 / (NEW.performance_score + 1)), -- Adjust based on performance
        'pending'
    FROM Fibonacci f
    WHERE f.n = (SELECT fibonacci_index FROM Nodes WHERE node_id = NEW.node_id)
    AND NEW.performance_score IS NOT NULL;
END;

-- Auto-unlock achievements when conditions are met
CREATE TRIGGER IF NOT EXISTS auto_unlock_achievements 
AFTER UPDATE ON Users
BEGIN
    -- Streak achievements
    UPDATE Achievements 
    SET unlocked_at = CURRENT_TIMESTAMP,
        progress_current = NEW.streak_days
    WHERE user_id = NEW.user_id 
    AND category = 'streak' 
    AND progress_target <= NEW.streak_days 
    AND unlocked_at IS NULL;
    
    -- Study time achievements
    UPDATE Achievements 
    SET unlocked_at = CURRENT_TIMESTAMP,
        progress_current = NEW.total_study_minutes
    WHERE user_id = NEW.user_id 
    AND category = 'study' 
    AND progress_target <= NEW.total_study_minutes 
    AND unlocked_at IS NULL;
END;

PRAGMA foreign_keys = ON;
