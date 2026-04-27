"""
db/ref_seeder.py — Seeds developer-reference level tables.

Populates ref_building_level and ref_troop_level with pre-computed stats and
costs for every level (1–10) of every building and troop type.

Run via:  flask seed-ref
Re-running is safe (idempotent — skipped if data already exists).

Design notes
────────────
Building cost formula   : base_cost × 2^(level-1)   — doubles each level
Build time formula      : base_time × level           — linear increase
Resource production     : 0.05 × 2^(level-1) /s      — matches engine multiplier
Training interval       : base_interval / 1.15^(level-1)  — 15% faster/level
Training multiplier     : 1.15^(level-1)              — throughput vs level 1
Def unit HP             : base_hp × 1.20^(level-1)
Def unit damage         : base_damage × 1.15^(level-1)
Def unit defense        : base_defense + (level-1)    — flat +1/level

Troop HP                : base_hp × 1.15^(level-1)
Troop damage            : base_damage × 1.10^(level-1)
Troop defense           : base_defense + floor((level-1) × 0.5)  — +1 every 2 levels
Troop cost              : base_cost × 1.50^(level-1)
Troop training time     : base_time × 1.25^(level-1)
"""

from __future__ import annotations

import math

# ── Constants ───────────────────────────────────────────────────────── #

MAX_LEVELS = 10

# Building scaling
_BLDG_COST_GROWTH      = 2.0    # cost doubles per level
_ARMY_SPEED_GROWTH     = 1.15   # training interval shrinks 15%/level
_DEF_HP_GROWTH         = 1.20   # spawned unit HP +20%/level
_DEF_DMG_GROWTH        = 1.15   # spawned unit damage +15%/level
_BASE_PROD_RATE        = 0.05   # resource buildings level-1 output per second

# Troop scaling
_TROOP_HP_GROWTH       = 1.15
_TROOP_DMG_GROWTH      = 1.10
_TROOP_COST_GROWTH     = 1.50
_TROOP_TIME_GROWTH     = 1.25


# ── Building definitions ─────────────────────────────────────────────── #

_RESOURCE_BUILDINGS: dict[str, dict] = {
    "Farm": {
        "category":           "resource",
        "base_costs":         {"gold": 0,   "food": 50,  "timber": 30, "metal": 0},
        "base_build_time":    45,
        "production_resource": "food",
    },
    "Lumber Mill": {
        "category":           "resource",
        "base_costs":         {"gold": 30,  "food": 0,   "timber": 50, "metal": 0},
        "base_build_time":    60,
        "production_resource": "timber",
    },
    "Merchant": {
        "category":           "resource",
        "base_costs":         {"gold": 80,  "food": 0,   "timber": 0,  "metal": 20},
        "base_build_time":    50,
        "production_resource": "gold",
    },
    "Mine": {
        "category":           "resource",
        "base_costs":         {"gold": 40,  "food": 0,   "timber": 0,  "metal": 50},
        "base_build_time":    55,
        "production_resource": "metal",
    },
}

_ARMY_BUILDINGS: dict[str, dict] = {
    "Garrison": {
        "category":                "army",
        "base_costs":              {"gold": 100, "food": 0, "timber": 0,  "metal": 50},
        "base_build_time":         60,
        "unit_produced":           "Longbowman",
        "base_training_interval":  60,   # seconds per unit at level 1
    },
    "Stable": {
        "category":                "army",
        "base_costs":              {"gold": 120, "food": 0, "timber": 20, "metal": 60},
        "base_build_time":         60,
        "unit_produced":           "Hussar",
        "base_training_interval":  90,
    },
}

_DEFENCE_BUILDINGS: dict[str, dict] = {
    "Cannon": {
        "category":          "defence",
        "base_costs":        {"gold": 50, "food": 0, "timber": 0,  "metal": 100},
        "base_build_time":   45,
        "unit_produced":     "Cannon",
        "base_unit_hp":      300,
        "base_unit_damage":  50,
        "base_unit_defense": 30,
        "unit_range":        4,
    },
    "Archer Tower": {
        "category":          "defence",
        "base_costs":        {"gold": 0,  "food": 0, "timber": 60, "metal": 60},
        "base_build_time":   45,
        "unit_produced":     "Archer Tower",
        "base_unit_hp":      200,
        "base_unit_damage":  30,
        "base_unit_defense": 20,
        "unit_range":        3,
    },
}

_SPECIAL_BUILDINGS: dict[str, dict] = {
    "Command Centre": {
        "category": "special",
        "notes":    "Auto-placed in slot 0 of every castle and fort. Cannot be removed or upgraded.",
    },
}


