# BattleCells — Central Configuration

GRID_ROWS = 4
GRID_COLS = 9

# Valid placement columns per team (units face each other left vs right)
TEAM_A_COLS = [0, 1, 2, 3]   # Team A starts on the left
TEAM_B_COLS = [5, 6, 7, 8]   # Team B starts on the right
# Column 4 is no-man's land

MAX_TICKS = 200  # Safety ceiling to prevent infinite loops

# Unit base stats registry
# speed: 1.0 = 1 cell/tick (1x), 0.5 = 1 cell every 2 ticks (0.5x)
UNIT_STATS: dict[str, dict] = {
    "Barbarian": {
        "hp": 10,
        "damage": 1,
        "defense": 0,
        "range": 1,
        "speed": 1.0,   # 1x — advances 1 cell every tick
    },
    "Archer": {
        "hp": 6,
        "damage": 2,
        "defense": 0,
        "range": 2,
        "speed": 0.5,   # 0.5x — advances 1 cell every 2 ticks
    },
    "Troll": {
        "hp": 20,
        "damage": 3,
        "defense": 2,
        "range": 1,
        "speed": 1.0,   # 1x melee brute
    },
    "Wraith": {
        "hp": 8,
        "damage": 3,
        "defense": 0,
        "range": 3,
        "speed": 1.0,   # 1x fast ranged glass cannon
    },
    "Longbowman": {
        "hp": 6,
        "damage": 2,
        "defense": 0,
        "range": 3,
        "speed": 0.5,   # slow, long-range infantry
    },
    "Hussar": {
        "hp": 8,
        "damage": 3,
        "defense": 1,
        "range": 1,
        "speed": 2.0,   # fast cavalry
    },
    "Cannon": {
        "hp": 30,
        "damage": 5,
        "defense": 3,
        "range": 4,
        "speed": 0.0,   # stationary defence building unit
    },
    "Archer Tower": {
        "hp": 20,
        "damage": 3,
        "defense": 2,
        "range": 3,
        "speed": 0.0,   # stationary defence building unit
    },
}

UNIT_TYPES = list(UNIT_STATS.keys())

# Troop classification metadata: faction (human/monster) and type (melee/ranged)
UNIT_CLASSIFICATION: dict[str, dict] = {
    "Barbarian": {"faction": "human", "type": "melee"},
    "Archer": {"faction": "human", "type": "ranged"},
    "Troll": {"faction": "monster", "type": "melee"},
    "Wraith": {"faction": "monster", "type": "ranged"},
    "Longbowman": {"faction": "human", "type": "ranged"},
    "Hussar": {"faction": "human", "type": "melee"},
    "Cannon": {"faction": "human", "type": "ranged"},
    "Archer Tower": {"faction": "human", "type": "ranged"},
}

# ── World map ──────────────────────────────────────────────────────── #
WORLD_GRID_W = 50
WORLD_GRID_H = 50
WORLD_TRAVEL_SECONDS_PER_CELL = 1  # base seconds of travel per grid cell

# NPC auto-population settings
MAX_NPC_COUNT       = 8   # max NPC player entities on the map
NPC_FORTS_PER_NPC   = 2   # forts each NPC spawns with

# Monster world entity targets (maintained by ensure_world_entities)
MAX_MONSTER_FORTS   = 15  # unowned monster-occupied forts on the map
MAX_MONSTER_CAMPS   = 10  # standalone monster camps on the map

# Fort slot distribution weights [4, 5, 6, 7, 8, 9, 10 slots]
FORT_SLOT_WEIGHTS = [20, 20, 20, 15, 10, 10, 5]

# Star level thresholds (defender unit counts → 1–4 stars)
STAR_THRESHOLDS = [4, 8, 12]   # ≤4 → ★, ≤8 → ★★, ≤12 → ★★★, else ★★★★

