"""
blueprints/world_bp.py — World map, attack dispatch, mission polling.
"""

from __future__ import annotations

import json
import math
import random
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import (
    Blueprint, current_app, jsonify, redirect, render_template,
    request, session, url_for,
)

from blueprints.auth_bp import login_required, mod_required
from db import models as m
from engine.battle import Battle
from engine.unit import Unit
from utils.battle_store import store_battle
from utils.csv_writer import write_battle_csv
from utils.serializer import build_tick_data
from utils.troops_store import get_all_unit_stats
from db.world_seeder import ensure_world_entities
import config

world_bp = Blueprint("world", __name__)

_TEAM_A_POSITIONS = [(r, c) for r in range(config.GRID_ROWS) for c in config.TEAM_A_COLS]
_TEAM_B_POSITIONS = [(r, c) for r in range(config.GRID_ROWS) for c in config.TEAM_B_COLS]
_PRESETS_DIR = Path(__file__).parent.parent / "presets"
_NOTIFICATIONS_CACHE_TTL_SECONDS = 5
_NOTIFICATIONS_CACHE: dict[int, tuple[float, dict]] = {}


# ── Pages ─────────────────────────────────────────────────────────────── #

@world_bp.route("/world")
@login_required
def world_map():
    world_id = session.get("world_id")
    if not world_id:
        worlds = m.get_all_worlds()
        if len(worlds) == 1:
            session["world_id"] = worlds[0]["id"]
            world_id = worlds[0]["id"]
        elif len(worlds) > 1:
            player = m.get_player_by_id(session["player_id"])
            if player and player["role"] in ("admin", "mod"):
                return redirect(url_for("world.select_world"))
            # Non-admin users are auto-assigned to the first world
            session["world_id"] = worlds[0]["id"]
            world_id = worlds[0]["id"]
        else:
            return render_template("world/no_worlds.html")
    world = m.get_world(world_id)
    if not world:
        session.pop("world_id", None)
        return redirect(url_for("world.world_map"))
    return render_template("world/map.html",
                           world=world,
                           world_w=world["grid_width"],
                           world_h=world["grid_height"],
                           active_theme=config.ACTIVE_THEME)


@world_bp.route("/world/select")
@mod_required
def select_world():
    worlds = m.get_all_worlds()
    if len(worlds) == 1:
        session["world_id"] = worlds[0]["id"]
        return redirect(url_for("world.world_map"))
    return render_template("world/select_world.html", worlds=worlds)


@world_bp.route("/world/select", methods=["POST"])
@mod_required
def select_world_post():
    world_id = request.form.get("world_id", type=int)
    if world_id and m.get_world(world_id):
        session["world_id"] = world_id
    return redirect(url_for("world.world_map"))


@world_bp.route("/world/item/<item_type>/<int:item_id>")
@login_required
def world_item_popup(item_type: str, item_id: int):
    """Return an HTMX partial for the world-map popup."""
    player_id = session["player_id"]
    ctx: dict = {"item_type": item_type, "item_id": item_id,
                 "player_id": player_id}

    if item_type == "castle":
        from db.models import get_castle_by_id
        castle = get_castle_by_id(item_id)
        if castle is None:
            return "Not found", 404
        ctx["item"] = castle
        ctx["is_own"] = (castle["player_id"] == player_id)

    elif item_type == "fort":
        fort = m.get_fort(item_id)
        if fort is None:
            return "Not found", 404
        ctx["item"] = fort
        ctx["is_own"] = (fort.get("owner_id") == player_id)
        ctx["is_monster_fort"] = fort.get("owner_id") is None

    elif item_type == "monster_camp":
        camp = m.get_monster_camp(item_id)
        if camp is None:
            return "Not found", 404
        ctx["item"] = camp

    return render_template("world/item_popup.html", **ctx)


# ── Attack preparation page ──────────────────────────────────────────── #

