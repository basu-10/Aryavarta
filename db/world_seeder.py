"""
db/world_seeder.py — Seeds initial forts and monster camps onto the world map.

Called via `flask seed-world` CLI command, at app startup, or via the admin panel.
"""

from __future__ import annotations

import random

import config
from db import models as m


# Monster types that appear in wild camps and unowned forts
_MONSTER_TYPES = ["Troll", "Wraith"]


def _random_monster_spec(star_level: int) -> list[dict]:
    """
    Build a unit spec list for the given star level.
    Returns [{type, count}, ...] with total units matching the star level.
    """
    thresholds = config.STAR_THRESHOLDS
    if star_level <= 1:
        total = random.randint(1, thresholds[0])
    elif star_level == 2:
        total = random.randint(thresholds[0] + 1, thresholds[1])
    elif star_level == 3:
        total = random.randint(thresholds[1] + 1, thresholds[2])
    else:
        max_cells = config.GRID_ROWS * len(config.TEAM_B_COLS)
        total = random.randint(thresholds[2] + 1, max_cells)

    spec: dict[str, int] = {}
    for _ in range(total):
        mtype = random.choice(_MONSTER_TYPES)
        spec[mtype] = spec.get(mtype, 0) + 1

    return [{"type": t, "count": c} for t, c in spec.items()]


def _count_monster_forts() -> int:
    """Count unowned (monster-occupied) forts."""
    from db import get_db
    return get_db().execute("SELECT COUNT(*) FROM fort WHERE owner_id IS NULL").fetchone()[0]


def _count_active_camps() -> int:
    from db import get_db
    return get_db().execute("SELECT COUNT(*) FROM monster_camp WHERE is_active=1").fetchone()[0]


def seed_world(num_forts: int = 15, num_camps: int = 10, force: bool = False) -> dict:
    """
    Place `num_forts` monster-occupied forts and `num_camps` standalone monster camps.
    Skips seeding if the target counts are already met (unless force=True).
    Returns a dict with counts of what was seeded.
    """
    existing_forts = _count_monster_forts()
    existing_camps = _count_active_camps()

    if not force and existing_forts >= num_forts and existing_camps >= num_camps:
        return {"forts": 0, "camps": 0, "skipped": True}

    forts_to_create = max(0, num_forts - existing_forts) if not force else num_forts
    camps_to_create = max(0, num_camps - existing_camps) if not force else num_camps

    forts_created = 0
    for _ in range(forts_to_create):
        star = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
        monster_data = _random_monster_spec(star)
        slot_count = random.choices(
            [4, 5, 6, 7, 8, 9, 10],
            weights=config.FORT_SLOT_WEIGHTS,
        )[0]
        x, y = m.find_empty_cell()
        m.create_fort(slot_count, x, y, monster_data, star)
        forts_created += 1

    camps_created = 0
    for _ in range(camps_to_create):
        star = random.choices([1, 2, 3, 4], weights=[30, 35, 25, 10])[0]
        unit_data = _random_monster_spec(star)
        x, y = m.find_empty_cell()
        m.create_monster_camp(x, y, unit_data, star)
        camps_created += 1

    return {"forts": forts_created, "camps": camps_created}


def ensure_world_entities() -> dict:
    """
    Top up monster forts and camps to the configured maximums if they fall below.
    Called automatically on app startup and on each world map API call.
    """
    existing_forts = _count_monster_forts()
    existing_camps = _count_active_camps()

    need_forts = max(0, config.MAX_MONSTER_FORTS - existing_forts)
    need_camps = max(0, config.MAX_MONSTER_CAMPS - existing_camps)

    if need_forts == 0 and need_camps == 0:
        return {"forts": 0, "camps": 0}

    return seed_world(num_forts=config.MAX_MONSTER_FORTS,
                      num_camps=config.MAX_MONSTER_CAMPS,
                      force=False)

