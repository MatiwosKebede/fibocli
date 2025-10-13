-- FIBOCLI Enhanced Schema v4.1 - Full CLI Integration with Advanced AI Features
-- Fully compatible with cli.py v3.0 while preserving all AI capabilities

PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = WAL;
PRAGMA auto_vacuum = INCREMENTAL;

-- Enhanced Users table with AI and CLI compatibility
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT,
    
    -- CLI-Compatible time management
    available_minutes_per_day TEXT DEFAULT '[120,120,120,120,120,90,60]',
    preferred_study_hours TEXT DEFAULT '{"morning": 2, "afternoon": 3, "evening": 1}',
    timezone TEXT DEFAULT 'UTC',
    
    -- CLI-Compatible gamification
    points INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    streak_multiplier REAL DEFAULT 1.0,
    longest_streak INTEGER DEFAULT 0,
    last_study_date TEXT,
    
    -- CLI-Required fields
    learning_efficiency REAL DEFAULT 1.0,
    fatigue_threshold REAL DEFAULT 75.0,
    daily_goal_minutes INTEGER DEFAULT 120,
    total_study_minutes INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    total_points_earned INTEGER DEFAULT 0,
    total_sessions_completed INTEGER DEFAULT 0,
    
    -- AI Learning Profile (preserved)
    learning_style TEXT DEFAULT 'balanced' CHECK (learning_style IN (
        'visual', 'auditory', 'kinesthetic', 'reading', 'balanced', 'adaptive'
    )),
    cognitive_profile TEXT DEFAULT '{}',
    attention_span_profile TEXT DEFAULT '{}',
    optimal_session_length INTEGER DEFAULT 45,
    
    -- Advanced AI metrics (preserved)
    knowledge_retention_rate REAL DEFAULT 0.75,
    fatigue_resistance REAL DEFAULT 50.0,
    adaptability_score REAL DEFAULT 50.0,
    
    -- AI-Optimized settings (preserved)
    ai_recommendation_confidence REAL DEFAULT 0.7,
    adaptive_difficulty_enabled BOOLEAN DEFAULT 1,
    personalized_scheduling BOOLEAN DEFAULT 1,
    
    -- Social learning (preserved)
    study_group_id INTEGER,
    mentor_id INTEGER,
    learning_community TEXT DEFAULT 'general',
    
    -- Enhanced timestamps with CLI support
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_ai_sync TEXT,
    profile_updated_at TEXT,
    streak_updated_at TEXT,
    
    FOREIGN KEY (study_group_id) REFERENCES StudyGroups(group_id) ON DELETE SET NULL,
    FOREIGN KEY (mentor_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- AI-Powered User Availability (preserved)
CREATE TABLE IF NOT EXISTS UserAvailability (
    availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    minutes INTEGER NOT NULL CHECK (minutes >= 0),
    preferred_start_time TEXT,
    preferred_end_time TEXT,
    timezone TEXT DEFAULT 'UTC',
    
    -- AI Pattern recognition (preserved)
    actual_usage_pattern TEXT DEFAULT '{}',
    efficiency_by_hour TEXT DEFAULT '{}',
    recommended_adjustments TEXT DEFAULT '[]',
    flexibility_score REAL DEFAULT 50.0,
    consistency_score REAL DEFAULT 50.0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, day_of_week)
);

-- Enhanced Sessions with CLI compatibility
CREATE TABLE IF NOT EXISTS Sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expiry TEXT NOT NULL,
    
    -- Enhanced security (preserved)
    device_info TEXT DEFAULT 'unknown',
    device_fingerprint TEXT,
    ip_address TEXT,
    geographic_location TEXT,
    security_level INTEGER DEFAULT 1 CHECK (security_level BETWEEN 1 AND 3),
    
    -- AI Security monitoring (preserved)
    suspicious_activity_score REAL DEFAULT 0.0,
    last_security_check TEXT,
    
    -- Activity tracking
    last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
    total_requests INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- AI-Enhanced Nodes with full CLI compatibility
