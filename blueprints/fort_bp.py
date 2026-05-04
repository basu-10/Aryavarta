"""
blueprints/fort_bp.py — Fort and castle management (buildings, troops, resources).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, session, url_for,
)

from blueprints.auth_bp import login_required
from db import models as m
import config

fort_bp = Blueprint("fort", __name__)
_PRESETS_DIR = Path(__file__).parent.parent / "presets"


# ── Castle page ───────────────────────────────────────────────────────── #

@fort_bp.route("/castle")
@login_required
def castle_page():
    castle = m.get_castle_by_player(session["player_id"])
    if not castle:
        return "Castle not found", 404
    m.process_all_training_queues("castle", castle["id"])
    buildings = m.get_buildings("castle", castle["id"])
    troops    = m.get_troops_at("castle", castle["id"])
    pending   = m.get_location_pending_resources("castle", castle["id"])
    owned_forts = m.get_forts_by_owner(session["player_id"])
    fort_cards = []
    for f in owned_forts:
        m.process_all_training_queues("fort", f["id"])
        f_pending = m.get_location_pending_resources("fort", f["id"])
        f_troops = m.get_troops_at("fort", f["id"])
        queue_count = m.get_location_training_queue_count("fort", f["id"])
        troop_total = sum(int(t["quantity"]) for t in f_troops)
        pending_total = sum(float(v) for v in f_pending.values())
        distance = max(abs(int(f["grid_x"]) - int(castle["grid_x"])), abs(int(f["grid_y"]) - int(castle["grid_y"])))
        fort_cards.append({
            "id": f["id"],
            "grid_x": f["grid_x"],
            "grid_y": f["grid_y"],
            "star_level": f.get("star_level", 1),
            "troop_total": troop_total,
            "queue_count": queue_count,
            "pending_total": round(pending_total, 1),
            "distance": distance,
            "pending_breakdown": f_pending,
        })
    player = m.get_player_by_id(session["player_id"])
    return render_template(
        "fort/location.html",
        location=castle, location_type="castle", location_id=castle["id"],
        buildings=buildings, troops=troops, pending=pending,
        player=player,
        owned_fort_cards=fort_cards,
        build_costs=config.BUILDING_BUILD_COST,
        build_types=list(config.BUILDING_BUILD_TIME.keys()),
        all_slots=range(1, castle["slot_count"] + 1),
    )


# ── Fort page ─────────────────────────────────────────────────────────── #

@fort_bp.route("/fort/<int:fort_id>")
@login_required
def fort_page(fort_id: int):
    fort = m.get_fort(fort_id)
    if not fort or fort.get("owner_id") != session["player_id"]:
        return "Fort not found or not owned by you", 403
    m.process_all_training_queues("fort", fort_id)
    buildings = m.get_buildings("fort", fort_id)
    troops    = m.get_troops_at("fort", fort_id)
    pending   = m.get_location_pending_resources("fort", fort_id)
    return render_template(
        "fort/location.html",
        location=fort, location_type="fort", location_id=fort_id,
        buildings=buildings, troops=troops, pending=pending,
        owned_fort_cards=[],
        build_costs=config.BUILDING_BUILD_COST,
        build_types=list(config.BUILDING_BUILD_TIME.keys()),
        all_slots=range(1, fort["slot_count"] + 1),
    )


# ── Resource polling (HTMX) — returns rendered HTML partial ──────────── #

@fort_bp.route("/api/fort/<int:fort_id>/resources")
@login_required
def api_fort_resources(fort_id: int):
    fort = m.get_fort(fort_id)
    if not fort or fort.get("owner_id") != session["player_id"]:
        return "Forbidden", 403
    pending = m.get_location_pending_resources("fort", fort_id)
    troops = m.get_troops_at("fort", fort_id)
    return render_template("fort/_header_cards.html", pending=pending, troops=troops, player=None)


@fort_bp.route("/api/castle/resources")
@login_required
def api_castle_resources():
    castle = m.get_castle_by_player(session["player_id"])
    if not castle:
        return "Not found", 404
    pending = m.get_location_pending_resources("castle", castle["id"])
    troops = m.get_troops_at("castle", castle["id"])
    player = m.get_player_by_id(session["player_id"])
    return render_template("fort/_header_cards.html", pending=pending, troops=troops, player=player)


# ── Collect ───────────────────────────────────────────────────────────── #

@fort_bp.route("/api/collect", methods=["POST"])
@login_required
def api_collect():
    data = request.get_json(force=True, silent=True) or {}
    location_type = data.get("location_type")
    location_id   = int(data.get("location_id", 0))

    if not _owns_location(session["player_id"], location_type, location_id):
        return jsonify({"error": "Forbidden"}), 403

    totals = m.collect_all_from_location(location_type, location_id, session["player_id"])
    return jsonify({"ok": True, "collected": totals})


# ── Place building ────────────────────────────────────────────────────── #

@fort_bp.route("/api/build", methods=["POST"])
@login_required
def api_build():
    data = request.get_json(force=True, silent=True) or {}
    location_type = data.get("location_type")
    location_id   = int(data.get("location_id", 0))
    slot_index    = int(data.get("slot_index", -1))
    building_type = data.get("building_type", "")

    if not _owns_location(session["player_id"], location_type, location_id):
        return jsonify({"error": "Forbidden"}), 403
    if building_type not in config.BUILDING_BUILD_TIME:
        return jsonify({"error": "Unknown building type"}), 400
    if building_type == "Command Centre":
        return jsonify({"error": "Command Centre is a default building"}), 400

    # Check slot is empty
    existing = m.get_buildings(location_type, location_id)
    taken = {b["slot_index"] for b in existing}
    if slot_index in taken:
        return jsonify({"error": "Slot is occupied"}), 409

    # Check and deduct cost
    cost = config.BUILDING_BUILD_COST.get(building_type, {})
    if not m.deduct_player_resources(session["player_id"], **cost):
        return jsonify({"error": "Not enough resources"}), 402

    building_id = m.place_building(location_type, location_id, slot_index, building_type)
    return jsonify({"ok": True, "building_id": building_id})


# ── Repair building ───────────────────────────────────────────────────── #

@fort_bp.route("/api/repair", methods=["POST"])
@login_required
def api_repair():
    data = request.get_json(force=True, silent=True) or {}
    building_id = int(data.get("building_id", 0))
    b = m.get_building_by_id(building_id)
    if not b:
        return jsonify({"error": "Building not found"}), 404
    if not _owns_location(session["player_id"], b["location_type"], b["location_id"]):
        return jsonify({"error": "Forbidden"}), 403
    if not b["is_destroyed"]:
        return jsonify({"error": "Building is not destroyed"}), 400

    cost = config.BUILDING_REPAIR_COST.get(b["type"], {})
    if not m.deduct_player_resources(session["player_id"], **cost):
        return jsonify({"error": "Not enough resources"}), 402

    m.repair_building(building_id)
    return jsonify({"ok": True})


# ── Helpers ───────────────────────────────────────────────────────────── #

def _owns_location(player_id: int, location_type: str, location_id: int) -> bool:
    if location_type == "castle":
        c = m.get_castle_by_id(location_id)
        return bool(c and c["player_id"] == player_id)
    elif location_type == "fort":
        f = m.get_fort(location_id)
        return bool(f and f.get("owner_id") == player_id)
    return False


def _owns_building(player_id: int, building_id: int):
    """Return the building dict if the player owns its location, else None."""
    b = m.get_building_by_id(building_id)
    if not b:
        return None
    if not _owns_location(player_id, b["location_type"], b["location_id"]):
        return None
    return b


def _safe_preset_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()


def _list_presets_with_names() -> list[dict]:
    _PRESETS_DIR.mkdir(exist_ok=True)
    presets: list[dict] = []
    for f in sorted(_PRESETS_DIR.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = str(payload.get("name") or f.stem).strip()
        if not name:
            continue
        presets.append({"name": name, "army_a": payload.get("army_a", [])})
    return presets


def _resolve_effective_defense_preset_name(selected_name: str, preset_names: list[str]) -> str | None:
    if selected_name and selected_name in preset_names:
        return selected_name
    if len(preset_names) == 1:
        return preset_names[0]
    return None


@fort_bp.route("/api/fort/<int:fort_id>/defense-presets")
@login_required
def api_fort_defense_presets(fort_id: int):
    fort = m.get_fort(fort_id)
    if not fort or fort.get("owner_id") != session["player_id"]:
        return jsonify({"error": "Forbidden"}), 403

    presets = _list_presets_with_names()
    preset_names = [p["name"] for p in presets]
    selected = str(fort.get("defense_preset_name") or "").strip()
    effective = _resolve_effective_defense_preset_name(selected, preset_names)

    return jsonify({
        "fort_id": fort_id,
        "selected_preset_name": selected or None,
        "effective_preset_name": effective,
        "presets": presets,
        "selection_required": len(preset_names) > 1 and not effective,
    })


@fort_bp.route("/api/fort/<int:fort_id>/defense-preset", methods=["POST"])
@login_required
def api_set_fort_defense_preset(fort_id: int):
    fort = m.get_fort(fort_id)
    if not fort or fort.get("owner_id") != session["player_id"]:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(force=True, silent=True) or {}
    requested = str(data.get("preset_name") or "").strip()
    if not requested:
        m.set_fort_defense_preset(fort_id, None)
        return jsonify({"ok": True, "preset_name": None})

    safe = _safe_preset_name(requested)
    if not safe:
        return jsonify({"error": "Invalid preset name"}), 400

    preset_names = [p["name"] for p in _list_presets_with_names()]
    if requested not in preset_names:
        return jsonify({"error": "Preset not found"}), 404

    m.set_fort_defense_preset(fort_id, requested)
    return jsonify({"ok": True, "preset_name": requested})


# ── Building details (used by panel UI) ───────────────────────────────── #

@fort_bp.route("/api/building/<int:building_id>/details")
@login_required
def api_building_details(building_id: int):
    b = _owns_building(session["player_id"], building_id)
    if not b:
        return jsonify({"error": "Not found or forbidden"}), 404

    # Process any completed training before returning queue
    m.process_training_queue(building_id, b["location_type"], b["location_id"])

    payload: dict = {"building": b}

    army = config.ARMY_BUILDINGS.get(b["type"])
    if army:
        queue = m.get_training_queue(building_id)
        troops = m.get_troops_at(b["location_type"], b["location_id"])
        troop_count = next(
            (t["quantity"] for t in troops if t["unit_type"] == army["unit_type"]), 0
        )
        payload["army"] = army
        payload["queue"] = queue
        payload["troop_count"] = troop_count
        payload["all_troops"] = troops
        payload["train_cost"] = config.TROOP_TRAIN_COST.get(army["unit_type"], {})

    ammo_type = config.DEFENCE_BUILDING_AMMO.get(b["type"])
    if ammo_type:
        payload["ammo_type"] = ammo_type
        payload["ammo_count"] = m.get_building_ammo(building_id).get(ammo_type, 0)
        payload["ammo_cost"] = config.AMMO_COST.get(ammo_type, {})

    if b["type"] == "Command Centre":
        troops = m.get_troops_at(b["location_type"], b["location_id"])
        all_stats = config.UNIT_STATS
        payload["troops"] = [
            {**t, "stats": all_stats.get(t["unit_type"], {})} for t in troops
        ]

    base_upgrade = config.BUILDING_UPGRADE_COST.get(b["type"], {})
    if base_upgrade:
        level = b.get("level", 1)
        scale = config.BUILDING_LEVEL_MULTIPLIER ** (level - 1)
        payload["upgrade_cost"] = {k: int(v * scale) for k, v in base_upgrade.items()}

    return jsonify(payload)


# ── Upgrade building ───────────────────────────────────────────────────── #

@fort_bp.route("/api/building/upgrade", methods=["POST"])
@login_required
def api_upgrade_building():
    data = request.get_json(force=True, silent=True) or {}
    building_id = int(data.get("building_id", 0))
    b = _owns_building(session["player_id"], building_id)
    if not b:
        return jsonify({"error": "Not found or forbidden"}), 404
    ok, err = m.upgrade_building_with_cost(building_id, session["player_id"])
    if not ok:
        return jsonify({"error": err}), 400
    return jsonify({"ok": True, "new_level": b["level"] + 1})


# ── Train troop ────────────────────────────────────────────────────────── #

@fort_bp.route("/api/troop/train", methods=["POST"])
@login_required
def api_troop_train():
    data = request.get_json(force=True, silent=True) or {}
    building_id = int(data.get("building_id", 0))
    b = _owns_building(session["player_id"], building_id)
    if not b:
        return jsonify({"error": "Not found or forbidden"}), 404
    if b["is_destroyed"] or b["build_complete_at"]:
        return jsonify({"error": "Building not operational"}), 400

    army = config.ARMY_BUILDINGS.get(b["type"])
    if not army:
        return jsonify({"error": "This building does not train troops"}), 400

    unit_type = army["unit_type"]
    cost = config.TROOP_TRAIN_COST.get(unit_type, {})
    if cost and not m.deduct_player_resources(session["player_id"], **cost):
        return jsonify({"error": "Not enough resources"}), 402

    entry = m.queue_troop_training(
        building_id, session["player_id"], unit_type, army["training_seconds"]
    )
    return jsonify({"ok": True, "queue_entry": entry})


# ── Delete troop ───────────────────────────────────────────────────────── #

@fort_bp.route("/api/troop/delete", methods=["POST"])
@login_required
def api_troop_delete():
    data = request.get_json(force=True, silent=True) or {}
    troop_id = int(data.get("troop_id", 0))
    quantity = max(1, int(data.get("quantity", 1)))
    ok = m.delete_troop_with_refund(troop_id, session["player_id"], quantity)
    if not ok:
        return jsonify({"error": "Troop not found or forbidden"}), 404
    return jsonify({"ok": True})


# ── Load ammo ──────────────────────────────────────────────────────────── #

@fort_bp.route("/api/ammo/load", methods=["POST"])
@login_required
def api_ammo_load():
    data = request.get_json(force=True, silent=True) or {}
    building_id = int(data.get("building_id", 0))
    count = max(1, int(data.get("count", 1)))
    b = _owns_building(session["player_id"], building_id)
    if not b:
        return jsonify({"error": "Not found or forbidden"}), 404

    ammo_type = config.DEFENCE_BUILDING_AMMO.get(b["type"])
    if not ammo_type:
        return jsonify({"error": "This building does not use ammo"}), 400
    if b["is_destroyed"] or b["build_complete_at"]:
        return jsonify({"error": "Building not operational"}), 400

    ok, err = m.add_building_ammo(building_id, ammo_type, count, session["player_id"])
    if not ok:
        return jsonify({"error": err}), 400
    new_count = m.get_building_ammo(building_id).get(ammo_type, 0)
    return jsonify({"ok": True, "ammo_type": ammo_type, "count": new_count})