@world_bp.route("/attack/<target_type>/<int:target_id>")
@login_required
def attack_prep(target_type: str, target_id: int):
    """Full-page attack preparation: pick a formation and launch."""
    player_id = session["player_id"]

    if target_type == "fort":
        target = m.get_fort(target_id)
        if target is None:
            return "Fort not found", 404
        if target.get("owner_id") == player_id:
            return "Cannot attack your own fort", 403
        target_label = (
            f"{target['owner_name']}'s Fort" if target.get("owner_name")
            else "Abandoned Fort" if target.get("owner_id") is None
            else f"Fort #{target_id}"
        )
        target_stars = target.get("star_level", 0)
    elif target_type == "monster_camp":
        target = m.get_monster_camp(target_id)
        if target is None or not target.get("is_active"):
            return "Monster camp not found or already defeated", 404
        target_label = "Monster Camp"
        target_stars = target.get("star_level", 0)
    else:
        return "Invalid target type", 400

    # Player origins with stationed troops
    castle = m.get_castle_by_player(player_id)
    forts_owned = m.get_forts_by_owner(player_id)
    origins: list[dict] = []
    if castle:
        troops = m.get_troops_at("castle", castle["id"])
        origins.append({
            "type": "castle", "id": castle["id"], "label": "My Castle",
            "troops": troops,
        })
    for fort in forts_owned:
        troops = m.get_troops_at("fort", fort["id"])
        origins.append({
            "type": "fort", "id": fort["id"], "label": f"Fort #{fort['id']}",
            "troops": troops,
        })

    # All saved presets
    presets: list[dict] = []
    for f in sorted(_PRESETS_DIR.glob("*.json")):
        try:
            presets.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass

    all_stats = get_all_unit_stats()
    # Buildings are never dispatched to attack — filter them out
    deployable_types = [t for t in all_stats.keys() if t not in config.BUILDING_TYPES]
    unit_classification = {k: v for k, v in config.UNIT_CLASSIFICATION.items()
                           if k not in config.BUILDING_TYPES}
    for unit_type in deployable_types:
        if unit_type not in unit_classification:
            stats = all_stats[unit_type]
            troop_type = "melee" if stats.get("range", 1) <= 1 else "ranged"
            unit_classification[unit_type] = {"faction": "human", "type": troop_type}

    return render_template(
        "world/attack_prep.html",
        target_type=target_type,
        target_id=target_id,
        target=target,
        target_label=target_label,
        target_stars=target_stars,
        origins=origins,
        presets=presets,
        grid_rows=config.GRID_ROWS,
        team_a_cols=config.TEAM_A_COLS,
        unit_types=deployable_types,
        unit_stats={k: v for k, v in all_stats.items() if k not in config.BUILDING_TYPES},
        unit_classification=unit_classification,
        active_theme=config.ACTIVE_THEME,
    )


# ── Player origins API ───────────────────────────────────────────────── #

@world_bp.route("/api/player/origins")
@login_required
def api_player_origins():
    """Return the current player's castle and owned forts for the attack modal."""
    player_id = session["player_id"]
    castle = m.get_castle_by_player(player_id)
    forts = m.get_forts_by_owner(player_id)
    origins = []
    if castle:
        origins.append({"type": "castle", "id": castle["id"], "label": "My Castle"})
    for fort in forts:
        origins.append({"type": "fort", "id": fort["id"], "label": f"Fort #{fort['id']}"})
    return jsonify({"origins": origins})


# ── World map data API ────────────────────────────────────────────────── #

@world_bp.route("/api/world/map")
@login_required
def api_world_map():
    world_id = session.get("world_id", 0)
    player_id = session["player_id"]
    # Auto-populate NPCs if below cap (cheap check)
    world = m.get_world(world_id)
    if world:
        m.ensure_npc_population(world_id, world["grid_width"], world["grid_height"])
    else:
        m.ensure_npc_population()
    # Top up monster forts/camps if any were defeated
    ensure_world_entities()
    return jsonify({"items": m.get_world_map_snapshot(world_id, viewer_player_id=player_id)})


# ── NPC generation endpoint ───────────────────────────────────────────── #

@world_bp.route("/api/world/ensure_npcs", methods=["POST"])
@login_required
def api_ensure_npcs():
    created = m.ensure_npc_population()
    return jsonify({"ok": True, "created": created})


# ── Active missions polling ──────────────────────────────────────────── #

@world_bp.route("/api/battles/active")
@login_required
def api_active_missions():
    player_id = session["player_id"]
    missions = m.get_active_missions_by_player(player_id)
    now = datetime.now(timezone.utc)
    result = []
    for mis in missions:
        arrive = datetime.fromisoformat(mis["arrive_time"])
        depart = datetime.fromisoformat(mis["depart_time"])
        if arrive.tzinfo is None:
            arrive = arrive.replace(tzinfo=timezone.utc)
        if depart.tzinfo is None:
            depart = depart.replace(tzinfo=timezone.utc)
        seconds_left = max(0, (arrive - now).total_seconds())
        total_seconds = max(1, (arrive - depart).total_seconds())
        result.append({
            "mission_id": mis["id"],
            "target_type": mis["target_type"],
            "target_id": mis["target_id"],
            "seconds_left": round(seconds_left),
            "total_seconds": round(total_seconds),
        })
    return render_template("world/_missions.html", missions=result)


# ── Notifications API ─────────────────────────────────────────────────── #

@world_bp.route("/api/notifications")
@login_required
def api_notifications():
    """Return unread defence count and castle-resources-ready flag for nav dots."""
    player_id = session["player_id"]
    now_ts = datetime.now(timezone.utc).timestamp()
    cached = _NOTIFICATIONS_CACHE.get(player_id)
    if cached and (now_ts - cached[0]) < _NOTIFICATIONS_CACHE_TTL_SECONDS:
        return jsonify(cached[1])

    unread_defences = m.count_unseen_defences(player_id)
    unread_dm = m.get_dm_unread_count(player_id)

    castle_ready = False
    castle = m.get_castle_by_player(player_id)
    if castle:
        pending = m.get_location_pending_resources("castle", castle["id"])
        castle_ready = sum(pending.values()) >= 1000

    payload = {
        "unread_defences": unread_defences,
        "unread_dm": unread_dm,
        "castle_ready": castle_ready,
    }
    _NOTIFICATIONS_CACHE[player_id] = (now_ts, payload)
    return jsonify(payload)


# ── Attack dispatch ───────────────────────────────────────────────────── #

