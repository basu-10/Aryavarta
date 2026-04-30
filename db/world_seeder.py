"""
db/world_seeder.py — Seeds initial forts and monster camps onto the world map.

Called via `flask seed-world` CLI command, at app startup, or via the admin panel.
"""

from __future__ import annotations

import random
from typing import Optional

import config
from db import get_db, models as m


# Monster types that appear in wild camps and unowned forts, keyed by star tier
_MONSTER_TYPES = ["Troll", "Wraith"]  # legacy fallback

# Decoration defaults (no form fields — hardcoded here)
_DEFAULT_TREES = 20
_DEFAULT_BUSHES = 10
_DEFAULT_FOREST_CLUSTERS = 3
_CLUSTER_SIZE_MIN = 3
_CLUSTER_SIZE_MAX = 7


def _random_star_level(minimum: int = 1) -> int:
    star_levels = list(config.MONSTER_STAR_SPAWN_WEIGHTS.keys())
    weights = list(config.MONSTER_STAR_SPAWN_WEIGHTS.values())
    result = random.choices(star_levels, weights=weights)[0]
    return max(minimum, result)


def _find_edge_cell(grid_w: int, grid_h: int,
                    occupied: set[tuple[int, int]]) -> tuple[int, int] | None:
    """Return a random unoccupied cell on the world border, or None if all edges are full."""
    edges: list[tuple[int, int]] = []
    for x in range(grid_w):
        edges.append((x, 0))
        edges.append((x, grid_h - 1))
    for y in range(1, grid_h - 1):
        edges.append((0, y))
        edges.append((grid_w - 1, y))
    random.shuffle(edges)
    for pos in edges:
        if pos not in occupied:
            occupied.add(pos)
            return pos
    return None