CREATE TABLE IF NOT EXISTS Nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN (
        'ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf'
    )),
    name TEXT NOT NULL,
    description TEXT,
    
    -- CLI-Required categorization
    course TEXT,
    course_code TEXT,
    subject_area TEXT,
    
    -- CLI-Required status system
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'active', 'completed', 'paused', 'archived', 'review', 'locked', 'in_progress'
    )),
    
    -- CLI-Required Core metrics
    importance REAL DEFAULT 50.0 CHECK (importance BETWEEN 1 AND 100),
    understanding REAL DEFAULT 50.0 CHECK (understanding BETWEEN 1 AND 100),
    difficulty REAL DEFAULT 50.0 CHECK (difficulty BETWEEN 1 AND 100),
    engagement REAL DEFAULT 50.0 CHECK (engagement BETWEEN 1 AND 100),
    fatigue REAL DEFAULT 50.0 CHECK (fatigue BETWEEN 1 AND 100),
    
    -- CLI-Required fields
    fibonacci_index INTEGER DEFAULT 1,
    parent_id INTEGER,
    total_active_minutes REAL DEFAULT 0.0,
    duration_days INTEGER,
    child_order INTEGER DEFAULT 0,
    
    -- CLI-Required intelligent restrictions
    prerequisites TEXT DEFAULT '[]',
    
    -- CLI-Required auto-duration
    auto_duration_enabled BOOLEAN DEFAULT 1,
    min_duration INTEGER DEFAULT 15 CHECK (min_duration >= 5),
    max_duration INTEGER DEFAULT 90 CHECK (max_duration <= 240),
    estimated_duration INTEGER DEFAULT 30,
    
    -- CLI-Required gamification
    points_value INTEGER DEFAULT 10,
    
    -- Advanced AI fields (preserved)
    knowledge_domain TEXT CHECK (knowledge_domain IN (
        'factual', 'conceptual', 'procedural', 'metacognitive', 'applied'
    )),
    bloom_taxonomy_level INTEGER CHECK (bloom_taxonomy_level BETWEEN 1 AND 6),
    complexity_score REAL DEFAULT 50.0,
    priority_score REAL DEFAULT 0.0,
    corequisites TEXT DEFAULT '[]',
    required_completion REAL DEFAULT 0.0 CHECK (required_completion BETWEEN 0 AND 1),
    unlock_conditions TEXT DEFAULT '{}',
    experience_value INTEGER DEFAULT 5,
    mastery_bonus_multiplier REAL DEFAULT 1.0,
    ai_recommended_duration INTEGER,
    related_concepts TEXT DEFAULT '[]',
    learning_path_recommendations TEXT DEFAULT '[]',
    common_misconceptions TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    ai_metadata TEXT DEFAULT '{}',
    
    -- Intelligent timestamps
    last_reviewed_at TEXT,
    completed_at TEXT,
    activated_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_ai_analysis TEXT,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    CHECK (parent_id IS NULL OR node_type != 'ecology')
);

-- CLI-Required Fibonacci table
CREATE TABLE IF NOT EXISTS Fibonacci (
    n INTEGER PRIMARY KEY,
    value INTEGER NOT NULL
);

-- CLI-Required Achievements table
CREATE TABLE IF NOT EXISTS Achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    points INTEGER DEFAULT 0,
    icon TEXT,
    unlocked_at TEXT,
    category TEXT,
    progress_current INTEGER DEFAULT 0,
    progress_target INTEGER DEFAULT 1,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- CLI-Required StudySessions with AI enhancements