# ── Troop definitions ────────────────────────────────────────────────── #

_TROOPS: dict[str, dict] = {
    "Barbarian": {
        "category":          "infantry",
        "base_hp":           100, "base_damage": 10, "base_defense": 0,
        "base_range":        1,   "speed": 1.0,
        "base_costs":        {"gold": 5,  "food": 3,  "timber": 0, "metal": 0},
        "base_training_time": 30,
        "lore": (
            "Fierce melee warrior. Advances every tick and overwhelms "
            "defences with sheer numbers."
        ),
        "notes": None,
    },
    "Archer": {
        "category":          "ranged",
        "base_hp":           60,  "base_damage": 20, "base_defense": 0,
        "base_range":        2,   "speed": 0.5,
        "base_costs":        {"gold": 8,  "food": 2,  "timber": 0, "metal": 0},
        "base_training_time": 45,
        "lore": (
            "Disciplined ranged unit. Hangs back to rain arrows "
            "while others advance."
        ),
        "notes": None,
    },
    "Troll": {
        "category":          "monster",
        "base_hp":           200, "base_damage": 30, "base_defense": 20,
        "base_range":        1,   "speed": 1.0,
        "base_costs":        {"gold": 20, "food": 5,  "timber": 0, "metal": 5},
        "base_training_time": 120,
        "lore": (
            "Massive brute found guarding monster camps. "
            "High HP and natural armour."
        ),
        "notes": "Monster unit. Naturally spawns in forts and monster camps.",
    },
    "Wraith": {
        "category":          "monster",
        "base_hp":           80,  "base_damage": 30, "base_defense": 0,
        "base_range":        3,   "speed": 1.0,
        "base_costs":        {"gold": 25, "food": 0,  "timber": 0, "metal": 10},
        "base_training_time": 120,
        "lore": (
            "Spectral assassin. Blurs across the battlefield to deliver "
            "devastating ranged strikes."
        ),
        "notes": "Monster unit. Naturally spawns in forts and monster camps.",
    },
    "Longbowman": {
        "category":          "ranged",
        "base_hp":           60,  "base_damage": 20, "base_defense": 0,
        "base_range":        3,   "speed": 0.5,
        "base_costs":        {"gold": 12, "food": 2,  "timber": 3, "metal": 0},
        "base_training_time": 60,
        "lore": (
            "Trained bowman from the Garrison. Steady, long-range support "
            "for assault waves."
        ),
        "notes": "Produced by the Garrison building.",
    },
    "Hussar": {
        "category":          "cavalry",
        "base_hp":           80,  "base_damage": 30, "base_defense": 10,
        "base_range":        1,   "speed": 2.0,
        "base_costs":        {"gold": 18, "food": 5,  "timber": 0, "metal": 4},
        "base_training_time": 90,
        "lore": (
            "Fast cavalry from the Stable. Charges at twice normal speed, "
            "punching through lines."
        ),
        "notes": "Produced by the Stable building.",
    },
    "Cannon": {
        "category":          "siege_defence",
        "base_hp":           300, "base_damage": 50, "base_defense": 30,
        "base_range":        4,   "speed": 0.0,
        "base_costs":        {"gold": 50, "food": 0,  "timber": 0,  "metal": 80},
        "base_training_time": 300,
        "lore": (
            "Heavy defensive emplacement. Stationary but deals massive "
            "damage at great range."
        ),
        "notes": "Spawned into battle from the Cannon building. Stationary (speed 0).",
    },
    "Archer Tower": {
        "category":          "siege_defence",
        "base_hp":           200, "base_damage": 30, "base_defense": 20,
        "base_range":        3,   "speed": 0.0,
        "base_costs":        {"gold": 35, "food": 0,  "timber": 30, "metal": 50},
        "base_training_time": 300,
        "lore": (
            "Fortified arrow platform. Defends locations with "
            "sustained ranged fire."
        ),
        "notes": "Spawned into battle from the Archer Tower building. Stationary (speed 0).",
    },
    # ── Tier-10 monster types ────────────────────────────────────────── #
    # Appear in star-level 7-10 camps and forts.
    # Stats are set so that ~1 billion level-10 Barbarians+Archers (16 cells,
    # 62.5M per cell) barely defeat 2 Demons/Pegasi.
    "Demon": {
        "category":          "monster",
        "base_hp":           400_000_000_000,    # 400 billion
        "base_damage":       1_200_000_000,       # 1.2 billion
        "base_defense":      1_000_000_000,       # 1 billion — blocks unstacked troops
        "base_range":        1,  "speed": 1.0,
        "base_costs":        {"gold": 0, "food": 0, "timber": 0, "metal": 0},
        "base_training_time": 0,
        "lore": (
            "An ancient infernal champion. Its armour alone repels all but "
            "the most overwhelming forces."
        ),
        "notes": "Tier-10 monster unit. Spawns in star-level 7-10 forts and camps.",
    },
    "Pegasus": {
        "category":          "monster",
        "base_hp":           250_000_000_000,    # 250 billion
        "base_damage":       2_000_000_000,       # 2 billion
        "base_defense":      0,
        "base_range":        3,  "speed": 0.5,
        "base_costs":        {"gold": 0, "food": 0, "timber": 0, "metal": 0},
        "base_training_time": 0,
        "lore": (
            "A demonic winged hunter. Unarmoured but deals catastrophic "
            "ranged damage from afar."
        ),
        "notes": "Tier-10 monster unit. Spawns in star-level 7-10 forts and camps.",
    },
}