@world_bp.route("/api/attack", methods=["POST"])
@login_required
def api_attack():
    """
    Body JSON:
    {
        "target_type": "fort" | "monster_camp",
        "target_id": <int>,
        "origin_type": "castle" | "fort",
        "origin_id": <int>,
        "formation": [{"unit_type": "...", "quantity": N}, ...]
    }
    """
    player_id = session["player_id"]
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    target_type = data.get("target_type")
    target_id   = data.get("target_id")
    origin_type = data.get("origin_type")
    origin_id   = data.get("origin_id")
    preset_name = (data.get("preset_name") or "").strip()

    # Prefer server-side preset resolution to ensure the selected preset is
    # authoritative (frontend previews can still send formation for display).
    formation = _formation_from_preset_name(preset_name)
    if not formation:
        formation = _normalize_formation(data.get("formation", []))

    if target_type not in ("fort", "monster_camp"):
        return jsonify({"error": "Invalid target_type"}), 400
    if origin_type not in ("castle", "fort"):
        return jsonify({"error": "Invalid origin_type"}), 400
    if not formation:
        return jsonify({"error": "Formation is empty"}), 400

    # Validate origin belongs to this player
    err = _validate_origin(player_id, origin_type, origin_id)
    if err:
        return jsonify({"error": err}), 403

    # Validate target
    target, err = _validate_target(target_type, target_id, player_id)
    if err:
        return jsonify({"error": err}), 400

    # Deduct troops
    for entry in formation:
        utype = (entry.get("unit_type") or entry.get("type") or "").strip()
        qty = entry.get("quantity", 1)
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = 1
        if qty <= 0:
            return jsonify({"error": f"Invalid quantity for {utype}"}), 400
        if not m.deduct_troop(player_id, utype, qty, origin_type, origin_id):
            return jsonify({"error": f"Not enough {utype} troops at {origin_type} {origin_id}"}), 400

    # Calculate travel time
    origin_coords = _get_coords(origin_type, origin_id)
    target_coords = (target["grid_x"], target["grid_y"])
    distance = _chebyshev(origin_coords, target_coords)
    slowest_speed = _slowest_speed(formation)
    travel_secs = max(1, math.ceil(distance / max(slowest_speed, 0.1))
                      * config.WORLD_TRAVEL_SECONDS_PER_CELL)

    instant_travel = m.get_instant_travel()
    if instant_travel:
        arrive_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        arrive_time = (datetime.now(timezone.utc) + timedelta(seconds=travel_secs)).isoformat(timespec="seconds")

    # Determine defender_id for player-owned fort targets
    defender_id = None
    if target_type == "fort":
        defender_id = target.get("owner_id")  # None for unowned/monster forts

    mission_id = m.create_mission(
        player_id, target_type, target_id, formation,
        origin_type, origin_id, arrive_time,
        world_id=session.get("world_id", 0),
        defender_id=defender_id,
    )

    # If instant travel, resolve immediately and return result in the same response
    resolved_result = None
    if instant_travel:
        mission = m.get_pending_missions_for_player(player_id)
        for mis in mission:
            if mis["id"] == mission_id:
                resolved_result = _resolve_one_mission(mis)
                break

    return jsonify({
        "ok": True,
        "mission_id": mission_id,
        "travel_seconds": travel_secs,
        "arrive_time": arrive_time,
        "result": resolved_result,
    })


def _normalize_formation(raw_formation: list[dict]) -> list[dict]:
    """Normalize flexible formation payloads to [{unit_type, quantity}, ...]."""
    counts: dict[str, int] = {}
    if not isinstance(raw_formation, list):
        return []

    for entry in raw_formation:
        if not isinstance(entry, dict):
            continue
        unit_type = (entry.get("unit_type") or entry.get("type") or "").strip()
        if not unit_type:
            continue
        try:
            qty = int(entry.get("quantity", 1))
        except (TypeError, ValueError):
            qty = 1
        if qty <= 0:
            continue
        counts[unit_type] = counts.get(unit_type, 0) + qty

    return [{"unit_type": unit_type, "quantity": qty} for unit_type, qty in counts.items()]


def _safe_preset_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()


