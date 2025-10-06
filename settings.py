DEFAULTS = {
    "base_time_minutes": 30,  # Base time for reviews
    "base_completion_days": 4,  # Default days to complete a node
    "S_ref": 30,  # Reference study time for scheduling
    "a_u": 0.5,  # Understanding adjustment factor
    "gamma": 0.2,  # Decay factor for spaced repetition
    "R_decay_cap": 10,  # Maximum readiness decay
    "k_u": 0.5,  # Understanding coefficient
    "k_d": 0.5,  # Difficulty coefficient
    "k_i": 0.5,  # Importance coefficient
    "h_coeff": {  # Hierarchy coefficients for duration scaling
        "ecology": 2.0,
        "forest": 2.0,
        "tree": 1.5,
        "super_branch": 1.5,
        "branch": 1.2,
        "sub_branch": 1.2,
        "leaf": 1.0
    },
    "calendar_max_hours_per_day": "[2, 2, 2, 2, 2, 2, 2]",  # Max study hours per day of week
    "default_status": {  # Default status for new nodes
        "ecology": "unlocked",
        "forest": "unlocked",
        "tree": "unlocked",
        "super_branch": "unlocked",
        "branch": "unlocked",
        "sub_branch": "unlocked",
        "leaf": "unlocked"
    },
    "min_review_duration": 5,  # Minimum review duration in minutes
    "default_difficulty": 3,  # Default difficulty (1-5)
    "default_importance": 0.5,  # Default importance (0-1)
    "default_understanding": 0.5  # Default understanding level (0-1)
}