CREATE TABLE IF NOT EXISTS StudySessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- CLI-Required timing
    start_time TEXT NOT NULL,
    end_time TEXT,
    planned_duration REAL NOT NULL,
    actual_duration REAL DEFAULT 0,
    paused_duration REAL DEFAULT 0,
    
    -- CLI-Required session metrics
    status TEXT DEFAULT 'active' CHECK (status IN (
        'active', 'completed', 'paused', 'abandoned', 'ai_interrupted'
    )),
    focus_score REAL CHECK (focus_score BETWEEN 0 AND 1),
    efficiency_score REAL CHECK (efficiency_score BETWEEN 0 AND 1),
    
    -- CLI-Required fatigue tracking
    fatigue_start REAL CHECK (fatigue_start BETWEEN 1 AND 100),
    fatigue_end REAL CHECK (fatigue_end BETWEEN 1 AND 100),
    fatigue_change REAL GENERATED ALWAYS AS (fatigue_end - fatigue_start) VIRTUAL,
    
    -- CLI-Required gamification
    points_earned INTEGER DEFAULT 0,
    experience_earned INTEGER DEFAULT 0,
    streak_bonus_multiplier REAL DEFAULT 1.0,
    
    -- CLI-Required session details
    current_node_id INTEGER,
    learning_path TEXT,
    pause_time TEXT,
    resume_time TEXT,
    session_type TEXT DEFAULT 'study' CHECK (session_type IN ('study', 'break')),
    
    -- Advanced AI fields (preserved)
    ai_optimized_duration REAL,
    satisfaction_score INTEGER CHECK (satisfaction_score BETWEEN 1 AND 5),
    flow_state_minutes REAL DEFAULT 0,
    fatigue_pattern TEXT,
    nodes_completed INTEGER DEFAULT 0,
    total_breaks INTEGER DEFAULT 0,
    device_used TEXT DEFAULT 'unknown',
    learning_environment TEXT,
    mood_start INTEGER CHECK (mood_start BETWEEN 1 AND 5),
    mood_end INTEGER CHECK (mood_end BETWEEN 1 AND 5),
    ai_session_insights TEXT,
    improvement_recommendations TEXT DEFAULT '[]',
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (current_node_id) REFERENCES Nodes(node_id) ON DELETE SET NULL
);

-- CLI-Required StudyAnalytics
CREATE TABLE IF NOT EXISTS StudyAnalytics (
    analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_id INTEGER,
    session_id INTEGER,
    
    -- CLI-Required core metrics
    duration_minutes REAL NOT NULL CHECK (duration_minutes > 0),
    focus_score REAL CHECK (focus_score BETWEEN 0 AND 1),
    efficiency_score REAL CHECK (efficiency_score BETWEEN 0 AND 1),
    
    -- CLI-Required timing
    completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Advanced AI fields (preserved)
    understanding_gain REAL,
    knowledge_retention_score REAL,
    timezone TEXT,
    local_completed_time TEXT,
    optimal_timing_score REAL,
    estimated_vs_actual REAL,
    pace_score REAL,
    cognitive_efficiency REAL,
    learning_velocity REAL,
    pattern_insights TEXT,
    anomaly_detected BOOLEAN DEFAULT 0,
    improvement_opportunities TEXT DEFAULT '[]',
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES StudySessions(session_id) ON DELETE SET NULL
);