def _seed_npc_population(world_id: int, grid_w: int, grid_h: int,
                         occupied: set[tuple[int, int]]) -> dict:
    """
    Create NPC players for a world, placing their castles on the world edges
    and distributing owned forts across the interior.

    NPC count and forts per NPC scale with world size:
      - Small world  (50×50  = 2 500 cells) → ~3 NPCs, ~3 forts each
      - Medium world (100×100= 10 000 cells) → ~10 NPCs, ~4 forts each
      - Large world  (200×200= 40 000 cells) → ~20 NPCs, ~6 forts each
    """
    area = grid_w * grid_h
    npc_count    = max(3, min(20, area // 800))
    forts_per_npc = max(2, min(8, area // (max(1, npc_count) * 300)))

    used_names: set[str] = {
        r["username"]
        for r in get_db().execute(
            "SELECT username FROM player WHERE role='npc'"
        ).fetchall()
    }
    # Build a pool of names, extending with numbered fallbacks as needed
    _base_names = [
        "Lord Malachar", "Baron Thorvik", "Lady Seraphine", "Duke Grawl",
        "Countess Vex", "Prince Daeron", "General Strix", "Empress Zyla",
        "Governor Krath", "Warlord Fenris", "Knight Aldric", "Duke Vrenn",
        "Lady Morwyn", "Baron Cassix", "Lord Turvak", "Count Dreyden",
        "Chieftain Rox", "Margrave Solen", "Thane Brekka", "Archon Zelva",
    ]
    available = [n for n in _base_names if n not in used_names]
    while len(available) < npc_count:
        available.append(f"NPC-{random.randint(1000, 9999)}")

    castles_placed = 0
    forts_placed = 0

    for i in range(npc_count):
        name = available[i]
        npc_id = m.create_npc_player(name)

        # Castle — prefer world edge; fall back to random interior if edges full
        edge = _find_edge_cell(grid_w, grid_h, occupied)
        if edge:
            cx, cy = edge
        else:
            cx, cy = m.find_empty_cell(world_id, grid_w, grid_h)
            occupied.add((cx, cy))
        m.create_castle(npc_id, 8, cx, cy, world_id)
        castles_placed += 1

        # Owned forts — placed anywhere non-occupied
        for _ in range(forts_per_npc):
            # Pick a random unoccupied cell (interior preferred)
            fx, fy = m.find_empty_cell(world_id, grid_w, grid_h)
            occupied.add((fx, fy))
            star = random.randint(1, 3)
            fort_id = m.create_fort(8, fx, fy, [], star, world_id)
            m.claim_fort(fort_id, npc_id)
            forts_placed += 1

    return {"npcs": npc_count, "npc_castles": castles_placed, "npc_forts": forts_placed}


def _random_monster_spec(star_level: int) -> list[dict]:
    """
    Build a unit spec list for the given star level.
    Returns [{type, count}, ...] with total units matching the star level.
    Monster types are drawn from config.MONSTER_STAR_TIER for the given star.
    """
    min_units, max_units = config.MONSTER_STAR_UNIT_RANGES[star_level]
    total = random.randint(min_units, max_units)
    monster_types = config.MONSTER_STAR_TIER.get(star_level, _MONSTER_TYPES)

    spec: dict[str, int] = {}
    for _ in range(total):
        mtype = random.choice(monster_types)
        spec[mtype] = spec.get(mtype, 0) + 1

    return [{"type": t, "count": c} for t, c in spec.items()]


def _count_monster_forts(world_id: Optional[int] = None) -> int:
    """Count unowned (monster-occupied) forts."""
    from db import get_db
    if world_id is not None:
        return get_db().execute(
            "SELECT COUNT(*) FROM fort WHERE owner_id IS NULL AND world_id=?", (world_id,)
        ).fetchone()[0]
    return get_db().execute("SELECT COUNT(*) FROM fort WHERE owner_id IS NULL").fetchone()[0]


def _count_active_camps(world_id: Optional[int] = None) -> int:
    from db import get_db
    if world_id is not None:
        return get_db().execute(
            "SELECT COUNT(*) FROM monster_camp WHERE is_active=1 AND world_id=?", (world_id,)
        ).fetchone()[0]
    return get_db().execute("SELECT COUNT(*) FROM monster_camp WHERE is_active=1").fetchone()[0]


def _place_decorations(world_id: int, grid_w: int, grid_h: int) -> dict:
    """Place trees, bushes and forest clusters for the given world."""
    m.clear_map_decorations(world_id)
    occupied = m.get_occupied_world_cells(world_id)

    def _place(dtype: str, scale: float, cluster_id: Optional[int] = None) -> bool:
        for _ in range(200):
            x = random.randint(0, grid_w - 1)
            y = random.randint(0, grid_h - 1)
            if (x, y) not in occupied:
                occupied.add((x, y))
                m.create_map_decoration(world_id, dtype, x, y, scale, cluster_id)
                return True
        return False

    trees_placed = 0
    bushes_placed = 0
    next_cluster = 1

    # Forest clusters (groups of trees)
    for _ in range(_DEFAULT_FOREST_CLUSTERS):
        size = random.randint(_CLUSTER_SIZE_MIN, _CLUSTER_SIZE_MAX)
        cid = next_cluster
        next_cluster += 1
        # Pick a cluster centre
        cx = random.randint(1, grid_w - 2)
        cy = random.randint(1, grid_h - 2)
        placed_in_cluster = 0
        for _ in range(size * 4):
            if placed_in_cluster >= size:
                break
            dx = random.randint(-2, 2)
            dy = random.randint(-2, 2)
            x = max(0, min(grid_w - 1, cx + dx))
            y = max(0, min(grid_h - 1, cy + dy))
            if (x, y) not in occupied:
                occupied.add((x, y))
                scale = round(random.uniform(0.8, 1.5), 2)
                m.create_map_decoration(world_id, "tree", x, y, scale, cid)
                placed_in_cluster += 1
                trees_placed += 1

    # Standalone trees
    for _ in range(_DEFAULT_TREES):
        scale = round(random.uniform(0.8, 1.4), 2)
        if _place("tree", scale, None):
            trees_placed += 1

    # Standalone bushes
    for _ in range(_DEFAULT_BUSHES):
        scale = round(random.uniform(0.6, 1.2), 2)
        if _place("bush", scale, None):
            bushes_placed += 1

    return {"trees": trees_placed, "bushes": bushes_placed}


def generate_world(world_id: int, grid_w: int, grid_h: int,
                   num_forts: int, num_camps: int) -> dict:
    """
    Fully populate a world with:
      1. NPC players — castles on edges, owned forts scattered inside
      2. Unowned monster forts
      3. Standalone monster camps
      4. Decorative tiles (trees, bushes)
    """
    # Track occupied cells across all placement phases to avoid overlaps
    occupied = m.get_occupied_world_cells(world_id)

    # ── Phase 1: NPC castles + forts ──────────────────────────────── #
    npc_stats = _seed_npc_population(world_id, grid_w, grid_h, occupied)

    # ── Phase 2: Monster forts (unowned) ──────────────────────────── #
    forts_created = 0
    for _ in range(num_forts):
        star = _random_star_level(minimum=1)
        monster_data = _random_monster_spec(star)
        slot_count = random.choices(
            [4, 5, 6, 7, 8, 9, 10],
            weights=config.FORT_SLOT_WEIGHTS,
        )[0]
        x, y = m.find_empty_cell(world_id, grid_w, grid_h)
        occupied.add((x, y))
        m.create_fort(slot_count, x, y, monster_data, star, world_id)
        forts_created += 1

    # ── Phase 3: Monster camps ─────────────────────────────────────── #
    camps_created = 0
    for _ in range(num_camps):
        star = _random_star_level(minimum=1)
        unit_data = _random_monster_spec(star)
        x, y = m.find_empty_cell(world_id, grid_w, grid_h)
        occupied.add((x, y))
        m.create_monster_camp(x, y, unit_data, star, world_id)
        camps_created += 1

    # ── Phase 4: Decorations ──────────────────────────────────────── #
    deco = _place_decorations(world_id, grid_w, grid_h)

    return {
        **npc_stats,
        "forts": forts_created,
        "camps": camps_created,
        "decorations": deco,
    }


def seed_world(num_forts: int = 15, num_camps: int = 10, force: bool = False,
               world_id: Optional[int] = None) -> dict:
    """
    Legacy shim — seeds into the first available world.
    Use generate_world() for explicit world targeting.
    Skips seeding if no worlds exist or target counts are already met (unless force=True).
    Returns a dict with counts of what was seeded.
    """
    # Resolve world
    if world_id is None:
        worlds = m.get_all_worlds()
        if not worlds:
            return {"forts": 0, "camps": 0, "skipped": True, "reason": "no worlds"}
        world_id = worlds[0]["id"]

    world = m.get_world(world_id)
    if not world:
        return {"forts": 0, "camps": 0, "skipped": True, "reason": "world not found"}
    grid_w, grid_h = world["grid_width"], world["grid_height"]

    existing_forts = _count_monster_forts(world_id)
    existing_camps = _count_active_camps(world_id)

    if not force and existing_forts >= num_forts and existing_camps >= num_camps:
        return {"forts": 0, "camps": 0, "skipped": True}

    forts_to_create = max(0, num_forts - existing_forts) if not force else num_forts
    camps_to_create = max(0, num_camps - existing_camps) if not force else num_camps

    forts_created = 0
    for _ in range(forts_to_create):
        star = _random_star_level(minimum=1)
        monster_data = _random_monster_spec(star)
        slot_count = random.choices(
            [4, 5, 6, 7, 8, 9, 10],
            weights=config.FORT_SLOT_WEIGHTS,
        )[0]
        x, y = m.find_empty_cell(world_id, grid_w, grid_h)
        m.create_fort(slot_count, x, y, monster_data, star, world_id)
        forts_created += 1

    camps_created = 0
    for _ in range(camps_to_create):
        star = _random_star_level(minimum=1)
        unit_data = _random_monster_spec(star)
        x, y = m.find_empty_cell(world_id, grid_w, grid_h)
        m.create_monster_camp(x, y, unit_data, star, world_id)
        camps_created += 1

    return {"forts": forts_created, "camps": camps_created}


def ensure_world_entities() -> dict:
    """
    Top up monster forts and camps to the configured maximums if they fall below.
    Called automatically on app startup and on each world map API call.
    No-op when no worlds exist yet.
    """
    worlds = m.get_all_worlds()
    if not worlds:
        return {"forts": 0, "camps": 0}

    totals = {"forts": 0, "camps": 0}
    for world in worlds:
        wid = world["id"]
        existing_forts = _count_monster_forts(wid)
        existing_camps = _count_active_camps(wid)
        need_forts = max(0, config.MAX_MONSTER_FORTS - existing_forts)
        need_camps = max(0, config.MAX_MONSTER_CAMPS - existing_camps)
        if need_forts or need_camps:
            result = seed_world(
                num_forts=config.MAX_MONSTER_FORTS,
                num_camps=config.MAX_MONSTER_CAMPS,
                force=False,
                world_id=wid,
            )
            totals["forts"] += result.get("forts", 0)
            totals["camps"] += result.get("camps", 0)
    return totals