# ── Row builders ─────────────────────────────────────────────────────── #

def _building_rows() -> list[dict]:
    rows: list[dict] = []

    # Resource buildings
    for name, d in _RESOURCE_BUILDINGS.items():
        base = d["base_costs"]
        for lvl in range(1, MAX_LEVELS + 1):
            cost_m = _BLDG_COST_GROWTH ** (lvl - 1)
            rows.append({
                "building_type":              name,
                "category":                   d["category"],
                "level":                      lvl,
                "gold_cost":                  round(base["gold"]   * cost_m),
                "food_cost":                  round(base["food"]   * cost_m),
                "timber_cost":                round(base["timber"] * cost_m),
                "metal_cost":                 round(base["metal"]  * cost_m),
                "build_time_seconds":         d["base_build_time"] * lvl,
                "production_resource":        d["production_resource"],
                "production_rate_per_second": round(_BASE_PROD_RATE * (2 ** (lvl - 1)), 8),
                "unit_produced":              None,
                "training_interval_seconds":  None,
                "training_multiplier":        None,
                "spawned_unit_hp":            None,
                "spawned_unit_damage":        None,
                "spawned_unit_defense":       None,
                "spawned_unit_range":         None,
                "notes":                      None,
            })

    # Army buildings
    for name, d in _ARMY_BUILDINGS.items():
        base = d["base_costs"]
        for lvl in range(1, MAX_LEVELS + 1):
            cost_m  = _BLDG_COST_GROWTH ** (lvl - 1)
            speed_f = _ARMY_SPEED_GROWTH ** (lvl - 1)
            rows.append({
                "building_type":              name,
                "category":                   d["category"],
                "level":                      lvl,
                "gold_cost":                  round(base["gold"]   * cost_m),
                "food_cost":                  round(base["food"]   * cost_m),
                "timber_cost":                round(base["timber"] * cost_m),
                "metal_cost":                 round(base["metal"]  * cost_m),
                "build_time_seconds":         d["base_build_time"] * lvl,
                "production_resource":        None,
                "production_rate_per_second": None,
                "unit_produced":              d["unit_produced"],
                "training_interval_seconds":  round(d["base_training_interval"] / speed_f),
                "training_multiplier":        round(speed_f, 6),
                "spawned_unit_hp":            None,
                "spawned_unit_damage":        None,
                "spawned_unit_defense":       None,
                "spawned_unit_range":         None,
                "notes":                      None,
            })

    # Defence buildings
    for name, d in _DEFENCE_BUILDINGS.items():
        base = d["base_costs"]
        for lvl in range(1, MAX_LEVELS + 1):
            cost_m = _BLDG_COST_GROWTH ** (lvl - 1)
            rows.append({
                "building_type":              name,
                "category":                   d["category"],
                "level":                      lvl,
                "gold_cost":                  round(base["gold"]   * cost_m),
                "food_cost":                  round(base["food"]   * cost_m),
                "timber_cost":                round(base["timber"] * cost_m),
                "metal_cost":                 round(base["metal"]  * cost_m),
                "build_time_seconds":         d["base_build_time"] * lvl,
                "production_resource":        None,
                "production_rate_per_second": None,
                "unit_produced":              d["unit_produced"],
                "training_interval_seconds":  None,
                "training_multiplier":        None,
                "spawned_unit_hp":            round(d["base_unit_hp"]     * (_DEF_HP_GROWTH  ** (lvl - 1))),
                "spawned_unit_damage":        round(d["base_unit_damage"] * (_DEF_DMG_GROWTH ** (lvl - 1))),
                "spawned_unit_defense":       d["base_unit_defense"] + (lvl - 1),
                "spawned_unit_range":         d["unit_range"],
                "notes":                      None,
            })

    # Special buildings (no upgrade levels)
    for name, d in _SPECIAL_BUILDINGS.items():
        rows.append({
            "building_type":              name,
            "category":                   d["category"],
            "level":                      1,
            "gold_cost":                  0,
            "food_cost":                  0,
            "timber_cost":                0,
            "metal_cost":                 0,
            "build_time_seconds":         0,
            "production_resource":        None,
            "production_rate_per_second": None,
            "unit_produced":              None,
            "training_interval_seconds":  None,
            "training_multiplier":        None,
            "spawned_unit_hp":            None,
            "spawned_unit_damage":        None,
            "spawned_unit_defense":       None,
            "spawned_unit_range":         None,
            "notes":                      d["notes"],
        })

    return rows


