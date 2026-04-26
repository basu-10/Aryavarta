"""
db/models.py — Repository layer for BattleCells World.

All database reads and writes go through these functions.
To switch database backends, update db/__init__.py (the connection layer) only.
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

import config
from db import get_db


# ── Datetime helpers ────────────────────────────────────────────────── #

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _row(row) -> Optional[dict]:
    return dict(row) if row is not None else None


# ── Player ───────────────────────────────────────────────────────────── #

def create_player(username: str, password_hash: str) -> int:
    db = get_db()
    sr = config.PLAYER_START_RESOURCES
    cur = db.execute(
        "INSERT INTO player (username, password_hash, food, timber, gold, metal) VALUES (?,?,?,?,?,?)",
        (username, password_hash, sr["food"], sr["timber"], sr["gold"], sr["metal"]),
    )
    db.commit()
    return cur.lastrowid


def get_player_by_username(username: str) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM player WHERE username=?", (username,)).fetchone())


def get_player_by_id(player_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM player WHERE id=?", (player_id,)).fetchone())


def get_all_players() -> list[dict]:
    return [dict(r) for r in get_db().execute("SELECT * FROM player ORDER BY created_at").fetchall()]


def add_player_resources(player_id: int, food: float = 0, timber: float = 0,
                         gold: float = 0, metal: float = 0) -> None:
    db = get_db()
    db.execute(
        "UPDATE player SET food=food+?, timber=timber+?, gold=gold+?, metal=metal+? WHERE id=?",
        (food, timber, gold, metal, player_id),
    )
    db.commit()


def deduct_player_resources(player_id: int, food: float = 0, timber: float = 0,
                             gold: float = 0, metal: float = 0) -> bool:
    """Deduct only if the player has enough of every resource. Returns False if not."""
    p = get_player_by_id(player_id)
    if not p:
        return False
    if p["food"] < food or p["timber"] < timber or p["gold"] < gold or p["metal"] < metal:
        return False
    db = get_db()
    db.execute(
        "UPDATE player SET food=food-?, timber=timber-?, gold=gold-?, metal=metal-? WHERE id=?",
        (food, timber, gold, metal, player_id),
    )
    db.commit()
    return True


def set_player_clan(player_id: int, clan_id: Optional[int]) -> None:
    db = get_db()
    db.execute("UPDATE player SET clan_id=? WHERE id=?", (clan_id, player_id))
    db.commit()


def set_player_role(player_id: int, role: str) -> None:
    db = get_db()
    db.execute("UPDATE player SET role=? WHERE id=?", (role, player_id))
    db.commit()


def ban_player(player_id: int) -> None:
    set_player_role(player_id, "banned")


# ── Castle ───────────────────────────────────────────────────────────── #

def create_castle(player_id: int, slot_count: int, grid_x: int, grid_y: int) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO castle (player_id, slot_count, grid_x, grid_y) VALUES (?,?,?,?)",
        (player_id, slot_count, grid_x, grid_y),
    )
    db.commit()
    castle_id = cur.lastrowid
    _place_building_internal("castle", castle_id, 0, "Command Centre")
    return castle_id


def get_castle_by_player(player_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM castle WHERE player_id=?", (player_id,)).fetchone())


def get_castle_by_id(castle_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM castle WHERE id=?", (castle_id,)).fetchone())


# ── Fort ─────────────────────────────────────────────────────────────── #

def create_fort(slot_count: int, grid_x: int, grid_y: int,
                monster_data: list, star_level: int) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO fort (slot_count, grid_x, grid_y, monster_data, star_level) VALUES (?,?,?,?,?)",
        (slot_count, grid_x, grid_y, json.dumps(monster_data), star_level),
    )
    db.commit()
    fort_id = cur.lastrowid
    _place_building_internal("fort", fort_id, 0, "Command Centre")
    return fort_id


def get_fort(fort_id: int) -> Optional[dict]:
    row = get_db().execute("SELECT * FROM fort WHERE id=?", (fort_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    if d.get("monster_data"):
        d["monster_data"] = json.loads(d["monster_data"])
    return d


def get_all_forts() -> list[dict]:
    rows = get_db().execute("SELECT * FROM fort").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("monster_data"):
            d["monster_data"] = json.loads(d["monster_data"])
        result.append(d)
    return result


def get_forts_by_owner(player_id: int) -> list[dict]:
    rows = get_db().execute("SELECT * FROM fort WHERE owner_id=?", (player_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("monster_data"):
            d["monster_data"] = json.loads(d["monster_data"])
        result.append(d)
    return result


def claim_fort(fort_id: int, player_id: int) -> None:
    """First-time claim: mark as owned, clear monster data."""
    db = get_db()
    db.execute("UPDATE fort SET owner_id=?, monster_data=NULL WHERE id=?", (player_id, fort_id))
    db.commit()


def capture_fort(fort_id: int, new_owner_id: int) -> None:
    """Transfer ownership and destroy all buildings (fort was defeated in battle)."""
    db = get_db()
    db.execute(
        "UPDATE fort SET owner_id=?, monster_data=NULL, last_defeated_at=? WHERE id=?",
        (new_owner_id, _now_iso(), fort_id),
    )
    db.execute(
        "UPDATE building SET is_destroyed=1 WHERE location_type='fort' AND location_id=?",
        (fort_id,),
    )
    db.commit()


# ── Building ─────────────────────────────────────────────────────────── #

def _place_building_internal(location_type: str, location_id: int,
                              slot_index: int, building_type: str) -> int:
    """Low-level insert; called by create_castle/create_fort for default buildings."""
    db = get_db()
    now = datetime.now(timezone.utc)
    build_secs = config.BUILDING_BUILD_TIME.get(building_type, 60)
    complete_at = None if build_secs == 0 else (
        (now + timedelta(seconds=build_secs)).isoformat(timespec="seconds")
    )
    cur = db.execute(
        """INSERT INTO building
           (location_type, location_id, slot_index, type, build_complete_at, last_collected_at)
           VALUES (?,?,?,?,?,?)""",
        (location_type, location_id, slot_index, building_type,
         complete_at, now.isoformat(timespec="seconds")),
    )
    db.commit()
    return cur.lastrowid


def place_building(location_type: str, location_id: int,
                   slot_index: int, building_type: str) -> int:
    """Place a new building in an empty slot. Caller must validate cost first."""
    return _place_building_internal(location_type, location_id, slot_index, building_type)


def get_buildings(location_type: str, location_id: int) -> list[dict]:
    rows = get_db().execute(
        "SELECT * FROM building WHERE location_type=? AND location_id=?",
        (location_type, location_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_building_by_id(building_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM building WHERE id=?", (building_id,)).fetchone())


def repair_building(building_id: int) -> None:
    db = get_db()
    db.execute(
        "UPDATE building SET is_destroyed=0, last_collected_at=? WHERE id=?",
        (_now_iso(), building_id),
    )
    db.commit()


def upgrade_building(building_id: int) -> None:
    db = get_db()
    db.execute("UPDATE building SET level=level+1 WHERE id=?", (building_id,))
    db.commit()


def _calc_accumulated(building: dict) -> dict[str, float]:
    """Calculate resources or troops accumulated since last collection (lazy eval)."""
    if building["is_destroyed"]:
        return {}
    btype = building["type"]

    # Resource buildings
    production = config.BUILDING_PRODUCTION_RATE.get(btype, {})
    if production:
        if building.get("build_complete_at"):
            complete = _parse_dt(building["build_complete_at"])
            if datetime.now(timezone.utc) < complete:
                return {}
        last = _parse_dt(building["last_collected_at"])
        elapsed = max(0.0, (datetime.now(timezone.utc) - last).total_seconds())
        multiplier = config.BUILDING_LEVEL_MULTIPLIER ** (building.get("level", 1) - 1)
        return {res: rate * elapsed * multiplier for res, rate in production.items()}

    # Army buildings (troop production)
    army = config.ARMY_PRODUCTION.get(btype)
    if army:
        if building.get("build_complete_at"):
            complete = _parse_dt(building["build_complete_at"])
            if datetime.now(timezone.utc) < complete:
                return {}
        last = _parse_dt(building["last_collected_at"])
        elapsed = max(0.0, (datetime.now(timezone.utc) - last).total_seconds())
        count = math.floor(elapsed / army["seconds_per_unit"])
        return {army["unit_type"]: float(count)} if count > 0 else {}

    return {}


def collect_all_from_location(location_type: str, location_id: int, player_id: int) -> dict:
    """
    Collect all accumulated resources (and troops) from every building at a location.
    Resources go to the player's account; troops are added to the troop table.
    Returns totals dict.
    """
    buildings = get_buildings(location_type, location_id)
    totals: dict[str, float] = {}
    now_s = _now_iso()
    db = get_db()

    resource_keys = {"food", "timber", "gold", "metal"}
    troop_delta: dict[str, int] = {}  # unit_type → count

    for b in buildings:
        amounts = _calc_accumulated(b)
        if not amounts:
            continue
        for k, v in amounts.items():
            if k in resource_keys:
                totals[k] = totals.get(k, 0.0) + v
            else:
                # troop type
                troop_delta[k] = troop_delta.get(k, 0) + int(v)
        db.execute("UPDATE building SET last_collected_at=? WHERE id=?", (now_s, b["id"]))

    db.commit()

    if totals:
        add_player_resources(player_id, **{k: totals.get(k, 0) for k in resource_keys})

    for utype, qty in troop_delta.items():
        if qty > 0:
            add_troop(player_id, utype, qty, location_type, location_id)

    all_collected = {**totals, **{k: float(v) for k, v in troop_delta.items()}}
    return {k: round(v, 2) for k, v in all_collected.items() if v > 0}


def get_location_pending_resources(location_type: str, location_id: int) -> dict:
    """Preview accumulated resources at a location (not yet collected)."""
    buildings = get_buildings(location_type, location_id)
    totals: dict[str, float] = {}
    for b in buildings:
        for k, v in _calc_accumulated(b).items():
            totals[k] = totals.get(k, 0.0) + v
    return {k: round(v, 2) for k, v in totals.items() if v > 0}


# ── Monster camp ──────────────────────────────────────────────────────── #

def create_monster_camp(grid_x: int, grid_y: int, unit_data: list, star_level: int) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO monster_camp (grid_x, grid_y, unit_data, star_level) VALUES (?,?,?,?)",
        (grid_x, grid_y, json.dumps(unit_data), star_level),
    )
    db.commit()
    return cur.lastrowid


def get_monster_camp(camp_id: int) -> Optional[dict]:
    row = get_db().execute("SELECT * FROM monster_camp WHERE id=?", (camp_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["unit_data"] = json.loads(d["unit_data"])
    return d


def get_all_active_monster_camps() -> list[dict]:
    rows = get_db().execute("SELECT * FROM monster_camp WHERE is_active=1").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["unit_data"] = json.loads(d["unit_data"])
        result.append(d)
    return result


def deactivate_monster_camp(camp_id: int) -> None:
    db = get_db()
    db.execute("UPDATE monster_camp SET is_active=0 WHERE id=?", (camp_id,))
    db.commit()


# ── Troop ─────────────────────────────────────────────────────────────── #

def add_troop(owner_id: int, unit_type: str, quantity: int,
              location_type: str, location_id: int) -> int:
    """Add troops, merging with an existing idle stack of the same type at same location."""
    db = get_db()
    existing = db.execute(
        """SELECT id, quantity FROM troop
           WHERE owner_id=? AND unit_type=? AND location_type=? AND location_id=? AND state='idle'""",
        (owner_id, unit_type, location_type, location_id),
    ).fetchone()
    if existing:
        db.execute("UPDATE troop SET quantity=quantity+? WHERE id=?",
                   (quantity, existing["id"]))
        db.commit()
        return existing["id"]
    cur = db.execute(
        "INSERT INTO troop (owner_id, unit_type, quantity, location_type, location_id) VALUES (?,?,?,?,?)",
        (owner_id, unit_type, quantity, location_type, location_id),
    )
    db.commit()
    return cur.lastrowid


def get_troops_at(location_type: str, location_id: int) -> list[dict]:
    rows = get_db().execute(
        "SELECT * FROM troop WHERE location_type=? AND location_id=? AND state='idle'",
        (location_type, location_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_troops_by_owner(owner_id: int) -> list[dict]:
    return [dict(r) for r in get_db().execute(
        "SELECT * FROM troop WHERE owner_id=?", (owner_id,)
    ).fetchall()]


def deduct_troop(owner_id: int, unit_type: str, quantity: int,
                 location_type: str, location_id: int) -> bool:
    """Remove N troops of a given type. Returns False if not enough available."""
    db = get_db()
    row = db.execute(
        """SELECT id, quantity FROM troop
           WHERE owner_id=? AND unit_type=? AND location_type=? AND location_id=? AND state='idle'""",
        (owner_id, unit_type, location_type, location_id),
    ).fetchone()
    if not row or row["quantity"] < quantity:
        return False
    new_qty = row["quantity"] - quantity
    if new_qty == 0:
        db.execute("DELETE FROM troop WHERE id=?", (row["id"],))
    else:
        db.execute("UPDATE troop SET quantity=? WHERE id=?", (new_qty, row["id"]))
    db.commit()
    return True


# ── Battle mission ───────────────────────────────────────────────────── #

def create_mission(attacker_id: int, target_type: str, target_id: int,
                   formation: list, origin_type: str, origin_id: int,
                   arrive_time_iso: str) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO battle_mission
           (attacker_id, target_type, target_id, formation, origin_type, origin_id,
            depart_time, arrive_time)
           VALUES (?,?,?,?,?,?,?,?)""",
        (attacker_id, target_type, target_id, json.dumps(formation),
         origin_type, origin_id, _now_iso(), arrive_time_iso),
    )
    db.commit()
    return cur.lastrowid


