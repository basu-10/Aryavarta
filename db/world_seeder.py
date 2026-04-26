"""
db/world_seeder.py — Seeds initial forts and monster camps onto the world map.

Called via `flask seed-world` CLI command, or during testing fixtures.
All placements are random; calling this multiple times adds more entities.
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


def seed_world(num_forts: int = 15, num_camps: int = 10) -> dict:
    """
    Place `num_forts` monster-occupied forts and `num_camps` standalone monster camps.
    Idempotent: skips seeding entirely if forts or camps already exist in the DB.
    Returns a dict with counts of what was seeded (both 0 if already seeded).
    """
    from db import get_db
    db = get_db()
    existing_forts = db.execute("SELECT COUNT(*) FROM fort").fetchone()[0]
    existing_camps = db.execute("SELECT COUNT(*) FROM monster_camp").fetchone()[0]
    if existing_forts > 0 or existing_camps > 0:
        return {"forts": 0, "camps": 0, "skipped": True}

    forts_created = 0
    camps_created = 0

    for _ in range(num_forts):
        star = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
        monster_data = _random_monster_spec(star)
        slot_count = random.choices(
            [4, 5, 6, 7, 8, 9, 10],
            weights=config.FORT_SLOT_WEIGHTS,
        )[0]
        x, y = m.find_empty_cell()
        m.create_fort(slot_count, x, y, monster_data, star)
        forts_created += 1

    for _ in range(num_camps):
        star = random.choices([1, 2, 3, 4], weights=[30, 35, 25, 10])[0]
        unit_data = _random_monster_spec(star)
        x, y = m.find_empty_cell()
        m.create_monster_camp(x, y, unit_data, star)
        camps_created += 1

    return {"forts": forts_created, "camps": camps_created}