def _load_preset_by_name(name: str) -> dict | None:
    safe = _safe_preset_name(name)
    if not safe:
        return None
    path = _PRESETS_DIR / f"{safe}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _list_all_preset_names() -> list[str]:
    names: list[str] = []
    for f in sorted(_PRESETS_DIR.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = str(payload.get("name") or f.stem).strip()
        if name:
            names.append(name)
    return names


def _formation_from_preset_name(name: str) -> list[dict]:
    """Load selected preset and derive attacker formation from Team A units."""
    preset = _load_preset_by_name(name)
    if not preset:
        return []

    # Preserve explicit unit placements so attack presets are deterministic.
    formation: list[dict] = []
    for unit in preset.get("army_a", []):
        if not isinstance(unit, dict):
            continue
        utype = (unit.get("type") or unit.get("unit_type") or "").strip()
        row = unit.get("row")
        col = unit.get("col")
        if not utype or not isinstance(row, int) or not isinstance(col, int):
            continue
        formation.append({"unit_type": utype, "quantity": unit.get("quantity", 1), "row": row, "col": col})
    return formation


# ── Mission resolution (player polls, server resolves on demand) ─────── #

@world_bp.route("/api/missions/resolve", methods=["POST"])
@login_required
def api_resolve_missions():
    """
    The client calls this after a countdown expires.
    Server resolves all due missions for this player.
    Returns a list of resolved battle_ids + winners for the UI.
    """
    player_id = session["player_id"]
    due = m.get_pending_missions_for_player(player_id)
    resolved = []

    for mission in due:
        result = _resolve_one_mission(mission)
        resolved.append(result)

    return jsonify({"resolved": resolved})


# ── Helpers ───────────────────────────────────────────────────────────── #

def _validate_origin(player_id: int, origin_type: str, origin_id: int) -> str | None:
    if origin_type == "castle":
        c = m.get_castle_by_id(origin_id)
        if not c or c["player_id"] != player_id:
            return "Origin castle not owned by you"
    elif origin_type == "fort":
        f = m.get_fort(origin_id)
        if not f or f.get("owner_id") != player_id:
            return "Origin fort not owned by you"
    return None


def _validate_target(target_type: str, target_id: int, player_id: int) -> tuple[dict | None, str | None]:
    if target_type == "fort":
        fort = m.get_fort(target_id)
        if not fort:
            return None, "Fort not found"
        if fort.get("owner_id") == player_id:
            return None, "Cannot attack your own fort"
        return fort, None
    else:
        camp = m.get_monster_camp(target_id)
        if not camp or not camp.get("is_active"):
            return None, "Monster camp not found or already defeated"
        return camp, None


def _get_coords(location_type: str, location_id: int) -> tuple[int, int]:
    if location_type == "castle":
        e = m.get_castle_by_id(location_id)
    else:
        e = m.get_fort(location_id)
    return (e["grid_x"], e["grid_y"])


def _chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _slowest_speed(formation: list[dict]) -> float:
    speeds = []
    all_stats = {**config.UNIT_STATS}
    for entry in formation:
        utype = entry.get("unit_type", "")
        if utype in all_stats:
            speeds.append(all_stats[utype]["speed"])
    return min(speeds) if speeds else 1.0


def _build_attacker_units(formation: list[dict]) -> list[Unit]:
    """Turn formation data into Unit objects.

    Supports two formats:
      1) [{unit_type, quantity}, ...] -> random Team A placement
      2) [{unit_type/type, row, col}, ...] -> explicit preset placement
    """
    all_stats = config.UNIT_STATS
    units: list[Unit] = []

    has_explicit_positions = any("row" in e and "col" in e for e in formation)
    if has_explicit_positions:
        occupied: set[tuple[int, int]] = set()
        for entry in formation:
            utype = (entry.get("unit_type") or entry.get("type") or "").strip()
            if not utype or utype not in all_stats:
                continue
            row = entry.get("row")
            col = entry.get("col")
            if not isinstance(row, int) or not isinstance(col, int):
                continue
            if not (0 <= row < config.GRID_ROWS and col in config.TEAM_A_COLS):
                continue
            if (row, col) in occupied:
                continue
            occupied.add((row, col))
            try:
                qty = max(1, int(entry.get("quantity", 1)))
            except (TypeError, ValueError):
                qty = 1
            stats = all_stats[utype]
            units.append(Unit(
                unit_id=f"A_{utype[0]}{len(units)+1}",
                team="A",
                unit_type=utype,
                row=row, col=col,
                hp=stats["hp"] * qty, max_hp=stats["hp"] * qty,
                damage=stats["damage"] * qty, defense=stats["defense"] * qty,
                range=stats["range"], speed=stats["speed"],
                quantity=qty,
            ))
        return units

    # One stacked unit per formation entry: HP and damage scale with quantity.
    # This mirrors the explicit-positions path so a large army is properly
    # represented even when no grid preset was chosen.
    n_entries = sum(1 for e in formation
                    if (e.get("unit_type") or e.get("type", "")).strip() in all_stats
                    and max(0, int(e.get("quantity", 0))) > 0)
    positions = random.sample(_TEAM_A_POSITIONS, min(len(_TEAM_A_POSITIONS), n_entries))
    pos_idx = 0
    for entry in formation:
        utype = (entry.get("unit_type") or entry.get("type") or "").strip()
        if not utype or utype not in all_stats:
            continue
        qty = max(0, int(entry.get("quantity", 0)))
        if qty <= 0:
            continue
        if pos_idx >= len(positions):
            break
        stats = all_stats[utype]
        row, col = positions[pos_idx]; pos_idx += 1
        units.append(Unit(
            unit_id=f"A_{utype[0]}{len(units)+1}",
            team="A",
            unit_type=utype,
            row=row, col=col,
            hp=stats["hp"] * qty, max_hp=stats["hp"] * qty,
            damage=stats["damage"] * qty, defense=stats["defense"] * qty,
            range=stats["range"], speed=stats["speed"],
            quantity=qty,
        ))
    return units


def _build_defender_units(defender_spec: list[dict]) -> list[Unit]:
    """
    Turn a defender spec [{type, count}, ...] into Unit objects.

    Buildings (Cannon, Archer Tower) are placed in the Team B defense column
    (TEAM_B_DEF_COL), up to a maximum of 4 (randomly selected if more are
    present).  Regular troop stacks are placed at random TEAM_B_COLS positions.
    """
    all_stats = config.UNIT_STATS
    units: list[Unit] = []

    # Separate buildings from regular troops
    building_entries = [e for e in defender_spec if e["type"] in config.BUILDING_TYPES]
    troop_entries    = [e for e in defender_spec if e["type"] not in config.BUILDING_TYPES]

    # Cap buildings at 4, chosen randomly
    if len(building_entries) > 4:
        building_entries = random.sample(building_entries, 4)

    # Place buildings in defense column rows 0-3 (one per row, shuffled)
    defense_rows = random.sample(range(config.GRID_ROWS), min(len(building_entries), config.GRID_ROWS))
    for i, entry in enumerate(building_entries):
        if i >= len(defense_rows):
            break
        utype = entry["type"]
        stats = all_stats.get(utype, {})
        if not stats:
            continue
        unit_id = f"B_DEF_{entry['building_id']}" if entry.get("building_id") is not None else f"B_BLD_{len(units)+1}"
        ammo = int(entry.get("ammo_count", 0)) if entry.get("building_id") is not None else None
        units.append(Unit(
            unit_id=unit_id,
            team="B",
            unit_type=utype,
            row=defense_rows[i], col=config.TEAM_B_DEF_COL,
            hp=stats["hp"], max_hp=stats["hp"],
            damage=stats["damage"], defense=stats["defense"],
            range=stats["range"], speed=stats["speed"],
            ammo=ammo,
            quantity=1,
        ))

    # Place explicitly positioned troops first, then random-fill the rest.
    occupied_b_positions: set[tuple[int, int]] = set()
    positioned_entries = [
        e for e in troop_entries
        if isinstance(e.get("row"), int) and isinstance(e.get("col"), int)
    ]
    unpositioned_entries = [
        e for e in troop_entries
        if not (isinstance(e.get("row"), int) and isinstance(e.get("col"), int))
    ]

    for entry in positioned_entries:
        utype = entry["type"]
        stats = all_stats.get(utype, config.UNIT_STATS.get("Troll", {}))
        row = int(entry.get("row", -1))
        col = int(entry.get("col", -1))
        if not (0 <= row < config.GRID_ROWS and col in config.TEAM_B_COLS):
            continue
        if (row, col) in occupied_b_positions:
            continue
        occupied_b_positions.add((row, col))
        qty = max(1, int(entry.get("count", 1)))
        unit_id = f"B_{utype[0]}{len(units)+1}"
        units.append(Unit(
            unit_id=unit_id,
            team="B",
            unit_type=utype,
            row=row, col=col,
            hp=stats["hp"] * qty, max_hp=stats["hp"] * qty,
            damage=stats["damage"] * qty, defense=stats["defense"] * qty,
            range=stats["range"], speed=stats["speed"],
            quantity=qty,
        ))

    available_positions = [pos for pos in _TEAM_B_POSITIONS if pos not in occupied_b_positions]
    positions = random.sample(available_positions, min(len(available_positions), len(unpositioned_entries)))
    pos_idx = 0
    for entry in unpositioned_entries:
        if pos_idx >= len(positions):
            break
        utype = entry["type"]
        stats = all_stats.get(utype, config.UNIT_STATS.get("Troll", {}))
        row, col = positions[pos_idx]
        pos_idx += 1
        qty = max(1, int(entry.get("count", 1)))
        unit_id = f"B_{utype[0]}{len(units)+1}"
        units.append(Unit(
            unit_id=unit_id,
            team="B",
            unit_type=utype,
            row=row, col=col,
            hp=stats["hp"] * qty, max_hp=stats["hp"] * qty,
            damage=stats["damage"] * qty, defense=stats["defense"] * qty,
            range=stats["range"], speed=stats["speed"],
            quantity=qty,
        ))
    return units


def _resolve_fort_defense_preset_name(fort: dict) -> str | None:
    """Resolve effective defense preset for a fort by explicit selection, then default rule."""
    all_names = _list_all_preset_names()
    selected = str(fort.get("defense_preset_name") or "").strip()
    if selected and selected in all_names:
        return selected
    if len(all_names) == 1:
        return all_names[0]
    return None


def _defense_positions_from_preset(preset_name: str, troop_spec: dict[str, int]) -> dict[str, tuple[int, int]]:
    """Map defender troop types to Team B cells based on Team A coordinates from a saved preset."""
    preset = _load_preset_by_name(preset_name)
    if not preset:
        return {}

    mapped: dict[str, tuple[int, int]] = {}
    occupied: set[tuple[int, int]] = set()

    for unit in preset.get("army_a", []):
        if not isinstance(unit, dict):
            continue
        unit_type = (unit.get("type") or unit.get("unit_type") or "").strip()
        row = unit.get("row")
        col = unit.get("col")
        if unit_type not in troop_spec or unit_type in mapped:
            continue
        if not isinstance(row, int) or not isinstance(col, int):
            continue
        if col not in config.TEAM_A_COLS or not (0 <= row < config.GRID_ROWS):
            continue

        b_col = config.TEAM_B_COLS[config.TEAM_A_COLS.index(col)]
        b_pos = (row, b_col)
        if b_pos in occupied:
            continue

        occupied.add(b_pos)
        mapped[unit_type] = b_pos

    return mapped


def _get_defender_spec(mission: dict) -> list[dict]:
    """Return defender unit spec from a fort or monster camp."""
    target_type = mission["target_type"]
    target_id   = mission["target_id"]

    if target_type == "monster_camp":
        camp = m.get_monster_camp(target_id)
        return camp["unit_data"] if camp else []

    fort = m.get_fort(target_id)
    if not fort:
        return []

    # Monster-occupied fort
    if fort.get("owner_id") is None:
        monster_data = fort.get("monster_data")
        if not monster_data:
            # Fort has no stored garrison — generate a fresh star-1 spec and persist it
            from db.world_seeder import _random_monster_spec
            star = max(1, int(fort.get("star_level") or 1))
            monster_data = _random_monster_spec(star)
            from db import get_db
            import json as _json
            get_db().execute(
                "UPDATE fort SET monster_data=? WHERE id=?",
                (_json.dumps(monster_data), fort["id"]),
            )
            get_db().commit()
        return monster_data

    # Player-owned fort: defence buildings (only if ammo > 0) + garrisoned troops
    spec_entries: list[dict] = []
    troop_spec: dict[str, int] = {}
    owner = m.get_player_by_id(fort.get("owner_id")) if fort.get("owner_id") else None
    owner_is_npc = bool(owner and owner.get("role") == "npc")

    buildings = m.get_buildings("fort", target_id)
    for b in buildings:
        if b["is_destroyed"]:
            continue
        if b["type"] == "Cannon":
            ammo = m.get_building_ammo(b["id"]).get("cannon_ball", 0)
            if ammo > 0:
                spec_entries.append({"type": "Cannon", "count": 1, "building_id": b["id"], "ammo_count": ammo})
        elif b["type"] == "Archer Tower":
            ammo = m.get_building_ammo(b["id"]).get("arrow", 0)
            if ammo > 0:
                spec_entries.append({"type": "Archer Tower", "count": 1, "building_id": b["id"], "ammo_count": ammo})

    troops = m.get_troops_at("fort", target_id)
    for t in troops:
        unit_type = t["unit_type"]
        if owner_is_npc:
            unit_cls = config.UNIT_CLASSIFICATION.get(unit_type, {})
            if unit_cls.get("faction") != "human":
                continue
        troop_spec[unit_type] = troop_spec.get(unit_type, 0) + t["quantity"]

    defense_preset_name = _resolve_fort_defense_preset_name(fort)
    defense_positions = (
        _defense_positions_from_preset(defense_preset_name, troop_spec)
        if defense_preset_name else {}
    )

    for k, v in troop_spec.items():
        entry = {"type": k, "count": v}
        if k in defense_positions:
            row, col = defense_positions[k]
            entry["row"] = row
            entry["col"] = col
        spec_entries.append(entry)

    return spec_entries


def _persist_defence_ammo_after_battle(target_id: int, all_units: list[Unit]) -> None:
    """Persist remaining ammo for defence-building units after a fort defence battle."""
    for u in all_units:
        if not u.unit_id.startswith("B_DEF_"):
            continue
        if u.unit_type == "Cannon":
            ammo_type = "cannon_ball"
        elif u.unit_type == "Archer Tower":
            ammo_type = "arrow"
        else:
            continue
        try:
            building_id = int(u.unit_id.split("B_DEF_")[1])
        except (ValueError, IndexError):
            continue
        m.set_building_ammo_count(building_id, ammo_type, u.ammo or 0)


def _build_uncontested_tick_data(attacker_units: list[Unit]) -> list[dict]:
    """Create a single replay snapshot for uncontested attacker victories."""
    cells: dict[str, dict] = {}
    units: list[dict] = []

    for u in attacker_units:
        unit = {
            "unit_id": u.unit_id,
            "team": u.team,
            "type": u.unit_type,
            "row": u.row,
            "col": u.col,
            "hp": u.hp,
            "max_hp": u.max_hp,
            "alive": u.alive,
            "status": "alive" if u.alive else "dead",
            "action": "hold",
            "target_id": None,
            "damage_dealt": 0,
        }
        units.append(unit)

        if u.alive:
            key = f"{u.row},{u.col}"
            cells[key] = {
                "unit_id": u.unit_id,
                "team": u.team,
                "type": u.unit_type,
                "hp": u.hp,
                "max_hp": u.max_hp,
                "status": "alive",
                "action": "hold",
            }

    return [
        {
            "tick": 0,
            "events": [],
            "log": ["Target had no defenders — instant attacker victory."],
            "cells": cells,
            "units": units,
        }
    ]


# ── World chat ─────────────────────────────────────────────────────── #

_MAX_WORLD_MSG_LEN = 300


@world_bp.route("/api/world/chat")
@login_required
def api_world_chat_get():
    """HTMX-polled endpoint — returns latest world chat messages as HTML partial."""
    world_id = session.get("world_id", 0)
    messages = m.get_world_messages(world_id, 60)
    player_id = session["player_id"]
    player = m.get_player_by_id(player_id)
    return render_template("world/_world_chat.html", messages=messages,
                           player_id=player_id, player=player)


@world_bp.route("/api/world/chat", methods=["POST"])
@login_required
def api_world_chat_post():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("message", "").strip()[:_MAX_WORLD_MSG_LEN]
    if not msg:
        return jsonify({"error": "Empty message"}), 400
    world_id = session.get("world_id", 0)
    m.add_world_message(session["player_id"], msg, world_id)
    return jsonify({"ok": True})


@world_bp.route("/api/world/chat/<int:msg_id>/delete", methods=["POST"])
@login_required
def api_world_chat_delete(msg_id: int):
    """Soft-delete a world chat message. Mods and admins only."""
    player = m.get_player_by_id(session["player_id"])
    if not player or player["role"] not in ("mod", "admin"):
        return jsonify({"error": "Forbidden"}), 403
    ok = m.soft_delete_world_message(msg_id, session["player_id"])
    if not ok:
        return jsonify({"error": "Not found or already deleted"}), 404
    return jsonify({"ok": True})


# ── Player-to-player DM ───────────────────────────────────────────── #

_MAX_DM_LEN = 500


@world_bp.route("/api/dm/<int:partner_id>")
@login_required
def api_dm_conversation(partner_id: int):
    """HTMX-polled partial — renders DM conversation."""
    player_id = session["player_id"]
    if partner_id == player_id:
        return "Cannot DM yourself", 400
    partner = m.get_player_by_id(partner_id)
    if not partner:
        return "Player not found", 404
    m.mark_dms_read(player_id, partner_id)
    messages = m.get_dm_conversation(player_id, partner_id)
    return render_template("world/_dm_conversation.html",
                           messages=messages,
                           partner=partner,
                           player_id=player_id)


@world_bp.route("/api/dm/<int:partner_id>", methods=["POST"])
@login_required
def api_dm_send(partner_id: int):
    player_id = session["player_id"]
    if partner_id == player_id:
        return jsonify({"error": "Cannot DM yourself"}), 400
    if not m.get_player_by_id(partner_id):
        return jsonify({"error": "Player not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("message", "").strip()[:_MAX_DM_LEN]
    if not msg:
        return jsonify({"error": "Empty message"}), 400
    m.send_dm(player_id, partner_id, msg)
    return jsonify({"ok": True})


@world_bp.route("/api/dm/inbox")
@login_required
def api_dm_inbox():
    """HTMX partial listing conversation partners."""
    player_id = session["player_id"]
    inbox = m.get_dm_inbox(player_id)
    return render_template("world/_dm_inbox.html", inbox=inbox, player_id=player_id)


@world_bp.route("/api/dm/unread")
@login_required
def api_dm_unread():
    count = m.get_dm_unread_count(session["player_id"])
    return jsonify({"unread": count})


@world_bp.route("/api/world/player/<int:target_id>/recruit", methods=["POST"])
@login_required
def api_send_recruitment(target_id: int):
    """Send a standard recruitment message DM to a player."""
    player_id = session["player_id"]
    if target_id == player_id:
        return jsonify({"error": "Cannot recruit yourself"}), 400
    target = m.get_player_by_id(target_id)
    if not target:
        return jsonify({"error": "Player not found"}), 404
    sender = m.get_player_by_id(player_id)
    msg = f"Hey {target['username']}! Join me — let's conquer the world together. — {sender['username']}"
    m.send_dm(player_id, target_id, msg)
    return jsonify({"ok": True})


# ── Friends API ───────────────────────────────────────────────────────── #

@world_bp.route("/api/friends")
@login_required
def api_get_friends():
    player_id = session["player_id"]
    friends = m.get_friends(player_id)
    # Attach castle location for map jumping
    result = []
    for f in friends:
        castle = m.get_castle_by_player(f["id"])
        result.append({
            "id": f["id"],
            "username": f["username"],
            "castle_id": castle["id"] if castle else None,
            "castle_x": castle["grid_x"] if castle else None,
            "castle_y": castle["grid_y"] if castle else None,
        })
    return jsonify({"friends": result})


@world_bp.route("/api/friends/pending")
@login_required
def api_friend_requests():
    player_id = session["player_id"]
    reqs = m.get_pending_friend_requests(player_id)
    return jsonify({"requests": reqs})


@world_bp.route("/api/friends/<int:other_id>", methods=["POST"])
@login_required
def api_add_friend(other_id: int):
    player_id = session["player_id"]
    ok, msg = m.send_friend_request(player_id, other_id)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "message": msg})


@world_bp.route("/api/friends/<int:other_id>/accept", methods=["POST"])
@login_required
def api_accept_friend(other_id: int):
    player_id = session["player_id"]
    ok, msg = m.accept_friend_request(player_id, other_id)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "message": msg})