-- CLI-Required Notifications
CREATE TABLE IF NOT EXISTS Notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    
    -- CLI-Required types
    type TEXT NOT NULL CHECK (type IN (
        'reminder', 'achievement', 'streak', 'review', 'goal', 'system',
        'motivational', 'ai_insight', 'recommendation', 'group_activity'
    )),
    
    -- CLI-Required interaction
    is_read BOOLEAN DEFAULT 0,
    is_actionable BOOLEAN DEFAULT 0,
    action_url TEXT,
    
    -- Enhanced AI personalization (preserved)
    personalization_level INTEGER DEFAULT 1 CHECK (personalization_level BETWEEN 1 AND 3),
    emotional_tone TEXT CHECK (emotional_tone IN ('neutral', 'encouraging', 'urgent', 'celebratory')),
    timing_optimized BOOLEAN DEFAULT 0,
    action_taken TEXT,
    scheduled_time TEXT,
    optimal_delivery_time TEXT,
    expires_at TEXT,
    engagement_metrics TEXT DEFAULT '{}',
    effectiveness_score REAL,
    
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- CLI-Required Reviews
CREATE TABLE IF NOT EXISTS Reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    node_type TEXT NOT NULL,
    
    -- CLI-Required scheduling
    scheduled_date TEXT NOT NULL,
    estimated_duration REAL CHECK (estimated_duration > 0),
    
    -- CLI-Required status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'completed', 'skipped', 'rescheduled', 'paused', 'in_progress', 'ai_optimized'
    )),
    
    -- Advanced AI fields (preserved)
    optimal_review_window TEXT,
    scheduling_confidence REAL,
    actual_duration REAL CHECK (actual_duration > 0),
    paused_duration REAL DEFAULT 0,
    ai_optimized_duration REAL,
    focus_level REAL CHECK (focus_level BETWEEN 1 AND 100),
    engagement REAL CHECK (engagement BETWEEN 1 AND 100),
    fatigue REAL CHECK (fatigue BETWEEN 1 AND 100),
    cognitive_load REAL CHECK (cognitive_load BETWEEN 1 AND 100),
    performance_score REAL CHECK (performance_score BETWEEN 0 AND 1),
    next_review_date TEXT,
    forecast_accuracy REAL,
    interval_days INTEGER,
    ease_factor REAL DEFAULT 2.5 CHECK (ease_factor >= 1.3),
    memory_strength REAL,
    completed_at TEXT,
    paused_at TEXT,
    resumed_at TEXT,
    started_at TEXT,
    ai_optimized_at TEXT,
    notes TEXT,
    ai_insights TEXT,
    session_quality INTEGER CHECK (session_quality BETWEEN 1 AND 5),
    learning_breakthroughs TEXT DEFAULT '[]',
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- CLI-Required Waves
CREATE TABLE IF NOT EXISTS Waves (
    wave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_type TEXT NOT NULL,
    parent_id INTEGER NOT NULL,
    wave_number INTEGER NOT NULL,
    
    -- CLI-Required planning
    planned_units_count INTEGER NOT NULL CHECK (planned_units_count >= 0),
    actual_units_planted INTEGER NOT NULL CHECK (actual_units_planted >= 0),
    
    -- CLI-Required status
    status TEXT DEFAULT 'planned' CHECK (status IN (
        'planned', 'planting', 'completed', 'paused', 'cancelled', 'optimizing'
    )),
    
    -- CLI-Required tracking
    planted_at TEXT,
    completed_at TEXT,
    scheduled_end_date TEXT,
    
    -- Advanced AI fields (preserved)
    ai_recommended_units INTEGER,
    progress REAL DEFAULT 0.0 CHECK (progress BETWEEN 0 AND 1),
    predicted_completion_date TEXT,
    completion_confidence REAL,
    efficiency_score REAL,
    adaptive_adjustments TEXT DEFAULT '[]',
    optimized_at TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- CLI-Required Schedules
CREATE TABLE IF NOT EXISTS Schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN (
        'study', 'break', 'review', 'wave_planting', 'maintenance', 'ai_optimization'
    )),
    
    -- CLI-Required timing
    start_time TEXT NOT NULL,
    duration REAL NOT NULL CHECK (duration > 0),
    
    -- CLI-Required status
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN (
        'planned', 'active', 'completed', 'cancelled', 'paused', 'rescheduled', 'ai_optimized'
    )),
    
    -- CLI-Required flexible scheduling
    flexible_window INTEGER DEFAULT 15,
    timezone TEXT,
    
    -- Advanced AI fields (preserved)
    priority REAL DEFAULT 0.0,
    optimal_time_window TEXT,
    scheduling_algorithm TEXT DEFAULT 'standard',
    can_reschedule BOOLEAN DEFAULT 1,
    ai_reschedule_recommendations TEXT DEFAULT '[]',
    completed_at TEXT,
    actual_start_time TEXT,
    actual_duration REAL,
    schedule_adherence_score REAL,
    recurrence_pattern TEXT,
    optimization_notes TEXT,
    ai_confidence_score REAL,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- =====================================================================