# ── Building system ────────────────────────────────────────────────── #
BUILDING_PRODUCTION_RATE: dict[str, dict] = {
    "Farm":         {"food":   0.05},
    "Lumber Mill":  {"timber": 0.05},
    "Merchant":     {"gold":   0.05},
    "Mine":         {"metal":  0.05},
}

# Level multiplier: level N outputs 2^(N-1) × base rate
BUILDING_LEVEL_MULTIPLIER = 2  # doubles per level

# Seconds to construct a new building in a blank slot
# NOTE: set to 10 s for testing; raise for production
BUILDING_BUILD_TIME: dict[str, int] = {
    "Farm": 10,
    "Lumber Mill": 10,
    "Merchant": 10,
    "Mine": 10,
    "Garrison": 10,
    "Stable": 10,
    "Cannon": 10,
    "Archer Tower": 10,
    "Command Centre": 0,
}

BUILDING_BUILD_COST: dict[str, dict] = {
    "Farm":          {"food": 50,   "timber": 30},
    "Lumber Mill":   {"timber": 50, "gold": 30},
    "Merchant":      {"gold": 80,   "metal": 20},
    "Mine":          {"metal": 50,  "gold": 40},
    "Garrison":      {"gold": 100,  "metal": 50},
    "Stable":        {"gold": 120,  "metal": 60, "timber": 20},
    "Cannon":        {"metal": 100, "gold": 50},
    "Archer Tower":  {"metal": 60,  "timber": 60},
    "Command Centre": {},
}

# Repair cost = half build cost (rounded down)
BUILDING_REPAIR_COST: dict[str, dict] = {
    k: {res: amt // 2 for res, amt in costs.items()}
    for k, costs in BUILDING_BUILD_COST.items()
}

# Army buildings: which troop type each building trains and base training time
ARMY_BUILDINGS: dict[str, dict] = {
    "Garrison": {"unit_type": "Longbowman", "training_seconds": 60},
    "Stable":   {"unit_type": "Hussar",     "training_seconds": 90},
}

# Cost to train one unit (resources deducted immediately on queuing)
TROOP_TRAIN_COST: dict[str, dict] = {
    "Longbowman": {"food": 20, "timber": 10, "gold": 30},
    "Hussar":     {"food": 30, "gold": 50, "metal": 20},
}

# Fraction of training cost refunded instantly on troop deletion
TROOP_REFUND_RATE: float = 0.5

# Ammo types and cost per unit
AMMO_COST: dict[str, dict] = {
    "cannon_ball": {"metal": 10, "gold": 5},
    "arrow":       {"timber": 5, "gold": 2},
}

# Which ammo type each defence building uses
DEFENCE_BUILDING_AMMO: dict[str, str] = {
    "Cannon":       "cannon_ball",
    "Archer Tower": "arrow",
}

# Upgrade costs (base at level 1; actual cost = base * BUILDING_LEVEL_MULTIPLIER^(current_level-1))
BUILDING_UPGRADE_COST: dict[str, dict] = {
    "Farm":          {"food": 80,   "timber": 50},
    "Lumber Mill":   {"timber": 80, "gold": 50},
    "Merchant":      {"gold": 120,  "metal": 40},
    "Mine":          {"metal": 80,  "gold": 60},
    "Garrison":      {"gold": 150,  "metal": 80},
    "Stable":        {"gold": 180,  "metal": 100, "timber": 30},
    "Cannon":        {"metal": 150, "gold": 80},
    "Archer Tower":  {"metal": 100, "timber": 80},
    "Command Centre": {"gold": 200, "metal": 100},
}

# Monster camp gold/metal loot on defeat
MONSTER_CAMP_LOOT = {"gold": 50, "metal": 30}

# Starting player resources on registration
PLAYER_START_RESOURCES = {"food": 200.0, "timber": 200.0, "gold": 100.0, "metal": 100.0}

# Phase ordering labels (for logging)
PHASES = [
    "Intent Evaluation",
    "Movement Resolution",
    "Target Selection",
    "Damage Application",
    "Death Resolution",
    "Win Check",
]
