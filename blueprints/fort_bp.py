"""
blueprints/fort_bp.py — Fort and castle management (buildings, troops, resources).
"""

from __future__ import annotations

from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, session, url_for,
)

from blueprints.auth_bp import login_required
from db import models as m
import config

fort_bp = Blueprint("fort", __name__)


# ── Castle page ───────────────────────────────────────────────────────── #

@fort_bp.route("/castle")
@login_required
def castle_page():
    castle = m.get_castle_by_player(session["player_id"])
    if not castle:
        return "Castle not found", 404
    buildings = m.get_buildings("castle", castle["id"])
    troops    = m.get_troops_at("castle", castle["id"])
    pending   = m.get_location_pending_resources("castle", castle["id"])
    return render_template(
        "fort/location.html",
        location=castle, location_type="castle", location_id=castle["id"],
        buildings=buildings, troops=troops, pending=pending,
        build_costs=config.BUILDING_BUILD_COST,
        build_types=list(config.BUILDING_BUILD_TIME.keys()),
        all_slots=range(castle["slot_count"]),
    )


# ── Fort page ─────────────────────────────────────────────────────────── #

@fort_bp.route("/fort/<int:fort_id>")
@login_required
def fort_page(fort_id: int):
    fort = m.get_fort(fort_id)
    if not fort or fort.get("owner_id") != session["player_id"]:
        return "Fort not found or not owned by you", 403
    buildings = m.get_buildings("fort", fort_id)
    troops    = m.get_troops_at("fort", fort_id)
    pending   = m.get_location_pending_resources("fort", fort_id)
    return render_template(
        "fort/location.html",
        location=fort, location_type="fort", location_id=fort_id,
        buildings=buildings, troops=troops, pending=pending,
        build_costs=config.BUILDING_BUILD_COST,
        build_types=list(config.BUILDING_BUILD_TIME.keys()),
        all_slots=range(fort["slot_count"]),
    )


# ── Resource polling (HTMX) ───────────────────────────────────────────── #

@fort_bp.route("/api/fort/<int:fort_id>/resources")
@login_required
def api_fort_resources(fort_id: int):
    fort = m.get_fort(fort_id)
    if not fort or fort.get("owner_id") != session["player_id"]:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(m.get_location_pending_resources("fort", fort_id))


@fort_bp.route("/api/castle/resources")
@login_required
def api_castle_resources():
    castle = m.get_castle_by_player(session["player_id"])
    if not castle:
        return jsonify({"error": "Castle not found"}), 404
    return jsonify(m.get_location_pending_resources("castle", castle["id"]))


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