def get_active_missions_by_player(player_id: int) -> list[dict]:
    rows = get_db().execute(
        "SELECT * FROM battle_mission WHERE attacker_id=? AND resolved=0 ORDER BY arrive_time",
        (player_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["formation"] = json.loads(d["formation"])
        result.append(d)
    return result


def get_pending_missions_for_player(player_id: int) -> list[dict]:
    """Missions whose arrive_time has passed but aren't resolved yet."""
    now = _now_iso()
    rows = get_db().execute(
        "SELECT * FROM battle_mission WHERE attacker_id=? AND resolved=0 AND arrive_time<=?",
        (player_id, now),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["formation"] = json.loads(d["formation"])
        result.append(d)
    return result


def get_all_pending_missions() -> list[dict]:
    now = _now_iso()
    rows = get_db().execute(
        "SELECT * FROM battle_mission WHERE resolved=0 AND arrive_time<=?", (now,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["formation"] = json.loads(d["formation"])
        result.append(d)
    return result


def resolve_mission(mission_id: int, winner: str, battle_id: str) -> None:
    db = get_db()
    db.execute(
        "UPDATE battle_mission SET resolved=1, winner=?, result_battle_id=? WHERE id=?",
        (winner, battle_id, mission_id),
    )
    db.commit()


def get_recent_resolved_missions(player_id: int, limit: int = 10) -> list[dict]:
    rows = get_db().execute(
        """SELECT * FROM battle_mission WHERE attacker_id=? AND resolved=1
           ORDER BY arrive_time DESC LIMIT ?""",
        (player_id, limit),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["formation"] = json.loads(d["formation"])
        result.append(d)
    return result


# ── Clan ─────────────────────────────────────────────────────────────── #

def create_clan(name: str, leader_id: int) -> int:
    db = get_db()
    cur = db.execute("INSERT INTO clan (name, leader_id) VALUES (?,?)", (name, leader_id))
    db.commit()
    clan_id = cur.lastrowid
    set_player_clan(leader_id, clan_id)
    return clan_id


def get_clan(clan_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM clan WHERE id=?", (clan_id,)).fetchone())


def get_clan_by_name(name: str) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM clan WHERE name=?", (name,)).fetchone())


def get_all_clans() -> list[dict]:
    return [dict(r) for r in get_db().execute("SELECT * FROM clan ORDER BY name").fetchall()]


def get_clan_members(clan_id: int) -> list[dict]:
    return [dict(r) for r in get_db().execute(
        "SELECT id, username, role FROM player WHERE clan_id=?", (clan_id,)
    ).fetchall()]


def disband_clan(clan_id: int) -> None:
    db = get_db()
    db.execute("UPDATE player SET clan_id=NULL WHERE clan_id=?", (clan_id,))
    db.execute("DELETE FROM clan_message WHERE clan_id=?", (clan_id,))
    db.execute("DELETE FROM clan WHERE id=?", (clan_id,))
    db.commit()


def add_clan_message(clan_id: int, sender_id: int, message: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO clan_message (clan_id, sender_id, message) VALUES (?,?,?)",
        (clan_id, sender_id, message),
    )
    db.commit()


def get_clan_messages(clan_id: int, limit: int = 60) -> list[dict]:
    rows = get_db().execute(
        """SELECT cm.id, cm.message, cm.sent_at, p.username
           FROM clan_message cm JOIN player p ON cm.sender_id=p.id
           WHERE cm.clan_id=? ORDER BY cm.sent_at DESC LIMIT ?""",
        (clan_id, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ── World map ────────────────────────────────────────────────────────── #

def get_occupied_world_cells() -> set[tuple[int, int]]:
    db = get_db()
    occupied: set[tuple[int, int]] = set()
    for r in db.execute("SELECT grid_x, grid_y FROM castle").fetchall():
        occupied.add((r["grid_x"], r["grid_y"]))
    for r in db.execute("SELECT grid_x, grid_y FROM fort").fetchall():
        occupied.add((r["grid_x"], r["grid_y"]))
    for r in db.execute("SELECT grid_x, grid_y FROM monster_camp WHERE is_active=1").fetchall():
        occupied.add((r["grid_x"], r["grid_y"]))
    return occupied


def find_empty_cell() -> tuple[int, int]:
    """Find a random unoccupied world grid cell."""
    occupied = get_occupied_world_cells()
    for _ in range(1000):
        x = random.randint(0, config.WORLD_GRID_W - 1)
        y = random.randint(0, config.WORLD_GRID_H - 1)
        if (x, y) not in occupied:
            occupied.add((x, y))
            return x, y
    raise RuntimeError("World grid is full — cannot find empty cell.")


def get_world_map_snapshot() -> list[dict]:
    """All world entities as a flat list for the map renderer."""
    db = get_db()
    items: list[dict] = []

    for r in db.execute(
        "SELECT c.id, c.grid_x, c.grid_y, p.id as owner_id, p.username as owner_name, p.role as owner_role "
        "FROM castle c JOIN player p ON c.player_id=p.id"
    ).fetchall():
        items.append({
            "type": "castle", "id": r["id"],
            "grid_x": r["grid_x"], "grid_y": r["grid_y"],
            "owner_id": r["owner_id"], "owner_name": r["owner_name"],
            "is_npc": r["owner_role"] == "npc",
            "star_level": None,
        })

    for r in db.execute(
        "SELECT f.*, p.username as owner_name, p.role as owner_role "
        "FROM fort f LEFT JOIN player p ON f.owner_id=p.id"
    ).fetchall():
        items.append({
            "type": "fort", "id": r["id"],
            "grid_x": r["grid_x"], "grid_y": r["grid_y"],
            "owner_id": r["owner_id"], "owner_name": r["owner_name"],
            "is_npc": (r["owner_role"] == "npc") if r["owner_id"] else False,
            "star_level": r["star_level"] if r["owner_id"] is None else None,
        })

    for r in db.execute(
        "SELECT id, grid_x, grid_y, star_level FROM monster_camp WHERE is_active=1"
    ).fetchall():
        items.append({
            "type": "monster_camp", "id": r["id"],
            "grid_x": r["grid_x"], "grid_y": r["grid_y"],
            "owner_id": None, "owner_name": None,
            "is_npc": False,
            "star_level": r["star_level"],
        })

    return items


# ── Star level ────────────────────────────────────────────────────────── #

def compute_star_level(unit_count: int) -> int:
    for star, threshold in enumerate(config.STAR_THRESHOLDS, start=1):
        if unit_count <= threshold:
            return star
    return len(config.STAR_THRESHOLDS) + 1


# ── NPC generation ────────────────────────────────────────────────────── #

_NPC_NAMES = [
    "Lord Malachar", "Baron Thorvik", "Lady Seraphine", "Duke Grawl",
    "Countess Vex", "Prince Daeron", "General Strix", "Empress Zyla",
    "Governor Krath", "Warlord Fenris",
]

def get_npc_count() -> int:
    """Return the number of NPC players currently in the database."""
    row = get_db().execute(
        "SELECT COUNT(*) as cnt FROM player WHERE role='npc'"
    ).fetchone()
    return row["cnt"] if row else 0


def create_npc_player(username: str) -> int:
    """Create a minimal NPC player (no password, no resources needed)."""
    db = get_db()
    cur = db.execute(
        "INSERT INTO player (username, password_hash, role, food, timber, gold, metal) "
        "VALUES (?,?,?,?,?,?,?)",
        (username, "npc_no_login", "npc", 0.0, 0.0, 0.0, 0.0),
    )
    db.commit()
    return cur.lastrowid


def ensure_npc_population() -> int:
    """
    Generate NPC players (with castles + forts) until MAX_NPC_COUNT is reached.
    Returns the number of new NPCs created.
    """
    current = get_npc_count()
    target  = config.MAX_NPC_COUNT
    if current >= target:
        return 0

    used_names = {
        r["username"]
        for r in get_db().execute("SELECT username FROM player WHERE role='npc'").fetchall()
    }
    available = [n for n in _NPC_NAMES if n not in used_names]

    created = 0
    for i in range(target - current):
        if available:
            name = available.pop(0)
        else:
            name = f"NPC-{random.randint(1000, 9999)}"

        npc_id = create_npc_player(name)

        # Give NPC a castle
        cx, cy = find_empty_cell()
        castle_id = create_castle(npc_id, 8, cx, cy)

        # Give NPC some forts
        for _ in range(config.NPC_FORTS_PER_NPC):
            fx, fy = find_empty_cell()
            star = random.randint(1, 3)
            monster_data: list = []  # NPC-owned forts start empty (no monsters)
            create_fort(8, fx, fy, monster_data, star)
            # Claim the fort for the NPC
            forts = get_db().execute(
                "SELECT id FROM fort WHERE grid_x=? AND grid_y=?", (fx, fy)
            ).fetchone()
            if forts:
                claim_fort(forts["id"], npc_id)

        created += 1

    return created


# ── Admin helpers ─────────────────────────────────────────────────────── #

def set_player_resources(player_id: int, food: Optional[float] = None,
                          timber: Optional[float] = None, gold: Optional[float] = None,
                          metal: Optional[float] = None) -> None:
    """Directly set one or more resource values for a player (admin use)."""
    parts, values = [], []
    for col, val in (("food", food), ("timber", timber), ("gold", gold), ("metal", metal)):
        if val is not None:
            parts.append(f"{col}=?")
            values.append(max(0.0, float(val)))
    if not parts:
        return
    values.append(player_id)
    db = get_db()
    db.execute(f"UPDATE player SET {', '.join(parts)} WHERE id=?", values)
    db.commit()


def admin_add_troops_to_castle(player_id: int, unit_type: str, quantity: int) -> bool:
    """Add troops directly to a player's castle. Returns False if no castle found."""
    castle = get_castle_by_player(player_id)
    if not castle:
        return False
    add_troop(player_id, unit_type, quantity, "castle", castle["id"])
    return True


def admin_grant_fort(player_id: int, slot_count: int = 6, fully_built: bool = False) -> int:
    """
    Create a new fort on a random empty cell and assign it to the player.
    If fully_built=True, fills all remaining slots with buildings that are
    immediately complete (no build timer).
    Returns the new fort id.
    """
    cx, cy = find_empty_cell()
    fort_id = create_fort(slot_count, cx, cy, [], star_level=1)
    # Assign to player directly (bypasses monster-clear since it never had monsters)
    db = get_db()
    db.execute("UPDATE fort SET owner_id=?, monster_data=NULL WHERE id=?", (player_id, fort_id))
    db.commit()

    if fully_built:
        building_types = [
            "Farm", "Lumber Mill", "Merchant", "Mine",
            "Garrison", "Stable", "Cannon", "Archer Tower",
        ]
        now_s = _now_iso()
        for slot_index in range(1, slot_count):
            btype = building_types[slot_index - 1] if slot_index - 1 < len(building_types) else "Farm"
            db.execute(
                """INSERT OR IGNORE INTO building
                   (location_type, location_id, slot_index, type, build_complete_at, last_collected_at)
                   VALUES (?,?,?,?,NULL,?)""",
                ("fort", fort_id, slot_index, btype, now_s),
            )
        db.commit()

    return fort_id


def delete_player(player_id: int) -> bool:
    """
    Permanently delete a player and all their game data.
    - Disbands any clans they lead.
    - Releases owned forts (owner_id → NULL).
    - Removes castle, buildings, troops, missions, and clan messages.
    Returns False if the player does not exist.
    """
    p = get_player_by_id(player_id)
    if not p:
        return False

    db = get_db()

    # Disband clans the player leads
    led_clans = db.execute("SELECT id FROM clan WHERE leader_id=?", (player_id,)).fetchall()
    for row in led_clans:
        disband_clan(row["id"])

    # Delete troops
    db.execute("DELETE FROM troop WHERE owner_id=?", (player_id,))

    # Delete pending battle missions
    db.execute("DELETE FROM battle_mission WHERE attacker_id=?", (player_id,))

    # Delete castle buildings, then castle
    castle = get_castle_by_player(player_id)
    if castle:
        db.execute(
            "DELETE FROM building WHERE location_type='castle' AND location_id=?",
            (castle["id"],),
        )
        db.execute("DELETE FROM castle WHERE id=?", (castle["id"],))

    # Release owned forts
    db.execute("UPDATE fort SET owner_id=NULL WHERE owner_id=?", (player_id,))

    # Delete clan messages sent by this player
    db.execute("DELETE FROM clan_message WHERE sender_id=?", (player_id,))

    # Remove player from any clan membership
    db.execute("UPDATE player SET clan_id=NULL WHERE id=?", (player_id,))

    # Delete the player record
    db.execute("DELETE FROM player WHERE id=?", (player_id,))
    db.commit()
    return True
