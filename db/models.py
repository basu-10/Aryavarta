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


def get_game_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    row = get_db().execute("SELECT value FROM game_setting WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    return str(row["value"])


def set_game_setting(key: str, value: str) -> None:
    db = get_db()
    db.execute(
        """INSERT INTO game_setting (key, value, updated_at)
           VALUES (?, ?, datetime('now'))
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
        (key, str(value)),
    )
    db.commit()


def get_instant_travel() -> bool:
    raw = get_game_setting("instant_travel", "1" if config.INSTANT_TRAVEL else "0")
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def set_instant_travel(enabled: bool) -> None:
    set_game_setting("instant_travel", "1" if enabled else "0")


# ── World ─────────────────────────────────────────────────────────────── #

def create_world(name: str, grid_width: int, grid_height: int,
                 num_forts: int, num_camps: int) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO world (name, grid_width, grid_height, num_forts, num_camps) VALUES (?,?,?,?,?)",
        (name, grid_width, grid_height, num_forts, num_camps),
    )
    db.commit()
    return cur.lastrowid


def get_world(world_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM world WHERE id=?", (world_id,)).fetchone())


def get_all_worlds() -> list[dict]:
    return [dict(r) for r in get_db().execute("SELECT * FROM world ORDER BY id").fetchall()]


def get_default_world() -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM world WHERE is_default=1 LIMIT 1").fetchone())


def set_default_world(world_id: int) -> None:
    db = get_db()
    db.execute("UPDATE world SET is_default=0")
    db.execute("UPDATE world SET is_default=1 WHERE id=?", (world_id,))
    db.commit()


def delete_world(world_id: int) -> bool:
    """Delete a world and all its entities (CASCADE). Player accounts are preserved."""
    db = get_db()
    row = db.execute("SELECT id FROM world WHERE id=?", (world_id,)).fetchone()
    if not row:
        return False
    db.execute("DELETE FROM world WHERE id=?", (world_id,))
    db.commit()
    return True


def get_world_count() -> int:
    row = get_db().execute("SELECT COUNT(*) AS cnt FROM world").fetchone()
    return row["cnt"] if row else 0


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
    """Legacy helper — prefer create_clan / leave_clan / resolve_application for full clan support."""
    db = get_db()
    if clan_id is None:
        db.execute(
            "UPDATE player SET clan_id=NULL, clan_role=NULL, clan_joined_at=NULL WHERE id=?",
            (player_id,),
        )
    else:
        db.execute(
            "UPDATE player SET clan_id=?, clan_joined_at=datetime('now') WHERE id=?",
            (clan_id, player_id),
        )
    db.commit()


def mark_tutorial_seen(player_id: int) -> None:
    db = get_db()
    db.execute("UPDATE player SET tutorial_seen=1 WHERE id=?", (player_id,))
    db.commit()


def set_player_role(player_id: int, role: str) -> None:
    db = get_db()
    db.execute("UPDATE player SET role=? WHERE id=?", (role, player_id))
    db.commit()


def ban_player(player_id: int) -> None:
    set_player_role(player_id, "banned")


def create_remember_token(player_id: int, token_hash: str, expires_at_ts: int) -> None:
    """Rotate to one active remember token per player and persist it."""
    db = get_db()
    db.execute("DELETE FROM auth_remember_token WHERE player_id=?", (player_id,))
    db.execute(
        "INSERT INTO auth_remember_token (player_id, token_hash, expires_at_ts) VALUES (?,?,?)",
        (player_id, token_hash, expires_at_ts),
    )
    db.commit()


def get_player_by_remember_token_hash(token_hash: str) -> Optional[dict]:
    row = get_db().execute(
        """
        SELECT p.*
        FROM auth_remember_token t
        JOIN player p ON p.id = t.player_id
        WHERE t.token_hash = ?
          AND t.revoked_at_ts IS NULL
          AND t.expires_at_ts > CAST(strftime('%s', 'now') AS INTEGER)
        LIMIT 1
        """,
        (token_hash,),
    ).fetchone()
    return _row(row)


def revoke_remember_token_hash(token_hash: str) -> None:
    db = get_db()
    db.execute(
        """
        UPDATE auth_remember_token
        SET revoked_at_ts = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE token_hash = ? AND revoked_at_ts IS NULL
        """,
        (token_hash,),
    )
    db.commit()


# ── Castle ───────────────────────────────────────────────────────────── #

def create_castle(player_id: int, slot_count: int, grid_x: int, grid_y: int,
                  world_id: int = 0) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO castle (world_id, player_id, slot_count, grid_x, grid_y) VALUES (?,?,?,?,?)",
        (world_id, player_id, slot_count, grid_x, grid_y),
    )
    db.commit()
    castle_id = cur.lastrowid
    _place_building_internal("castle", castle_id, 0, "Command Centre")
    return castle_id


def get_castle_by_player(player_id: int, world_id: Optional[int] = None) -> Optional[dict]:
    if world_id is not None:
        return _row(get_db().execute(
            "SELECT * FROM castle WHERE player_id=? AND world_id=?", (player_id, world_id)
        ).fetchone())
    return _row(get_db().execute("SELECT * FROM castle WHERE player_id=?", (player_id,)).fetchone())


def get_castle_by_id(castle_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM castle WHERE id=?", (castle_id,)).fetchone())


# ── Fort ─────────────────────────────────────────────────────────────── #

def create_fort(slot_count: int, grid_x: int, grid_y: int,
                monster_data: list, star_level: int, world_id: int = 0) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO fort (world_id, slot_count, grid_x, grid_y, monster_data, star_level) VALUES (?,?,?,?,?,?)",
        (world_id, slot_count, grid_x, grid_y, json.dumps(monster_data), star_level),
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


def get_all_forts(world_id: Optional[int] = None) -> list[dict]:
    if world_id is not None:
        rows = get_db().execute("SELECT * FROM fort WHERE world_id=?", (world_id,)).fetchall()
    else:
        rows = get_db().execute("SELECT * FROM fort").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("monster_data"):
            d["monster_data"] = json.loads(d["monster_data"])
        result.append(d)
    return result


def get_forts_by_owner(player_id: int, world_id: Optional[int] = None) -> list[dict]:
    if world_id is not None:
        rows = get_db().execute(
            "SELECT * FROM fort WHERE owner_id=? AND world_id=?", (player_id, world_id)
        ).fetchall()
    else:
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
        "UPDATE fort SET owner_id=?, monster_data=NULL, defense_preset_name=NULL, last_defeated_at=? WHERE id=?",
        (new_owner_id, _now_iso(), fort_id),
    )
    db.execute(
        "UPDATE building SET is_destroyed=1 WHERE location_type='fort' AND location_id=?",
        (fort_id,),
    )
    db.commit()


def set_fort_defense_preset(fort_id: int, preset_name: Optional[str]) -> None:
    db = get_db()
    db.execute(
        "UPDATE fort SET defense_preset_name=? WHERE id=?",
        (preset_name if preset_name else None, fort_id),
    )
    db.commit()


def _seed_npc_fort_human_garrison(npc_id: int, fort_id: int, star_level: int) -> None:
    """Seed a newly created NPC fort with human-only troops."""
    human_types = [
        unit_type
        for unit_type, cls in config.UNIT_CLASSIFICATION.items()
        if cls.get("faction") == "human" and unit_type not in config.BUILDING_TYPES
    ]
    if not human_types:
        return

    stacks = random.randint(1, min(3, len(human_types)))
    for unit_type in random.sample(human_types, stacks):
        qty = random.randint(20, 80) * max(1, int(star_level))
        add_troop(npc_id, unit_type, qty, "fort", fort_id)


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
    db = get_db()
    # Auto-finalise buildings whose construction timer has elapsed
    db.execute(
        """UPDATE building SET build_complete_at=NULL
           WHERE location_type=? AND location_id=?
             AND build_complete_at IS NOT NULL
             AND build_complete_at <= ?""",
        (location_type, location_id, _now_iso()),
    )
    db.commit()
    rows = db.execute(
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

def create_monster_camp(grid_x: int, grid_y: int, unit_data: list, star_level: int,
                        world_id: int = 0) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO monster_camp (world_id, grid_x, grid_y, unit_data, star_level) VALUES (?,?,?,?,?)",
        (world_id, grid_x, grid_y, json.dumps(unit_data), star_level),
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


def get_all_active_monster_camps(world_id: Optional[int] = None) -> list[dict]:
    if world_id is not None:
        rows = get_db().execute(
            "SELECT * FROM monster_camp WHERE is_active=1 AND world_id=?", (world_id,)
        ).fetchall()
    else:
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


def delete_troop_with_refund(troop_id: int, owner_id: int, quantity: int) -> bool:
    """Delete *quantity* troops of a stack and refund TROOP_REFUND_RATE of their training cost."""
    db = get_db()
    troop = db.execute(
        "SELECT * FROM troop WHERE id=? AND owner_id=? AND state='idle'",
        (troop_id, owner_id),
    ).fetchone()
    if not troop:
        return False
    qty = min(quantity, troop["quantity"])
    cost = config.TROOP_TRAIN_COST.get(troop["unit_type"], {})
    if cost:
        refund = {k: v * config.TROOP_REFUND_RATE * qty for k, v in cost.items()}
        add_player_resources(
            owner_id,
            food=refund.get("food", 0),
            timber=refund.get("timber", 0),
            gold=refund.get("gold", 0),
            metal=refund.get("metal", 0),
        )
    if qty >= troop["quantity"]:
        db.execute("DELETE FROM troop WHERE id=?", (troop_id,))
    else:
        db.execute("UPDATE troop SET quantity=quantity-? WHERE id=?", (qty, troop_id))
    db.commit()
    return True


# ── Training Queue ─────────────────────────────────────────────────────── #

def get_training_queue(building_id: int) -> list[dict]:
    """Return pending training entries for a building, oldest first."""
    rows = get_db().execute(
        "SELECT * FROM training_queue WHERE building_id=? ORDER BY complete_at",
        (building_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_location_training_queue_count(location_type: str, location_id: int) -> int:
    """Return total queued troops across all buildings at a location."""
    row = get_db().execute(
        """SELECT COUNT(*) AS c
           FROM training_queue tq
           JOIN building b ON b.id = tq.building_id
           WHERE b.location_type=? AND b.location_id=?""",
        (location_type, location_id),
    ).fetchone()
    return int(row["c"]) if row else 0


def process_training_queue(building_id: int, location_type: str,
                            location_id: int) -> int:
    """Drain all completed entries: add the troops, remove rows. Returns count completed."""
    now = _now_iso()
    db = get_db()
    done = db.execute(
        """SELECT * FROM training_queue
           WHERE building_id=? AND complete_at <= ?
           ORDER BY complete_at""",
        (building_id, now),
    ).fetchall()
    for entry in done:
        add_troop(entry["owner_id"], entry["unit_type"], 1, location_type, location_id)
        db.execute("DELETE FROM training_queue WHERE id=?", (entry["id"],))
    if done:
        db.commit()
    return len(done)


def queue_troop_training(building_id: int, owner_id: int,
                          unit_type: str, training_seconds: int) -> dict:
    """
    Enqueue one unit for training. Computes complete_at based on the tail of
    the existing queue (or now if empty). Resources must be deducted by caller.
    Returns the new queue entry dict.
    """
    db = get_db()
    last = db.execute(
        """SELECT complete_at FROM training_queue
           WHERE building_id=? ORDER BY complete_at DESC LIMIT 1""",
        (building_id,),
    ).fetchone()
    if last:
        start_from = _parse_dt(last["complete_at"])
    else:
        start_from = datetime.now(timezone.utc)
    complete_at = (start_from + timedelta(seconds=training_seconds)).isoformat(timespec="seconds")
    cur = db.execute(
        "INSERT INTO training_queue (building_id, owner_id, unit_type, complete_at) VALUES (?,?,?,?)",
        (building_id, owner_id, unit_type, complete_at),
    )
    db.commit()
    return {"id": cur.lastrowid, "unit_type": unit_type, "complete_at": complete_at}


def process_all_training_queues(location_type: str, location_id: int) -> None:
    """Process training queues for all buildings at a location (called on page render)."""
    buildings = get_db().execute(
        "SELECT id FROM building WHERE location_type=? AND location_id=?",
        (location_type, location_id),
    ).fetchall()
    for b in buildings:
        process_training_queue(b["id"], location_type, location_id)


# ── Building Upgrade ───────────────────────────────────────────────────── #

def upgrade_building_with_cost(building_id: int, player_id: int) -> tuple[bool, str]:
    """Upgrade a building one level, scaling cost by current level. Returns (ok, error_msg)."""
    b = get_building_by_id(building_id)
    if not b:
        return False, "Building not found"
    if b["is_destroyed"]:
        return False, "Building is destroyed"
    if b["build_complete_at"]:
        return False, "Building is still under construction"
    base = config.BUILDING_UPGRADE_COST.get(b["type"], {})
    if not base:
        return False, "This building cannot be upgraded"
    level = b.get("level", 1)
    scale = config.BUILDING_LEVEL_MULTIPLIER ** (level - 1)
    cost = {k: int(v * scale) for k, v in base.items()}
    if not deduct_player_resources(player_id, **cost):
        return False, "Not enough resources"
    upgrade_building(building_id)
    return True, ""


# ── Building Ammo ──────────────────────────────────────────────────────── #

def get_building_ammo(building_id: int) -> dict:
    """Return {ammo_type: count} for a defence building."""
    rows = get_db().execute(
        "SELECT ammo_type, count FROM building_ammo WHERE building_id=?",
        (building_id,),
    ).fetchall()
    return {r["ammo_type"]: r["count"] for r in rows}


def add_building_ammo(building_id: int, ammo_type: str,
                       count: int, player_id: int) -> tuple[bool, str]:
    """Purchase *count* units of ammo for a defence building. Deducts resources."""
    if count < 1:
        return False, "Count must be at least 1"
    cost_per = config.AMMO_COST.get(ammo_type, {})
    if not cost_per:
        return False, "Unknown ammo type"
    total = {k: v * count for k, v in cost_per.items()}
    if not deduct_player_resources(player_id, **total):
        return False, "Not enough resources"
    db = get_db()
    db.execute(
        """INSERT INTO building_ammo (building_id, ammo_type, count)
           VALUES (?,?,?)
           ON CONFLICT(building_id, ammo_type) DO UPDATE SET count=count+excluded.count""",
        (building_id, ammo_type, count),
    )
    db.commit()
    return True, ""


def set_building_ammo_count(building_id: int, ammo_type: str, count: int) -> None:
    """Set absolute ammo count for a building/ammo_type pair."""
    db = get_db()
    value = max(0, int(count))
    db.execute(
        """INSERT INTO building_ammo (building_id, ammo_type, count)
           VALUES (?,?,?)
           ON CONFLICT(building_id, ammo_type) DO UPDATE SET count=excluded.count""",
        (building_id, ammo_type, value),
    )
    db.commit()


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
                   arrive_time_iso: str, world_id: int = 0,
                   defender_id: Optional[int] = None) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO battle_mission
           (world_id, attacker_id, target_type, target_id, formation, origin_type, origin_id,
            depart_time, arrive_time, defender_id)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (world_id, attacker_id, target_type, target_id, json.dumps(formation),
         origin_type, origin_id, _now_iso(), arrive_time_iso, defender_id),
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


def get_recent_defence_reports(player_id: int, limit: int = 50) -> list[dict]:
    """Fetch missions where this player was the defender (their fort was attacked)."""
    rows = get_db().execute(
        """SELECT * FROM battle_mission WHERE defender_id=? AND resolved=1
           ORDER BY arrive_time DESC LIMIT ?""",
        (player_id, limit),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["formation"] = json.loads(d["formation"])
        result.append(d)
    return result


def mark_defences_seen(player_id: int) -> None:
    db = get_db()
    db.execute(
        "UPDATE battle_mission SET defender_seen=1 WHERE defender_id=? AND resolved=1",
        (player_id,),
    )
    db.commit()


def count_unseen_defences(player_id: int) -> int:
    row = get_db().execute(
        "SELECT COUNT(*) FROM battle_mission WHERE defender_id=? AND resolved=1 AND defender_seen=0",
        (player_id,),
    ).fetchone()
    return row[0] if row else 0


# ── Clan ─────────────────────────────────────────────────────────────── #

# Role hierarchy — higher index = higher rank
_CLAN_ROLE_RANK = {"member": 0, "elder": 1, "co-leader": 2, "leader": 3}

CLAN_CREATION_COST = {"food": 1000, "timber": 1000, "gold": 1000, "metal": 1000}


def create_clan(name: str, leader_id: int) -> int:
    db = get_db()
    cur = db.execute("INSERT INTO clan (name, leader_id) VALUES (?,?)", (name, leader_id))
    clan_id = cur.lastrowid
    db.execute(
        "UPDATE player SET clan_id=?, clan_role='leader', clan_joined_at=datetime('now') WHERE id=?",
        (clan_id, leader_id),
    )
    db.commit()
    return clan_id


def get_clan(clan_id: int) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM clan WHERE id=?", (clan_id,)).fetchone())


def get_clan_by_name(name: str) -> Optional[dict]:
    return _row(get_db().execute("SELECT * FROM clan WHERE name=?", (name,)).fetchone())


def get_all_clans() -> list[dict]:
    rows = get_db().execute(
        """SELECT c.*, COUNT(p.id) AS member_count
           FROM clan c LEFT JOIN player p ON p.clan_id=c.id
           GROUP BY c.id ORDER BY c.name"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_clan_with_member_count(clan_id: int) -> Optional[dict]:
    return _row(get_db().execute(
        """SELECT c.*, COUNT(p.id) AS member_count
           FROM clan c LEFT JOIN player p ON p.clan_id=c.id
           WHERE c.id=? GROUP BY c.id""",
        (clan_id,),
    ).fetchone())


def get_clan_members(clan_id: int) -> list[dict]:
    return [dict(r) for r in get_db().execute(
        "SELECT id, username, clan_role FROM player WHERE clan_id=? ORDER BY clan_role, username",
        (clan_id,),
    ).fetchall()]


def set_clan_description(clan_id: int, description: str) -> None:
    db = get_db()
    db.execute("UPDATE clan SET description=? WHERE id=?", (description, clan_id))
    db.commit()


def set_clan_member_role(clan_id: int, target_id: int, new_role: str) -> None:
    """Update a member's clan_role. If promoting to leader, demote old leader to co-leader."""
    db = get_db()
    if new_role == "leader":
        # Demote current leader to co-leader
        db.execute(
            "UPDATE player SET clan_role='co-leader' WHERE clan_id=? AND clan_role='leader'",
            (clan_id,),
        )
        db.execute("UPDATE clan SET leader_id=? WHERE id=?", (target_id, clan_id))
    db.execute(
        "UPDATE player SET clan_role=? WHERE id=? AND clan_id=?",
        (new_role, target_id, clan_id),
    )
    db.commit()


def remove_clan_member(clan_id: int, player_id: int) -> None:
    """Kick a player from a clan."""
    db = get_db()
    db.execute(
        "UPDATE player SET clan_id=NULL, clan_role=NULL, clan_joined_at=NULL WHERE id=? AND clan_id=?",
        (player_id, clan_id),
    )
    db.commit()


def leave_clan(player_id: int) -> None:
    db = get_db()
    db.execute(
        "UPDATE player SET clan_id=NULL, clan_role=NULL, clan_joined_at=NULL WHERE id=?",
        (player_id,),
    )
    db.commit()


def disband_clan(clan_id: int) -> None:
    db = get_db()
    db.execute(
        "UPDATE player SET clan_id=NULL, clan_role=NULL, clan_joined_at=NULL WHERE clan_id=?",
        (clan_id,),
    )
    db.execute("DELETE FROM clan_application WHERE clan_id=?", (clan_id,))
    db.execute("DELETE FROM clan_message WHERE clan_id=?", (clan_id,))
    db.execute("DELETE FROM clan WHERE id=?", (clan_id,))
    db.commit()


# ── Clan applications ──────────────────────────────────────────────── #

def apply_to_clan(clan_id: int, player_id: int) -> tuple[bool, str]:
    """Player applies to join a clan. Returns (ok, error_message)."""
    db = get_db()
    existing = db.execute(
        "SELECT status FROM clan_application WHERE clan_id=? AND player_id=?",
        (clan_id, player_id),
    ).fetchone()
    if existing:
        if existing["status"] == "pending":
            return False, "Application already pending"
        # Allow re-application after rejection
        db.execute(
            "UPDATE clan_application SET status='pending', applied_at=datetime('now'), resolved_at=NULL, resolved_by=NULL WHERE clan_id=? AND player_id=?",
            (clan_id, player_id),
        )
    else:
        db.execute(
            "INSERT INTO clan_application (clan_id, player_id) VALUES (?,?)",
            (clan_id, player_id),
        )
    db.commit()
    return True, ""


def get_pending_applications(clan_id: int) -> list[dict]:
    rows = get_db().execute(
        """SELECT ca.id, ca.player_id, ca.applied_at, p.username
           FROM clan_application ca JOIN player p ON ca.player_id=p.id
           WHERE ca.clan_id=? AND ca.status='pending'
           ORDER BY ca.applied_at""",
        (clan_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def resolve_application(app_id: int, resolver_id: int, accept: bool) -> tuple[bool, str]:
    """Accept or reject an application. If accepted, add player to clan."""
    db = get_db()
    row = _row(db.execute("SELECT * FROM clan_application WHERE id=?", (app_id,)).fetchone())
    if not row:
        return False, "Application not found"
    if row["status"] != "pending":
        return False, "Application already resolved"
    status = "accepted" if accept else "rejected"
    db.execute(
        "UPDATE clan_application SET status=?, resolved_at=datetime('now'), resolved_by=? WHERE id=?",
        (status, resolver_id, app_id),
    )
    if accept:
        db.execute(
            "UPDATE player SET clan_id=?, clan_role='member', clan_joined_at=datetime('now') WHERE id=?",
            (row["clan_id"], row["player_id"]),
        )
    db.commit()
    return True, ""


def get_player_application(clan_id: int, player_id: int) -> Optional[dict]:
    return _row(get_db().execute(
        "SELECT * FROM clan_application WHERE clan_id=? AND player_id=?",
        (clan_id, player_id),
    ).fetchone())


# ── Clan chat ────────────────────────────────────────────────────────── #

def add_clan_message(clan_id: int, sender_id: int, message: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO clan_message (clan_id, sender_id, message) VALUES (?,?,?)",
        (clan_id, sender_id, message),
    )
    db.commit()


def get_clan_messages(clan_id: int, since_iso: Optional[str] = None, limit: int = 80) -> list[dict]:
    """Return messages for a clan, optionally only those sent after the player joined."""
    if since_iso:
        rows = get_db().execute(
            """SELECT cm.id, cm.message, cm.sent_at, p.username
               FROM clan_message cm JOIN player p ON cm.sender_id=p.id
               WHERE cm.clan_id=? AND cm.sent_at >= ?
               ORDER BY cm.sent_at DESC LIMIT ?""",
            (clan_id, since_iso, limit),
        ).fetchall()
    else:
        rows = get_db().execute(
            """SELECT cm.id, cm.message, cm.sent_at, p.username
               FROM clan_message cm JOIN player p ON cm.sender_id=p.id
               WHERE cm.clan_id=? ORDER BY cm.sent_at DESC LIMIT ?""",
            (clan_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ── Clan recruitment DM ───────────────────────────────────────────────── #

def send_recruit_dm(sender_id: int, recipient_id: int, clan_id: int, message: str) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO dm_message (sender_id, recipient_id, message, is_recruit, recruit_clan_id) VALUES (?,?,?,1,?)",
        (sender_id, recipient_id, message, clan_id),
    )
    db.commit()
    return cur.lastrowid


# ── World chat ───────────────────────────────────────────────────────── #

def add_world_message(sender_id: int, message: str, world_id: int = 0) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO world_message (world_id, sender_id, message) VALUES (?,?,?)",
        (world_id, sender_id, message),
    )
    db.commit()


def get_world_messages(world_id: int = 0, limit: int = 60) -> list[dict]:
    rows = get_db().execute(
        """SELECT wm.id, wm.message, wm.sent_at, p.username, p.id AS sender_id,
                  c.id AS castle_id, c.grid_x, c.grid_y,
                  wm.deleted_by, wm.deleted_at
           FROM world_message wm
           JOIN player p ON wm.sender_id=p.id
           LEFT JOIN castle c ON c.player_id=p.id AND c.world_id=wm.world_id
           WHERE wm.world_id=? AND wm.deleted_at IS NULL
           ORDER BY wm.sent_at DESC LIMIT ?""",
        (world_id, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def soft_delete_world_message(msg_id: int, deleter_id: int) -> bool:
    """Soft-delete a world chat message. Returns False if not found."""
    db = get_db()
    row = db.execute("SELECT id FROM world_message WHERE id=? AND deleted_at IS NULL",
                     (msg_id,)).fetchone()
    if not row:
        return False
    db.execute(
        "UPDATE world_message SET deleted_by=?, deleted_at=? WHERE id=?",
        (deleter_id, _now_iso(), msg_id),
    )
    db.commit()
    return True


def purge_deleted_world_messages(world_id: int) -> int:
    """Hard-delete all soft-deleted messages in a world. Admin only. Returns count deleted."""
    db = get_db()
    cur = db.execute(
        "DELETE FROM world_message WHERE world_id=? AND deleted_at IS NOT NULL",
        (world_id,),
    )
    db.commit()
    return cur.rowcount


# ── Direct messages ──────────────────────────────────────────────────── #

def send_dm(sender_id: int, recipient_id: int, message: str) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO dm_message (sender_id, recipient_id, message) VALUES (?,?,?)",
        (sender_id, recipient_id, message),
    )
    db.commit()
    return cur.lastrowid


def get_dm_conversation(player_a: int, player_b: int, limit: int = 80) -> list[dict]:
    rows = get_db().execute(
        """SELECT dm.id, dm.message, dm.sent_at, dm.read_at,
                  p.username AS sender_username, dm.sender_id, dm.recipient_id
           FROM dm_message dm JOIN player p ON dm.sender_id=p.id
           WHERE (dm.sender_id=? AND dm.recipient_id=?)
              OR (dm.sender_id=? AND dm.recipient_id=?)
           ORDER BY dm.sent_at DESC LIMIT ?""",
        (player_a, player_b, player_b, player_a, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def mark_dms_read(reader_id: int, sender_id: int) -> None:
    """Mark all messages from sender_id to reader_id as read."""
    db = get_db()
    db.execute(
        "UPDATE dm_message SET read_at=? WHERE recipient_id=? AND sender_id=? AND read_at IS NULL",
        (_now_iso(), reader_id, sender_id),
    )
    db.commit()


def get_dm_inbox(player_id: int) -> list[dict]:
    """Return one row per conversation partner, newest message first."""
    rows = get_db().execute(
        """SELECT p.id AS partner_id, p.username AS partner_username,
                  MAX(dm.sent_at) AS last_at,
                  SUM(CASE WHEN dm.recipient_id=? AND dm.read_at IS NULL THEN 1 ELSE 0 END) AS unread
           FROM dm_message dm
           JOIN player p ON p.id = CASE WHEN dm.sender_id=? THEN dm.recipient_id ELSE dm.sender_id END
           WHERE dm.sender_id=? OR dm.recipient_id=?
           GROUP BY p.id
           ORDER BY last_at DESC""",
        (player_id, player_id, player_id, player_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_dm_unread_count(player_id: int) -> int:
    row = get_db().execute(
        "SELECT COUNT(*) AS cnt FROM dm_message WHERE recipient_id=? AND read_at IS NULL",
        (player_id,),
    ).fetchone()
    return row["cnt"] if row else 0


# ── World map ────────────────────────────────────────────────────────── #

def get_occupied_world_cells(world_id: int = 0) -> set[tuple[int, int]]:
    db = get_db()
    occupied: set[tuple[int, int]] = set()
    for r in db.execute("SELECT grid_x, grid_y FROM castle WHERE world_id=?", (world_id,)).fetchall():
        occupied.add((r["grid_x"], r["grid_y"]))
    for r in db.execute("SELECT grid_x, grid_y FROM fort WHERE world_id=?", (world_id,)).fetchall():
        occupied.add((r["grid_x"], r["grid_y"]))
    for r in db.execute(
        "SELECT grid_x, grid_y FROM monster_camp WHERE is_active=1 AND world_id=?", (world_id,)
    ).fetchall():
        occupied.add((r["grid_x"], r["grid_y"]))
    return occupied


def find_empty_cell(world_id: int = 0, grid_w: int = 0, grid_h: int = 0) -> tuple[int, int]:
    """Find a random unoccupied cell within the given world's grid dimensions."""
    if grid_w <= 0:
        grid_w = config.WORLD_GRID_W
    if grid_h <= 0:
        grid_h = config.WORLD_GRID_H
    occupied = get_occupied_world_cells(world_id)
    for _ in range(1000):
        x = random.randint(0, grid_w - 1)
        y = random.randint(0, grid_h - 1)
        if (x, y) not in occupied:
            occupied.add((x, y))
            return x, y
    raise RuntimeError("World grid is full — cannot find empty cell.")


def get_world_map_snapshot(world_id: int = 0) -> list[dict]:
    """All world entities as a flat list for the map renderer (filtered by world)."""
    db = get_db()
    items: list[dict] = []

    for r in db.execute(
        "SELECT c.id, c.grid_x, c.grid_y, p.id as owner_id, p.username as owner_name, p.role as owner_role "
        "FROM castle c JOIN player p ON c.player_id=p.id WHERE c.world_id=?",
        (world_id,),
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
        "FROM fort f LEFT JOIN player p ON f.owner_id=p.id WHERE f.world_id=?",
        (world_id,),
    ).fetchall():
        items.append({
            "type": "fort", "id": r["id"],
            "grid_x": r["grid_x"], "grid_y": r["grid_y"],
            "owner_id": r["owner_id"], "owner_name": r["owner_name"],
            "is_npc": (r["owner_role"] == "npc") if r["owner_id"] else False,
            "star_level": r["star_level"] if r["owner_id"] is None else None,
        })

    for r in db.execute(
        "SELECT id, grid_x, grid_y, star_level FROM monster_camp WHERE is_active=1 AND world_id=?",
        (world_id,),
    ).fetchall():
        items.append({
            "type": "monster_camp", "id": r["id"],
            "grid_x": r["grid_x"], "grid_y": r["grid_y"],
            "owner_id": None, "owner_name": None,
            "is_npc": False,
            "star_level": r["star_level"],
        })

    for r in db.execute(
        "SELECT id, grid_x, grid_y, decoration_type, display_scale, cluster_id "
        "FROM map_decoration WHERE world_id=?",
        (world_id,),
    ).fetchall():
        items.append({
            "type": "decoration", "id": r["id"],
            "grid_x": r["grid_x"], "grid_y": r["grid_y"],
            "owner_id": None, "owner_name": None,
            "is_npc": False, "star_level": None,
            "decoration_type": r["decoration_type"],
            "display_scale": r["display_scale"],
            "cluster_id": r["cluster_id"],
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


def ensure_npc_population(world_id: int = 0, grid_w: int = 0, grid_h: int = 0) -> int:
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
        cx, cy = find_empty_cell(world_id, grid_w, grid_h)
        castle_id = create_castle(npc_id, 8, cx, cy, world_id)

        # Give NPC some forts
        for _ in range(config.NPC_FORTS_PER_NPC):
            fx, fy = find_empty_cell(world_id, grid_w, grid_h)
            star = random.randint(1, 3)
            monster_data: list = []  # NPC-owned forts start empty (no monsters)
            fort_id = create_fort(8, fx, fy, monster_data, star, world_id)
            claim_fort(fort_id, npc_id)
            _seed_npc_fort_human_garrison(npc_id, fort_id, star)

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


def admin_add_troops_to_castle(player_id: int, unit_type: str, quantity: int,
                               world_id: Optional[int] = None) -> bool:
    """Add troops directly to a player's castle. Returns False if no castle found."""
    castle = get_castle_by_player(player_id, world_id=world_id)
    if not castle:
        # Fall back to any castle if world-scoped lookup misses
        castle = get_castle_by_player(player_id)
    if not castle:
        return False
    add_troop(player_id, unit_type, quantity, "castle", castle["id"])
    return True


def admin_grant_fort(player_id: int, slot_count: int = 6, fully_built: bool = False,
                     world_id: int = 0) -> int:
    """
    Create a new fort on a random empty cell and assign it to the player.
    If fully_built=True, fills all remaining slots with buildings that are
    immediately complete (no build timer).
    Returns the new fort id.
    """
    cx, cy = find_empty_cell(world_id)
    fort_id = create_fort(slot_count, cx, cy, [], star_level=1, world_id=world_id)
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


# ── Friends / Social ──────────────────────────────────────────────────── #

def send_friend_request(requester_id: int, receiver_id: int) -> tuple[bool, str]:
    """Send a friend request. Idempotent if already sent. Returns (ok, message)."""
    if requester_id == receiver_id:
        return False, "Cannot friend yourself"
    db = get_db()
    # Check for any existing relationship in either direction
    row = db.execute(
        """SELECT id, status FROM friendship
           WHERE (requester_id=? AND receiver_id=?) OR (requester_id=? AND receiver_id=?)""",
        (requester_id, receiver_id, receiver_id, requester_id),
    ).fetchone()
    if row:
        if row["status"] == "accepted":
            return False, "Already friends"
        return False, "Friend request already pending"
    db.execute(
        "INSERT INTO friendship (requester_id, receiver_id, status) VALUES (?,?,'pending')",
        (requester_id, receiver_id),
    )
    db.commit()
    return True, "Friend request sent"


def accept_friend_request(receiver_id: int, requester_id: int) -> tuple[bool, str]:
    """Accept an incoming friend request."""
    db = get_db()
    row = db.execute(
        "SELECT id FROM friendship WHERE requester_id=? AND receiver_id=? AND status='pending'",
        (requester_id, receiver_id),
    ).fetchone()
    if not row:
        return False, "No pending request found"
    db.execute("UPDATE friendship SET status='accepted' WHERE id=?", (row["id"],))
    db.commit()
    return True, "Friend request accepted"


def remove_friend(player_id: int, other_id: int) -> bool:
    """Remove a friendship (or pending request) in either direction."""
    db = get_db()
    db.execute(
        """DELETE FROM friendship
           WHERE (requester_id=? AND receiver_id=?) OR (requester_id=? AND receiver_id=?)""",
        (player_id, other_id, other_id, player_id),
    )
    db.commit()
    return True


def get_friends(player_id: int) -> list[dict]:
    """Return accepted friends as list of {id, username}."""
    rows = get_db().execute(
        """SELECT p.id, p.username FROM friendship f
           JOIN player p ON p.id = CASE
               WHEN f.requester_id=? THEN f.receiver_id
               ELSE f.requester_id
           END
           WHERE (f.requester_id=? OR f.receiver_id=?) AND f.status='accepted'
           ORDER BY p.username""",
        (player_id, player_id, player_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_pending_friend_requests(player_id: int) -> list[dict]:
    """Incoming pending requests for this player."""
    rows = get_db().execute(
        """SELECT f.id, p.id AS requester_id, p.username AS requester_name, f.created_at
           FROM friendship f JOIN player p ON p.id=f.requester_id
           WHERE f.receiver_id=? AND f.status='pending'
           ORDER BY f.created_at""",
        (player_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_friendship_status(player_id: int, other_id: int) -> str:
    """Return 'none' | 'pending_sent' | 'pending_received' | 'accepted'."""
    row = get_db().execute(
        """SELECT requester_id, status FROM friendship
           WHERE (requester_id=? AND receiver_id=?) OR (requester_id=? AND receiver_id=?)""",
        (player_id, other_id, other_id, player_id),
    ).fetchone()
    if not row:
        return "none"
    if row["status"] == "accepted":
        return "accepted"
    if row["requester_id"] == player_id:
        return "pending_sent"
    return "pending_received"


# ── Map Decorations ────────────────────────────────────────────────── #

def create_map_decoration(world_id: int, decoration_type: str, grid_x: int, grid_y: int,
                          display_scale: float = 1.0,
                          cluster_id: Optional[int] = None) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO map_decoration (world_id, decoration_type, grid_x, grid_y, display_scale, cluster_id) "
        "VALUES (?,?,?,?,?,?)",
        (world_id, decoration_type, grid_x, grid_y, display_scale, cluster_id),
    )
    db.commit()
    return cur.lastrowid


def get_map_decorations(world_id: int) -> list[dict]:
    rows = get_db().execute(
        "SELECT * FROM map_decoration WHERE world_id=? ORDER BY id",
        (world_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def clear_map_decorations(world_id: int) -> None:
    """Remove all decorations for a world (called before regenerating)."""
    db = get_db()
    db.execute("DELETE FROM map_decoration WHERE world_id=?", (world_id,))
    db.commit()

