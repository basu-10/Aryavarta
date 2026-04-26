"""
blueprints/world_bp.py — World map, attack dispatch, mission polling.
"""

from __future__ import annotations

import json
import math
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import (
    Blueprint, current_app, jsonify, render_template,
    request, session,
)

from blueprints.auth_bp import login_required
from db import models as m
from engine.battle import Battle
from engine.unit import Unit
from utils.battle_store import store_battle
from utils.csv_writer import write_battle_csv
from utils.serializer import build_tick_data
import config

world_bp = Blueprint("world", __name__)

_TEAM_A_POSITIONS = [(r, c) for r in range(config.GRID_ROWS) for c in config.TEAM_A_COLS]
_TEAM_B_POSITIONS = [(r, c) for r in range(config.GRID_ROWS) for c in config.TEAM_B_COLS]


# ── Pages ─────────────────────────────────────────────────────────────── #

@world_bp.route("/world")
@login_required
def world_map():
    return render_template("world/map.html",
                           world_w=config.WORLD_GRID_W,
                           world_h=config.WORLD_GRID_H)


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
    # Auto-populate NPCs if below cap (cheap check)
    m.ensure_npc_population()
    return jsonify({"items": m.get_world_map_snapshot()})


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
    formation   = data.get("formation", [])

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
        utype = entry.get("unit_type", "")
        qty   = int(entry.get("quantity", 0))
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
    # NOTE (testing): set arrive_time = now so the mission resolves instantly
    arrive_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

    mission_id = m.create_mission(
        player_id, target_type, target_id, formation,
        origin_type, origin_id, arrive_time,
    )

    # Resolve immediately and return result in the same response
    mission = m.get_pending_missions_for_player(player_id)
    resolved_result = None
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
    """Turn a formation spec into Unit objects placed on random Team A cells."""
    positions = random.sample(_TEAM_A_POSITIONS, min(len(_TEAM_A_POSITIONS),
                                                      sum(e["quantity"] for e in formation)))
    all_stats = config.UNIT_STATS
    units: list[Unit] = []
    pos_idx = 0
    for entry in formation:
        utype = entry["unit_type"]
        stats = all_stats.get(utype, {})
        for n in range(entry["quantity"]):
            if pos_idx >= len(positions):
                break
            row, col = positions[pos_idx]; pos_idx += 1
            units.append(Unit(
                unit_id=f"A_{utype[0]}{len(units)+1}",
                team="A",
                unit_type=utype,
                row=row, col=col,
                hp=stats["hp"], max_hp=stats["hp"],
                damage=stats["damage"], defense=stats["defense"],
                range=stats["range"], speed=stats["speed"],
            ))
    return units


def _build_defender_units(defender_spec: list[dict]) -> list[Unit]:
    """
    Turn a defender spec [{type, count}, ...] into Unit objects at random
    Team B positions.
    """
    total = sum(e["count"] for e in defender_spec)
    positions = random.sample(_TEAM_B_POSITIONS, min(len(_TEAM_B_POSITIONS), total))
    all_stats = config.UNIT_STATS
    units: list[Unit] = []
    pos_idx = 0
    for entry in defender_spec:
        utype = entry["type"]
        stats = all_stats.get(utype, config.UNIT_STATS.get("Troll", {}))
        for n in range(entry["count"]):
            if pos_idx >= len(positions):
                break
            row, col = positions[pos_idx]; pos_idx += 1
            units.append(Unit(
                unit_id=f"B_{utype[0]}{len(units)+1}",
                team="B",
                unit_type=utype,
                row=row, col=col,
                hp=stats["hp"], max_hp=stats["hp"],
                damage=stats["damage"], defense=stats["defense"],
                range=stats["range"], speed=stats["speed"],
            ))
    return units


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
        return fort.get("monster_data") or []

    # Player-owned fort: defence buildings + garrisoned troops
    spec: dict[str, int] = {}
    buildings = m.get_buildings("fort", target_id)
    for b in buildings:
        if b["is_destroyed"]:
            continue
        if b["type"] == "Cannon":
            spec["Cannon"] = spec.get("Cannon", 0) + 1
        elif b["type"] == "Archer Tower":
            spec["Archer Tower"] = spec.get("Archer Tower", 0) + 1
    troops = m.get_troops_at("fort", target_id)
    for t in troops:
        spec[t["unit_type"]] = spec.get(t["unit_type"], 0) + t["quantity"]

    return [{"type": k, "count": v} for k, v in spec.items()]


def _resolve_one_mission(mission: dict) -> dict:
    attacker_units  = _build_attacker_units(mission["formation"])
    defender_spec   = _get_defender_spec(mission)
    defender_units  = _build_defender_units(defender_spec) if defender_spec else []

    winner_label = "attacker"

    if not defender_units:
        # Empty target — attacker wins uncontested
        battle_id = str(uuid.uuid4())
    else:
        battle = Battle(attacker_units, defender_units)
        result = battle.run()

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

        winner_label = "attacker" if result.winner == "A" else "defender"

    # Apply consequences
    _apply_outcome(mission, winner_label)
    m.resolve_mission(mission["id"], winner_label, battle_id)

    return {
        "mission_id": mission["id"],
        "battle_id": battle_id,
        "winner": winner_label,
        "target_type": mission["target_type"],
        "target_id": mission["target_id"],
    }


def _apply_outcome(mission: dict, winner_label: str) -> None:
    attacker_id = mission["attacker_id"]
    target_type = mission["target_type"]
    target_id   = mission["target_id"]

    if winner_label == "defender":
        # Total wipeout — all troops already deducted at dispatch, nothing to do
        return

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
