# BattleCells — Central Configuration

GRID_ROWS = 4
GRID_COLS = 11   # Columns 0-10: A-defense(0) | A-troops(1-4) | NML(5) | B-troops(6-9) | B-defense(10)

# Valid placement columns per team (units face each other left vs right)
TEAM_A_COLS = [1, 2, 3, 4]   # Team A starts on the left
TEAM_B_COLS = [6, 7, 8, 9]   # Team B starts on the right
# Column 5 is no-man's land
NO_MANS_LAND_COL = 5
# Defense columns — buildings (Cannon, Archer Tower) spawn here, outside the troop zone
TEAM_A_DEF_COL = 0   # behind Team A's back line; Team B units attack this column
TEAM_B_DEF_COL = 10  # behind Team B's back line; Team A units attack this column

# Building unit types — stationary, not player-dispatched, only appear as defenders
BUILDING_TYPES = ["Cannon", "Archer Tower"]

MAX_TICKS = 500  # Safety ceiling to prevent infinite loops — raised to handle high-HP battles

# Unit base stats registry (LEVEL 1 base stats)
# All human troops scaled to Barbarian base_hp = 100 (10× rescale from original).
# Monster roster tiers:
#   Star 1 starts at Troll/Wraith.
#   Stars 2-9 introduce progressively stronger mythical pairs.
#   Star 10 is the apex Demon/Pegasus pair.
# speed: 1.0 = 1 cell/tick (1x), 0.5 = 1 cell every 2 ticks (0.5x)
UNIT_STATS: dict[str, dict] = {
    "Barbarian": {
        "hp": 100,
        "damage": 10,
        "defense": 0,
        "range": 1,
        "speed": 1.0,   # 1x — advances 1 cell every tick
    },
    "Archer": {
        "hp": 60,
        "damage": 20,
        "defense": 0,
        "range": 2,
        "speed": 0.5,   # 0.5x — advances 1 cell every 2 ticks
    },
    "Troll": {
        "hp": 200,
        "damage": 30,
        "defense": 20,
        "range": 1,
        "speed": 1.0,   # 1x melee brute
        "attack_speed": 1.0,
    },
    "Wraith": {
        "hp": 80,
        "damage": 30,
        "defense": 0,
        "range": 3,
        "speed": 1.0,   # 1x fast ranged glass cannon
        "attack_speed": 1.1,
    },
    "Goblin Brute": {
        "hp": 450,
        "damage": 55,
        "defense": 35,
        "range": 1,
        "speed": 1.0,
        "attack_speed": 0.95,
    },
    "Harpy": {
        "hp": 220,
        "damage": 70,
        "defense": 10,
        "range": 3,
        "speed": 1.0,
        "attack_speed": 1.05,
    },
    "Minotaur": {
        "hp": 900,
        "damage": 95,
        "defense": 70,
        "range": 1,
        "speed": 1.0,
        "attack_speed": 0.9,
    },
    "Basilisk": {
        "hp": 450,
        "damage": 120,
        "defense": 30,
        "range": 3,
        "speed": 0.9,
        "attack_speed": 1.0,
    },
    "Gargoyle": {
        "hp": 1_800,
        "damage": 170,
        "defense": 130,
        "range": 1,
        "speed": 0.9,
        "attack_speed": 0.85,
    },
    "Manticore": {
        "hp": 900,
        "damage": 210,
        "defense": 55,
        "range": 3,
        "speed": 0.9,
        "attack_speed": 0.95,
    },
    "Hydra": {
        "hp": 3_600,
        "damage": 300,
        "defense": 240,
        "range": 1,
        "speed": 0.9,
        "attack_speed": 0.8,
    },
    "Siren": {
        "hp": 1_700,
        "damage": 360,
        "defense": 100,
        "range": 3,
        "speed": 0.8,
        "attack_speed": 0.9,
    },
    "Behemoth": {
        "hp": 8_000,
        "damage": 520,
        "defense": 420,
        "range": 1,
        "speed": 0.8,
        "attack_speed": 0.78,
    },
    "Chimera": {
        "hp": 3_600,
        "damage": 650,
        "defense": 180,
        "range": 4,
        "speed": 0.8,
        "attack_speed": 0.88,
    },
    "Leviathan": {
        "hp": 20_000,
        "damage": 1_200,
        "defense": 900,
        "range": 1,
        "speed": 0.8,
        "attack_speed": 0.75,
    },
    "Phoenix": {
        "hp": 10_000,
        "damage": 1_700,
        "defense": 320,
        "range": 4,
        "speed": 0.7,
        "attack_speed": 0.85,
    },
    "Colossus": {
        "hp": 120_000,
        "damage": 8_000,
        "defense": 6_000,
        "range": 1,
        "speed": 0.7,
        "attack_speed": 0.72,
    },
    "Thunderbird": {
        "hp": 70_000,
        "damage": 11_000,
        "defense": 2_200,
        "range": 4,
        "speed": 0.7,
        "attack_speed": 0.82,
    },
    "Abyssal Titan": {
        "hp": 8_000_000,
        "damage": 300_000,
        "defense": 180_000,
        "range": 1,
        "speed": 0.7,
        "attack_speed": 0.7,
    },
    "Void Drake": {
        "hp": 5_000_000,
        "damage": 420_000,
        "defense": 90_000,
        "range": 4,
        "speed": 0.6,
        "attack_speed": 0.8,
    },
    "Longbowman": {
        "hp": 60,
        "damage": 20,
        "defense": 0,
        "range": 3,
        "speed": 0.5,   # slow, long-range infantry
    },
    "Hussar": {
        "hp": 80,
        "damage": 30,
        "defense": 10,
        "range": 1,
        "speed": 2.0,   # fast cavalry
    },
    "Cannon": {
        "hp": 300,
        "damage": 50,
        "defense": 30,
        "range": 4,
        "speed": 0.0,   # stationary defence building unit
    },
    "Archer Tower": {
        "hp": 200,
        "damage": 30,
        "defense": 20,
        "range": 3,
        "speed": 0.0,   # stationary defence building unit
    },
    # ── Tier-10 monster types ────────────────────────────────────────── #
    # Require ~1 billion stacked level-10 Barbarians+Archers (across all 16
    # attacker cells) to defeat 2 Demons — the minimum spawn count.
    "Demon": {
        "hp": 400_000_000_000,       # 400 billion
        "damage": 1_200_000_000,     # 1.2 billion
        "defense": 1_000_000_000,    # 1 billion — blocks all but stacked troops
        "range": 1,
        "speed": 1.0,
        "attack_speed": 0.68,
    },
    "Pegasus": {
        "hp": 250_000_000_000,       # 250 billion
        "damage": 2_000_000_000,     # 2 billion
        "defense": 0,                # No physical armour — pure glass-cannon
        "range": 3,
        "speed": 0.5,
        "attack_speed": 0.78,
    },
}