def _troop_rows() -> list[dict]:
    rows: list[dict] = []

    for name, d in _TROOPS.items():
        base = d["base_costs"]
        for lvl in range(1, MAX_LEVELS + 1):
            cost_m = _TROOP_COST_GROWTH ** (lvl - 1)
            time_m = _TROOP_TIME_GROWTH ** (lvl - 1)
            rows.append({
                "troop_type":            name,
                "category":              d["category"],
                "level":                 lvl,
                "hp":                    round(d["base_hp"]     * (_TROOP_HP_GROWTH  ** (lvl - 1))),
                "damage":                round(d["base_damage"] * (_TROOP_DMG_GROWTH ** (lvl - 1))),
                "defense":               d["base_defense"] + math.floor((lvl - 1) * 0.5),
                "range":                 d["base_range"],
                "speed":                 d["speed"],
                "attack_speed":          1.0,
                "gold_cost":             round(base["gold"]   * cost_m),
                "food_cost":             round(base["food"]   * cost_m),
                "timber_cost":           round(base["timber"] * cost_m),
                "metal_cost":            round(base["metal"]  * cost_m),
                "training_time_seconds": round(d["base_training_time"] * time_m),
                # lore and notes stored once (at level 1) to avoid redundancy
                "lore":                  d["lore"]  if lvl == 1 else None,
                "notes":                 d["notes"] if lvl == 1 else None,
            })

    return rows


# ── Public seeder ────────────────────────────────────────────────────── #

_INSERT_BUILDING = """
    INSERT INTO ref_building_level (
        building_type, category, level,
        gold_cost, food_cost, timber_cost, metal_cost,
        build_time_seconds,
        production_resource, production_rate_per_second,
        unit_produced, training_interval_seconds, training_multiplier,
        spawned_unit_hp, spawned_unit_damage, spawned_unit_defense, spawned_unit_range,
        notes
    ) VALUES (
        :building_type, :category, :level,
        :gold_cost, :food_cost, :timber_cost, :metal_cost,
        :build_time_seconds,
        :production_resource, :production_rate_per_second,
        :unit_produced, :training_interval_seconds, :training_multiplier,
        :spawned_unit_hp, :spawned_unit_damage, :spawned_unit_defense, :spawned_unit_range,
        :notes
    )
"""

_INSERT_TROOP = """
    INSERT INTO ref_troop_level (
        troop_type, category, level,
        hp, damage, defense, range, speed, attack_speed,
        gold_cost, food_cost, timber_cost, metal_cost,
        training_time_seconds,
        lore, notes
    ) VALUES (
        :troop_type, :category, :level,
        :hp, :damage, :defense, :range, :speed, :attack_speed,
        :gold_cost, :food_cost, :timber_cost, :metal_cost,
        :training_time_seconds,
        :lore, :notes
    )
"""


def seed_ref(db) -> dict:
    """
    Insert all building and troop level rows into the reference tables.
    Idempotent: returns skipped=True if data already exists.
    Returns a dict: {buildings: int, troops: int, skipped: bool}.
    """
    existing = db.execute("SELECT COUNT(*) FROM ref_building_level").fetchone()[0]
    if existing > 0:
        return {"buildings": 0, "troops": 0, "skipped": True}

    b_rows = _building_rows()
    t_rows = _troop_rows()

    db.executemany(_INSERT_BUILDING, b_rows)
    db.executemany(_INSERT_TROOP, t_rows)
    db.commit()

    return {"buildings": len(b_rows), "troops": len(t_rows), "skipped": False}