@world_bp.route("/api/friends/<int:other_id>", methods=["DELETE"])
@login_required
def api_remove_friend(other_id: int):
    player_id = session["player_id"]
    m.remove_friend(player_id, other_id)
    return jsonify({"ok": True})


@world_bp.route("/api/friends/<int:other_id>/status")
@login_required
def api_friend_status(other_id: int):
    player_id = session["player_id"]
    status = m.get_friendship_status(player_id, other_id)
    return jsonify({"status": status})


def _resolve_one_mission(mission: dict) -> dict:
    attacker_units  = _build_attacker_units(mission["formation"])
    defender_spec   = _get_defender_spec(mission)
    defender_units  = _build_defender_units(defender_spec) if defender_spec else []

    winner_label = "attacker"
    all_battle_units: list[Unit] = attacker_units  # default: uncontested, all survive

    if not defender_units:
        # Empty target — attacker wins uncontested; still store one replay snapshot.
        battle_id = str(uuid.uuid4())
        store_battle(battle_id, {
            "tick_data": _build_uncontested_tick_data(attacker_units),
            "csv_path": "",
            "winner": "A",
            "total_ticks": 0,
        })
    else:
        battle = Battle(attacker_units, defender_units)
        result = battle.run()
        all_battle_units = result.all_units

        battle_id = str(uuid.uuid4())
        csv_path = Path(current_app.config["OUTPUT_DIR"]) / f"{battle_id}.csv"
        write_battle_csv(result, csv_path)
        tick_data = build_tick_data(result)
        store_battle(battle_id, {
            "tick_data": tick_data,
            "csv_path": str(csv_path),
            "winner": result.winner,
            "total_ticks": result.total_ticks,
        })

        # For defended player-owned forts, persist consumed defence ammo.
        if mission["target_type"] == "fort" and result.winner == "B":
            fort = m.get_fort(mission["target_id"])
            if fort and fort.get("owner_id") is not None:
                _persist_defence_ammo_after_battle(mission["target_id"], result.all_units)

        winner_label = "attacker" if result.winner == "A" else "defender"

    # Apply consequences
    _apply_outcome(mission, winner_label, all_battle_units)
    m.resolve_mission(mission["id"], winner_label, battle_id)

    return {
        "mission_id": mission["id"],
        "battle_id": battle_id,
        "winner": winner_label,
        "target_type": mission["target_type"],
        "target_id": mission["target_id"],
    }


