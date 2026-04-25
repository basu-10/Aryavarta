"""
battle_bp.py — Flask blueprint for BattleCells routes.

Routes
------
GET  /              → redirect to /setup
GET  /setup         → army builder form
POST /run           → run simulation, return battle_id
GET  /results/<id>  → tick stepper page
GET  /download/<id> → download battle CSV
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from engine.battle import Battle
from engine.unit import Unit
from utils.csv_writer import write_battle_csv
from utils.serializer import build_tick_data, army_from_json
from utils.troops_store import (
    load_custom_troops,
    save_custom_troops,
    get_all_unit_stats,
    get_all_unit_types,
)
import config

battle_bp = Blueprint("battle", __name__)

# In-memory battle store: battle_id -> { tick_data, csv_path, winner, total_ticks }
# In production you'd persist this, but for V1 an in-process dict is fine.
_battles: dict[str, dict] = {}


@battle_bp.route("/")
def index():
    return redirect(url_for("battle.setup"))


@battle_bp.route("/setup")
def setup():
    all_stats = get_all_unit_stats()
    return render_template(
        "setup.html",
        grid_rows=config.GRID_ROWS,
        grid_cols=config.GRID_COLS,
        team_a_cols=config.TEAM_A_COLS,
        team_b_cols=config.TEAM_B_COLS,
        unit_types=list(all_stats.keys()),
        unit_stats=all_stats,
        move_behaviors=config.MOVE_BEHAVIORS,
        attack_behaviors=config.ATTACK_BEHAVIORS,
    )


# ------------------------------------------------------------------ #
# Troop type routes                                                    #
# ------------------------------------------------------------------ #

@battle_bp.route("/troops")
def troops_page():
    return render_template(
        "troops.html",
        builtin_stats=config.UNIT_STATS,
        move_behaviors=config.MOVE_BEHAVIORS,
        attack_behaviors=config.ATTACK_BEHAVIORS,
    )


@battle_bp.route("/api/troops", methods=["GET"])
def api_list_troops():
    custom = load_custom_troops()
    builtin = [
        {"name": name, **stats, "builtin": True}
        for name, stats in config.UNIT_STATS.items()
    ]
    return jsonify({"builtin": builtin, "custom": custom})


@battle_bp.route("/api/troops", methods=["POST"])
def api_create_troop():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    # Reject names that clash with built-in types
    if name in config.UNIT_STATS:
        return jsonify({"error": f"'{name}' is a built-in type and cannot be overridden"}), 409

    custom = load_custom_troops()
    if any(t["name"].lower() == name.lower() for t in custom):
        return jsonify({"error": f"A custom troop named '{name}' already exists"}), 409

    def _int_field(key: str, default: int, min_val: int = 0) -> int:
        try:
            return max(min_val, int(data.get(key, default)))
        except (TypeError, ValueError):
            return default

    new_troop = {
        "name": name,
        "hp": _int_field("hp", 10, 1),
        "damage": _int_field("damage", 1, 0),
        "defense": _int_field("defense", 0, 0),
        "range": _int_field("range", 1, 1),
        "speed": _int_field("speed", 1, 1),
        "default_move": data.get("default_move", config.MOVE_BEHAVIORS[0]),
        "default_attack": data.get("default_attack", config.ATTACK_BEHAVIORS[0]),
    }
    custom.append(new_troop)
    save_custom_troops(custom)
    return jsonify({"ok": True, "troop": new_troop}), 201


@battle_bp.route("/api/troops/<name>", methods=["DELETE"])
def api_delete_troop(name: str):
    custom = load_custom_troops()
    new_list = [t for t in custom if t["name"] != name]
    if len(new_list) == len(custom):
        return jsonify({"error": "Troop type not found"}), 404
    save_custom_troops(new_list)
    return jsonify({"ok": True})


# ------------------------------------------------------------------ #
# Preset routes                                                        #
# ------------------------------------------------------------------ #

PRESETS_DIR = Path(__file__).parent.parent / "presets"


def _safe_preset_name(name: str) -> str:
    """Strip filesystem-unsafe chars; keep spaces and common punctuation."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()


@battle_bp.route("/presets", methods=["GET"])
def list_presets():
    PRESETS_DIR.mkdir(exist_ok=True)
    names = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            names.append(data.get("name", f.stem))
        except Exception:
            names.append(f.stem)
    return jsonify({"presets": names})


