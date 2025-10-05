DEFAULTS = {
    "base_time_minutes": 30,
    "base_completion_days": 4,
    "S_ref": 30,
    "a_u": 0.5,
    "gamma": 0.2,
    "R_decay_cap": 10,
    "k_u": 0.5,
    "k_d": 0.5,
    "k_i": 0.5,
    "h_coeff": {
        "ecology": 2.0,  # Reduced from 10
        "forest": 2.0,
        "tree": 1.5,
        "super_branch": 1.5,
        "branch": 1.2,
        "sub_branch": 1.2,
        "leaf": 1.0
    },
    "calendar_max_hours_per_day": "[2, 2, 2, 2, 2, 2, 2]"
}
