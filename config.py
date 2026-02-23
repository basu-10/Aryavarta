# BattleCells — Central Configuration

GRID_ROWS = 4
GRID_COLS = 5

# Valid placement columns per team (units face each other left vs right)
TEAM_A_COLS = [0, 1]   # Team A starts on the left
TEAM_B_COLS = [3, 4]   # Team B starts on the right

MAX_TICKS = 200  # Safety ceiling to prevent infinite loops

# Unit base stats registry
UNIT_STATS: dict[str, dict] = {
    "Barbarian": {
        "hp": 10,
        "damage": 1,
        "defense": 0,
        "range": 1,
        "speed": 2,
    },
    "Archer": {
        "hp": 6,
        "damage": 2,
        "defense": 0,
        "range": 3,
        "speed": 1,
    },
}

UNIT_TYPES = list(UNIT_STATS.keys())
MOVE_BEHAVIORS = ["Advance", "Hold"]
ATTACK_BEHAVIORS = ["Closest", "LowestHP", "HighestHP"]

# Phase ordering labels (for logging)
PHASES = [
    "Intent Evaluation",
    "Movement Resolution",
    "Target Selection",
    "Damage Application",
    "Death Resolution",
    "Win Check",
]