-- CLI-REQUIRED SUPPORT TABLES
-- =====================================================================

-- CLI-Required for difficulty adjustment
CREATE TABLE IF NOT EXISTS DifficultyHistory (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    old_difficulty REAL,
    new_difficulty REAL,
    adjustment_type TEXT,
    reason TEXT,
    performance_data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- CLI-Required for efficiency tracking
CREATE TABLE IF NOT EXISTS EfficiencyHistory (
    efficiency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    efficiency_score REAL,
    recorded_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- CLI-Required for fatigue management
CREATE TABLE IF NOT EXISTS FatiguePatterns (
    pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day_of_week INTEGER,
    hour_of_day INTEGER,
    recommended_max_duration INTEGER,
    sample_size INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- CLI-Required for study breaks
CREATE TABLE IF NOT EXISTS StudyBreaks (
    break_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    break_duration INTEGER,
    break_type TEXT,
    start_time TEXT,
    end_time TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES StudySessions(session_id) ON DELETE CASCADE
);

-- CLI-Required for node relationships
CREATE TABLE IF NOT EXISTS NodeRelationships (
    relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_node_id INTEGER NOT NULL,
    child_node_id INTEGER NOT NULL,
    relationship_type TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (child_node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE
);

-- CLI-Required for study goals
CREATE TABLE IF NOT EXISTS StudyGoals (
    goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    goal_type TEXT,
    target_value REAL,
    unit TEXT,
    reward_points INTEGER,
    ai_optimized BOOLEAN DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- CLI-Required for exports
CREATE TABLE IF NOT EXISTS Exports (
    export_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    export_type TEXT,
    file_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- CLI-Required for learning objectives
CREATE TABLE IF NOT EXISTS LearningObjectives (
    objective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE SET NULL
);

-- =====================================================================
-- PRESERVED ADVANCED AI TABLES
-- =====================================================================

-- AI-Powered Knowledge Graph (preserved)
CREATE TABLE IF NOT EXISTS KnowledgeGraph (
    graph_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source_node_id INTEGER NOT NULL,
    target_node_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN (
        'prerequisite', 'corequisite', 'similar', 'contrasting', 'hierarchical',
        'sequential', 'complementary', 'foundational'
    )),
    strength REAL DEFAULT 1.0 CHECK (strength BETWEEN 0 AND 1),
    confidence REAL DEFAULT 0.8 CHECK (confidence BETWEEN 0 AND 1),
    
    -- AI Analysis data (preserved)
    ai_generated BOOLEAN DEFAULT 0,
    semantic_similarity REAL,
    contextual_relevance REAL,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES Nodes(node_id) ON DELETE CASCADE,
    UNIQUE (source_node_id, target_node_id, relationship_type)
);

-- AI Model Training Data (preserved)
CREATE TABLE IF NOT EXISTS AITrainingData (
    training_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN (
        'learning_pattern', 'schedule_optimization', 'difficulty_prediction',
        'fatigue_prediction', 'engagement_pattern'
    )),
    input_features TEXT NOT NULL,
    output_prediction TEXT NOT NULL,
    actual_outcome TEXT,
    prediction_accuracy REAL,
    model_version TEXT NOT NULL,
    training_date TEXT NOT NULL,
    used_in_production BOOLEAN DEFAULT 0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Study Groups with AI matching (preserved)
CREATE TABLE IF NOT EXISTS StudyGroups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    
    -- AI Matching criteria (preserved)
    learning_style_compatibility REAL DEFAULT 0.7,
    knowledge_level_range TEXT DEFAULT '{}',
    preferred_schedule_sync BOOLEAN DEFAULT 0,
    
    -- Group analytics (preserved)
    total_collective_study_hours REAL DEFAULT 0,
    average_efficiency REAL DEFAULT 0.0,
    group_cohesion_score REAL DEFAULT 0.0,
    
    -- AI Management (preserved)
    auto_manage_members BOOLEAN DEFAULT 0,
    optimal_size INTEGER DEFAULT 5,
    activity_level TEXT DEFAULT 'medium' CHECK (activity_level IN ('low', 'medium', 'high')),
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Collaborative Learning Features (preserved)
CREATE TABLE IF NOT EXISTS CollaborativeSessions (
    collab_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Session details (preserved)
    scheduled_start TEXT NOT NULL,
    scheduled_end TEXT,
    actual_start TEXT,
    actual_end TEXT,
    duration_minutes REAL,
    
    -- Collaborative metrics (preserved)
    participant_count INTEGER DEFAULT 0,
    engagement_score REAL,
    collaboration_efficiency REAL,
    shared_understanding_gain REAL,
    
    -- AI Facilitation (preserved)
    ai_facilitator_enabled BOOLEAN DEFAULT 0,
    facilitation_notes TEXT,
    session_insights TEXT,
    
    status TEXT DEFAULT 'scheduled' CHECK (status IN (
        'scheduled', 'active', 'completed', 'cancelled'
    )),
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (group_id) REFERENCES StudyGroups(group_id) ON DELETE CASCADE
);

-- AI-Powered Learning Recommendations (preserved)
CREATE TABLE IF NOT EXISTS AIRecommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    recommendation_type TEXT NOT NULL CHECK (recommendation_type IN (
        'study_schedule', 'node_sequence', 'break_timing', 'difficulty_adjustment',
        'learning_style_adaptation', 'resource_suggestion', 'review_timing'
    )),
    
    -- Recommendation details (preserved)
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    reasoning TEXT,
    confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    expected_impact REAL,
    
    -- Implementation tracking (preserved)
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'accepted', 'implemented', 'rejected', 'expired'
    )),
    accepted_at TEXT,
    implemented_at TEXT,
    actual_impact REAL,
    
    -- Metadata (preserved)
    algorithm_version TEXT,
    input_parameters TEXT DEFAULT '{}',
    expires_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Neural Efficiency Tracking (preserved)
CREATE TABLE IF NOT EXISTS NeuralEfficiency (
    efficiency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    measurement_date TEXT NOT NULL,
    
    -- Cognitive metrics (preserved)
    baseline_processing_speed REAL,
    current_processing_speed REAL,
    working_memory_capacity REAL,
    attention_control REAL,
    cognitive_flexibility REAL,
    
    -- Learning-specific efficiency (preserved)
    information_encoding_speed REAL,
    retrieval_efficiency REAL,
    pattern_recognition_speed REAL,
    
    -- AI Analysis (preserved)
    neural_efficiency_score REAL,
    improvement_recommendations TEXT DEFAULT '[]',
    cognitive_fatigue_level REAL,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, measurement_date)
);

-- Predictive Learning Analytics (preserved)
CREATE TABLE IF NOT EXISTS PredictiveAnalytics (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    prediction_type TEXT NOT NULL CHECK (prediction_type IN (
        'completion_time', 'difficulty_spike', 'burnout_risk', 'optimal_schedule'
    )),
    
    -- Prediction details (preserved)
    predicted_value REAL NOT NULL,
    confidence_interval TEXT,
    prediction_horizon TEXT,
    relevant_factors TEXT DEFAULT '{}',
    
    -- Outcome tracking (preserved)
    actual_value REAL,
    prediction_accuracy REAL,
    feedback_incorporated BOOLEAN DEFAULT 0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Learning Resource Intelligence (preserved)
CREATE TABLE IF NOT EXISTS LearningResources (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_id INTEGER,
    
    -- Resource details (preserved)
    title TEXT NOT NULL,
    resource_type TEXT CHECK (resource_type IN (
        'video', 'article', 'book', 'podcast', 'interactive', 'exercise', 'cheatsheet'
    )),
    url TEXT,
    content_quality_score REAL,
    difficulty_match REAL,
    
    -- AI Evaluation (preserved)
    relevance_score REAL,
    engagement_potential REAL,
    time_efficiency REAL,
    ai_recommended BOOLEAN DEFAULT 0,
    
    -- Usage tracking (preserved)
    times_accessed INTEGER DEFAULT 0,
    average_rating REAL,
    user_notes TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES Nodes(node_id) ON DELETE SET NULL
);

-- =====================================================================
-- ENHANCED INDEXES for CLI Performance and AI
-- =====================================================================

-- CLI-Optimized indexes
CREATE INDEX IF NOT EXISTS idx_users_cli ON Users(username, streak_days, level);
CREATE INDEX IF NOT EXISTS idx_nodes_cli ON Nodes(user_id, status, node_type, parent_id);
CREATE INDEX IF NOT EXISTS idx_study_sessions_cli ON StudySessions(user_id, status, start_time);
CREATE INDEX IF NOT EXISTS idx_reviews_cli ON Reviews(node_id, status, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_achievements_cli ON Achievements(user_id, unlocked_at, category);

-- AI-Optimized indexes (preserved)
CREATE INDEX IF NOT EXISTS idx_users_ai_profile ON Users(learning_style, adaptability_score);
CREATE INDEX IF NOT EXISTS idx_nodes_ai_metrics ON Nodes(complexity_score, knowledge_domain, bloom_taxonomy_level);
CREATE INDEX IF NOT EXISTS idx_knowledge_graph_ai ON KnowledgeGraph(ai_generated, confidence, semantic_similarity);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_active ON AIRecommendations(user_id, status, confidence_score) WHERE status IN ('pending', 'accepted');
CREATE INDEX IF NOT EXISTS idx_neural_efficiency_trends ON NeuralEfficiency(user_id, measurement_date DESC, neural_efficiency_score);

-- Enhanced performance indexes
CREATE INDEX IF NOT EXISTS idx_nodes_scheduling ON Nodes(priority_score, status, user_id);
CREATE INDEX IF NOT EXISTS idx_study_sessions_analytics ON StudySessions(user_id, end_time, efficiency_score);
CREATE INDEX IF NOT EXISTS idx_notifications_delivery ON Notifications(user_id, is_read, created_at);

-- =====================================================================
-- CLI-COMPATIBLE TRIGGERS with AI Enhancements
-- =====================================================================

-- Auto-update timestamps
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

-- CLI-Required streak management
CREATE TRIGGER IF NOT EXISTS update_streak_on_study
AFTER UPDATE ON StudySessions
WHEN NEW.status = 'completed' AND OLD.status != 'completed'
BEGIN
    UPDATE Users 
    SET last_study_date = DATE('now'),
        streak_updated_at = CURRENT_TIMESTAMP
    WHERE user_id = NEW.user_id;
END;

-- AI-Powered Adaptive Difficulty Adjustment (preserved)
CREATE TRIGGER IF NOT EXISTS ai_adaptive_difficulty 
AFTER INSERT ON Reviews
WHEN NEW.performance_score IS NOT NULL AND NEW.status = 'completed'
BEGIN
    INSERT INTO DifficultyHistory (node_id, old_difficulty, new_difficulty, adjustment_type, reason, performance_data)
    SELECT 
        NEW.node_id,
        (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id),
        CASE 
            WHEN NEW.performance_score > 0.85 AND NEW.cognitive_load < 70 THEN
                MIN(95, (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id) * 
                    (1.0 + (NEW.performance_score - 0.8) * 0.3))
            WHEN NEW.performance_score < 0.4 OR NEW.cognitive_load > 85 THEN
                MAX(15, (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id) * 
                    (0.9 - (0.5 - NEW.performance_score) * 0.2))
            ELSE (SELECT difficulty FROM Nodes WHERE node_id = NEW.node_id)
        END,
        'ai_adaptive',
        CASE 
            WHEN NEW.performance_score > 0.85 AND NEW.cognitive_load < 70 THEN
                'AI: Excellent performance with low cognitive load - increasing challenge'
            WHEN NEW.performance_score < 0.4 OR NEW.cognitive_load > 85 THEN
                'AI: High cognitive load or low performance - reducing difficulty'
            ELSE 'AI: No significant adjustment needed'
        END,
        json_object(
            'performance_score', NEW.performance_score,
            'cognitive_load', NEW.cognitive_load,
            'engagement', NEW.engagement,
            'review_id', NEW.review_id,
            'ai_confidence', 0.85
        )
    WHERE NEW.performance_score > 0.85 OR NEW.performance_score < 0.4 OR NEW.cognitive_load > 85;
END;

-- AI-Powered Knowledge Graph Auto-generation (preserved)
CREATE TRIGGER IF NOT EXISTS ai_knowledge_graph_auto 
AFTER INSERT ON Nodes
WHEN NEW.user_id IS NOT NULL AND NEW.node_type IN ('branch', 'sub_branch', 'leaf')
BEGIN
    INSERT OR IGNORE INTO KnowledgeGraph (
        user_id, source_node_id, target_node_id, relationship_type, 
        strength, confidence, ai_generated
    )
    SELECT 
        NEW.user_id,
        NEW.node_id,
        parent.node_id,
        'hierarchical',
        0.8,
        0.9,
        1
    FROM Nodes parent
    WHERE parent.node_id = NEW.parent_id
    AND parent.user_id = NEW.user_id;
END;

-- =====================================================================
-- ENHANCED DEFAULT DATA with CLI and AI Focus
-- =====================================================================

-- Insert extended Fibonacci sequence for CLI and AI scheduling
INSERT OR REPLACE INTO Fibonacci (n, value) VALUES
(0, 0), (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13), (8, 21), (9, 34),
(10, 55), (11, 89), (12, 144), (13, 233), (14, 377), (15, 610), (16, 987), (17, 1597),
(18, 2584), (19, 4181), (20, 6765), (21, 10946), (22, 17711), (23, 28657), (24, 46368),
(25, 75025), (26, 121393), (27, 196418), (28, 317811), (29, 514229), (30, 832040);

-- CLI-Compatible default achievements
INSERT OR IGNORE INTO Achievements (name, description, points, icon, category, progress_target) VALUES
-- CLI Basic achievements
('First Steps', 'Complete your first study session', 10, '🎯', 'study', 1),
('Consistent Learner', 'Maintain a 3-day study streak', 25, '🔥', 'streak', 3),
('Week Warrior', 'Maintain a 7-day study streak', 50, '⚡', 'streak', 7),
('Marathon Learner', 'Maintain a 30-day study streak', 100, '🏆', 'streak', 30),

-- AI Mastery achievements (preserved)
('AI Learning Partner', 'Complete 10 AI-optimized study sessions', 75, '🤖', 'ai_mastery', 10),
('Neural Optimizer', 'Achieve 20% efficiency improvement through AI recommendations', 150, '🧠', 'ai_mastery', 20),
('Adaptive Learner', 'Successfully adapt learning style based on AI insights', 100, '🔄', 'ai_mastery', 1),

-- Enhanced existing achievements
('Efficient Explorer', 'Complete nodes with 90%+ AI-calculated efficiency', 120, '⚡', 'efficiency', 10),
('Knowledge Architect', 'Build a complex knowledge graph with AI assistance', 180, '🏗️', 'exploration', 1);

-- Initialize AI model versions
INSERT OR IGNORE INTO AITrainingData (user_id, data_type, input_features, output_prediction, model_version, training_date) VALUES
(0, 'learning_pattern', '{"baseline": "default"}', '{"recommendation": "balanced"}', 'v1.0-cli-integrated', CURRENT_TIMESTAMP);

PRAGMA optimize;
PRAGMA foreign_keys = ON;