def _deduct_defender_casualties(
    location_type: str, location_id: int, owner_id: int, all_units: list
) -> None:
    """Deduct defender casualties from the garrison after a defence.

    For each defending troop stack (not a building), calculate casualties as
    the difference between original quantity and surviving quantity (HP-to-troop
    conversion).  Both dead and partially damaged alive stacks are accounted for.
    """
    for u in all_units:
        if u.team != "B" or u.unit_id.startswith("B_DEF_"):
            continue
        casualties = u.quantity - u.surviving_quantity
        if casualties > 0:
            m.deduct_troop(owner_id, u.unit_type, casualties, location_type, location_id)


def _apply_outcome(mission: dict, winner_label: str, all_units: list | None = None) -> None:
    attacker_id = mission["attacker_id"]
    target_type = mission["target_type"]
    target_id   = mission["target_id"]
    origin_type = mission["origin_type"]
    origin_id   = mission["origin_id"]

    if winner_label == "defender":
        # Attacker wiped out — troops already deducted at dispatch.
        # Apply defender casualties to player-owned fort garrison.
        if target_type == "fort" and all_units is not None:
            fort = m.get_fort(target_id)
            if fort and fort.get("owner_id") is not None:
                _deduct_defender_casualties("fort", target_id, fort["owner_id"], all_units)
        return

    # Attacker wins — return surviving attacker troops to their origin.
    # Quantity returned is based on HP-to-troop conversion (surviving_quantity),
    # so a stack that took heavy damage returns fewer troops.
    if all_units is not None:
        survivors: dict[str, int] = {}
        for u in all_units:
            if u.team == "A":
                qty = u.surviving_quantity
                if qty > 0:
                    survivors[u.unit_type] = survivors.get(u.unit_type, 0) + qty
        for utype, count in survivors.items():
            m.add_troop(attacker_id, utype, count, origin_type, origin_id)

    # Attacker wins
    if target_type == "monster_camp":
        camp = m.get_monster_camp(target_id)
        if camp:
            loot = config.MONSTER_CAMP_LOOT
            m.add_player_resources(attacker_id, gold=loot["gold"], metal=loot["metal"])
            # Capture monsters: add to attacker's Command Centre at their castle
            castle = m.get_castle_by_player(attacker_id)
            if castle:
                for entry in camp["unit_data"]:
                    m.add_troop(attacker_id, entry["type"], entry["count"],
                                "castle", castle["id"])
            m.deactivate_monster_camp(target_id)

    elif target_type == "fort":
        fort = m.get_fort(target_id)
        if not fort:
            return

        # Loot uncollected resources from all fort buildings
        buildings = m.get_buildings("fort", target_id)
        for b in buildings:
            from db.models import _calc_accumulated
            amounts = _calc_accumulated(b)
            food  = amounts.get("food", 0.0)
            timber = amounts.get("timber", 0.0)
            gold  = amounts.get("gold", 0.0)
            metal = amounts.get("metal", 0.0)
            if any([food, timber, gold, metal]):
                m.add_player_resources(attacker_id, food=food, timber=timber,
                                       gold=gold, metal=metal)

        # Capture monsters from a monster-occupied fort
        if fort.get("owner_id") is None:
            castle = m.get_castle_by_player(attacker_id)
            if castle and fort.get("monster_data"):
                for entry in fort["monster_data"]:
                    m.add_troop(attacker_id, entry["type"], entry["count"],
                                "castle", castle["id"])
            m.claim_fort(target_id, attacker_id)
        else:
            # Capture player-owned fort: transfer, destroy all buildings
            m.capture_fort(target_id, attacker_id)
