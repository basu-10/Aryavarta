"""
blueprints/admin_bp.py — Admin dashboard (role-gated).
"""

from __future__ import annotations

import random

from flask import (
    Blueprint, jsonify, render_template,
    request,
)
from werkzeug.security import generate_password_hash

from blueprints.auth_bp import admin_required
from db import models as m
from db.models import find_empty_cell
from db.world_seeder import seed_world
import config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    players = m.get_all_players()
    forts   = m.get_all_forts()
    camps   = m.get_all_active_monster_camps()
    clans   = m.get_all_clans()
    return render_template(
        "admin/dashboard.html",
        players=players, forts=forts, camps=camps, clans=clans,
        unit_stats=config.UNIT_STATS,
        unit_types=config.UNIT_TYPES,
        building_types=list(config.BUILDING_BUILD_COST.keys()),
    )


# ── User management ───────────────────────────────────────────────────── #

@admin_bp.route("/ban/<int:player_id>", methods=["POST"])
@admin_required
def ban_player(player_id: int):
    m.ban_player(player_id)
    return jsonify({"ok": True})


@admin_bp.route("/unban/<int:player_id>", methods=["POST"])
@admin_required
def unban_player(player_id: int):
    m.set_player_role(player_id, "player")
    return jsonify({"ok": True})


@admin_bp.route("/promote/<int:player_id>", methods=["POST"])
@admin_required
def promote_player(player_id: int):
    m.set_player_role(player_id, "admin")
    return jsonify({"ok": True})


@admin_bp.route("/demote/<int:player_id>", methods=["POST"])
@admin_required
def demote_player(player_id: int):
    m.set_player_role(player_id, "player")
    return jsonify({"ok": True})


@admin_bp.route("/users/create", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    role     = data.get("role", "player")

    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password are required."}), 400
    if role not in ("player", "admin"):
        return jsonify({"ok": False, "error": "Role must be 'player' or 'admin'."}), 400
    if m.get_player_by_username(username):
        return jsonify({"ok": False, "error": "Username already taken."}), 409

    pw_hash = generate_password_hash(password)
    player_id = m.create_player(username, pw_hash)
    if role == "admin":
        m.set_player_role(player_id, "admin")

    # Give the new user a castle on the world map
    slot_count = random.choices(
        [4, 5, 6, 7, 8, 9, 10],
        weights=config.FORT_SLOT_WEIGHTS,
    )[0]
    cx, cy = find_empty_cell()
    m.create_castle(player_id, slot_count, cx, cy)

    return jsonify({"ok": True, "player_id": player_id, "username": username})


@admin_bp.route("/users/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_user(player_id: int):
    ok = m.delete_player(player_id)
    if not ok:
        return jsonify({"ok": False, "error": "Player not found."}), 404
    return jsonify({"ok": True})


# ── Resource management ───────────────────────────────────────────────── #

@admin_bp.route("/users/<int:player_id>/resources", methods=["POST"])
@admin_required
def edit_resources(player_id: int):
    """
    Body: { action: "add"|"set", food?: N, timber?: N, gold?: N, metal?: N }
    """
    if not m.get_player_by_id(player_id):
        return jsonify({"ok": False, "error": "Player not found."}), 404

    data   = request.get_json(force=True, silent=True) or {}
    action = data.get("action", "add")

    def _f(key):
        v = data.get(key)
        return float(v) if v not in (None, "") else None

    food   = _f("food")
    timber = _f("timber")
    gold   = _f("gold")
    metal  = _f("metal")

    if action == "set":
        m.set_player_resources(player_id, food=food, timber=timber, gold=gold, metal=metal)
    else:
        m.add_player_resources(
            player_id,
            food=food or 0,
            timber=timber or 0,
            gold=gold or 0,
            metal=metal or 0,
        )

    p = m.get_player_by_id(player_id)
    return jsonify({"ok": True, "food": p["food"], "timber": p["timber"],
                    "gold": p["gold"], "metal": p["metal"]})


# ── Troop management ──────────────────────────────────────────────────── #

@admin_bp.route("/users/<int:player_id>/troops", methods=["POST"])
@admin_required
def add_troops(player_id: int):
    """Body: { unit_type: str, quantity: int }"""
    if not m.get_player_by_id(player_id):
        return jsonify({"ok": False, "error": "Player not found."}), 404

    data      = request.get_json(force=True, silent=True) or {}
    unit_type = data.get("unit_type", "").strip()
    quantity  = int(data.get("quantity", 0))

    if unit_type not in config.UNIT_STATS:
        return jsonify({"ok": False, "error": f"Unknown unit type: {unit_type}"}), 400
    if quantity <= 0:
        return jsonify({"ok": False, "error": "Quantity must be > 0"}), 400

    ok = m.admin_add_troops_to_castle(player_id, unit_type, quantity)
    if not ok:
        return jsonify({"ok": False, "error": "Player has no castle."}), 400
    return jsonify({"ok": True})


# ── Fort management ───────────────────────────────────────────────────── #

@admin_bp.route("/users/<int:player_id>/grant-fort", methods=["POST"])
@admin_required
def grant_fort(player_id: int):
    """Body: { slot_count?: int, fully_built?: bool }"""
    if not m.get_player_by_id(player_id):
        return jsonify({"ok": False, "error": "Player not found."}), 404

    data        = request.get_json(force=True, silent=True) or {}
    slot_count  = int(data.get("slot_count", 6))
    fully_built = bool(data.get("fully_built", False))

    slot_count = max(4, min(10, slot_count))
    fort_id = m.admin_grant_fort(player_id, slot_count=slot_count, fully_built=fully_built)
    return jsonify({"ok": True, "fort_id": fort_id})


# ── World management ──────────────────────────────────────────────────── #

@admin_bp.route("/spawn", methods=["POST"])
@admin_required
def spawn_entities():
    data = request.get_json(force=True, silent=True) or {}
    num_forts = int(data.get("forts", 5))
    num_camps = int(data.get("camps", 5))
    counts = seed_world(num_forts=num_forts, num_camps=num_camps, force=True)
    return jsonify({"ok": True, **counts})


@admin_bp.route("/deactivate-camp/<int:camp_id>", methods=["POST"])
@admin_required
def deactivate_camp(camp_id: int):
    m.deactivate_monster_camp(camp_id)
    return jsonify({"ok": True})


# ── Clan management ───────────────────────────────────────────────────── #

@admin_bp.route("/disband-clan/<int:clan_id>", methods=["POST"])
@admin_required
def disband_clan(clan_id: int):
    m.disband_clan(clan_id)
    return jsonify({"ok": True})
