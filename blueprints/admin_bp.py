"""
blueprints/admin_bp.py — Admin dashboard (role-gated).
"""

from __future__ import annotations

import random

from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import generate_password_hash

from blueprints.auth_bp import admin_required
from db import get_db, models as m
from db.models import find_empty_cell
from db.world_seeder import seed_world, generate_world
from utils.admin_test_harness import list_available_presets, run_admin_formation_tests
import config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    players = m.get_all_players()
    forts   = m.get_all_forts()
    camps   = m.get_all_active_monster_camps()
    clans   = m.get_all_clans()
    worlds  = m.get_all_worlds()
    return render_template(
        "admin/dashboard.html",
        players=players, forts=forts, camps=camps, clans=clans,
        worlds=worlds,
        unit_stats=config.UNIT_STATS,
        unit_types=config.UNIT_TYPES,
        building_types=list(config.BUILDING_BUILD_COST.keys()),
        available_themes=config.AVAILABLE_THEMES,
        active_theme=config.ACTIVE_THEME,
    )


@admin_bp.route("/test-run", methods=["GET"])
@admin_required
def test_run_page():
    return render_template("admin/test_run.html", presets=list_available_presets())


@admin_bp.route("/test-run", methods=["POST"])
@admin_required
def run_test_harness():
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("auth.login"))

    preset_names = request.form.getlist("preset_names")
    target_types = set(request.form.getlist("target_types"))
    star_level_raw = request.form.get("star_level", "1").strip()
    max_targets_raw = request.form.get("max_targets", "").strip()

    try:
        star_level = int(star_level_raw)
    except ValueError:
        star_level = 1

    max_targets = None
    if max_targets_raw:
        try:
            max_targets = int(max_targets_raw)
        except ValueError:
            max_targets = None

    try:
        summary = run_admin_formation_tests(
            admin_player_id=player_id,
            preset_names=preset_names,
            star_level=star_level,
            target_types=target_types,
            max_targets=max_targets,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.test_run_page"))

    resolved = summary.get("resolved_battles", 0)
    failures = summary.get("failures", [])
    flash(
        f"Test run complete: {resolved} battle(s) resolved for admin history.",
        "success" if resolved > 0 else "error",
    )
    if failures:
        flash(f"{len(failures)} run(s) failed. First error: {failures[0]}", "error")

    return redirect(url_for("auth.battles"))


# ── Theme management ─────────────────────────────────────────────────── #

@admin_bp.route("/set-theme/<theme_name>", methods=["POST"])
@admin_required
def set_theme(theme_name: str):
    """Switch active theme (instant, no DB required)."""
    if theme_name not in config.AVAILABLE_THEMES:
        return jsonify({"ok": False, "error": f"Theme '{theme_name}' not found."}), 400
    config.ACTIVE_THEME = theme_name
    return jsonify({"ok": True, "active_theme": config.ACTIVE_THEME})


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


@admin_bp.route("/promote-mod/<int:player_id>", methods=["POST"])
@admin_required
def promote_mod(player_id: int):
    m.set_player_role(player_id, "mod")
    return jsonify({"ok": True})


@admin_bp.route("/demote-mod/<int:player_id>", methods=["POST"])
@admin_required
def demote_mod(player_id: int):
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
    if role not in ("player", "admin", "mod"):
        return jsonify({"ok": False, "error": "Role must be 'player', 'admin', or 'mod'."}), 400
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
    world_id = int(data.get("world_id") or 0)
    world = m.get_world(world_id) if world_id else None
    if not world:
        # Fall back to first available world
        worlds = m.get_all_worlds()
        world = worlds[0] if worlds else None
        world_id = world["id"] if world else 0
    grid_w = world["grid_width"] if world else config.WORLD_GRID_W
    grid_h = world["grid_height"] if world else config.WORLD_GRID_H
    cx, cy = find_empty_cell(world_id, grid_w, grid_h)
    m.create_castle(player_id, slot_count, cx, cy, world_id)

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
    """Body: { unit_type: str, quantity: int, world_id?: int }"""
    if not m.get_player_by_id(player_id):
        return jsonify({"ok": False, "error": "Player not found."}), 404

    data      = request.get_json(force=True, silent=True) or {}
    unit_type = data.get("unit_type", "").strip()
    quantity  = int(data.get("quantity", 0))
    world_id  = int(data.get("world_id") or 0) or None

    if unit_type not in config.UNIT_STATS:
        return jsonify({"ok": False, "error": f"Unknown unit type: {unit_type}"}), 400
    if quantity <= 0:
        return jsonify({"ok": False, "error": "Quantity must be > 0"}), 400

    ok = m.admin_add_troops_to_castle(player_id, unit_type, quantity, world_id=world_id)
    if not ok:
        return jsonify({"ok": False, "error": "Player has no castle in that world."}), 400
    return jsonify({"ok": True})


# ── Fort management ───────────────────────────────────────────────────── #

@admin_bp.route("/users/<int:player_id>/grant-fort", methods=["POST"])
@admin_required
def grant_fort(player_id: int):
    """Body: { slot_count?: int, fully_built?: bool, world_id?: int }"""
    if not m.get_player_by_id(player_id):
        return jsonify({"ok": False, "error": "Player not found."}), 404

    data        = request.get_json(force=True, silent=True) or {}
    slot_count  = int(data.get("slot_count", 6))
    fully_built = bool(data.get("fully_built", False))
    world_id    = int(data.get("world_id") or 0)

    # Default to first available world if not specified
    if not world_id:
        worlds = m.get_all_worlds()
        if not worlds:
            return jsonify({"ok": False, "error": "No worlds exist yet."}), 400
        world_id = worlds[0]["id"]

    slot_count = max(4, min(10, slot_count))
    fort_id = m.admin_grant_fort(player_id, slot_count=slot_count, fully_built=fully_built,
                                 world_id=world_id)
    return jsonify({"ok": True, "fort_id": fort_id})


# ── World management ──────────────────────────────────────────────────── #
@admin_bp.route("/worlds")
@admin_required
def list_worlds():
    worlds = m.get_all_worlds()
    return render_template("admin/worlds.html", worlds=worlds,
                           default_w=config.WORLD_GRID_W,
                           default_h=config.WORLD_GRID_H)


@admin_bp.route("/worlds", methods=["POST"])
@admin_required
def create_world():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "World name is required."}), 400
    grid_w = max(20, int(data.get("grid_width") or config.WORLD_GRID_W))
    grid_h = max(20, int(data.get("grid_height") or config.WORLD_GRID_H))
    num_forts = max(0, int(data.get("num_forts") or 15))
    num_camps = max(0, int(data.get("num_camps") or 10))
    try:
        world_id = m.create_world(name, grid_w, grid_h, num_forts, num_camps)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 409
    generate_world(world_id, grid_w, grid_h, num_forts, num_camps)
    return jsonify({"ok": True, "world_id": world_id})


