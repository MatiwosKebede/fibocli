# settings.py
from typing import Dict, Any

DEFAULTS: Dict[str, Any] = {
    "k_u": 0.2,
    "k_d": 0.3,
    "k_i": 0.3,
    "S_ref": 30,
    "h_coeff": {
        "leaf": 1.0,
        "sub_branch": 1.5,
        "branch": 2.0,
        "super_branch": 2.5,
        "tree": 3.0,
        "forest": 3.5,
        "ecology": 4.0
    },
    "a_u": 0.5,
    "gamma": 0.2,
    "R_decay_cap": 10,
    "R_threshold": 0.7,
    "calendar_max_hours_per_day": [8,8,8,8,8,8,8],
    "base_time_minutes": 30
}