@battle_bp.route("/presets/<path:name>", methods=["GET"])
def get_preset(name: str):
    safe = _safe_preset_name(name)
    path = PRESETS_DIR / f"{safe}.json"
    if not path.exists():
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@battle_bp.route("/presets", methods=["POST"])
def save_preset():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Preset name is required"}), 400
    safe = _safe_preset_name(name)
    if not safe:
        return jsonify({"error": "Preset name contains only invalid characters"}), 400
    PRESETS_DIR.mkdir(exist_ok=True)
    payload = {
        "name": name,
        "army_a": data.get("army_a", []),
        "army_b": data.get("army_b", []),
    }
    (PRESETS_DIR / f"{safe}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return jsonify({"ok": True, "name": name})


@battle_bp.route("/run", methods=["POST"])
def run():
    """
    Accepts JSON body:
      {
        "army_a": [ <unit_dict>, ... ],
        "army_b": [ <unit_dict>, ... ]
      }
    Returns:
      { "battle_id": "<uuid>", "redirect": "/results/<uuid>" }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    army_a_raw: list[dict] = data.get("army_a", [])
    army_b_raw: list[dict] = data.get("army_b", [])

    if not army_a_raw or not army_b_raw:
        return jsonify({"error": "Both army_a and army_b must be non-empty"}), 400

    # Validate unit positions
    errors = _validate_armies(army_a_raw, army_b_raw)
    if errors:
        return jsonify({"error": errors}), 422

    try:
        army_a = army_from_json(army_a_raw)
        army_b = army_from_json(army_b_raw)
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422

    # Run simulation
    try:
        battle = Battle(army_a, army_b)
        result = battle.run()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    # Persist results
    battle_id = str(uuid.uuid4())
    csv_path = Path(current_app.config["OUTPUT_DIR"]) / f"{battle_id}.csv"
    write_battle_csv(result, csv_path)

    tick_data = build_tick_data(result)

    _battles[battle_id] = {
        "tick_data": tick_data,
        "csv_path": str(csv_path),
        "winner": result.winner,
        "total_ticks": result.total_ticks,
    }

    return jsonify(
        {
            "battle_id": battle_id,
            "redirect": url_for("battle.results", battle_id=battle_id),
        }
    )


@battle_bp.route("/results/<battle_id>")
def results(battle_id: str):
    record = _battles.get(battle_id)
    if record is None:
        return "Battle not found. It may have expired (server restart clears memory).", 404

    return render_template(
        "results.html",
        battle_id=battle_id,
        winner=record["winner"],
        total_ticks=record["total_ticks"],
        grid_rows=config.GRID_ROWS,
        grid_cols=config.GRID_COLS,
        tick_data_json=json.dumps(record["tick_data"]),
    )


@battle_bp.route("/download/<battle_id>")
def download(battle_id: str):
    record = _battles.get(battle_id)
    if record is None:
        return "Battle not found.", 404

    csv_path = Path(record["csv_path"])
    if not csv_path.exists():
        return "CSV file not found.", 404

    return send_file(
        csv_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"battle_{battle_id[:8]}.csv",
    )


# ------------------------------------------------------------------ #
# Validation helpers                                                   #
# ------------------------------------------------------------------ #

def _validate_armies(army_a: list[dict], army_b: list[dict]) -> list[str]:
    errors = []
    all_positions: set[tuple[int, int]] = set()

    for label, army, allowed_cols in [
        ("Team A", army_a, config.TEAM_A_COLS),
        ("Team B", army_b, config.TEAM_B_COLS),
    ]:
        for i, u in enumerate(army):
            uid = u.get("unit_id", f"unit_{i}")
            row = u.get("row")
            col = u.get("col")

            if row is None or col is None:
                errors.append(f"{label} unit {uid}: missing row/col")
                continue

            if not (0 <= row < config.GRID_ROWS):
                errors.append(f"{label} unit {uid}: row {row} out of bounds (0-{config.GRID_ROWS - 1})")

            if col not in allowed_cols:
                errors.append(
                    f"{label} unit {uid}: col {col} not in allowed columns {allowed_cols}"
                )

            pos = (row, col)
            if pos in all_positions:
                errors.append(f"{label} unit {uid}: position {pos} already occupied")
            all_positions.add(pos)

            utype = u.get("type")
            if utype not in get_all_unit_stats():
                errors.append(f"{label} unit {uid}: unknown type '{utype}'")

    return errors