UNIT_TYPES = list(UNIT_STATS.keys())

# Troop classification metadata: faction (human/monster) and type (melee/ranged)
UNIT_CLASSIFICATION: dict[str, dict] = {
    "Barbarian": {"faction": "human", "type": "melee"},
    "Archer": {"faction": "human", "type": "ranged"},
    "Troll": {"faction": "monster", "type": "melee"},
    "Wraith": {"faction": "monster", "type": "ranged"},
    "Goblin Brute": {"faction": "monster", "type": "melee"},
    "Harpy": {"faction": "monster", "type": "ranged"},
    "Minotaur": {"faction": "monster", "type": "melee"},
    "Basilisk": {"faction": "monster", "type": "ranged"},
    "Gargoyle": {"faction": "monster", "type": "melee"},
    "Manticore": {"faction": "monster", "type": "ranged"},
    "Hydra": {"faction": "monster", "type": "melee"},
    "Siren": {"faction": "monster", "type": "ranged"},
    "Behemoth": {"faction": "monster", "type": "melee"},
    "Chimera": {"faction": "monster", "type": "ranged"},
    "Leviathan": {"faction": "monster", "type": "melee"},
    "Phoenix": {"faction": "monster", "type": "ranged"},
    "Colossus": {"faction": "monster", "type": "melee"},
    "Thunderbird": {"faction": "monster", "type": "ranged"},
    "Abyssal Titan": {"faction": "monster", "type": "melee"},
    "Void Drake": {"faction": "monster", "type": "ranged"},
    "Longbowman": {"faction": "human", "type": "ranged"},
    "Hussar": {"faction": "human", "type": "melee"},
    "Cannon": {"faction": "human", "type": "ranged"},
    "Archer Tower": {"faction": "human", "type": "ranged"},
    "Demon": {"faction": "monster", "type": "melee"},
    "Pegasus": {"faction": "monster", "type": "ranged"},
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

# Monster fort/camp spawn table (star levels 1-10)
MONSTER_STAR_SPAWN_WEIGHTS: dict[int, int] = {
    1:  20,
    2:  18,
    3:  15,
    4:  12,
    5:  10,
    6:   8,
    7:   7,
    8:   5,
    9:   3,
    10:  2,
}

# Monster unit pair per star level
MONSTER_STAR_TIER: dict[int, list[str]] = {
    1:  ["Troll", "Wraith"],
    2:  ["Goblin Brute", "Harpy"],
    3:  ["Minotaur", "Basilisk"],
    4:  ["Gargoyle", "Manticore"],
    5:  ["Hydra", "Siren"],
    6:  ["Behemoth", "Chimera"],
    7:  ["Leviathan", "Phoenix"],
    8:  ["Colossus", "Thunderbird"],
    9:  ["Abyssal Titan", "Void Drake"],
    10: ["Demon", "Pegasus"],
}

MONSTER_STAR_UNIT_RANGES: dict[int, tuple[int, int]] = {
    1:  (2,  3),
    2:  (4,  5),
    3:  (6,  8),
    4:  (9,  11),
    5:  (12, 14),
    6:  (15, 16),
    7:  (17, 19),
    8:  (20, 22),
    9:  (23, 25),
    10: (26, 30),
}

# Generic star thresholds derived from the world spawn table.
STAR_THRESHOLDS = [
    max_units
    for _, max_units in list(MONSTER_STAR_UNIT_RANGES.values())[:-1]
]

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
# Starter pack — enough to place all 4 resource buildings (Farm, Lumber Mill,
# Merchant, Mine), both army buildings (Garrison, Stable), and train a
# comfortable first army (≈20 Longbowmen + 15 Hussars) to defeat a star-1 fort.
PLAYER_START_RESOURCES = {"food": 1000.0, "timber": 350.0, "gold": 1800.0, "metal": 500.0}

# Phase ordering labels (for logging)
PHASES = [
    "Intent Evaluation",
    "Movement Resolution",
    "Target Selection",
    "Damage Application",
    "Death Resolution",
    "Win Check",
]

# ── Theme Configuration ─────────────────────────────────────────────── #
ACTIVE_THEME = "theme1"  # Switch between "theme1" and "theme2" from admin panel
AVAILABLE_THEMES = ["theme1", "theme2"]