@admin_bp.route("/worlds/<int:world_id>")
@admin_required
def view_world(world_id: int):
    world = m.get_world(world_id)
    if not world:
        return "Not found", 404
    forts = m.get_all_forts(world_id)
    camps = m.get_all_active_monster_camps(world_id)
    return render_template("admin/world_detail.html", world=world,
                           forts=forts, camps=camps)


@admin_bp.route("/worlds/<int:world_id>/delete", methods=["POST"])
@admin_required
def delete_world(world_id: int):
    ok = m.delete_world(world_id)
    if not ok:
        return jsonify({"ok": False, "error": "World not found."}), 404
    return jsonify({"ok": True})


@admin_bp.route("/worlds/<int:world_id>/set-default", methods=["POST"])
@admin_required
def set_default_world(world_id: int):
    if not m.get_world(world_id):
        return jsonify({"ok": False, "error": "World not found."}), 404
    m.set_default_world(world_id)
    return jsonify({"ok": True})


@admin_bp.route("/worlds/<int:world_id>/purge-chat", methods=["POST"])
@admin_required
def purge_world_chat(world_id: int):
    if not m.get_world(world_id):
        return jsonify({"ok": False, "error": "World not found."}), 404
    count = m.purge_deleted_world_messages(world_id)
    return jsonify({"ok": True, "purged": count})

@admin_bp.route("/spawn", methods=["POST"])
@admin_required
def spawn_entities():
    data = request.get_json(force=True, silent=True) or {}
    num_forts = int(data.get("forts", 5))
    num_camps = int(data.get("camps", 5))
    world_id  = int(data.get("world_id") or 0)
    counts = seed_world(num_forts=num_forts, num_camps=num_camps, force=True, world_id=world_id or None)
    return jsonify({"ok": True, **counts})


@admin_bp.route("/deactivate-camp/<int:camp_id>", methods=["POST"])
@admin_required
def deactivate_camp(camp_id: int):
    m.deactivate_monster_camp(camp_id)
    return jsonify({"ok": True})


@admin_bp.route("/users/<int:player_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(player_id: int):
    """Body: { password: str }"""
    if not m.get_player_by_id(player_id):
        return jsonify({"ok": False, "error": "Player not found."}), 404
    data = request.get_json(force=True, silent=True) or {}
    new_pw = (data.get("password") or "").strip()
    if not new_pw:
        return jsonify({"ok": False, "error": "Password cannot be empty."}), 400
    db = get_db()
    db.execute(
        "UPDATE player SET password_hash=? WHERE id=?",
        (generate_password_hash(new_pw), player_id),
    )
    db.commit()
    return jsonify({"ok": True})


# ── Clan management ───────────────────────────────────────────────────── #

@admin_bp.route("/disband-clan/<int:clan_id>", methods=["POST"])
@admin_required
def disband_clan(clan_id: int):
    m.disband_clan(clan_id)
    return jsonify({"ok": True})
